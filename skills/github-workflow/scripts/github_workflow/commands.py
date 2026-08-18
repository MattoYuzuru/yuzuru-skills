"""Coarse-grained GitHub workflow command implementations."""

from __future__ import annotations

import json
import random
import re
import subprocess
import sys
import time
import urllib.parse
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from .client import GitHubClient, Response
from .errors import GitHubError
from .graphql import (
    ADD_PROJECT_ITEM,
    PR_REVIEW_STATE,
    PROJECT_FIELDS_ORGANIZATION,
    PROJECT_FIELDS_USER,
    PROJECT_ID_ORGANIZATION,
    PROJECT_ID_USER,
    PROJECT_ITEMS_ORGANIZATION,
    PROJECT_ITEMS_USER,
    PROJECT_LIST_ORGANIZATION,
    PROJECT_LIST_USER,
    PROJECT_READ_ORGANIZATION,
    PROJECT_READ_USER,
    PROJECT_VIEWS_ORGANIZATION,
    PROJECT_VIEWS_USER,
    SET_PROJECT_FIELD,
)
from .project_targets import ProjectTarget, resolve_project_target
from .targets import RepositoryTarget, git_remote_urls, parse_repository, redact_url


TERMINAL_CONCLUSIONS = {
    "success", "failure", "cancelled", "skipped", "timed_out", "action_required", "neutral", "stale"
}
FAILED_CONCLUSIONS = {"failure", "cancelled", "timed_out", "action_required", "stale"}


def _repo_path(target: RepositoryTarget, suffix: str = "") -> str:
    owner = urllib.parse.quote(target.owner, safe="")
    repo = urllib.parse.quote(target.repo, safe="")
    return f"/repos/{owner}/{repo}{suffix}"


def _issue_path(target: RepositoryTarget, number: int) -> str:
    return _repo_path(target, f"/issues/{number}")


def _pr_path(target: RepositoryTarget, number: int) -> str:
    return _repo_path(target, f"/pulls/{number}")


def _select(value: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: value.get(field) for field in fields}


