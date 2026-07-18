#!/usr/bin/env python3
"""Bounded GitLab REST helper with explicit mutation confirmation."""

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
WRITE_COMMANDS = {"fork-create", "mr-create", "mr-note-create", "mr-discussion-reply"}
DESTRUCTIVE_COMMANDS = {"mr-discussion-resolve"}


class GitLabError(RuntimeError):
    pass


class SameOriginRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        old = urllib.parse.urlsplit(req.full_url)
        new = urllib.parse.urlsplit(newurl)
        if (old.scheme, old.netloc) != (new.scheme, new.netloc):
            raise GitLabError("GitLab API refused a cross-origin redirect to protect the token.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = urllib.request.build_opener(SameOriginRedirectHandler())


def validate_host(value: str) -> str:
    parsed = urllib.parse.urlsplit(value.rstrip("/"))
    if parsed.scheme != "https" or not parsed.netloc:
        raise GitLabError("GitLab host must be an absolute HTTPS origin.")
    if parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        raise GitLabError("GitLab host must not contain credentials, a path, query, or fragment.")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def load_token(token_file: str | None) -> str:
    for name in ("GITLAB_TOKEN", "GITLAB_PAT"):
        value = os.environ.get(name)
        if value:
            return value.strip()

    path = Path(token_file or "~/.gitlab_token").expanduser()
    if path.exists():
        if os.name != "nt" and path.stat().st_mode & 0o077:
            raise GitLabError(f"GitLab token file permissions are too broad: {path}; run chmod 600.")
        return path.read_text(encoding="utf-8").strip()

    raise GitLabError("GitLab token not found in GITLAB_TOKEN, GITLAB_PAT, or ~/.gitlab_token")


def project_id(path: str) -> str:
    return urllib.parse.quote(path, safe="")


def file_id(path: str) -> str:
    return urllib.parse.quote(path, safe="")


def request_json(host: str, token: str, method: str, path: str, data: dict | None = None) -> object:
    host = validate_host(host)
    body = None
    headers = {"PRIVATE-TOKEN": token, "Accept": "application/json"}

    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(f"{host}/api/v4{path}", data=body, headers=headers, method=method)
    try:
        with OPENER.open(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        message = exc.read(4001).decode("utf-8", errors="replace")[:4000]
        raise GitLabError(f"GitLab API error {exc.code}: {message}") from exc
    except urllib.error.URLError as exc:
        raise GitLabError(f"GitLab API connection error: {exc.reason}") from exc

    if not raw:
        return {}
    return json.loads(raw)


def request_text(host: str, token: str, method: str, path: str, max_chars: int) -> tuple[str, bool]:
    host = validate_host(host)
    headers = {"PRIVATE-TOKEN": token, "Accept": "text/plain"}

    req = urllib.request.Request(f"{host}/api/v4{path}", headers=headers, method=method)
    try:
        with OPENER.open(req, timeout=30) as resp:
            raw = resp.read(max_chars + 1).decode("utf-8", errors="replace")
            return raw[:max_chars], len(raw) > max_chars
    except urllib.error.HTTPError as exc:
        message = exc.read(4001).decode("utf-8", errors="replace")[:4000]
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


def bounded_int(minimum: int, maximum: int):
    def parse(value: str) -> int:
        parsed = int(value)
        if not minimum <= parsed <= maximum:
            raise argparse.ArgumentTypeError(f"must be between {minimum} and {maximum}")
        return parsed
    return parse


def add_write_flags(parser: argparse.ArgumentParser, *, destructive: bool = False) -> None:
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--confirm-destructive" if destructive else "--confirm-write",
        action="store_true",
    )


def dry_run(method: str, path: str, body: dict[str, object] | None = None) -> None:
    pretty({"dry_run": True, "method": method, "path": path, "body": body})


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
    tree.add_argument("--per-page", type=bounded_int(1, 100), default=100)

    raw = sub.add_parser("file-raw")
    raw.add_argument("project")
    raw.add_argument("file_path")
    raw.add_argument("--ref", default="main")
    raw.add_argument("--max-chars", type=bounded_int(1, 200000), default=20000)

    outline = sub.add_parser("file-outline")
    outline.add_argument("project")
    outline.add_argument("file_paths", nargs="+")
    outline.add_argument("--ref", default="main")
    outline.add_argument("--max-level", type=int, default=2)
    outline.add_argument("--max-chars-per-file", type=bounded_int(1, 1000000), default=200000)

    mr_list = sub.add_parser("mr-list")
    mr_list.add_argument("project")
    mr_list.add_argument("--state", default="opened")
    mr_list.add_argument("--per-page", type=bounded_int(1, 100), default=20)

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
    pipelines.add_argument("--per-page", type=bounded_int(1, 100), default=10)

    jobs = sub.add_parser("pipeline-jobs")
    jobs.add_argument("project")
    jobs.add_argument("pipeline_id")
    jobs.add_argument("--per-page", type=bounded_int(1, 100), default=50)

    trace = sub.add_parser("job-trace")
    trace.add_argument("project")
    trace.add_argument("job_id")
    trace.add_argument("--max-chars", type=bounded_int(1, 200000), default=30000)

    search = sub.add_parser("code-search")
    search.add_argument("project")
    search.add_argument("query")
    search.add_argument("--per-page", type=bounded_int(1, 100), default=20)

    commit_list = sub.add_parser("commit-list")
    commit_list.add_argument("project")
    commit_list.add_argument("--ref", default=None)
    commit_list.add_argument("--per-page", type=bounded_int(1, 100), default=20)

    commit_read = sub.add_parser("commit-read")
    commit_read.add_argument("project")
    commit_read.add_argument("sha")

    fork = sub.add_parser("fork-create")
    fork.add_argument("project")
    add_write_flags(fork)

    mr_create = sub.add_parser("mr-create")
    mr_create.add_argument("project")
    mr_create.add_argument("--source-branch", required=True)
    mr_create.add_argument("--target-branch", required=True)
    mr_create.add_argument("--title", required=True)
    mr_create.add_argument("--description", default="")
    mr_create.add_argument("--target-project-id", type=int)
    mr_create.add_argument("--remove-source-branch", action="store_true")
    add_write_flags(mr_create)

    mr_note = sub.add_parser("mr-note-create")
    mr_note.add_argument("project")
    mr_note.add_argument("iid")
    mr_note.add_argument("--body", required=True)
    add_write_flags(mr_note)

    discussion_reply = sub.add_parser("mr-discussion-reply")
    discussion_reply.add_argument("project")
    discussion_reply.add_argument("iid")
    discussion_reply.add_argument("discussion_id")
    discussion_reply.add_argument("--body", required=True)
    add_write_flags(discussion_reply)

    discussion_resolve = sub.add_parser("mr-discussion-resolve")
    discussion_resolve.add_argument("project")
    discussion_resolve.add_argument("iid")
    discussion_resolve.add_argument("discussion_id")
    discussion_resolve.add_argument("--unresolve", action="store_true")
    add_write_flags(discussion_resolve, destructive=True)

    args = parser.parse_args()

    try:
        args.host = validate_host(args.host)
        if args.command in WRITE_COMMANDS and not args.dry_run and not args.confirm_write:
            raise GitLabError("Write requires --confirm-write after approval of the exact dry-run.")
        if args.command in DESTRUCTIVE_COMMANDS and not args.dry_run and not args.confirm_destructive:
            raise GitLabError(
                "Discussion resolution requires --confirm-destructive after exact thread confirmation."
            )
        token = "" if getattr(args, "dry_run", False) else load_token(args.token_file)

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
            text, truncated = request_text(
                args.host,
                token,
                "GET",
                f"/projects/{project_id(args.project)}/repository/files/{file_id(args.file_path)}/raw?{query}",
                args.max_chars,
            )
            pretty({"path": args.file_path, "text": text, "truncated": truncated, "max_chars": args.max_chars})
        elif args.command == "file-outline":
            outlines = {}
            query = urllib.parse.urlencode({"ref": args.ref})
            for path in args.file_paths:
                text, _ = request_text(
                    args.host,
                    token,
                    "GET",
                    f"/projects/{project_id(args.project)}/repository/files/{file_id(path)}/raw?{query}",
                    args.max_chars_per_file,
                )
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
        elif args.command == "job-trace":
            text, truncated = request_text(
                args.host,
                token,
                "GET",
                f"/projects/{project_id(args.project)}/jobs/{args.job_id}/trace",
                args.max_chars,
            )
            pretty({"job_id": args.job_id, "trace": text, "truncated": truncated, "max_chars": args.max_chars})
        elif args.command == "code-search":
            query = urllib.parse.urlencode({"scope": "blobs", "search": args.query, "per_page": args.per_page})
            pretty(request_json(args.host, token, "GET", f"/projects/{project_id(args.project)}/search?{query}"))
        elif args.command == "commit-list":
            params = {"per_page": args.per_page}
            if args.ref:
                params["ref_name"] = args.ref
            query = urllib.parse.urlencode(params)
            pretty(request_json(args.host, token, "GET", f"/projects/{project_id(args.project)}/repository/commits?{query}"))
        elif args.command == "commit-read":
            pretty(request_json(args.host, token, "GET", f"/projects/{project_id(args.project)}/repository/commits/{args.sha}"))
        elif args.command == "fork-create":
            path = f"/projects/{project_id(args.project)}/fork"
            if args.dry_run:
                dry_run("POST", path, {})
            else:
                pretty(request_json(args.host, token, "POST", path, {}))
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
            path = f"/projects/{project_id(args.project)}/merge_requests"
            if args.dry_run:
                dry_run("POST", path, payload)
            else:
                pretty(request_json(args.host, token, "POST", path, payload))
        elif args.command == "mr-note-create":
            path = f"/projects/{project_id(args.project)}/merge_requests/{args.iid}/notes"
            body = {"body": args.body}
            if args.dry_run:
                dry_run("POST", path, body)
            else:
                pretty(request_json(args.host, token, "POST", path, body))
        elif args.command == "mr-discussion-reply":
            path = f"/projects/{project_id(args.project)}/merge_requests/{args.iid}/discussions/{args.discussion_id}/notes"
            body = {"body": args.body}
            if args.dry_run:
                dry_run("POST", path, body)
            else:
                pretty(request_json(args.host, token, "POST", path, body))
        elif args.command == "mr-discussion-resolve":
            path = f"/projects/{project_id(args.project)}/merge_requests/{args.iid}/discussions/{args.discussion_id}"
            body = {"resolved": not args.unresolve}
            if args.dry_run:
                dry_run("PUT", path, body)
            else:
                pretty(request_json(args.host, token, "PUT", path, body))
        else:
            raise GitLabError(f"Unsupported command: {args.command}")
    except GitLabError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
