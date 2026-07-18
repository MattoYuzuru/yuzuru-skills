#!/usr/bin/env python3
"""Bounded Jira Data Center REST helper with explicit mutation confirmation."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


class JiraError(RuntimeError):
    pass


class SameOriginRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        old = urllib.parse.urlsplit(req.full_url)
        new = urllib.parse.urlsplit(newurl)
        if (old.scheme, old.netloc) != (new.scheme, new.netloc):
            raise JiraError("Jira API refused a cross-origin redirect to protect the PAT.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = urllib.request.build_opener(SameOriginRedirectHandler())
PROJECT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
ISSUE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*-[0-9]+$")
WRITE_COMMANDS = {"create", "link", "move-status"}


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def load_config(env_file: str | None, *, require_token: bool = True) -> dict[str, str]:
    path = Path(env_file or "~/.jira.env").expanduser()
    if path.exists() and os.name != "nt" and path.stat().st_mode & 0o077:
        raise JiraError(f"Jira env file permissions are too broad: {path}; run chmod 600.")
    file_values = parse_env_file(path)

    config = {
        name: os.environ.get(name) or file_values.get(name, "")
        for name in ("JIRA_PAT", "JIRA_HOST", "PROJECT_KEY")
    }

    if require_token and not config["JIRA_PAT"]:
        raise JiraError(
            f"Jira PAT not found in JIRA_PAT env var or {path}. "
            f"Add JIRA_PAT=<token> to {path} (create it with chmod 600)."
        )
    return config


def require_host(config: dict[str, str]) -> str:
    host = config.get("JIRA_HOST")
    if not host:
        raise JiraError("JIRA_HOST not set. Add JIRA_HOST=<instance-hostname> to ~/.jira.env.")
    value = host if "://" in host else f"https://{host}"
    parsed = urllib.parse.urlsplit(value.rstrip("/"))
    if parsed.scheme != "https" or not parsed.netloc:
        raise JiraError("JIRA_HOST must be an HTTPS origin.")
    if parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        raise JiraError("JIRA_HOST must not contain credentials, a path, query, or fragment.")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def require_project(args: argparse.Namespace, config: dict[str, str]) -> str:
    project = getattr(args, "project", None) or config.get("PROJECT_KEY")
    if not project:
        raise JiraError("--project is required (or set PROJECT_KEY in ~/.jira.env).")
    if not PROJECT_RE.fullmatch(project):
        raise JiraError(f"Invalid Jira project key: {project}")
    return project


def issue_key(value: str) -> str:
    if not ISSUE_RE.fullmatch(value):
        raise JiraError(f"Invalid Jira issue key: {value}")
    return value.upper()


def request_json(
    host: str,
    token: str,
    method: str,
    path: str,
    params: dict[str, object] | None = None,
    data: dict | None = None,
) -> object:
    url = f"{host}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    body = None
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with OPENER.open(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        message = exc.read(4001).decode("utf-8", errors="replace")[:4000]
        raise JiraError(f"Jira API error {exc.code}: {message}") from exc
    except urllib.error.URLError as exc:
        raise JiraError(f"Jira API connection error: {exc.reason}") from exc

    if not raw:
        return {}
    return json.loads(raw)


def pretty(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def summarize_issue(issue: dict) -> dict:
    fields = issue.get("fields", {}) or {}
    description = fields.get("description") or ""
    return {
        "key": issue.get("key"),
        "summary": fields.get("summary"),
        "status": (fields.get("status") or {}).get("name"),
        "type": (fields.get("issuetype") or {}).get("name"),
        "priority": (fields.get("priority") or {}).get("name"),
        "assignee": (fields.get("assignee") or {}).get("displayName"),
        "reporter": (fields.get("reporter") or {}).get("displayName"),
        "created": fields.get("created"),
        "updated": fields.get("updated"),
        "description": description[:2000],
    }


def page_values(data: object, *fallback_keys: str) -> list[dict]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []
    for key in ("values", *fallback_keys):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def field_summary(field: dict) -> dict[str, object]:
    field_id = field.get("fieldId") or field.get("id") or field.get("key")
    entry: dict[str, object] = {
        "id": field_id,
        "name": field.get("name") or field_id,
        "required": bool(field.get("required")),
        "type": (field.get("schema") or {}).get("type", "?"),
    }
    allowed = field.get("allowedValues")
    if isinstance(allowed, list):
        entry["allowed_values"] = [
            value.get("name") or value.get("value") or value.get("id")
            for value in allowed[:20]
            if isinstance(value, dict)
        ]
        entry["allowed_values_truncated"] = len(allowed) > 20
    return entry


def create_metadata(
    host: str,
    token: str,
    project: str,
    issuetype_names: list[str],
) -> dict[str, object]:
    """Use Jira 9+ granular create-metadata endpoints."""
    project_segment = urllib.parse.quote(project, safe="")
    types_path = f"/rest/api/2/issue/createmeta/{project_segment}/issuetypes"
    types_data = request_json(host, token, "GET", types_path, params={"maxResults": 100})
    types = page_values(types_data, "issueTypes", "issuetypes")
    wanted = {name.casefold() for name in issuetype_names} if issuetype_names else None
    output = []
    for issue_type in types:
        name = str(issue_type.get("name") or "")
        if wanted is not None and name.casefold() not in wanted:
            continue
        type_id = str(issue_type.get("id") or "")
        if not type_id:
            continue
        fields_path = f"{types_path}/{urllib.parse.quote(type_id, safe='')}"
        fields_data = request_json(host, token, "GET", fields_path, params={"maxResults": 100})
        fields = page_values(fields_data, "fields")
        output.append(
            {
                "id": type_id,
                "name": name,
                "fields": [field_summary(field) for field in fields],
                "fields_truncated": bool(isinstance(fields_data, dict) and fields_data.get("isLast") is False),
            }
        )
    if not output:
        raise JiraError("No matching issue types returned; check project key, names, and permissions.")
    return {"project": {"key": project}, "issuetypes": output}


def parse_field_value(raw: str) -> object:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def parse_fields(pairs: list[str]) -> dict[str, object]:
    fields: dict[str, object] = {}
    for pair in pairs:
        if "=" not in pair:
            raise JiraError(f"--field must be KEY=VALUE, got: {pair}")
        key, _, raw_value = pair.partition("=")
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", key):
            raise JiraError(f"Invalid Jira field id: {key}")
        fields[key] = parse_field_value(raw_value)
    return fields


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--env-file", default="~/.jira.env")


def bounded_int(minimum: int, maximum: int):
    def parse(value: str) -> int:
        parsed = int(value)
        if not minimum <= parsed <= maximum:
            raise argparse.ArgumentTypeError(f"must be between {minimum} and {maximum}")
        return parsed
    return parse


def add_write_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm-write", action="store_true")


def main() -> int:
    parser = argparse.ArgumentParser(description="Jira REST helper")
    add_common(parser)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("auth-check")

    read = sub.add_parser("read")
    read.add_argument("key")

    search = sub.add_parser("search")
    search.add_argument("--jql", required=True)
    search.add_argument("--fields", default="summary,status,assignee,updated")
    search.add_argument("--max-results", type=bounded_int(1, 100), default=20)

    createmeta = sub.add_parser("createmeta")
    createmeta.add_argument("--project", default=None)
    createmeta.add_argument("--issuetype-name", action="append", default=[], dest="issuetype_names")

    sub.add_parser("link-types")

    transitions = sub.add_parser("transitions")
    transitions.add_argument("key")

    epics_open = sub.add_parser("epics-open")
    epics_open.add_argument("--project", default=None)
    epics_open.add_argument("--max-results", type=bounded_int(1, 100), default=30)

    create = sub.add_parser("create")
    create.add_argument("--project", default=None)
    create.add_argument("--issuetype-id", required=True)
    create.add_argument("--summary", required=True)
    create.add_argument("--description", default="")
    create.add_argument("--field", action="append", default=[], dest="fields", metavar="KEY=VALUE")
    add_write_flags(create)

    link = sub.add_parser("link")
    link.add_argument("--type", required=True, dest="link_type")
    link.add_argument("--inward", required=True)
    link.add_argument("--outward", required=True)
    add_write_flags(link)

    move_status = sub.add_parser("move-status")
    move_status.add_argument("key")
    move_status.add_argument("--transition-id", required=True)
    add_write_flags(move_status)

    args = parser.parse_args()

    try:
        dry_run = getattr(args, "dry_run", False)
        if args.command in WRITE_COMMANDS and not dry_run and not args.confirm_write:
            raise JiraError("Write requires --confirm-write after approval of the exact dry-run preview.")
        config = load_config(args.env_file, require_token=not dry_run)
        host = require_host(config)
        token = config["JIRA_PAT"]

        if args.command == "auth-check":
            pretty(request_json(host, token, "GET", "/rest/api/2/myself"))
        elif args.command == "read":
            key = issue_key(args.key)
            data = request_json(host, token, "GET", f"/rest/api/2/issue/{key}", params={"expand": "names"})
            pretty(summarize_issue(data))
        elif args.command == "search":
            data = request_json(host, token, "GET", "/rest/api/2/search", params={
                "jql": args.jql, "fields": args.fields, "maxResults": args.max_results,
            })
            issues = [{"key": issue.get("key"), "fields": issue.get("fields", {})} for issue in data.get("issues", [])]
            pretty({"total": data.get("total", 0), "issues": issues})
        elif args.command == "createmeta":
            project = require_project(args, config)
            pretty(create_metadata(host, token, project, args.issuetype_names))
        elif args.command == "link-types":
            data = request_json(host, token, "GET", "/rest/api/2/issueLinkType")
            types = [
                {"name": t.get("name"), "inward": t.get("inward"), "outward": t.get("outward")}
                for t in data.get("issueLinkTypes", [])
            ]
            pretty(types)
        elif args.command == "transitions":
            key = issue_key(args.key)
            data = request_json(host, token, "GET", f"/rest/api/2/issue/{key}/transitions")
            items = [
                {"id": t.get("id"), "name": t.get("name"), "to": (t.get("to") or {}).get("name")}
                for t in data.get("transitions", [])
            ]
            pretty(items)
        elif args.command == "epics-open":
            project = require_project(args, config)
            jql = f"project = {project} AND issuetype = Epic AND status not in (Done, Closed) ORDER BY created DESC"
            data = request_json(host, token, "GET", "/rest/api/2/search", params={
                "jql": jql, "fields": "key,summary,status", "maxResults": args.max_results,
            })
            epics = [
                {
                    "key": issue.get("key"),
                    "summary": (issue.get("fields") or {}).get("summary"),
                    "status": ((issue.get("fields") or {}).get("status") or {}).get("name"),
                }
                for issue in data.get("issues", [])
            ]
            pretty({"total": data.get("total", 0), "epics": epics})
        elif args.command == "create":
            project = require_project(args, config)
            fields: dict[str, object] = {
                "project": {"key": project},
                "issuetype": {"id": args.issuetype_id},
                "summary": args.summary,
            }
            if args.description:
                fields["description"] = args.description
            fields.update(parse_fields(args.fields))
            payload = {"fields": fields}
            if args.dry_run:
                pretty({"dry_run": True, "payload": payload})
            else:
                pretty(request_json(host, token, "POST", "/rest/api/2/issue", data=payload))
        elif args.command == "link":
            payload = {
                "type": {"name": args.link_type},
                "inwardIssue": {"key": issue_key(args.inward)},
                "outwardIssue": {"key": issue_key(args.outward)},
            }
            if args.dry_run:
                pretty({"dry_run": True, "payload": payload})
            else:
                pretty(request_json(host, token, "POST", "/rest/api/2/issueLink", data=payload))
        elif args.command == "move-status":
            key = issue_key(args.key)
            if not args.transition_id.isdigit():
                raise JiraError("--transition-id must be numeric and come from the transitions command.")
            payload = {"transition": {"id": args.transition_id}}
            if args.dry_run:
                pretty({"dry_run": True, "payload": payload})
            else:
                pretty(request_json(host, token, "POST", f"/rest/api/2/issue/{key}/transitions", data=payload))
        else:
            raise JiraError(f"Unsupported command: {args.command}")
    except JiraError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
