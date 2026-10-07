---
name: google-sheets-workflow
description: Read and update Google Sheets through a service account. Use when a shared spreadsheet needs ranges, formulas, formatting, or pivots; use an available account connector for other access.
---

# Google Sheets Workflow

## Overview

Talks to the Google Sheets and Drive REST APIs through a service account. There is no
browser consent screen and no "Allow" click, ever: `scripts/sheets_config.py` signs a
short-lived JWT with the service account's private key and exchanges it for an access token
over a plain HTTPS call. Access to a specific spreadsheet is granted the same way you'd share
it with a colleague — by adding the service account's email in Sheets' own Share dialog.

Resolve this installed skill directory first; run every command below from there (or address
`scripts/` relative to it).

## Access and setup

Use this route when the target is shared with a service account or that access mode is requested.
Prefer an available account connector when it already has the required spreadsheet access; do not
create a second credential path solely because this skill was selected.

From the installed skill directory, run `python3 scripts/bootstrap.py` if its isolated runtime is
not established, then `<python> scripts/setup.py check` with the returned executable. Read
[references/setup.md](references/setup.md) only when keys, sharing, or creation permissions are missing.
Import a user-provided key by local path; never request its contents in chat.

For an existing spreadsheet, resolve its ID and try the smallest requested read before proposing
sharing changes. If access is missing, ask the user to share it with the reported `client_email`:
Viewer suffices for reads, Editor is needed for writes. Do not ask to repeat setup for a spreadsheet
that is already accessible. A 403/404 needs a target/permission diagnosis, not an automatic grant.

## Routing

| Intent | Read | Run | Effect |
|---|---|---|---|
| See which spreadsheets are already shared with the service account | — | `list` | read |
| Recall a spreadsheet's id from a title/URL seen before, without a fresh API call | — | `setup.py known-spreadsheets` | read |
| Inspect a spreadsheet's tabs/size | — | `info <id>` | read |
| Read one range | `references/ranges-and-values.md` | `read <id> --range <A1>` | read |
| Read several ranges at once | `references/ranges-and-values.md` | `read-batch <id> --ranges <A1,A1,...>` | read |
| Create a new spreadsheet | — | `create --title <title>` (personal/non-Workspace service accounts will get a 403 — see below) | write |
| Write/overwrite a range (values or formulas) | `references/ranges-and-values.md` | `write <id> --range <A1> --values <json>` | write |
| Append rows below existing data | `references/ranges-and-values.md` | `append <id> --range <A1> --values <json>` | write |
| Add a sheet tab | — | `add-sheet <id> --title <title>` | write |
| Format cells, freeze rows, merge cells, build a pivot table | `references/batch-update-recipes.md` | `batch-update <id> --requests-file <json>` | write |
| Clear a range | — | `clear <id> --range <A1>` | destructive |
| Delete a sheet tab | — | `delete-sheet <id> --sheet-id <id>` | destructive |
| Move a spreadsheet to trash | — | `trash <id>` | destructive |

Every command runs as `<python> scripts/sheets_api.py <command> ...`, using the venv python
from `bootstrap.py`. Read only the reference row matching the current task.

`list`, `info`, and `create` each cache the spreadsheet's id/title/URL into a local registry
(`setup.py known-spreadsheets`) as a side effect — check that registry before asking the user
for a link/ID again if they refer to a spreadsheet by name they've used in this skill before.

## Formulas And Values

`write`/`append` default to `--value-input USER_ENTERED`, so `"=SUM(A1:A10)"` is parsed as a
live formula, not stored as literal text — this is almost always what the user wants when they
say "add a formula". Use `--value-input RAW` only when they explicitly want a value preserved
exactly as typed (e.g. a string that happens to start with `=`). See
`references/ranges-and-values.md` for A1 range syntax and `read`'s `--value-render` options.

## Pivot Tables And Formatting

There is no dedicated `pivot-create` command. `batch-update` validates a JSON request file for
non-destructive operations beyond plain cell values: pivot tables, formatting, freeze panes,
merges, conditional formatting, and resizing. It rejects destructive request types; use a
dedicated destructive command instead. Read `references/batch-update-recipes.md` first.

## Error Handling

| Status | Cause | Action |
|---|---|---|
| `403` / `404` on a spreadsheet the user expects to work | Not shared with the service account yet | Tell the user to open it and Share it (Editor) with the `client_email` from `setup.py check`, then retry |
| `403 The caller does not have permission` on `create` specifically | The service account has no personal Drive storage quota — normal for accounts outside Google Workspace (no Shared Drive, no domain-wide delegation) | Do not retry. Tell the user this account can't create new spreadsheets via the API; have them create the spreadsheet themselves in Sheets and share it with `client_email`, then use `write`/`append`/`batch-update` on it instead |
| `400 invalid_grant` during auth | Service-account key revoked/deleted in Cloud Console | Ask the user to create a new key and re-run `import-service-account` |
| `429` on a read | Rate limit | The script retries one GET once; if it still fails, wait rather than looping |
| `429` or timeout on a write | Ambiguous mutation result | Do not retry automatically; read the target state first |
| `400` on `write`/`append`/`batch-update` | Malformed range or request body | Fix the payload using the error message; don't retry blindly |

## Guardrails

- Never print the service-account key file, the cached access token, or any file under this
  skill's config directory — only ever pass file *paths* to `setup.py import-service-account`.
- `create`, `write`, `append`, `add-sheet`, and `batch-update` are writes: preview the exact
  command and payload with `--dry-run`, obtain approval, then add `--confirm-write`.
- Before running `write` (it silently overwrites) on a range that isn't provably empty (e.g.
  not a range you just created via `create`/`add-sheet` this turn), run a plain `read` on that
  exact range first and show its current contents next to the intended new values as part of
  the confirmation — one cheap read call, and the only way to catch "this range already has
  data" before it's gone. `append` doesn't need this; it only adds rows.
- `clear`, `delete-sheet`, and `trash` are destructive: confirm the exact spreadsheet id, range,
  or sheet name after a dry-run, then add `--confirm-destructive`.
- Reads return at most 10,000 cells by default and mark `truncated`; raise `--max-cells` only when
  the task requires the additional context.
- If `create` reports `created-not-shared`, use its returned id and share it manually. Never retry
  `create`, because the spreadsheet already exists.
- `list` only shows spreadsheets already shared with the service account, not the user's whole
  Drive — say so plainly if the user seems to expect otherwise.
- Never invent a `sheetId` or range — resolve it from `info`/`read` first.
- Newly created spreadsheets belong to the service account; `create` auto-shares them with the
  configured user email so they show up for the user — if no user email is configured yet, warn
  the user that the new spreadsheet is currently only visible to the service account.
- `create` only works for service accounts backed by a Google Workspace (Shared Drive or
  domain-wide delegation). On a personal (non-Workspace) account it always fails with
  `403 The caller does not have permission` — there's no fix from this skill's side; the
  workaround is the user creates the spreadsheet by hand and shares it with `client_email`.
