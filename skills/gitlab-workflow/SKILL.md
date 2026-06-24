---
name: gitlab-workflow
description: GitLab repository and merge request workflow for Codex. Use when the user asks to inspect a GitLab project, read merge requests, check pipelines, search code, create a fork workflow, push a branch, or prepare a merge request through GitLab REST API using a local Personal Access Token.
---

# GitLab Workflow

## Overview

Use this skill for GitLab read workflows and controlled fork-based write workflows. Prefer the helper script in `scripts/gitlab_api.py` for API reads so tokens are never pasted into prompts or committed to repositories.

## Authentication

Read a Personal Access Token from one of:

- `GITLAB_TOKEN`
- `GITLAB_PAT`
- `~/.gitlab_token`

The token should have the narrowest scope that supports the requested action. For full project and MR automation, GitLab usually requires `api`.

Never print the token. Never place it in a repository, command transcript, issue, MR description, or code block shown to the user.

## Host And Project

Default host is `https://gitlab.com`. Override with:

```bash
export GITLAB_HOST="https://gitlab.example.com"
```

Project identifiers are namespace paths such as `group/subgroup/repo`. The helper URL-encodes them.

## Read Workflows

Use the helper for compact JSON:

```bash
python3 skills/gitlab-workflow/scripts/gitlab_api.py auth-check
python3 skills/gitlab-workflow/scripts/gitlab_api.py repo-info group/repo
python3 skills/gitlab-workflow/scripts/gitlab_api.py mr-list group/repo --state opened
python3 skills/gitlab-workflow/scripts/gitlab_api.py mr-read group/repo 123
python3 skills/gitlab-workflow/scripts/gitlab_api.py mr-comments group/repo 123
python3 skills/gitlab-workflow/scripts/gitlab_api.py pipeline-list group/repo
python3 skills/gitlab-workflow/scripts/gitlab_api.py pipeline-jobs group/repo 456
python3 skills/gitlab-workflow/scripts/gitlab_api.py code-search group/repo "SomeClass"
python3 skills/gitlab-workflow/scripts/gitlab_api.py mr-diff group/repo 123
```

After reading raw JSON, summarize only the fields needed for the user's task.

## Fork-Based Write Workflow

Use write operations only after the user confirms the target project, branch, commit message, and MR title.

1. Read project info and default branch.
2. Create or reuse a fork.
3. Clone the fork locally with token-safe credential handling or use the user's existing checkout.
4. Add upstream remote.
5. Create a feature branch.
6. Apply edits, test, commit, and push to the fork.
7. Create an MR targeting upstream.

The helper currently covers API reads, `fork-create`, and `mr-create`; use `git` for local clone, commit, and push.

```bash
python3 skills/gitlab-workflow/scripts/gitlab_api.py fork-create group/repo
python3 skills/gitlab-workflow/scripts/gitlab_api.py mr-create group/repo \
  --source-branch feature/example \
  --target-branch main \
  --title "Describe the change" \
  --description "Short MR description"
```

## Guardrails

- Do not push directly to upstream unless the user explicitly asks and has confirmed the exact remote and branch.
- Do not use `--force` push without a separate explicit confirmation.
- Do not delete branches, close MRs, approve MRs, or resolve discussions without a separate confirmation.
- Do not create repositories from this skill.
- Treat 401/403/404 as access or token problems; do not attempt bypasses.
- Keep the token outside this repository.

