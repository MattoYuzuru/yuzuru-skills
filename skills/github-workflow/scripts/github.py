#!/usr/bin/env python3
"""GitHub repository, issue, pull request, Projects, and Actions helper."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from github_workflow.auth import DEFAULT_TOKEN_FILE, discover_credential
from github_workflow.client import DEFAULT_API_VERSION, GitHubClient
from github_workflow.commands import dispatch
from github_workflow.errors import GitHubError
from github_workflow.output import emit_error, emit_success
from github_workflow.targets import resolve_repository


def add_limit(parser: argparse.ArgumentParser, default: int = 20) -> None:
    parser.add_argument("--limit", type=int, default=default, help="maximum items to return (1-100)")


def add_body(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--body", help="short Markdown body")
    group.add_argument("--body-file", help="UTF-8 Markdown file, or - for stdin")


def add_write(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dry-run", action="store_true", help="show the sanitized mutation without sending it")
    parser.add_argument("--confirm-write", action="store_true", help="confirm this exact external write")


def add_destructive(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dry-run", action="store_true", help="show the sanitized mutation without sending it")
    parser.add_argument("--confirm-destructive", action="store_true", help="confirm this destructive action")
    parser.add_argument("--confirm-target", help="exact target string shown by --dry-run")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="GitHub workflow helper using local Git plus REST and GraphQL APIs without MCP"
    )
    parser.add_argument("--repo", help="owner/repo or GitHub repository URL; defaults to local remotes")
    parser.add_argument("--cwd", default=".", help="local Git checkout used for target and Git context")
    parser.add_argument("--host", default=os.environ.get("GH_HOST", "github.com"), help="GitHub web host")
    parser.add_argument("--api-url", default=os.environ.get("GITHUB_API_URL"), help="REST API base URL")
    parser.add_argument("--graphql-url", default=os.environ.get("GITHUB_GRAPHQL_URL"), help="GraphQL endpoint")
    parser.add_argument("--api-version", default=os.environ.get("GITHUB_API_VERSION", DEFAULT_API_VERSION))
    parser.add_argument("--token-file", default=DEFAULT_TOKEN_FILE, help="token file outside the repository")
    parser.add_argument("--no-gh-auth", action="store_true", help="do not fall back to gh auth token")
    parser.add_argument("--timeout", type=float, default=30.0, help="per-request timeout in seconds")
    parser.add_argument("--retries", type=int, default=4, help="maximum attempts for safe reads")
    parser.add_argument("--max-wait", type=float, default=60.0, help="maximum total retry sleep")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("auth-check", help="verify authentication without printing a token")
    sub.add_parser("repo-info", help="read repository About and core metadata")
    sub.add_parser("repo-languages", help="summarize repository languages")
    sub.add_parser("repo-context", help="aggregate repository metadata with local Git context")

    about = sub.add_parser("repo-update-about", help="update repository description or homepage")
    about.add_argument("--description")
    about.add_argument("--homepage")
    add_write(about)

    topics = sub.add_parser("repo-topics-set", help="replace the complete repository topic set")
    topics.add_argument("topics", nargs="*", help="up to 20 topics; omit all to clear")
    add_write(topics)

    search = sub.add_parser("issue-search", help="search issues in the target repository")
    search.add_argument("query")
    add_limit(search)

    issues = sub.add_parser("issue-list", help="list repository issues without pull requests")
    issues.add_argument("--state", choices=("open", "closed", "all"), default="open")
    issues.add_argument("--sort", choices=("created", "updated", "comments"), default="created")
    issues.add_argument("--direction", choices=("asc", "desc"), default="desc")
    add_limit(issues)

    issue = sub.add_parser("issue-read", help="read one issue")
    issue.add_argument("number", type=int)

    labels = sub.add_parser("label-list", help="list labels")
    add_limit(labels, 100)

    milestones = sub.add_parser("milestone-list", help="list milestones")
    milestones.add_argument("--state", choices=("open", "closed", "all"), default="open")
    add_limit(milestones, 100)

    create_issue = sub.add_parser("issue-create", help="create an issue")
    create_issue.add_argument("--title", required=True)
    add_body(create_issue)
    create_issue.add_argument("--assignees", nargs="*")
    create_issue.add_argument("--labels", nargs="*")
    create_issue.add_argument("--milestone", help="milestone number or exact title")
    add_write(create_issue)

    update_issue = sub.add_parser("issue-update", help="update an issue")
    update_issue.add_argument("number", type=int)
    update_issue.add_argument("--title")
    add_body(update_issue)
    update_issue.add_argument("--assignees", nargs="*")
    update_issue.add_argument("--labels", nargs="*")
    update_issue.add_argument("--milestone", help="milestone number, exact title, or none to clear")
    add_write(update_issue)

    close_issue = sub.add_parser("issue-close", help="close an issue")
    close_issue.add_argument("number", type=int)
    close_issue.add_argument("--reason", choices=("completed", "not_planned"), default="completed")
    add_destructive(close_issue)

    project_list = sub.add_parser("project-list", help="list Projects V2 for a user or organization")
    project_list.add_argument("--owner", help="project owner; defaults to repository owner")
    project_list.add_argument("--owner-type", choices=("user", "organization"), default="user")
    add_limit(project_list)

    project_add = sub.add_parser("project-add-item", help="add an issue or pull request to Projects V2")
    project_add.add_argument("--owner", help="project owner; defaults to repository owner")
    project_add.add_argument("--owner-type", choices=("user", "organization"), default="user")
    project_add.add_argument("--project-number", type=int, required=True)
    item = project_add.add_mutually_exclusive_group(required=True)
    item.add_argument("--issue-number", type=int)
    item.add_argument("--pull-number", type=int)
    item.add_argument("--node-id")
    add_write(project_add)

    project_field = sub.add_parser("project-field-set", help="set one Projects V2 item field")
    project_field.add_argument("--project-id", required=True)
    project_field.add_argument("--item-id", required=True)
    project_field.add_argument("--field-id", required=True)
    value = project_field.add_mutually_exclusive_group(required=True)
    value.add_argument("--text")
    value.add_argument("--value-number", type=float)
    value.add_argument("--date")
    value.add_argument("--single-select-option-id")
    value.add_argument("--iteration-id")
    add_write(project_field)

    candidate = sub.add_parser("pr-candidate", help="derive head/base and detect an existing open PR")
    candidate.add_argument("--base")

    prs = sub.add_parser("pr-list", help="list pull requests")
    prs.add_argument("--state", choices=("open", "closed", "all"), default="open")
    prs.add_argument("--sort", choices=("created", "updated", "popularity", "long-running"), default="created")
    prs.add_argument("--direction", choices=("asc", "desc"), default="desc")
    add_limit(prs)

    pr = sub.add_parser("pr-read", help="read one pull request")
    pr.add_argument("number", type=int)

    pr_files = sub.add_parser("pr-files", help="list files changed by a pull request")
    pr_files.add_argument("number", type=int)
    add_limit(pr_files, 100)

    pr_checks = sub.add_parser("pr-checks", help="summarize checks and commit statuses for a pull request")
    pr_checks.add_argument("number", type=int)

    pr_create = sub.add_parser("pr-create", help="create a pull request")
    pr_create.add_argument("--title", required=True)
    pr_create.add_argument("--head", required=True, help="branch or owner:branch")
    pr_create.add_argument("--base", help="defaults to repository default branch")
    add_body(pr_create)
    pr_create.add_argument("--draft", action="store_true")
    pr_create.add_argument("--maintainer-can-modify", action=argparse.BooleanOptionalAction, default=True)
    add_write(pr_create)

    pr_metadata = sub.add_parser("pr-metadata-update", help="update PR assignees, labels, or milestone")
    pr_metadata.add_argument("number", type=int)
    pr_metadata.add_argument("--assignees", nargs="*")
    pr_metadata.add_argument("--labels", nargs="*")
    pr_metadata.add_argument("--milestone", help="milestone number, exact title, or none to clear")
    add_write(pr_metadata)

    pr_update = sub.add_parser("pr-update", help="update non-destructive pull request fields")
    pr_update.add_argument("number", type=int)
    pr_update.add_argument("--title")
    pr_update.add_argument("--base")
    pr_update.add_argument("--state", choices=("open",), help="reopen a closed PR")
    add_body(pr_update)
    add_write(pr_update)

    pr_close = sub.add_parser("pr-close", help="close a pull request")
    pr_close.add_argument("number", type=int)
    add_destructive(pr_close)

    pr_merge = sub.add_parser("pr-merge", help="merge a pull request at an expected head SHA")
    pr_merge.add_argument("number", type=int)
    pr_merge.add_argument("--method", choices=("merge", "squash", "rebase"), default="squash")
    pr_merge.add_argument("--expected-head-sha", required=True)
    pr_merge.add_argument("--title")
    pr_merge.add_argument("--message")
    pr_merge.add_argument("--allow-non-green", action="store_true", help="allow merge without green checks after explicit approval")
    add_destructive(pr_merge)

    branch_delete = sub.add_parser("branch-delete", help="delete a remote branch through the Git refs API")
    branch_delete.add_argument("branch")
    add_destructive(branch_delete)

    workflows = sub.add_parser("workflow-list", help="list Actions workflows")
    add_limit(workflows)

    runs = sub.add_parser("run-list", help="list Actions workflow runs")
    runs.add_argument("--workflow", help="workflow ID or file name")
    runs.add_argument("--branch")
    runs.add_argument("--event")
    runs.add_argument("--status")
    add_limit(runs)

    run = sub.add_parser("run-read", help="read one Actions workflow run")
    run.add_argument("run_id", type=int)

    jobs = sub.add_parser("run-jobs", help="list jobs in an Actions run")
    jobs.add_argument("run_id", type=int)
    jobs.add_argument("--filter", choices=("latest", "all"), default="latest")
    add_limit(jobs, 100)

    job = sub.add_parser("job-read", help="read one Actions job")
    job.add_argument("job_id", type=int)

    failures = sub.add_parser("run-failures", help="collect failed jobs and bounded log excerpts")
    failures.add_argument("run_id", type=int)
    failures.add_argument("--max-jobs", type=int, default=4)
    failures.add_argument("--log-bytes", type=int, default=65536)
    failures.add_argument("--no-logs", action="store_true")

    watch = sub.add_parser("run-watch", help="poll an Actions run until it reaches a terminal state")
    watch.add_argument("run_id", type=int)
    watch.add_argument("--deadline", type=float, default=1200.0)
    watch.add_argument("--initial-interval", type=float, default=5.0)
    watch.add_argument("--max-interval", type=float, default=30.0)

    rerun = sub.add_parser("run-rerun", help="rerun an Actions workflow run")
    rerun.add_argument("run_id", type=int)
    add_write(rerun)

    rerun_failed = sub.add_parser("run-rerun-failed", help="rerun only failed jobs in an Actions run")
    rerun_failed.add_argument("run_id", type=int)
    add_write(rerun_failed)

    rerun_job = sub.add_parser("job-rerun", help="rerun one Actions job")
    rerun_job.add_argument("job_id", type=int)
    add_write(rerun_job)

    cancel = sub.add_parser("run-cancel", help="cancel an active Actions run")
    cancel.add_argument("run_id", type=int)
    add_destructive(cancel)

    dispatch_workflow = sub.add_parser("workflow-dispatch", help="dispatch a workflow_dispatch workflow")
    dispatch_workflow.add_argument("workflow", help="workflow ID or file name")
    dispatch_workflow.add_argument("--ref", required=True)
    dispatch_workflow.add_argument("--inputs", help="JSON object of workflow inputs")
    add_write(dispatch_workflow)
    return parser


def endpoint_defaults(host: str, api_url: str | None, graphql_url: str | None) -> tuple[str, str]:
    if api_url:
        rest = api_url.rstrip("/")
    elif host == "github.com":
        rest = "https://api.github.com"
    else:
        rest = f"https://{host}/api/v3"
    graph = graphql_url or ("https://api.github.com/graphql" if host == "github.com" else f"https://{host}/api/graphql")
    return rest, graph


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        credential = discover_credential(
            args.host,
            args.token_file,
            required=args.command == "auth-check",
            allow_gh=not args.no_gh_auth,
        )
        if credential and credential.warning:
            print(credential.warning, file=sys.stderr)
        rest, graph = endpoint_defaults(args.host, args.api_url, args.graphql_url)
        client = GitHubClient(
            token=credential.token if credential else None,
            api_url=rest,
            graphql_url=graph,
            api_version=args.api_version,
            timeout=args.timeout,
            retries=args.retries,
            max_wait=args.max_wait,
        )

        if args.command == "auth-check":
            response = client.request("GET", "/user")
            data: dict[str, Any] = {
                key: response.data.get(key) for key in ("id", "login", "name", "type", "html_url")
            }
            data["credential_source"] = credential.source
            scopes = response.headers.get("x-oauth-scopes")
            if scopes:
                data["oauth_scopes"] = [scope.strip() for scope in scopes.split(",") if scope.strip()]
            emit_success(args.command, data, response=response)
            return 0

        target = resolve_repository(args.repo, cwd=args.cwd, default_host=args.host)
        if target.host != args.host.casefold():
            raise GitHubError(
                f"repository host {target.host} differs from --host {args.host}; pass the matching --host explicitly",
                kind="validation",
            )
        if hasattr(args, "owner") and args.owner is None:
            args.owner = target.owner
        data, response = dispatch(args.command, args, client, target)
        pagination = {"returned": len(data)} if isinstance(data, list) else None
        emit_success(args.command, data, target=target, response=response, pagination=pagination)
        return 0
    except GitHubError as exc:
        emit_error(exc)
        return 1
    except KeyboardInterrupt:
        emit_error(GitHubError("operation interrupted", kind="network", retryable=True))
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
