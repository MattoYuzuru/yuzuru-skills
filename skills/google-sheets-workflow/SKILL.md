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
3. If `service_account_key_configured` is `false`, send the user this exact checklist verbatim
   (don't paraphrase it into a vaguer summary — a vague version reliably produces a
   clarifying-question round-trip):

   ```text
   1. Open https://console.cloud.google.com/projectcreate and create a project (or pick an existing one).
   2. Open https://console.cloud.google.com/apis/library/sheets.googleapis.com and click Enable.
   3. Open https://console.cloud.google.com/apis/library/drive.googleapis.com and click Enable.
   4. Open https://console.cloud.google.com/iam-admin/serviceaccounts, pick the project, click
      "Create Service Account". Any name works; no roles need to be granted.
   5. Open the new service account → Keys tab → Add Key → Create new key → JSON. This downloads
      a file — don't paste its contents anywhere, including this chat.
   6. Tell me the local path of that downloaded file, and the Google account email you want new
      spreadsheets shared back to.
   ```
4. Once they give you the path, run `<python> scripts/setup.py import-service-account <path>`
   yourself — it only ever touches a file path, never the file's contents, so it never exposes
   the key. Never ask the user to paste the key's contents into chat.
5. Once they give you the email, run `<python> scripts/setup.py set-user-email <address>`
   yourself — an email address isn't a secret, this is agent-safe too.
6. Re-run `check`; when `ready` is `true`, note the `client_email` it reports.
7. Before touching any *existing* spreadsheet, send the user this exact checklist (again,
   verbatim, with the real `client_email` substituted in) and wait for the link/ID back:

   ```text
   1. Open the spreadsheet in Google Sheets.
   2. Click "Share" (top-right corner).
   3. Paste this email: <client_email>
   4. Set its role to "Editor" (not "Viewer").
   5. Click "Share" / "Send".
   6. Send me the spreadsheet's link (or just the ID from the URL, between /d/ and /edit).
   ```

   This is a one-time action per spreadsheet, done by the user in their own Sheets UI, not by a
   script. If a command fails with 403/404 on a spreadsheet the user expected to work, this
   checklist is the fix — send it again for that specific spreadsheet.

Read `references/setup.md` only when the user needs more detail than the checklists above.

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
| Format cells, freeze rows, merge cells, build a pivot table | `references/batch-update-recipes.md` | `batch-update <id> --requests <json>` | write |
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

There is no dedicated `pivot-create` command. `batch-update` is the generic escape hatch for
everything beyond plain cell values — pivot tables, cell formatting, freeze panes, merged
cells, conditional formatting, column/row resizing — built from a raw `batchUpdate` requests
array. Read `references/batch-update-recipes.md` for worked request bodies before writing one
from scratch.

## Error Handling

| Status | Cause | Action |
|---|---|---|
| `403` / `404` on a spreadsheet the user expects to work | Not shared with the service account yet | Tell the user to open it and Share it (Editor) with the `client_email` from `setup.py check`, then retry |
| `403 The caller does not have permission` on `create` specifically | The service account has no personal Drive storage quota — normal for accounts outside Google Workspace (no Shared Drive, no domain-wide delegation) | Do not retry. Tell the user this account can't create new spreadsheets via the API; have them create the spreadsheet themselves in Sheets and share it with `client_email`, then use `write`/`append`/`batch-update` on it instead |
| `400 invalid_grant` during auth | Service-account key revoked/deleted in Cloud Console | Ask the user to create a new key and re-run `import-service-account` |
| `429` | Rate limit | The script retries once automatically; if it still fails, wait and retry that one call — don't loop |
| `400` on `write`/`append`/`batch-update` | Malformed range or request body | Fix the payload using the error message; don't retry blindly |

## Guardrails

- Never print the service-account key file, the cached access token, or any file under this
  skill's config directory — only ever pass file *paths* to `setup.py import-service-account`.
- `create`, `write`, `append`, `add-sheet`, and `batch-update` are writes: preview the exact
  command and payload (via `--dry-run`) and get explicit user confirmation before dropping it.
- Before running `write` (it silently overwrites) on a range that isn't provably empty (e.g.
  not a range you just created via `create`/`add-sheet` this turn), run a plain `read` on that
  exact range first and show its current contents next to the intended new values as part of
  the confirmation — one cheap read call, and the only way to catch "this range already has
  data" before it's gone. `append` doesn't need this; it only adds rows.
- `clear`, `delete-sheet`, and `trash` are destructive: confirm the exact spreadsheet id, range,
  or sheet name with the user before running, even after a `--dry-run` preview.
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
