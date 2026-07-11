"""Coarse-grained GitHub workflow command implementations."""

from __future__ import annotations

import json
import random
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any, Callable

from .client import GitHubClient, Response
from .errors import GitHubError
from .graphql import (
    ADD_PROJECT_ITEM,
    PROJECT_ID_ORGANIZATION,
    PROJECT_ID_USER,
    PROJECT_LIST_ORGANIZATION,
    PROJECT_LIST_USER,
    SET_PROJECT_FIELD,
)
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


def project_command(command: str, args: Any, client: GitHubClient, target: RepositoryTarget) -> tuple[Any, Response | None]:
    if command == "project-list":
        if not 1 <= args.limit <= 100:
            raise GitHubError("--limit must be between 1 and 100", kind="validation")
        document = PROJECT_LIST_ORGANIZATION if args.owner_type == "organization" else PROJECT_LIST_USER
        response = client.graphql(document, {"owner": args.owner, "first": args.limit})
        container = _project(response.data, args.owner_type)
        projects = container.get("projectsV2", {}).get("nodes", []) if isinstance(container, dict) else []
        return projects, response
    if command == "project-add-item":
        project_id, lookup = _project_id(client, args.owner, args.owner_type, args.project_number)
        if args.node_id:
            content_id = args.node_id
        else:
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
        variables = {"project": args.project_id, "item": args.item_id, "field": args.field_id, "value": selected}
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
    if command == "pr-create":
        body = read_body(args)
        base = args.base
        if not base:
            base = client.request("GET", _repo_path(target)).data.get("default_branch")
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
        exact = f"{target.full_name}#{args.number}"
        current = client.request("GET", _pr_path(target, args.number))
        actual_sha = current.data.get("head", {}).get("sha")
        if actual_sha != args.expected_head_sha:
            raise GitHubError(f"expected head SHA does not match current PR head: {actual_sha}", kind="validation")
        checks, _ = _collect_checks(client, target, actual_sha)
        green_checks = all(
            item.get("status") == "completed" and item.get("conclusion") in {"success", "neutral", "skipped"}
            for item in checks["check_runs"]
        )
        green_statuses = all(item.get("state") == "success" for item in checks["statuses"])
        has_signal = bool(checks["check_runs"] or checks["statuses"])
        if not args.allow_non_green and (not has_signal or not green_checks or not green_statuses):
            raise GitHubError("pull request checks are missing, pending, or non-green; inspect pr-checks or use --allow-non-green after explicit approval", kind="validation")
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
    action_paths = {
        "run-rerun": (f"/actions/runs/{args.run_id}/rerun", "write", f"{target.full_name}:run:{args.run_id}"),
        "run-rerun-failed": (f"/actions/runs/{args.run_id}/rerun-failed-jobs", "write", f"{target.full_name}:run:{args.run_id}"),
        "job-rerun": (f"/actions/jobs/{args.job_id}/rerun", "write", f"{target.full_name}:job:{args.job_id}"),
        "run-cancel": (f"/actions/runs/{args.run_id}/cancel", "destructive", f"{target.full_name}:run:{args.run_id}"),
    }
    if command in action_paths:
        suffix, effect, exact = action_paths[command]
        data, response = mutation(client, args, target, "POST", _repo_path(target, suffix), {}, effect=effect, exact_target=exact)
        if response:
            verified = client.request("GET", _repo_path(target, f"/actions/runs/{args.run_id}")) if hasattr(args, "run_id") else client.request("GET", _repo_path(target, f"/actions/jobs/{args.job_id}"))
            return {"accepted": response.status in {201, 202, 204}, "current": normalize_run(verified.data) if hasattr(args, "run_id") else normalize_job(verified.data)}, verified
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


def dispatch(command: str, args: Any, client: GitHubClient, target: RepositoryTarget) -> tuple[Any, Response | None]:
    if command.startswith("repo-"):
        return repository_command(command, args, client, target)
    if command.startswith("issue-") or command in {"label-list", "milestone-list"}:
        return issue_command(command, args, client, target)
    if command.startswith("project-"):
        return project_command(command, args, client, target)
    if command.startswith("pr-") or command == "branch-delete":
        return pr_command(command, args, client, target)
    if command.startswith(("workflow-", "run-", "job-")):
        return actions_command(command, args, client, target)
    raise GitHubError(f"unsupported command: {command}", kind="validation")