def _bounded_review_files(files: list[dict[str, Any]], max_bytes: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Keep file metadata while bounding aggregate UTF-8 patch content."""
    remaining = max_bytes
    used = 0
    returned: list[dict[str, Any]] = []
    truncated_files = 0
    omitted_patch_files = 0
    for item in files:
        normalized = _select(
            item, ("sha", "filename", "status", "additions", "deletions", "changes", "patch", "blob_url"),
        )
        patch = normalized.get("patch")
        if isinstance(patch, str):
            encoded = patch.encode("utf-8")
            if remaining <= 0:
                normalized["patch"] = None
                normalized["patch_omitted"] = True
                omitted_patch_files += 1
            elif len(encoded) > remaining:
                normalized["patch"] = encoded[:remaining].decode("utf-8", errors="ignore")
                normalized["patch_truncated"] = True
                truncated_files += 1
                used += len(normalized["patch"].encode("utf-8"))
                remaining = 0
            else:
                remaining -= len(encoded)
                used += len(encoded)
        returned.append(normalized)
    return returned, {
        "max_patch_bytes": max_bytes,
        "returned_patch_bytes": used,
        "truncated_patch_files": truncated_files,
        "omitted_patch_files": omitted_patch_files,
        "truncated": bool(truncated_files or omitted_patch_files),
    }


def _user(value: Any) -> str | None:
    return value.get("login") if isinstance(value, dict) else None


def _names(values: Any, field: str = "name") -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(item.get(field)) for item in values if isinstance(item, dict) and item.get(field) is not None]


def normalize_repo(value: dict[str, Any]) -> dict[str, Any]:
    return {
        **_select(value, (
            "id", "node_id", "full_name", "private", "visibility", "description", "homepage",
            "topics", "default_branch", "has_issues", "open_issues_count", "archived", "disabled",
            "fork", "html_url", "created_at", "updated_at", "pushed_at",
        )),
        "owner": _user(value.get("owner")),
        "permissions": value.get("permissions"),
    }


def normalize_issue(value: dict[str, Any]) -> dict[str, Any]:
    return {
        **_select(value, (
            "id", "node_id", "number", "title", "body", "state", "state_reason", "locked",
            "comments", "created_at", "updated_at", "closed_at", "html_url",
        )),
        "author": _user(value.get("user")),
        "assignees": _names(value.get("assignees"), "login"),
        "labels": _names(value.get("labels")),
        "milestone": value.get("milestone", {}).get("title") if isinstance(value.get("milestone"), dict) else None,
        "is_pull_request": "pull_request" in value,
    }


def normalize_pr(value: dict[str, Any]) -> dict[str, Any]:
    return {
        **_select(value, (
            "id", "node_id", "number", "title", "body", "state", "draft", "locked",
            "mergeable", "mergeable_state", "merged", "merge_commit_sha", "commits", "additions",
            "deletions", "changed_files", "created_at", "updated_at", "closed_at", "merged_at", "html_url",
        )),
        "author": _user(value.get("user")),
        "assignees": _names(value.get("assignees"), "login"),
        "labels": _names(value.get("labels")),
        "milestone": value.get("milestone", {}).get("title") if isinstance(value.get("milestone"), dict) else None,
        "head": _select(value.get("head", {}), ("ref", "sha", "label")),
        "base": _select(value.get("base", {}), ("ref", "sha", "label")),
    }


def normalize_run(value: dict[str, Any]) -> dict[str, Any]:
    return _select(value, (
        "id", "name", "display_title", "event", "status", "conclusion", "workflow_id", "run_number",
        "run_attempt", "head_branch", "head_sha", "created_at", "updated_at", "run_started_at", "html_url",
        "jobs_url", "logs_url",
    ))


def normalize_job(value: dict[str, Any], *, include_steps: bool = True) -> dict[str, Any]:
    result = _select(value, (
        "id", "run_id", "run_attempt", "name", "status", "conclusion", "started_at", "completed_at", "html_url",
    ))
    if include_steps:
        result["steps"] = [
            _select(step, ("number", "name", "status", "conclusion", "started_at", "completed_at"))
            for step in value.get("steps", []) if isinstance(step, dict)
        ]
    return result


def read_body(args: Any) -> str | None:
    body = getattr(args, "body", None)
    body_file = getattr(args, "body_file", None)
    if body is not None and body_file is not None:
        raise GitHubError("use either --body or --body-file, not both", kind="validation")
    if body_file == "-":
        return sys.stdin.read()
    if body_file:
        path = Path(body_file).expanduser()
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise GitHubError(f"cannot read body file: {exc}", kind="validation") from exc
    return body


def require_token(client: GitHubClient) -> None:
    if not client.token:
        raise GitHubError("this operation requires a GitHub token", kind="auth")


def mutation(
    client: GitHubClient,
    args: Any,
    target: RepositoryTarget,
    method: str,
    path: str,
    payload: Any,
    *,
    effect: str = "write",
    exact_target: str | None = None,
) -> tuple[Any, Response | None]:
    preview = {
        "dry_run": True,
        "effect": effect,
        "method": method,
        "endpoint": path,
        "payload": payload,
        "exact_target": exact_target or target.full_name,
    }
    if getattr(args, "dry_run", False):
        return preview, None
    if effect == "destructive":
        if not getattr(args, "confirm_destructive", False):
            raise GitHubError("destructive operation requires --confirm-destructive", kind="validation")
        if getattr(args, "confirm_target", None) != exact_target:
            raise GitHubError(f"--confirm-target must equal {exact_target}", kind="validation")
    elif not getattr(args, "confirm_write", False):
        raise GitHubError("write operation requires --confirm-write", kind="validation")
    require_token(client)
    response = client.request(method, path, payload=payload)
    return response.data, response


def resolve_milestone(client: GitHubClient, target: RepositoryTarget, value: str | None) -> int | None:
    if value is None:
        return None
    if value.casefold() in {"none", "null"}:
        return None
    if value.isdigit():
        return int(value)
    milestones, _ = client.paginate(_repo_path(target, "/milestones"), query={"state": "all"}, limit=100)
    matches = [item for item in milestones if str(item.get("title", "")).casefold() == value.casefold()]
    if len(matches) != 1:
        raise GitHubError(f"milestone title must match exactly once: {value}", kind="validation")
    return int(matches[0]["number"])


def validate_issue_metadata(
    client: GitHubClient,
    target: RepositoryTarget,
    assignees: list[str] | None,
    labels: list[str] | None,
) -> None:
    if assignees is not None and len(assignees) > 10:
        raise GitHubError("at most 10 assignees may be supplied", kind="validation")
    if labels is not None and len(labels) > 20:
        raise GitHubError("at most 20 labels may be supplied", kind="validation")
    for assignee in assignees or []:
        encoded = urllib.parse.quote(assignee, safe="")
        try:
            client.request("GET", _repo_path(target, f"/assignees/{encoded}"))
        except GitHubError as exc:
            if exc.kind in {"not-found", "validation"}:
                raise GitHubError(f"user cannot be assigned to this repository: {assignee}", kind="validation") from None
            raise
    for label in labels or []:
        encoded = urllib.parse.quote(label, safe="")
        try:
            client.request("GET", _repo_path(target, f"/labels/{encoded}"))
        except GitHubError as exc:
            if exc.kind == "not-found":
                raise GitHubError(f"repository label does not exist: {label}", kind="validation") from None
            raise


def normalize_topic(value: str) -> str:
    topic = re.sub(r"[^a-z0-9-]+", "-", value.strip().lower().replace("_", "-"))
    return re.sub(r"-+", "-", topic).strip("-")


def validate_pr_head(client: GitHubClient, target: RepositoryTarget, head: str) -> tuple[str, str]:
    if ":" in head:
        owner, branch = head.split(":", 1)
    else:
        owner, branch = target.owner, head
    if not owner or not branch:
        raise GitHubError("pull request head must be branch or owner:branch", kind="validation")
    source = RepositoryTarget(target.host, owner, target.repo)
    encoded = urllib.parse.quote(branch, safe="")
    try:
        client.request("GET", _repo_path(source, f"/branches/{encoded}"))
    except GitHubError as exc:
        if exc.kind == "not-found":
            raise GitHubError(f"pull request head branch is not pushed: {head}", kind="validation") from None
        raise
    return owner, branch


def repository_command(command: str, args: Any, client: GitHubClient, target: RepositoryTarget) -> tuple[Any, Response | None]:
    if command == "repo-info":
        response = client.request("GET", _repo_path(target))
        return normalize_repo(response.data), response
    if command == "repo-languages":
        response = client.request("GET", _repo_path(target, "/languages"))
        languages = response.data if isinstance(response.data, dict) else {}
        total = sum(value for value in languages.values() if isinstance(value, int))
        data = [
            {"language": name, "bytes": count, "percent": round(count * 100 / total, 2) if total else 0.0}
            for name, count in sorted(languages.items(), key=lambda item: item[1], reverse=True)
        ]
        return {"total_bytes": total, "languages": data}, response
    if command == "repo-context":
        repo_response = client.request("GET", _repo_path(target))
        lang_response = client.request("GET", _repo_path(target, "/languages"))
        remotes = {name: redact_url(url) for name, url in git_remote_urls(args.cwd).items()}
        branch = _git(["branch", "--show-current"], args.cwd, allow_failure=True).strip() or None
        status = _git(["status", "--short", "--branch"], args.cwd, allow_failure=True).splitlines()
        return {
            "repository": normalize_repo(repo_response.data),
            "languages": lang_response.data,
            "local": {"cwd": str(Path(args.cwd).resolve()), "branch": branch, "remotes": remotes, "status": status[:100]},
        }, repo_response
    if command == "repo-update-about":
        payload = {key: value for key, value in {"description": args.description, "homepage": args.homepage}.items() if value is not None}
        if not payload:
            raise GitHubError("provide --description and/or --homepage", kind="validation")
        data, response = mutation(client, args, target, "PATCH", _repo_path(target), payload)
        if response:
            verified = client.request("GET", _repo_path(target))
            return normalize_repo(verified.data), verified
        return data, response
    if command == "repo-topics-set":
        topics = [normalize_topic(value) for value in args.topics]
        topics = list(dict.fromkeys(topic for topic in topics if topic))
        if len(topics) > 20:
            raise GitHubError("GitHub supports at most 20 repository topics", kind="validation")
        data, response = mutation(client, args, target, "PUT", _repo_path(target, "/topics"), {"names": topics})
        if response:
            verified = client.request("GET", _repo_path(target, "/topics"))
            return verified.data, verified
        return data, response
    raise GitHubError(f"unsupported repository command: {command}", kind="validation")


def issue_command(command: str, args: Any, client: GitHubClient, target: RepositoryTarget) -> tuple[Any, Response | None]:
    if command == "issue-search":
        query = args.query.strip()
        repo_qualifiers = re.findall(r"(?:^|\s)repo:([^\s]+)", query, re.I)
        if repo_qualifiers and any(value.casefold() != target.full_name.casefold() for value in repo_qualifiers):
            raise GitHubError("issue search repo qualifier must match the resolved target", kind="validation")
        if not repo_qualifiers:
            query += f" repo:{target.full_name}"
        if not re.search(r"(?:^|\s)is:(?:issue|pr)(?:\s|$)", query, re.I):
            query += " is:issue"
        items, response = client.paginate("/search/issues", query={"q": query}, limit=args.limit, item_key="items")
        return {"query": query, "items": [normalize_issue(item) for item in items if "pull_request" not in item]}, response
    if command == "issue-list":
        query = {"state": args.state, "sort": args.sort, "direction": args.direction}
        items, response = client.paginate(_repo_path(target, "/issues"), query=query, limit=args.limit)
        return [normalize_issue(item) for item in items if "pull_request" not in item], response
    if command == "issue-read":
        response = client.request("GET", _issue_path(target, args.number))
        if "pull_request" in response.data:
            raise GitHubError(f"#{args.number} is a pull request, not an issue", kind="validation")
        return normalize_issue(response.data), response
    if command == "label-list":
        items, response = client.paginate(_repo_path(target, "/labels"), limit=args.limit)
        return [_select(item, ("id", "name", "color", "description", "default")) for item in items], response
    if command == "milestone-list":
        items, response = client.paginate(_repo_path(target, "/milestones"), query={"state": args.state}, limit=args.limit)
        return [_select(item, ("id", "number", "title", "description", "state", "open_issues", "closed_issues", "due_on", "html_url")) for item in items], response
    if command in {"issue-create", "issue-update"}:
        body = read_body(args)
        payload: dict[str, Any] = {}
        for name in ("title", "assignees", "labels"):
            value = getattr(args, name, None)
            if value is not None:
                payload[name] = value
        if body is not None:
            payload["body"] = body
        milestone = getattr(args, "milestone", None)
        if milestone is not None:
            payload["milestone"] = resolve_milestone(client, target, milestone)
        validate_issue_metadata(client, target, payload.get("assignees"), payload.get("labels"))
        if command == "issue-create" and not payload.get("title"):
            raise GitHubError("issue-create requires --title", kind="validation")
        if command == "issue-update" and not payload:
            raise GitHubError("issue-update requires at least one changed field", kind="validation")
        path = _repo_path(target, "/issues") if command == "issue-create" else _issue_path(target, args.number)
        method = "POST" if command == "issue-create" else "PATCH"
        data, response = mutation(client, args, target, method, path, payload)
        if response:
            number = data.get("number") if isinstance(data, dict) else getattr(args, "number", None)
            verified = client.request("GET", _issue_path(target, int(number)))
            return normalize_issue(verified.data), verified
        return data, response
    if command == "issue-close":
        exact = f"{target.full_name}#{args.number}"
        payload = {"state": "closed", "state_reason": args.reason}
        data, response = mutation(client, args, target, "PATCH", _issue_path(target, args.number), payload, effect="destructive", exact_target=exact)
        if response:
            verified = client.request("GET", _issue_path(target, args.number))
            return normalize_issue(verified.data), verified
        return data, response
    raise GitHubError(f"unsupported issue command: {command}", kind="validation")


def _project(data: Any, owner_type: str) -> Any:
    if not isinstance(data, dict):
        return None
    return data.get("organization" if owner_type == "organization" else "user")


def _project_id(client: GitHubClient, owner: str, owner_type: str, number: int) -> tuple[str, Response]:
    document = PROJECT_ID_ORGANIZATION if owner_type == "organization" else PROJECT_ID_USER
    response = client.graphql(document, {"owner": owner, "number": number})
    container = _project(response.data, owner_type)
    project = container.get("projectV2") if isinstance(container, dict) else None
    if not isinstance(project, dict) or not project.get("id"):
        raise GitHubError(f"Project V2 {owner}#{number} was not found", kind="not-found")
    return str(project["id"]), response


def _project_node(response: Response, project: ProjectTarget) -> dict[str, Any]:
    container = _project(response.data, project.owner_type)
    value = container.get("projectV2") if isinstance(container, dict) else None
    if not isinstance(value, dict):
        raise GitHubError(f"Project V2 {project.owner}#{project.number} was not found", kind="not-found")
    return value


def _project_document(project: ProjectTarget, user: str, organization: str) -> str:
    return organization if project.owner_type == "organization" else user


def _project_fields(client: GitHubClient, project: ProjectTarget) -> tuple[list[dict[str, Any]], Response]:
    document = _project_document(project, PROJECT_FIELDS_USER, PROJECT_FIELDS_ORGANIZATION)
    response = client.graphql(
        document,
        {"owner": project.owner, "number": project.number, "first": 100},
    )
    connection = _project_node(response, project).get("fields", {})
    nodes = connection.get("nodes", []) if isinstance(connection, dict) else []
    return [item for item in nodes if isinstance(item, dict)], response


def _normalize_project_item(value: dict[str, Any]) -> dict[str, Any]:
    content = value.get("content") if isinstance(value.get("content"), dict) else {}
    repository = content.get("repository") if isinstance(content.get("repository"), dict) else {}
    author = content.get("author") if isinstance(content.get("author"), dict) else {}
    fields: dict[str, Any] = {}
    field_ids: dict[str, Any] = {}
    nodes = value.get("fieldValues", {}).get("nodes", []) if isinstance(value.get("fieldValues"), dict) else []
    for field_value in nodes:
        if not isinstance(field_value, dict):
            continue
        field = field_value.get("field") if isinstance(field_value.get("field"), dict) else {}
        name = field.get("name")
        field_id = field.get("id")
        scalar = next(
            (
                field_value.get(key)
                for key in ("name", "text", "number", "date", "title")
                if field_value.get(key) is not None
            ),
            None,
        )
        if scalar is None and isinstance(field_value.get("repository"), dict):
            scalar = field_value["repository"].get("nameWithOwner")
        if scalar is None and isinstance(field_value.get("milestone"), dict):
            scalar = field_value["milestone"].get("title")
        if scalar is None:
            for plural, label in (("labels", "name"), ("users", "login")):
                connection = field_value.get(plural)
                if isinstance(connection, dict):
                    scalar = [
                        node.get(label) for node in connection.get("nodes", [])
                        if isinstance(node, dict) and node.get(label)
                    ]
                    break
        if name:
            fields[str(name)] = scalar
        if field_id:
            field_ids[str(field_id)] = scalar
    return {
        "item_id": value.get("id"),
        "archived": value.get("isArchived"),
        "item_created_at": value.get("createdAt"),
        "item_updated_at": value.get("updatedAt"),
        "content": {
            "type": content.get("__typename") or "Redacted",
            "id": content.get("id"),
            "number": content.get("number"),
            "title": content.get("title"),
            "body": content.get("body") if content.get("__typename") == "DraftIssue" else None,
            "url": content.get("url"),
            "state": content.get("state"),
            "draft": content.get("isDraft"),
            "repository": repository.get("nameWithOwner"),
            "author": author.get("login"),
            "created_at": content.get("createdAt"),
            "updated_at": content.get("updatedAt"),
            "closed_at": content.get("closedAt"),
            "merged_at": content.get("mergedAt"),
        },
        "fields": fields,
        "fields_by_id": field_ids,
    }


def _project_items_page(
    client: GitHubClient,
    project: ProjectTarget,
    *,
    first: int,
    after: str | None,
    query: str | None,
) -> tuple[dict[str, Any], Response]:
    if not 1 <= first <= 100:
        raise GitHubError("project page size must be between 1 and 100", kind="validation")
    document = _project_document(project, PROJECT_ITEMS_USER, PROJECT_ITEMS_ORGANIZATION)
    response = client.graphql(
        document,
        {"owner": project.owner, "number": project.number, "first": first, "after": after, "query": query},
    )
    connection = _project_node(response, project).get("items", {})
    if not isinstance(connection, dict):
        raise GitHubError("Project V2 items response is invalid", kind="graphql")
    return connection, response


def _archive_matches(item: dict[str, Any], mode: str) -> bool:
    if mode == "all":
        return True
    return bool(item.get("archived")) == (mode == "archived")


def _match_named(values: list[dict[str, Any]], name: str, label: str) -> dict[str, Any]:
    matches = [item for item in values if str(item.get("name", "")).casefold() == name.casefold()]
    if len(matches) != 1:
        detail = "not found" if not matches else "ambiguous"
        raise GitHubError(f"{label} {name!r} is {detail}", kind="validation")
    return matches[0]


def project_command(command: str, args: Any, client: GitHubClient, target: RepositoryTarget | None) -> tuple[Any, Response | None]:
    if command == "project-list":
        if not 1 <= args.limit <= 100:
            raise GitHubError("--limit must be between 1 and 100", kind="validation")
        document = PROJECT_LIST_ORGANIZATION if args.owner_type == "organization" else PROJECT_LIST_USER
        response = client.graphql(document, {"owner": args.owner, "first": args.limit})
        container = _project(response.data, args.owner_type)
        projects = container.get("projectsV2", {}).get("nodes", []) if isinstance(container, dict) else []
        return projects, response
    project = resolve_project_target(args, expected_host=getattr(args, "host", "github.com"))
    if command == "project-read":
        document = _project_document(project, PROJECT_READ_USER, PROJECT_READ_ORGANIZATION)
        response = client.graphql(document, {"owner": project.owner, "number": project.number})
        value = _project_node(response, project)
        return {
            **_select(value, ("id", "number", "title", "shortDescription", "readme", "url", "public", "closed", "createdAt", "updatedAt")),
            "owner": project.owner,
            "owner_type": project.owner_type,
            "view_number": project.view_number,
            "item_count": value.get("items", {}).get("totalCount"),
            "field_count": value.get("fields", {}).get("totalCount"),
            "view_count": value.get("views", {}).get("totalCount"),
        }, response
    if command == "project-field-list":
        fields, response = _project_fields(client, project)
        return fields, response
    if command == "project-view-list":
        document = _project_document(project, PROJECT_VIEWS_USER, PROJECT_VIEWS_ORGANIZATION)
        response = client.graphql(
            document,
            {"owner": project.owner, "number": project.number, "first": args.limit},
        )
        connection = _project_node(response, project).get("views", {})
        return connection.get("nodes", []) if isinstance(connection, dict) else [], response
    if command == "project-count":
        connection, response = _project_items_page(
            client, project, first=1, after=None, query=args.query,
        )
        return {"project": project.label, "query": args.query, "count": connection.get("totalCount")}, response
    if command == "project-item-list":
        connection, response = _project_items_page(
            client, project, first=args.limit, after=args.after, query=args.query,
        )
        normalized = [
            _normalize_project_item(item) for item in connection.get("nodes", []) if isinstance(item, dict)
        ]
        normalized = [item for item in normalized if _archive_matches(item, args.archived)]
        page = connection.get("pageInfo", {})
        return {
            "project": project.label,
            "query": args.query,
            "total_count": connection.get("totalCount"),
            "items": normalized,
            "page_info": page,
        }, response
    if command == "project-stats":
        if not 1 <= args.scan_limit <= 10000:
            raise GitHubError("--scan-limit must be between 1 and 10000", kind="validation")
        items: list[dict[str, Any]] = []
        cursor: str | None = None
        total_count: int | None = None
        response: Response | None = None
        while len(items) < args.scan_limit:
            connection, response = _project_items_page(
                client,
                project,
                first=min(100, args.scan_limit - len(items)),
                after=cursor,
                query=args.query,
            )
            total_count = connection.get("totalCount")
            items.extend(
                _normalize_project_item(item)
                for item in connection.get("nodes", []) if isinstance(item, dict)
            )
            page = connection.get("pageInfo", {})
            cursor = page.get("endCursor")
            if not page.get("hasNextPage") or not cursor:
                break
        items = [item for item in items if _archive_matches(item, args.archived)]
        counts: Counter[str] = Counter()
        for item in items:
            content = item["content"]
            if args.group_by == "content-type":
                value = content.get("type")
            elif args.group_by == "repository":
                value = content.get("repository")
            elif args.group_by == "created":
                created = content.get("created_at") or item.get("item_created_at") or ""
                value = created[:10] if args.bucket == "day" else created[:7]
                if args.bucket == "week" and len(created) >= 10:
                    from datetime import date
                    parsed = date.fromisoformat(created[:10])
                    iso = parsed.isocalendar()
                    value = f"{iso.year}-W{iso.week:02d}"
            else:
                value = item["fields"].get(args.group_by)
            if isinstance(value, list):
                counts.update(str(part) for part in value)
            else:
                counts[str(value) if value not in {None, ""} else "(none)"] += 1
        if args.group_by not in {"content-type", "repository", "created"}:
            fields, _ = _project_fields(client, project)
            field = _match_named(fields, args.group_by, "project field")
            for option in field.get("options", []) or []:
                if isinstance(option, dict) and option.get("name"):
                    counts.setdefault(str(option["name"]), 0)
        exact = total_count is not None and len(items) >= total_count
        return {
            "project": project.label,
            "query": args.query,
            "group_by": args.group_by,
            "bucket": args.bucket if args.group_by == "created" else None,
            "total_count": total_count,
            "scanned": len(items),
            "exact": exact,
            "counts": dict(sorted(counts.items())),
        }, response
    if command == "project-add-item":
        project_id, lookup = _project_id(client, project.owner, project.owner_type, project.number)
        if args.node_id:
            content_id = args.node_id
        else:
            if target is None:
                raise GitHubError("project-add-item with issue/pull number requires --repo", kind="validation")
            path = _pr_path(target, args.pull_number) if args.pull_number else _issue_path(target, args.issue_number)
            content = client.request("GET", path)
            content_id = content.data.get("node_id")
        if not content_id:
            raise GitHubError("issue or pull request node ID was not found", kind="github")
        preview = {"project_id": project_id, "content_id": content_id}
        if args.dry_run:
            return {"dry_run": True, "effect": "write", **preview}, lookup
        if not args.confirm_write:
            raise GitHubError("write operation requires --confirm-write", kind="validation")
        require_token(client)
        response = client.graphql(ADD_PROJECT_ITEM, {"project": project_id, "content": content_id}, mutation=True)
        return response.data.get("addProjectV2ItemById", {}).get("item"), response
    if command == "project-field-set":
        project_id = args.project_id
        field_id = args.field_id
        resolved_value = args.value
        resolved_type: str | None = None
        if not project_id:
            project_id, _ = _project_id(client, project.owner, project.owner_type, project.number)
        if args.field:
            fields, _ = _project_fields(client, project)
            field = _match_named(fields, args.field, "project field")
            field_id = field.get("id")
            resolved_type = field.get("dataType")
            if resolved_value is None:
                raise GitHubError("--field requires --value", kind="validation")
            if resolved_type == "SINGLE_SELECT":
                option = _match_named(field.get("options", []), resolved_value, "field option")
                args.single_select_option_id = option.get("id")
            elif resolved_type == "ITERATION":
                configuration = field.get("configuration", {})
                options = [
                    *configuration.get("iterations", []),
                    *configuration.get("completedIterations", []),
                ] if isinstance(configuration, dict) else []
                option = _match_named(options, resolved_value, "iteration")
                args.iteration_id = option.get("id")
            elif resolved_type == "NUMBER":
                try:
                    args.value_number = float(resolved_value)
                except ValueError as exc:
                    raise GitHubError("NUMBER field value must be numeric", kind="validation") from exc
            elif resolved_type == "DATE":
                args.date = resolved_value
            elif resolved_type == "TEXT":
                args.text = resolved_value
            else:
                raise GitHubError(f"field type {resolved_type} is not writable by this command", kind="validation")
        values = {
            "text": args.text,
            "number": args.value_number,
            "date": args.date,
            "singleSelectOptionId": args.single_select_option_id,
            "iterationId": args.iteration_id,
        }
        selected = {key: value for key, value in values.items() if value is not None}
        if len(selected) != 1:
            raise GitHubError("provide exactly one project field value", kind="validation")
        if not field_id:
            raise GitHubError("provide --field-id or --field", kind="validation")
        variables = {"project": project_id, "item": args.item_id, "field": field_id, "value": selected}
        if args.dry_run:
            return {"dry_run": True, "effect": "write", "variables": variables}, None
        if not args.confirm_write:
            raise GitHubError("write operation requires --confirm-write", kind="validation")
        require_token(client)
        response = client.graphql(SET_PROJECT_FIELD, variables, mutation=True)
        return response.data.get("updateProjectV2ItemFieldValue", {}).get("projectV2Item"), response
    raise GitHubError(f"unsupported project command: {command}", kind="validation")


def _git(arguments: list[str], cwd: str, *, allow_failure: bool = False) -> str:
    try:
        result = subprocess.run(
            ["git", *arguments], cwd=cwd, capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GitHubError(f"git command failed: {exc}", kind="validation") from exc
    if result.returncode and not allow_failure:
        message = result.stderr.strip() or "git command failed"
        raise GitHubError(message[:1000], kind="validation")
    return result.stdout


def _normalize_review(value: dict[str, Any]) -> dict[str, Any]:
    return {
        **_select(value, ("id", "node_id", "state", "body", "commit_id", "submitted_at", "html_url")),
        "reviewer": _user(value.get("user")),
    }


def _pr_rules(
    client: GitHubClient,
    target: RepositoryTarget,
    pr: dict[str, Any],
) -> tuple[dict[str, Any], Response]:
    base = pr.get("base", {}).get("ref")
    if not base:
        raise GitHubError("pull request base branch is missing", kind="github")
    encoded = urllib.parse.quote(str(base), safe="")
    rules_response = client.request("GET", _repo_path(target, f"/rules/branches/{encoded}"))
    repository = client.request("GET", _repo_path(target))
    rules = rules_response.data if isinstance(rules_response.data, list) else []
    required_checks: list[str] = []
    strict = False
    review_threads_required = False
    merge_queue_required = False
    pull_request_parameters: dict[str, Any] = {}
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        parameters = rule.get("parameters") if isinstance(rule.get("parameters"), dict) else {}
        if rule.get("type") == "required_status_checks":
            required_checks.extend(
                str(item.get("context"))
                for item in parameters.get("required_status_checks", [])
                if isinstance(item, dict) and item.get("context")
            )
            strict = bool(parameters.get("strict_required_status_checks_policy"))
        elif rule.get("type") == "pull_request":
            pull_request_parameters.update(parameters)
        elif rule.get("type") == "required_review_thread_resolution":
            review_threads_required = True
        elif rule.get("type") == "merge_queue":
            merge_queue_required = True
    allowed_methods = [
        method for method, key in (
            ("merge", "allow_merge_commit"),
            ("squash", "allow_squash_merge"),
            ("rebase", "allow_rebase_merge"),
        ) if repository.data.get(key)
    ]
    review_threads_required = review_threads_required or bool(
        pull_request_parameters.get("required_review_thread_resolution")
    )
    rule_methods = pull_request_parameters.get("allowed_merge_methods")
    if isinstance(rule_methods, list) and rule_methods:
        allowed_methods = [method for method in allowed_methods if method in rule_methods]
    return {
        "base": base,
        "active_rules": rules,
        "required_checks": sorted(set(required_checks)),
        "strict_required_checks": strict,
        "review_threads_required": review_threads_required,
        "merge_queue_required": merge_queue_required,
        "pull_request": pull_request_parameters,
        "allowed_merge_methods": allowed_methods,
    }, rules_response


def _pr_readiness(
    client: GitHubClient,
    target: RepositoryTarget,
    number: int,
    method: str,
) -> tuple[dict[str, Any], Response]:
    pr_response = client.request("GET", _pr_path(target, number))
    pr = pr_response.data
    sha = pr.get("head", {}).get("sha")
    if not sha:
        raise GitHubError("pull request head SHA is missing", kind="github")
    rules, _ = _pr_rules(client, target, pr)
    checks, _ = _collect_checks(client, target, sha)
    graph = client.graphql(
        PR_REVIEW_STATE,
        {"owner": target.owner, "repo": target.repo, "number": number, "first": 100},
    )
    repository = graph.data.get("repository") if isinstance(graph.data, dict) else None
    review = repository.get("pullRequest") if isinstance(repository, dict) else None
    if not isinstance(review, dict):
        raise GitHubError("pull request review state was not found", kind="graphql")
    threads = review.get("reviewThreads", {})
    thread_nodes = threads.get("nodes", []) if isinstance(threads, dict) else []
    unresolved = sum(1 for item in thread_nodes if isinstance(item, dict) and not item.get("isResolved"))

    check_states: dict[str, bool] = {}
    optional_failures: list[str] = []
    for item in checks["check_runs"]:
        name = item.get("name")
        success = item.get("status") == "completed" and item.get("conclusion") in {"success", "neutral", "skipped"}
        if name and name not in check_states:
            check_states[str(name)] = success
        if name and not success:
            optional_failures.append(str(name))
    for item in checks["statuses"]:
        name = item.get("context")
        success = item.get("state") == "success"
        if name and name not in check_states:
            check_states[str(name)] = success
        if name and not success:
            optional_failures.append(str(name))
    required = rules["required_checks"]
    missing = [name for name in required if name not in check_states]
    failing = [name for name in required if name in check_states and not check_states[name]]
    optional_failures = sorted(set(optional_failures) - set(required))

    blockers: list[dict[str, Any]] = []
    if pr.get("state") != "open" or pr.get("merged"):
        blockers.append({"kind": "state", "detail": "pull request is not open and unmerged"})
    if pr.get("draft"):
        blockers.append({"kind": "draft", "detail": "pull request is a draft"})
    if pr.get("mergeable") is False or review.get("mergeStateStatus") == "DIRTY":
        blockers.append({"kind": "conflict", "detail": "pull request has merge conflicts"})
    if review.get("reviewDecision") in {"CHANGES_REQUESTED", "REVIEW_REQUIRED"}:
        blockers.append({"kind": "review", "detail": review.get("reviewDecision")})
    if rules["review_threads_required"] and unresolved:
        blockers.append({"kind": "review-threads", "detail": f"{unresolved} unresolved thread(s)"})
    if missing:
        blockers.append({"kind": "required-checks-missing", "contexts": missing})
    if failing:
        blockers.append({"kind": "required-checks-non-green", "contexts": failing})
    if rules["strict_required_checks"] and review.get("mergeStateStatus") == "BEHIND":
        blockers.append({"kind": "behind", "detail": "strict rules require an up-to-date base"})
    if method not in rules["allowed_merge_methods"]:
        blockers.append({"kind": "merge-method", "detail": f"{method} is not enabled"})
    if rules["merge_queue_required"]:
        blockers.append({"kind": "merge-queue", "detail": "branch rules require merge queue"})
    unknown = (
        pr.get("mergeable") is None
        or review.get("mergeStateStatus") == "UNKNOWN"
        or bool(threads.get("pageInfo", {}).get("hasNextPage"))
        or graph.partial
    )
    ready: bool | None = None if unknown else not blockers
    return {
        "ready": ready,
        "head_sha": sha,
        "base": pr.get("base", {}).get("ref"),
        "mergeable": pr.get("mergeable"),
        "merge_state_status": review.get("mergeStateStatus"),
        "review_decision": review.get("reviewDecision"),
        "unresolved_review_threads": unresolved,
        "required_checks": required,
        "required_checks_missing": missing,
        "required_checks_non_green": failing,
        "optional_non_green_checks": optional_failures,
        "strict_required_checks": rules["strict_required_checks"],
        "allowed_merge_methods": rules["allowed_merge_methods"],
        "requested_merge_method": method,
        "merge_queue_required": rules["merge_queue_required"],
        "blockers": blockers,
        "warnings": ["optional checks are non-green"] if optional_failures else [],
    }, pr_response


def pr_command(command: str, args: Any, client: GitHubClient, target: RepositoryTarget) -> tuple[Any, Response | None]:
    if command == "pr-candidate":
        branch = _git(["branch", "--show-current"], args.cwd).strip()
        if not branch:
            raise GitHubError("detached HEAD cannot be proposed as a pull request", kind="validation")
        repo_response = client.request("GET", _repo_path(target))
        base = args.base or repo_response.data.get("default_branch")
        remotes = git_remote_urls(args.cwd)
        origin = parse_repository(remotes["origin"]) if "origin" in remotes else target
        head = f"{origin.owner}:{branch}"
        existing, _ = client.paginate(_repo_path(target, "/pulls"), query={"state": "open", "head": head, "base": base}, limit=10)
        tracking = _git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"], args.cwd, allow_failure=True).strip() or None
        return {
            "head": head,
            "base": base,
            "branch": branch,
            "tracking_branch": tracking,
            "already_open": [normalize_pr(item) for item in existing],
            "suggested": not existing and branch != base,
        }, repo_response
    if command == "pr-list":
        query = {"state": args.state, "sort": args.sort, "direction": args.direction}
        items, response = client.paginate(_repo_path(target, "/pulls"), query=query, limit=args.limit)
        return [normalize_pr(item) for item in items], response
    if command == "pr-read":
        response = client.request("GET", _pr_path(target, args.number))
        return normalize_pr(response.data), response
    if command == "pr-files":
        items, response = client.paginate(_pr_path(target, args.number) + "/files", limit=args.limit)
        return [_select(item, ("sha", "filename", "status", "additions", "deletions", "changes", "blob_url", "raw_url")) for item in items], response
    if command == "pr-checks":
        pr_response = client.request("GET", _pr_path(target, args.number))
        sha = pr_response.data.get("head", {}).get("sha")
        if not sha:
            raise GitHubError("pull request head SHA is missing", kind="github")
        return _collect_checks(client, target, sha)
    if command == "pr-reviews":
        items, response = client.paginate(_pr_path(target, args.number) + "/reviews", limit=args.limit)
        normalized = [_normalize_review(item) for item in items]
        latest: dict[str, dict[str, Any]] = {}
        for item in normalized:
            reviewer = item.get("reviewer")
            if reviewer:
                latest[str(reviewer)] = item
        return {"reviews": normalized, "latest_by_reviewer": latest}, response
    if command == "pr-rules":
        response = client.request("GET", _pr_path(target, args.number))
        rules, rules_response = _pr_rules(client, target, response.data)
        return rules, rules_response
    if command == "pr-readiness":
        return _pr_readiness(client, target, args.number, args.method)
    if command == "pr-review-context":
        if not 1 <= args.max_files <= 100:
            raise GitHubError("--max-files must be between 1 and 100", kind="validation")
        if not 1024 <= args.max_bytes <= 1048576:
            raise GitHubError("--max-bytes must be between 1024 and 1048576", kind="validation")
        pr_response = client.request("GET", _pr_path(target, args.number))
        files, _ = client.paginate(_pr_path(target, args.number) + "/files", limit=args.max_files)
        reviews, _ = client.paginate(_pr_path(target, args.number) + "/reviews", limit=100)
        readiness, _ = _pr_readiness(client, target, args.number, args.method)
        bounded_files, patch_budget = _bounded_review_files(files, args.max_bytes)
        return {
            "pull_request": normalize_pr(pr_response.data),
            "head_sha": pr_response.data.get("head", {}).get("sha"),
            "files": bounded_files,
            "patch_budget": patch_budget,
            "reviews": [_normalize_review(item) for item in reviews],
            "readiness": readiness,
            "review_contract": {
                "verdicts": ["approve", "request_changes", "comment"],
                "head_sha_must_match": True,
                "subagent_verdict_is_evidence_not_user_authorization": True,
            },
        }, pr_response
    if command == "pr-review-submit":
        current = client.request("GET", _pr_path(target, args.number))
        actual_sha = current.data.get("head", {}).get("sha")
        if actual_sha != args.expected_head_sha:
            raise GitHubError(f"expected head SHA does not match current PR head: {actual_sha}", kind="validation")
        body = read_body(args)
        if args.event in {"request-changes", "comment"} and not body:
            raise GitHubError(f"{args.event} review requires --body or --body-file", kind="validation")
        if args.event == "approve":
            viewer = client.request("GET", "/user").data.get("login")
            author = current.data.get("user", {}).get("login")
            if viewer and author and str(viewer).casefold() == str(author).casefold():
                raise GitHubError(
                    "GitHub does not allow an author to approve their own pull request; return a local approve-recommended verdict instead",
                    kind="validation",
                )
        payload: dict[str, Any] = {
            "event": args.event.replace("-", "_").upper(),
            "commit_id": args.expected_head_sha,
        }
        if body is not None:
            payload["body"] = body
        data, response = mutation(
            client, args, target, "POST", _pr_path(target, args.number) + "/reviews", payload,
        )
        if response:
            reviews, verified = client.paginate(_pr_path(target, args.number) + "/reviews", limit=100)
            return {"submitted": _normalize_review(data), "reviews": [_normalize_review(item) for item in reviews]}, verified
        return data, response
    if command == "pr-create":
        body = read_body(args)
        head_owner, head_branch = validate_pr_head(client, target, args.head)
        base = args.base
        if not base:
            base = client.request("GET", _repo_path(target)).data.get("default_branch")
        if head_owner.casefold() == target.owner.casefold() and head_branch == base:
            raise GitHubError("pull request head and base must differ", kind="validation")
        existing, _ = client.paginate(_repo_path(target, "/pulls"), query={"state": "open", "head": args.head, "base": base}, limit=10)
        if existing:
            raise GitHubError(f"an open pull request already exists: {existing[0].get('html_url')}", kind="validation")
        payload = {"title": args.title, "head": args.head, "base": base, "draft": args.draft, "maintainer_can_modify": args.maintainer_can_modify}
        if body is not None:
            payload["body"] = body
        data, response = mutation(client, args, target, "POST", _repo_path(target, "/pulls"), payload)
        if response:
            verified = client.request("GET", _pr_path(target, int(data["number"])))
            return normalize_pr(verified.data), verified
        return data, response
    if command == "pr-metadata-update":
        payload: dict[str, Any] = {}
        if args.assignees is not None:
            payload["assignees"] = args.assignees
        if args.labels is not None:
            payload["labels"] = args.labels
        if args.milestone is not None:
            payload["milestone"] = resolve_milestone(client, target, args.milestone)
        if not payload:
            raise GitHubError("pr-metadata-update requires assignees, labels, or milestone", kind="validation")
        validate_issue_metadata(client, target, payload.get("assignees"), payload.get("labels"))
        data, response = mutation(client, args, target, "PATCH", _issue_path(target, args.number), payload)
        if response:
            verified = client.request("GET", _pr_path(target, args.number))
            return normalize_pr(verified.data), verified
        return data, response
    if command == "pr-update":
        body = read_body(args)
        payload = {key: value for key, value in {"title": args.title, "base": args.base, "state": args.state}.items() if value is not None}
        if body is not None:
            payload["body"] = body
        if not payload:
            raise GitHubError("pr-update requires at least one changed field", kind="validation")
        data, response = mutation(client, args, target, "PATCH", _pr_path(target, args.number), payload)
        if response:
            verified = client.request("GET", _pr_path(target, args.number))
            return normalize_pr(verified.data), verified
        return data, response
    if command == "pr-close":
        exact = f"{target.full_name}#{args.number}"
        data, response = mutation(client, args, target, "PATCH", _pr_path(target, args.number), {"state": "closed"}, effect="destructive", exact_target=exact)
        if response:
            verified = client.request("GET", _pr_path(target, args.number))
            return normalize_pr(verified.data), verified
        return data, response
    if command == "pr-merge":
        current = client.request("GET", _pr_path(target, args.number))
        actual_sha = current.data.get("head", {}).get("sha")
        if actual_sha != args.expected_head_sha:
            raise GitHubError(f"expected head SHA does not match current PR head: {actual_sha}", kind="validation")
        readiness, _ = _pr_readiness(client, target, args.number, args.method)
        if readiness["ready"] is not True:
            raise GitHubError(
                f"pull request is not ready for direct merge: {readiness['blockers'] or 'readiness is unknown'}",
                kind="validation",
            )
        exact = f"{target.full_name}#{args.number}@{args.expected_head_sha} via {args.method}"
        payload = {"merge_method": args.method, "sha": args.expected_head_sha}
        if args.title is not None:
            payload["commit_title"] = args.title
        if args.message is not None:
            payload["commit_message"] = args.message
        data, response = mutation(client, args, target, "PUT", _pr_path(target, args.number) + "/merge", payload, effect="destructive", exact_target=exact)
        if response:
            verified = client.request("GET", _pr_path(target, args.number))
            return {"merge": data, "pull_request": normalize_pr(verified.data)}, verified
        return data, response
    if command == "branch-delete":
        _git(["check-ref-format", "--branch", args.branch], args.cwd)
        exact = f"{target.full_name}@{args.branch}"
        encoded = urllib.parse.quote(f"heads/{args.branch}", safe="/")
        return mutation(client, args, target, "DELETE", _repo_path(target, f"/git/refs/{encoded}"), None, effect="destructive", exact_target=exact)
    raise GitHubError(f"unsupported pull request command: {command}", kind="validation")


def _collect_checks(client: GitHubClient, target: RepositoryTarget, sha: str) -> tuple[dict[str, Any], Response]:
    encoded = urllib.parse.quote(sha, safe="")
    checks = client.request("GET", _repo_path(target, f"/commits/{encoded}/check-runs"), query={"per_page": 100})
    status = client.request("GET", _repo_path(target, f"/commits/{encoded}/status"))
    check_runs = [
        _select(item, ("id", "name", "status", "conclusion", "started_at", "completed_at", "html_url", "details_url"))
        for item in checks.data.get("check_runs", [])
    ]
    return {
        "head_sha": sha,
        "check_runs": check_runs,
        "combined_status": status.data.get("state"),
        "statuses": [
            _select(item, ("id", "context", "state", "description", "target_url", "created_at"))
            for item in status.data.get("statuses", [])
        ],
    }, checks


def actions_command(command: str, args: Any, client: GitHubClient, target: RepositoryTarget) -> tuple[Any, Response | None]:
    if command == "workflow-list":
        items, response = client.paginate(_repo_path(target, "/actions/workflows"), limit=args.limit, item_key="workflows")
        return [_select(item, ("id", "node_id", "name", "path", "state", "created_at", "updated_at", "html_url")) for item in items], response
    if command == "run-list":
        query = {key: value for key, value in {"branch": args.branch, "event": args.event, "status": args.status}.items() if value}
        path = _repo_path(target, f"/actions/workflows/{urllib.parse.quote(args.workflow, safe='')}/runs") if args.workflow else _repo_path(target, "/actions/runs")
        items, response = client.paginate(path, query=query, limit=args.limit, item_key="workflow_runs")
        return [normalize_run(item) for item in items], response
    if command == "run-read":
        response = client.request("GET", _repo_path(target, f"/actions/runs/{args.run_id}"))
        return normalize_run(response.data), response
    if command == "run-jobs":
        items, response = client.paginate(_repo_path(target, f"/actions/runs/{args.run_id}/jobs"), query={"filter": args.filter}, limit=args.limit, item_key="jobs")
        return [normalize_job(item) for item in items], response
    if command == "job-read":
        response = client.request("GET", _repo_path(target, f"/actions/jobs/{args.job_id}"))
        return normalize_job(response.data), response
    if command == "run-failures":
        if not 1 <= args.max_jobs <= 20:
            raise GitHubError("--max-jobs must be between 1 and 20", kind="validation")
        if not 1024 <= args.log_bytes <= 1024 * 1024:
            raise GitHubError("--log-bytes must be between 1024 and 1048576", kind="validation")
        items, response = client.paginate(_repo_path(target, f"/actions/runs/{args.run_id}/jobs"), query={"filter": "latest"}, limit=100, item_key="jobs")
        failed_jobs = [item for item in items if item.get("conclusion") in FAILED_CONCLUSIONS]
        failures = []
        for job in failed_jobs[: args.max_jobs]:
            normalized = normalize_job(job)
            if not args.no_logs:
                logs = client.request("GET", _repo_path(target, f"/actions/jobs/{job['id']}/logs"), raw=True, max_bytes=args.log_bytes)
                text = logs.data.decode("utf-8", errors="replace") if isinstance(logs.data, bytes) else str(logs.data or "")
                normalized["log_excerpt"] = text
                normalized["log_truncated"] = logs.truncated
            failures.append(normalized)
        return {
            "run_id": args.run_id,
            "failed_jobs": failures,
            "failed_count": len(failed_jobs),
            "returned": len(failures),
            "truncated": len(failed_jobs) > len(failures),
        }, response
    if command == "run-watch":
        if args.deadline <= 0 or args.initial_interval <= 0 or args.max_interval <= 0:
            raise GitHubError("watch timing values must be positive", kind="validation")
        started = time.monotonic()
        interval = args.initial_interval
        last: Response | None = None
        while True:
            last = client.request("GET", _repo_path(target, f"/actions/runs/{args.run_id}"))
            run = normalize_run(last.data)
            if run.get("status") == "completed" or run.get("conclusion") in TERMINAL_CONCLUSIONS:
                jobs, _ = client.paginate(_repo_path(target, f"/actions/runs/{args.run_id}/jobs"), query={"filter": "latest"}, limit=100, item_key="jobs")
                return {"run": run, "jobs": [normalize_job(item) for item in jobs]}, last
            elapsed = time.monotonic() - started
            if elapsed >= args.deadline:
                raise GitHubError(f"workflow run did not complete within {args.deadline}s", kind="network", retryable=True)
            print(json.dumps({"run_id": args.run_id, "status": run.get("status"), "elapsed": round(elapsed, 1)}), file=sys.stderr)
            remaining = max(0.0, args.deadline - elapsed)
            base_delay = min(interval, remaining)
            delay = min(remaining, base_delay + random.uniform(0.0, min(1.0, base_delay * 0.1)))
            time.sleep(delay)
            interval = min(args.max_interval, interval * 1.5)
    if command in {"run-rerun", "run-rerun-failed", "job-rerun", "run-cancel"}:
        if command == "job-rerun":
            object_id = args.job_id
            suffix, effect = f"/actions/jobs/{object_id}/rerun", "write"
            exact = f"{target.full_name}:job:{object_id}"
        else:
            object_id = args.run_id
            suffixes = {
                "run-rerun": ("rerun", "write"),
                "run-rerun-failed": ("rerun-failed-jobs", "write"),
                "run-cancel": ("cancel", "destructive"),
            }
            tail, effect = suffixes[command]
            suffix = f"/actions/runs/{object_id}/{tail}"
            exact = f"{target.full_name}:run:{object_id}"
        data, response = mutation(client, args, target, "POST", _repo_path(target, suffix), {}, effect=effect, exact_target=exact)
        if response:
            if command == "job-rerun":
                verified = client.request("GET", _repo_path(target, f"/actions/jobs/{object_id}"))
                current = normalize_job(verified.data)
            else:
                verified = client.request("GET", _repo_path(target, f"/actions/runs/{object_id}"))
                current = normalize_run(verified.data)
            return {"accepted": response.status in {201, 202, 204}, "current": current}, verified
        return data, response
    if command == "workflow-dispatch":
        payload: dict[str, Any] = {"ref": args.ref}
        if args.inputs:
            try:
                inputs = json.loads(args.inputs)
            except json.JSONDecodeError as exc:
                raise GitHubError(f"--inputs must be a JSON object: {exc}", kind="validation") from exc
            if not isinstance(inputs, dict):
                raise GitHubError("--inputs must be a JSON object", kind="validation")
            payload["inputs"] = inputs
        workflow = urllib.parse.quote(args.workflow, safe="")
        return mutation(client, args, target, "POST", _repo_path(target, f"/actions/workflows/{workflow}/dispatches"), payload)
    raise GitHubError(f"unsupported Actions command: {command}", kind="validation")


def dispatch(command: str, args: Any, client: GitHubClient, target: RepositoryTarget | None) -> tuple[Any, Response | None]:
    if command.startswith("project-"):
        return project_command(command, args, client, target)
    if target is None:
        raise GitHubError(f"{command} requires --repo or a resolvable local Git remote", kind="validation")
    if command.startswith("repo-"):
        return repository_command(command, args, client, target)
    if command.startswith("issue-") or command in {"label-list", "milestone-list"}:
        return issue_command(command, args, client, target)
    if command.startswith("pr-") or command == "branch-delete":
        return pr_command(command, args, client, target)
    if command.startswith(("workflow-", "run-", "job-")):
        return actions_command(command, args, client, target)
    raise GitHubError(f"unsupported command: {command}", kind="validation")
