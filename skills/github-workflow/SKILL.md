---
name: github-workflow
description: GitHub repository, issue, pull request, and Actions workflow through local Git plus GitHub REST and GraphQL APIs without MCP. Use when the user asks to inspect or update a GitHub repository, manage issues or pull requests, push a feature branch, check or retry GitHub Actions, or carry a change from a local checkout to a verified GitHub PR.
---

# GitHub Workflow

## Overview

Use this skill to connect local Git work with GitHub repository metadata, issues,
pull requests, Projects V2, and Actions. Use the bundled Python helper for API
operations; use `git` directly for local history and transport operations.

## Workflow

1. Resolve this installed skill directory before running bundled helpers.
2. Resolve the GitHub repository from an explicit target or the local checkout.
3. Inspect state before proposing a mutation.
4. Obtain the required confirmation for every external write.
5. Verify a successful mutation with a read and return compact links and state.

## Guardrails

- Classify external operations as read, write, or destructive.
- Require explicit authorization for writes and exact authorization for destructive actions.
- Never print, log, or place a GitHub token in a repository or command argument.
- Never force-push, merge, close, cancel, or delete a branch implicitly.
