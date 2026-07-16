---
name: google-sheets-workflow
description: Google Sheets read/write workflow via a service account: list spreadsheets shared with it, read and write cell ranges and formulas, create spreadsheets, and edit structure through batchUpdate (formatting, pivot tables, sheet tabs). Use when the user asks to read, write, or summarize data in a Google Sheet, create a new spreadsheet, or build a pivot table/summary from spreadsheet data.
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

## Setup

1. Run `python3 scripts/bootstrap.py` once per machine. It creates/reuses an isolated venv and
   installs `google-auth` (needed only to RSA-sign the token). Use the `python` path from its
   JSON output for every command below.
2. Run `<python> scripts/setup.py check`.
3. If `service_account_key_configured` is `false`, tell the user to:
   - open the `setup_url` it reports (Cloud Console → IAM & Admin → Service Accounts);
   - create a project if needed, then enable the **Google Sheets API** and **Google Drive API**;
   - create a Service Account, add a JSON key, and download it;
   - tell you the local path of the downloaded file.
4. Run `<python> scripts/setup.py import-service-account <path>` yourself once you have that
   path — it only ever touches a file path, never the file's contents, so it never exposes the
   key. Never ask the user to paste the key's contents into chat.
5. Once they tell you the Google account email spreadsheets should be shared back to, run
   `<python> scripts/setup.py set-user-email <address>` yourself — an email address isn't a
   secret, this is agent-safe too.
6. Re-run `check`; when `ready` is `true`, note the `client_email` it reports.
7. Before touching any *existing* spreadsheet, confirm the user has shared it with that
   `client_email` (Editor, via Sheets' Share button) — a one-time action per spreadsheet, done
   by the user in their own Sheets UI, not by a script. If a command fails with 403/404, this is
   the most likely cause.

Read `references/setup.md` only when the user needs the exact click-path through Cloud Console.

## Routing

| Intent | Read | Run | Effect |
|---|---|---|---|
| See which spreadsheets are already shared with the service account | — | `list` | read |
| Inspect a spreadsheet's tabs/size | — | `info <id>` | read |
| Read one range | `references/ranges-and-values.md` | `read <id> --range <A1>` | read |
| Read several ranges at once | `references/ranges-and-values.md` | `read-batch <id> --ranges <A1,A1,...>` | read |
| Create a new spreadsheet | — | `create --title <title>` | write |
| Write/overwrite a range (values or formulas) | `references/ranges-and-values.md` | `write <id> --range <A1> --values <json>` | write |
| Append rows below existing data | `references/ranges-and-values.md` | `append <id> --range <A1> --values <json>` | write |
| Add a sheet tab | — | `add-sheet <id> --title <title>` | write |
| Format cells, freeze rows, merge cells, build a pivot table | `references/batch-update-recipes.md` | `batch-update <id> --requests <json>` | write |
| Clear a range | — | `clear <id> --range <A1>` | destructive |
| Delete a sheet tab | — | `delete-sheet <id> --sheet-id <id>` | destructive |
| Move a spreadsheet to trash | — | `trash <id>` | destructive |

Every command runs as `<python> scripts/sheets_api.py <command> ...`, using the venv python
from `bootstrap.py`. Read only the reference row matching the current task.

## Formulas And Values

`write`/`append` default to `--value-input USER_ENTERED`, so `"=SUM(A1:A10)"` is parsed as a
live formula, not stored as literal text — this is almost always what the user wants when they
say "add a formula". Use `--value-input RAW` only when they explicitly want a value preserved
exactly as typed (e.g. a string that happens to start with `=`). See
`references/ranges-and-values.md` for A1 range syntax and `read`'s `--value-render` options.

## Pivot Tables And Formatting

There is no dedicated `pivot-create` command. `batch-update` is the generic escape hatch for
everything beyond plain cell values — pivot tables, cell formatting, freeze panes, merged
cells, conditional formatting, column/row resizing — built from a raw `batchUpdate` requests
array. Read `references/batch-update-recipes.md` for worked request bodies before writing one
from scratch.

## Error Handling

| Status | Cause | Action |
|---|---|---|
| `403` / `404` on a spreadsheet the user expects to work | Not shared with the service account yet | Tell the user to open it and Share it (Editor) with the `client_email` from `setup.py check`, then retry |
| `400 invalid_grant` during auth | Service-account key revoked/deleted in Cloud Console | Ask the user to create a new key and re-run `import-service-account` |
| `429` | Rate limit | The script retries once automatically; if it still fails, wait and retry that one call — don't loop |
| `400` on `write`/`append`/`batch-update` | Malformed range or request body | Fix the payload using the error message; don't retry blindly |

## Guardrails

- Never print the service-account key file, the cached access token, or any file under this
  skill's config directory — only ever pass file *paths* to `setup.py import-service-account`.
- `create`, `write`, `append`, `add-sheet`, and `batch-update` are writes: preview the exact
  command and payload (via `--dry-run`) and get explicit user confirmation before dropping it.
- `clear`, `delete-sheet`, and `trash` are destructive: confirm the exact spreadsheet id, range,
  or sheet name with the user before running, even after a `--dry-run` preview.
- `list` only shows spreadsheets already shared with the service account, not the user's whole
  Drive — say so plainly if the user seems to expect otherwise.
- Never invent a `sheetId` or range — resolve it from `info`/`read` first.
- Newly created spreadsheets belong to the service account; `create` auto-shares them with the
  configured user email so they show up for the user — if no user email is configured yet, warn
  the user that the new spreadsheet is currently only visible to the service account.
