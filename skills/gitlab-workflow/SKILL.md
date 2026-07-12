---
name: gitlab-workflow
description: GitLab repository and merge request workflow. Use when the user asks to inspect a GitLab project, browse its files, read merge requests or discussions, check pipelines or job logs, search code, comment on or resolve an MR discussion, create a fork workflow, push a branch, or prepare a merge request through GitLab REST API using a local Personal Access Token.
---

# GitLab Workflow

## Overview

Use this skill for GitLab read workflows and controlled write workflows. Prefer the helper script in `scripts/gitlab_api.py` for every API call so tokens are never pasted into prompts or committed to repositories. Resolve this skill's installed directory before running the examples below; run commands from that directory (or address `scripts/gitlab_api.py` relative to it).

## Authentication

Read a Personal Access Token from one of:

- `GITLAB_TOKEN`
- `GITLAB_PAT`
- `~/.gitlab_token`

The token should have the narrowest scope that supports the requested action. For full project and MR automation, GitLab usually requires `api`.

Never print the token. Never place it in a repository, command transcript, issue, MR description, or code block shown to the user.

## Host And Project

Default host is `https://gitlab.tcsbank.ru`. Override with:

```bash
export GITLAB_HOST="https://gitlab.example.com"
```

Project identifiers are namespace paths such as `group/subgroup/repo`. The helper URL-encodes them.

## Routing

| Intent | Run | Effect |
|---|---|---|
| Check token / current user | `auth-check` | read |
| Inspect a project | `repo-info <project>` | read |
| Browse the repository tree | `tree <project> [--path] [--ref] [--recursive]` | read |
| Read a file's raw contents | `file-raw <project> <file_path> [--ref]` | read |
| Get a heading outline of Markdown files | `file-outline <project> <file_path...> [--ref] [--max-level]` | read |
| List commits | `commit-list <project> [--ref] [--per-page]` | read |
| Read one commit | `commit-read <project> <sha>` | read |
| List merge requests | `mr-list <project> [--state]` | read |
| Inspect a merge request | `mr-read <project> <iid>` | read |
| Read MR discussions/comments | `mr-comments <project> <iid>` | read |
| Get an MR's diff | `mr-diff <project> <iid>` | read |
| List pipelines | `pipeline-list <project>` | read |
| List a pipeline's jobs | `pipeline-jobs <project> <pipeline_id>` | read |
| Read a job's CI log | `job-trace <project> <job_id>` | read |
| Search code | `code-search <project> <query>` | read |
| Fork a project | `fork-create <project>` | write |
| Create a merge request | `mr-create <project> --source-branch ... --target-branch ... --title ...` | write |
| Post a general MR note | `mr-note-create <project> <iid> --body <text>` | write |
| Reply inside an MR discussion thread | `mr-discussion-reply <project> <iid> <discussion_id> --body <text>` | write |
| Resolve/unresolve an MR discussion | `mr-discussion-resolve <project> <iid> <discussion_id> [--unresolve]` | destructive |

## Read Workflows

Use the helper for compact JSON:

```bash
python3 scripts/gitlab_api.py auth-check
python3 scripts/gitlab_api.py repo-info group/repo
python3 scripts/gitlab_api.py tree group/repo --path src --ref main
python3 scripts/gitlab_api.py file-raw group/repo path/to/file.py --ref main
python3 scripts/gitlab_api.py file-outline group/repo README.md docs/guide.md
python3 scripts/gitlab_api.py commit-list group/repo --ref main --per-page 20
python3 scripts/gitlab_api.py commit-read group/repo <sha>
python3 scripts/gitlab_api.py mr-list group/repo --state opened
python3 scripts/gitlab_api.py mr-read group/repo 123
python3 scripts/gitlab_api.py mr-comments group/repo 123
python3 scripts/gitlab_api.py mr-diff group/repo 123
python3 scripts/gitlab_api.py pipeline-list group/repo
python3 scripts/gitlab_api.py pipeline-jobs group/repo 456
python3 scripts/gitlab_api.py job-trace group/repo 789
python3 scripts/gitlab_api.py code-search group/repo "SomeClass"
```

After reading raw JSON (or a raw job trace/file), summarize only the fields needed for the user's task.

## MR Discussion And Comment Write Workflow

`mr-note-create`, `mr-discussion-reply`, and `mr-discussion-resolve` are publish actions: they are visible to
every collaborator on the target project the moment they run. Only run one of these commands after the user has
explicitly asked for that specific action in this conversation — never post a comment, reply to a thread, or
resolve/unresolve a discussion proactively just because it seems helpful while reviewing an MR.

```bash
python3 scripts/gitlab_api.py mr-note-create group/repo 123 --body "Looks good, one nit below."
python3 scripts/gitlab_api.py mr-discussion-reply group/repo 123 <discussion_id> --body "Fixed in the latest push."
python3 scripts/gitlab_api.py mr-discussion-resolve group/repo 123 <discussion_id>
python3 scripts/gitlab_api.py mr-discussion-resolve group/repo 123 <discussion_id> --unresolve
```

Resolving/unresolving is a state change other reviewers rely on to track review progress — confirm the exact
discussion (quote the thread you are resolving) before running `mr-discussion-resolve`.

## Fork-Based Write Workflow

Use write operations only after the user confirms the target project, branch, commit message, and MR title.

1. Read project info and default branch.
2. Create or reuse a fork.
3. Clone the fork locally with token-safe credential handling or use the user's existing checkout.
4. Add upstream remote.
5. Create a feature branch.
6. Before committing, run `git log --oneline -n 10` in the target repository and match its existing commit
   message style and format (conventional commits, ticket prefixes, sentence case, etc. — whatever that repo
   already does). Never add a `Co-Authored-By: Claude`, `Co-Authored-By: Codex`, or similar AI-attribution
   trailer to any commit this skill authors, even if that is this repository's own habit elsewhere.
7. Apply edits, test, commit, and push to the fork.
8. Create an MR targeting upstream.

The helper currently covers API reads, `fork-create`, and `mr-create`; use `git` for local clone, commit, and push.

```bash
python3 scripts/gitlab_api.py fork-create group/repo
python3 scripts/gitlab_api.py mr-create group/repo \
  --source-branch feature/example \
  --target-branch main \
  --title "Describe the change" \
  --description "Short MR description"
```

## Guardrails

- Reads are unrestricted. Every write or destructive action (`fork-create`, `mr-create`, `mr-note-create`,
  `mr-discussion-reply`, `mr-discussion-resolve`, any `git push`) requires the user to have asked for that
  specific action first in this conversation — never perform one proactively, even mid-task, even if it looks
  like the obviously helpful next step.
- Do not push directly to upstream unless the user explicitly asks and has confirmed the exact remote and branch.
- Do not use `--force` push without a separate explicit confirmation.
- Do not delete branches, close MRs, approve MRs, or resolve discussions without a separate confirmation of the
  exact discussion.
- Do not create repositories from this skill.
- Treat 401/403/404 as access or token problems; do not attempt bypasses.
- Keep the token outside this repository.
