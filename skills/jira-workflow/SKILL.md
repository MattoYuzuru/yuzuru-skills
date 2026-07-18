---
name: jira-workflow
description: Jira Data Center and Server issue workflow: read, search, create, link, and transition issues through REST API v2 using a local Personal Access Token. Use when the user asks to inspect a self-managed Jira issue, search via JQL, create an epic/feature/task, link issues, or move an issue's status.
---

# Jira Workflow

## Overview

Use this skill for self-managed Jira Data Center/Server read workflows and controlled writes. It
does not implement Jira Cloud authentication or REST v3. Prefer the helper script in
`scripts/jira_api.py` for every API call so tokens are never pasted into prompts or committed to
repositories. Resolve this skill's installed directory before running the examples below; run
commands from that directory (or address `scripts/jira_api.py` relative to it).

## Authentication

`~/.jira.env` holds all three variables together:

```bash
JIRA_PAT=<personal access token>
JIRA_HOST=<instance-hostname>   # e.g. jira3.example.com, no scheme
PROJECT_KEY=<default project key>   # e.g. LP
```

`JIRA_PAT`, `JIRA_HOST`, and `PROJECT_KEY` environment variables take precedence over the file when
set. `--env-file <path>` overrides the default `~/.jira.env` location.

If `JIRA_PAT` is missing, tell the user to create the file (`chmod 600 ~/.jira.env`) with a
Personal Access Token generated from `https://<instance>/secure/ViewProfile.jspa` → Personal Access
Tokens. Never print the token or place it in a repository, command transcript, issue, or code block
shown to the user.

If `JIRA_HOST` or `PROJECT_KEY` is missing, ask the user once for the real values (they differ per
team — never assume the example values above) and append them to `~/.jira.env`. Never overwrite an
existing `JIRA_PAT` while doing this.

## Routing

| Intent | Run | Effect |
|---|---|---|
| Check token / current user | `auth-check` | read |
| Read an issue | `read <key>` | read |
| Search issues via JQL | `search --jql <jql> [--fields] [--max-results]` | read |
| Inspect creation metadata (fields per issue type) | `createmeta [--project] [--issuetype-name ...]` | read |
| List issue link types | `link-types` | read |
| List an issue's available transitions | `transitions <key>` | read |
| List open epics | `epics-open [--project] [--max-results]` | read |
| Create an issue, epic, or sub-task | `create --project --issuetype-id --summary [--description] [--field KEY=VALUE ...]` | write |
| Decompose an epic into sub-tasks | workflow built from `read` + repeated `create` (see below) | write |
| Link two issues | `link --type --inward --outward [--dry-run]` | write |
| Move an issue's status | `move-status <key> --transition-id <id> [--dry-run]` | write |
| Quality-check an issue before Review | workflow built from `read` + `references/task-quality-checklist.md` | read |

## Read Workflows

```bash
python3 scripts/jira_api.py auth-check
python3 scripts/jira_api.py read LP-123
python3 scripts/jira_api.py search --jql "assignee = currentUser() AND status != Done ORDER BY updated DESC"
python3 scripts/jira_api.py createmeta --project LP --issuetype-name Feature
python3 scripts/jira_api.py link-types
python3 scripts/jira_api.py transitions LP-123
python3 scripts/jira_api.py epics-open --project LP
```

`read` returns a compact summary (key, summary, status, type, priority, assignee, reporter, dates,
and a truncated description) — never a hardcoded Epic Link field, since that custom field id
differs per instance. If you need the Epic Link (or any other custom field), read it from
`createmeta` first.

## Creating Issues And Epics

1. Determine the issue type (Epic, Feature, Engineering Task, Idea) and, for Epic/Feature, the
   subtype (Business/Technical). Ask the questions in `references/question-bank.md`, grouped in the
   blocks it defines, before drafting anything.
2. Run `createmeta --project <KEY> --issuetype-name <Name>` to get the real field ids and any
   `allowed_values` for that issue type in that project. Never invent a project-specific custom
   field id — always resolve it from `createmeta`.
