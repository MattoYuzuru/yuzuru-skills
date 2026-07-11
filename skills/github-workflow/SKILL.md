---
name: github-workflow
description: GitHub repository, issue, pull request, and Actions workflow through local Git plus GitHub REST and GraphQL APIs without MCP. Use when the user asks to inspect or update a GitHub repository, manage issues or pull requests, push a feature branch, check or retry GitHub Actions, or carry a change from a local checkout to a verified GitHub PR.
---

# GitHub Workflow

## Overview

Connect local Git work with GitHub repository metadata, issues, Projects V2,
pull requests, and Actions. Use `scripts/github.py` for bounded REST and GraphQL
operations. Use `git` directly for local history and transport; do not require MCP.

Resolve the installed skill directory and run helper commands from it. Keep
multi-line Markdown in a UTF-8 file and pass `--body-file`; use `--body-file -`
for stdin.

## Routing

| Intent | Read | Run | Effect |
|---|---|---|---|
| Authenticate or resolve host/repository | `references/authentication-and-targets.md` | `auth-check`, global options | read |
| Inspect About/languages or perform local Git/push | `references/repositories-and-git.md` | `repo-*`, `git` | mixed |
| Search or manage issues, milestones, labels, Projects V2 | `references/issues-and-projects.md` | `issue-*`, `project-*` | mixed |
| Detect or manage a pull request | `references/pull-requests.md` | `pr-*`, `branch-delete` | mixed |
| Inspect, watch, diagnose, rerun, dispatch, or cancel Actions | `references/actions.md` | `workflow-*`, `run-*`, `job-*` | mixed |

Read only the selected reference. For a feature lifecycle, start with the
repository/Git route, then load the PR and Actions references only when reaching
those stages.

## Workflow

1. Resolve the installed skill directory and target repository.
2. Inspect the repository, local status, branch, remotes, and relevant GitHub object.
3. Preserve unrelated local changes; use the repository's own tests.
4. For a mutation, run `--dry-run` and show its exact target and effect.
5. Obtain explicit confirmation for each external write. Obtain exact confirmation
   for destructive operations.
6. Execute once. Do not automatically retry a mutating request.
7. Read the object again when the helper does not already verify it.
8. Return compact state, IDs, URLs, checks, and any partial failure.

## Effects

- Run reads without confirmation when they are already in user scope.
- Treat push, About/topic changes, issue/PR/Project changes, workflow dispatch,
  and reruns as external writes. Require a separate explicit confirmation.
- Treat issue/PR close, PR merge, run cancel, branch deletion, and force updates
  as destructive. Require the exact target and action.
- Treat branch creation, file edits, tests, and commits as local work authorized
  by an explicit coding task. Inspect before `pull --ff-only` changes the checkout.
- Accept a pre-authorized batch only when the user named every target and action;
  never extend it silently.

## Guardrails

- Never print, log, or place a GitHub token in a repository or command argument.
- Never use a raw API escape hatch to bypass command validation.
- Never use `git push --force`; use `--force-with-lease` only after exact confirmation.
- Never bypass branch protection, required reviews, status checks, 2FA, or access controls.
- Never infer `main` or `master`; read the repository default branch.
- Never claim to delete an issue or pull request. GitHub supports closing them;
  branch deletion is a separate destructive action.
- Stop on 401/403/404 or repeated validation failures. Ask for credentials,
  permissions, target clarification, or user action instead of bypassing controls.
