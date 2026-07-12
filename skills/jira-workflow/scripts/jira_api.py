#!/usr/bin/env python3
"""Small Jira REST helper mirroring gitlab_api.py's shape."""

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


def load_config(env_file: str | None) -> dict[str, str]:
    path = Path(env_file or "~/.jira.env").expanduser()
    file_values = parse_env_file(path)

    config = {
        name: os.environ.get(name) or file_values.get(name, "")
        for name in ("JIRA_PAT", "JIRA_HOST", "PROJECT_KEY")
    }

    if not config["JIRA_PAT"]:
        raise JiraError(
            f"Jira PAT not found in JIRA_PAT env var or {path}. "
            f"Add JIRA_PAT=<token> to {path} (create it with chmod 600)."
        )
    return config


def require_host(config: dict[str, str]) -> str:
    host = config.get("JIRA_HOST")
    if not host:
        raise JiraError("JIRA_HOST not set. Add JIRA_HOST=<instance-hostname> to ~/.jira.env.")
    return re.sub(r"^https?://", "", host).rstrip("/")


def require_project(args: argparse.Namespace, config: dict[str, str]) -> str:
    project = getattr(args, "project", None) or config.get("PROJECT_KEY")
    if not project:
        raise JiraError("--project is required (or set PROJECT_KEY in ~/.jira.env).")
    return project


def request_json(
    host: str,
    token: str,
    method: str,
    path: str,
    params: dict[str, object] | None = None,
    data: dict | None = None,
) -> object:
    url = f"https://{host}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    body = None
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
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


def format_createmeta(data: dict, issuetype_names: list[str]) -> dict:
    projects = data.get("projects", [])
    if not projects:
        raise JiraError("createmeta returned no projects; check the project key and permissions")

    project = projects[0]
    wanted = {name.lower() for name in issuetype_names} if issuetype_names else None
    result: dict[str, object] = {
        "project": {"key": project.get("key"), "name": project.get("name")},
        "issuetypes": [],
    }
    for issuetype in project.get("issuetypes", []):
        name = issuetype.get("name", "")
        if wanted is not None and name.lower() not in wanted:
            continue
        fields = []
        for field_id, meta in issuetype.get("fields", {}).items():
            entry = {
                "id": field_id,
                "name": meta.get("name", field_id),
                "required": bool(meta.get("required")),
                "type": (meta.get("schema") or {}).get("type", "?"),
            }
            allowed = meta.get("allowedValues")
            if allowed:
                values = [v.get("name") or v.get("value") or v.get("id") for v in allowed[:20]]
                entry["allowed_values"] = values
            fields.append(entry)
        result["issuetypes"].append({"id": issuetype.get("id"), "name": name, "fields": fields})
    return result


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
        fields[key.strip()] = parse_field_value(raw_value)
    return fields


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--env-file", default="~/.jira.env")


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
    search.add_argument("--max-results", type=int, default=20)

    createmeta = sub.add_parser("createmeta")
    createmeta.add_argument("--project", default=None)
    createmeta.add_argument("--issuetype-name", action="append", default=[], dest="issuetype_names")

    sub.add_parser("link-types")

    transitions = sub.add_parser("transitions")
    transitions.add_argument("key")

    epics_open = sub.add_parser("epics-open")
    epics_open.add_argument("--project", default=None)
    epics_open.add_argument("--max-results", type=int, default=30)

    create = sub.add_parser("create")
    create.add_argument("--project", default=None)
    create.add_argument("--issuetype-id", required=True)
    create.add_argument("--summary", required=True)
    create.add_argument("--description", default="")
    create.add_argument("--field", action="append", default=[], dest="fields", metavar="KEY=VALUE")
    create.add_argument("--dry-run", action="store_true")

    link = sub.add_parser("link")
    link.add_argument("--type", required=True, dest="link_type")
    link.add_argument("--inward", required=True)
    link.add_argument("--outward", required=True)
    link.add_argument("--dry-run", action="store_true")

    move_status = sub.add_parser("move-status")
    move_status.add_argument("key")
    move_status.add_argument("--transition-id", required=True)
    move_status.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    try:
        config = load_config(args.env_file)
        host = require_host(config)
        token = config["JIRA_PAT"]

        if args.command == "auth-check":
            pretty(request_json(host, token, "GET", "/rest/api/2/myself"))
        elif args.command == "read":
            data = request_json(host, token, "GET", f"/rest/api/2/issue/{args.key}", params={"expand": "names"})
            pretty(summarize_issue(data))
        elif args.command == "search":
            data = request_json(host, token, "GET", "/rest/api/2/search", params={
                "jql": args.jql, "fields": args.fields, "maxResults": args.max_results,
            })
            issues = [{"key": issue.get("key"), "fields": issue.get("fields", {})} for issue in data.get("issues", [])]
            pretty({"total": data.get("total", 0), "issues": issues})
        elif args.command == "createmeta":
            project = require_project(args, config)
            data = request_json(host, token, "GET", "/rest/api/2/issue/createmeta", params={
                "projectKeys": project, "expand": "projects.issuetypes.fields",
            })
            pretty(format_createmeta(data, args.issuetype_names))
        elif args.command == "link-types":
            data = request_json(host, token, "GET", "/rest/api/2/issueLinkType")
            types = [
                {"name": t.get("name"), "inward": t.get("inward"), "outward": t.get("outward")}
                for t in data.get("issueLinkTypes", [])
            ]
            pretty(types)
        elif args.command == "transitions":
            data = request_json(host, token, "GET", f"/rest/api/2/issue/{args.key}/transitions")
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
                "inwardIssue": {"key": args.inward},
                "outwardIssue": {"key": args.outward},
            }
            if args.dry_run:
                pretty({"dry_run": True, "payload": payload})
            else:
                pretty(request_json(host, token, "POST", "/rest/api/2/issueLink", data=payload))
        elif args.command == "move-status":
            payload = {"transition": {"id": args.transition_id}}
            if args.dry_run:
                pretty({"dry_run": True, "payload": payload})
            else:
                pretty(request_json(host, token, "POST", f"/rest/api/2/issue/{args.key}/transitions", data=payload))
        else:
            raise JiraError(f"Unsupported command: {args.command}")
    except JiraError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
