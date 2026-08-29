---
name: github-workflow
description: GitHub repository, issue, Projects V2, pull request, review, merge, and Actions workflow through local Git plus GitHub REST and GraphQL APIs without MCP. Use when the user asks to inspect or update GitHub, work with a project board, manage issues or pull requests, review or merge a PR, push a feature branch, check or retry Actions, or carry a local change to a verified GitHub PR.
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
4. Determine whether authorization is interactive or a task-scoped mandate. Record
   the repository/work item, outcome, allowed lifecycle effects, and stop conditions.
5. For a mutation, run `--dry-run` and surface its exact target and effect. Execute
   without pausing when an unchanged mandate covers it; otherwise obtain explicit
   confirmation. A short “merge it” covers only the unchanged preview just shown.
6. Execute once. Do not automatically retry a mutating request.
7. Read the object again when the helper does not already verify it.
8. Return compact state, IDs, URLs, checks, and any partial failure.

## Effects

- Run reads without confirmation when they are already in user scope.
- Treat push, About/topic changes, issue/PR/Project changes, workflow dispatch,
  and reruns as external writes that require explicit authorization.
- Treat issue/PR close, PR merge, run cancel, branch deletion, and force updates
  as destructive. Require the exact target and action.
- Treat branch creation, file edits, tests, and commits as local work authorized
  by an explicit coding task. Inspect before `pull --ff-only` changes the checkout.
- A request to carry a bounded repository change end to end may authorize its
  feature-branch pushes, PR creation/updates, CI remediation, repository-required
  work-item updates, and merge when the user explicitly includes merge or shipping.
  Generated branch, PR, run, and SHA identifiers remain inside that finite mandate.
- Bind every review and merge request to the current repository, PR number, head
  SHA, and method. In-scope agent-authored follow-up commits do not expire a task
  mandate; an unrelated target, material scope change, or another actor's change does.
- Do not infer production deployment, branch deletion, force update, PR/issue close,
  or unrelated publication from ordinary end-to-end development authorization.
- A subagent verdict is review evidence, never user authorization or a separate
  GitHub identity.

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
