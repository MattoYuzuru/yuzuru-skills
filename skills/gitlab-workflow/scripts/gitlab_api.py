#!/usr/bin/env python3
"""Small GitLab REST helper for Codex skills."""

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


DEFAULT_HOST = "https://gitlab.com"


class GitLabError(RuntimeError):
    pass


def load_token(token_file: str | None) -> str:
    for name in ("GITLAB_TOKEN", "GITLAB_PAT"):
        value = os.environ.get(name)
        if value:
            return value.strip()

    path = Path(token_file or "~/.gitlab_token").expanduser()
    if path.exists():
        return path.read_text(encoding="utf-8").strip()

    raise GitLabError("GitLab token not found in GITLAB_TOKEN, GITLAB_PAT, or ~/.gitlab_token")


def project_id(path: str) -> str:
    return urllib.parse.quote(path, safe="")


def file_id(path: str) -> str:
    return urllib.parse.quote(path, safe="")


def request_json(host: str, token: str, method: str, path: str, data: dict | None = None) -> object:
    host = host.rstrip("/")
    body = None
    headers = {"PRIVATE-TOKEN": token, "Accept": "application/json"}

    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(f"{host}/api/v4{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise GitLabError(f"GitLab API error {exc.code}: {message}") from exc
    except urllib.error.URLError as exc:
        raise GitLabError(f"GitLab API connection error: {exc.reason}") from exc

    if not raw:
        return {}
    return json.loads(raw)


def request_text(host: str, token: str, method: str, path: str) -> str:
    host = host.rstrip("/")
    headers = {"PRIVATE-TOKEN": token, "Accept": "text/plain"}

    req = urllib.request.Request(f"{host}/api/v4{path}", headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise GitLabError(f"GitLab API error {exc.code}: {message}") from exc
    except urllib.error.URLError as exc:
        raise GitLabError(f"GitLab API connection error: {exc.reason}") from exc


def pretty(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def markdown_outline(text: str, max_level: int) -> list[dict[str, object]]:
    outline = []
    for line in text.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if not match:
            continue
        level = len(match.group(1))
        if level <= max_level:
            outline.append({"level": level, "title": match.group(2)})
    return outline


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", default=os.environ.get("GITLAB_HOST", DEFAULT_HOST))
    parser.add_argument("--token-file", default="~/.gitlab_token")


def main() -> int:
    parser = argparse.ArgumentParser(description="GitLab REST helper")
    add_common(parser)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("auth-check")

    repo = sub.add_parser("repo-info")
    repo.add_argument("project")

    tree = sub.add_parser("tree")
    tree.add_argument("project")
    tree.add_argument("--path", default="")
    tree.add_argument("--ref", default="main")
    tree.add_argument("--recursive", action="store_true")
    tree.add_argument("--per-page", type=int, default=100)

    raw = sub.add_parser("file-raw")
    raw.add_argument("project")
    raw.add_argument("file_path")
    raw.add_argument("--ref", default="main")

    outline = sub.add_parser("file-outline")
    outline.add_argument("project")
    outline.add_argument("file_paths", nargs="+")
    outline.add_argument("--ref", default="main")
    outline.add_argument("--max-level", type=int, default=2)

    mr_list = sub.add_parser("mr-list")
    mr_list.add_argument("project")
    mr_list.add_argument("--state", default="opened")
    mr_list.add_argument("--per-page", type=int, default=20)

    mr_read = sub.add_parser("mr-read")
    mr_read.add_argument("project")
    mr_read.add_argument("iid")

    comments = sub.add_parser("mr-comments")
    comments.add_argument("project")
    comments.add_argument("iid")

    diff = sub.add_parser("mr-diff")
    diff.add_argument("project")
    diff.add_argument("iid")

    pipelines = sub.add_parser("pipeline-list")
    pipelines.add_argument("project")
    pipelines.add_argument("--per-page", type=int, default=10)

    jobs = sub.add_parser("pipeline-jobs")
    jobs.add_argument("project")
    jobs.add_argument("pipeline_id")
    jobs.add_argument("--per-page", type=int, default=50)

    search = sub.add_parser("code-search")
    search.add_argument("project")
    search.add_argument("query")
    search.add_argument("--per-page", type=int, default=20)

    fork = sub.add_parser("fork-create")
    fork.add_argument("project")

    mr_create = sub.add_parser("mr-create")
    mr_create.add_argument("project")
    mr_create.add_argument("--source-branch", required=True)
    mr_create.add_argument("--target-branch", required=True)
    mr_create.add_argument("--title", required=True)
    mr_create.add_argument("--description", default="")
    mr_create.add_argument("--target-project-id", type=int)
    mr_create.add_argument("--remove-source-branch", action="store_true")

    args = parser.parse_args()

    try:
        token = load_token(args.token_file)

        if args.command == "auth-check":
            pretty(request_json(args.host, token, "GET", "/user"))
        elif args.command == "repo-info":
            pretty(request_json(args.host, token, "GET", f"/projects/{project_id(args.project)}"))
        elif args.command == "tree":
            query = urllib.parse.urlencode({
                "path": args.path,
                "ref": args.ref,
                "recursive": str(args.recursive).lower(),
                "per_page": args.per_page,
            })
            pretty(request_json(args.host, token, "GET", f"/projects/{project_id(args.project)}/repository/tree?{query}"))
        elif args.command == "file-raw":
            query = urllib.parse.urlencode({"ref": args.ref})
            print(request_text(args.host, token, "GET", f"/projects/{project_id(args.project)}/repository/files/{file_id(args.file_path)}/raw?{query}"), end="")
        elif args.command == "file-outline":
            outlines = {}
            query = urllib.parse.urlencode({"ref": args.ref})
            for path in args.file_paths:
                text = request_text(args.host, token, "GET", f"/projects/{project_id(args.project)}/repository/files/{file_id(path)}/raw?{query}")
                outlines[path] = markdown_outline(text, args.max_level)
            pretty(outlines)
        elif args.command == "mr-list":
            query = urllib.parse.urlencode({"state": args.state, "per_page": args.per_page})
            pretty(request_json(args.host, token, "GET", f"/projects/{project_id(args.project)}/merge_requests?{query}"))
        elif args.command == "mr-read":
            pretty(request_json(args.host, token, "GET", f"/projects/{project_id(args.project)}/merge_requests/{args.iid}"))
        elif args.command == "mr-comments":
            pretty(request_json(args.host, token, "GET", f"/projects/{project_id(args.project)}/merge_requests/{args.iid}/discussions?per_page=100"))
        elif args.command == "mr-diff":
            pretty(request_json(args.host, token, "GET", f"/projects/{project_id(args.project)}/merge_requests/{args.iid}/diffs?per_page=100"))
        elif args.command == "pipeline-list":
            pretty(request_json(args.host, token, "GET", f"/projects/{project_id(args.project)}/pipelines?per_page={args.per_page}"))
        elif args.command == "pipeline-jobs":
            pretty(request_json(args.host, token, "GET", f"/projects/{project_id(args.project)}/pipelines/{args.pipeline_id}/jobs?per_page={args.per_page}"))
        elif args.command == "code-search":
            query = urllib.parse.urlencode({"scope": "blobs", "search": args.query, "per_page": args.per_page})
            pretty(request_json(args.host, token, "GET", f"/projects/{project_id(args.project)}/search?{query}"))
        elif args.command == "fork-create":
            pretty(request_json(args.host, token, "POST", f"/projects/{project_id(args.project)}/fork", {}))
        elif args.command == "mr-create":
            payload = {
                "source_branch": args.source_branch,
                "target_branch": args.target_branch,
                "title": args.title,
                "description": args.description,
                "remove_source_branch": args.remove_source_branch,
            }
            if args.target_project_id is not None:
                payload["target_project_id"] = args.target_project_id
            pretty(request_json(args.host, token, "POST", f"/projects/{project_id(args.project)}/merge_requests", payload))
        else:
            raise GitLabError(f"Unsupported command: {args.command}")
    except GitLabError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