3. Build the description in Jira wiki markup from the matching template: `references/template-epic.md`,
   `references/template-feature.md`, `references/template-engineering-task.md`, or
   `references/template-idea.md`. See `references/jira-markup.md` for markup syntax.
4. Preview the exact payload (project, issue type, summary, description's first ~300 characters, and
   every custom field) and get explicit user confirmation before creating anything.
5. Run `create` with `--field KEY=VALUE` repeated for every custom/required field surfaced by
   `createmeta` — plain strings pass through as-is, and JSON object/array syntax is parsed, e.g.:

```bash
python3 scripts/jira_api.py create --project LP --issuetype-id 10001 \
  --summary "Add search filters" \
  --description "{panel:title=What we're doing|borderColor=#cccccc|titleBGColor=#d5e8d4}\n...\n{panel}" \
  --field customfield_10102=LP-100 \
  --field 'customfield_10481={"id": "500"}' \
  --dry-run
```

After confirmation, replace `--dry-run` with `--confirm-write`.

## Epic Decomposition

There is no dedicated subcommand — this is a workflow composed from existing commands:

1. `read <epic-key>` to get the epic's summary and description.
2. Propose a sub-task breakdown as a Markdown table:

   ```markdown
   ## Decomposition of <EPIC_KEY>: <summary>

   | # | Type | Title | Description | Epic link |
   |---|------|-------|--------------|-----------|
   | 1 | Feature | ... | ... | <EPIC_KEY> |
   | 2 | Engineering Task | ... | ... | <EPIC_KEY> |
   ```

3. Get explicit user confirmation of the proposed table before creating anything.
4. For each confirmed row, run `create` once, linking it to the epic through whichever field
   `createmeta` reports for that issue type (native sub-tasks use `parent`, standalone
   Feature/Engineering Task issues typically use the Epic Link custom field instead):

```bash
python3 scripts/jira_api.py create --project LP --issuetype-id <id> \
  --summary "<sub-task title>" \
  --description "<description>" \
  --field 'parent={"key": "LP-100"}' \
  --dry-run
```

5. After creation, report the new issue keys back to the user.

## Quality Check

See `references/task-quality-checklist.md` for the full checklist and required output format.
`read` the issue, evaluate it against the checklist, and return the PASS/WARN/FAIL report in the
exact Markdown format the reference specifies — do not invent fields that aren't in the issue or in
`createmeta`.

## Error Handling

| Status | Cause | Action |
|---|---|---|
| `401` | Token expired | Ask the user to generate a new PAT |
| `403` | Insufficient permissions | Report the permission gap, don't attempt a bypass |
| `404` | Issue or project not found | Recheck the key |
| `400` + `"Field ... is required"` | Missing required field | Add it from the error message |
| `400` + `"allowedValues"` | Invalid id for a field | Take the id from `createmeta` |
| `5xx` on `create` / `link` / `move-status` | Not always a true failure — Jira Server can return a gateway timeout after the write already succeeded server-side | Before retrying, search JQL for a possible duplicate (below). Found → report the existing key, do not create again. Not found → retry once; if it fails again, stop and report to the user instead of looping |

5xx dedupe check before retrying a `create`:

```bash
python3 scripts/jira_api.py search --jql 'project = LP AND reporter = currentUser() AND summary ~ "<exact summary>" AND created >= -10m'
```

## Guardrails

- Never create, link, or transition an issue without previewing the exact payload with `--dry-run`.
  After approval, execute once with `--confirm-write`; the helper never retries mutations.
- Never invent a project-specific custom field id — always resolve it via `createmeta` first.
- `createmeta` uses the Jira 9+ granular per-project/per-issue-type endpoints, not the removed
  aggregate endpoint.
- Use only an HTTPS Jira origin. Cross-origin redirects are rejected to protect the PAT.
- Never retry `create` after a `5xx` response without checking JQL for a possible duplicate first —
  an unconditional retry can create duplicate issues.
- Prefer forward-only status transitions. A transition that closes or cancels an issue requires a
  second explicit confirmation naming the exact transition before running `move-status`.
- Keep the token outside this repository; never print it.
- This skill does not fork repositories, review code, or push branches (see `gitlab-workflow`), and
  does not touch Confluence/Wiki or time tracking.
