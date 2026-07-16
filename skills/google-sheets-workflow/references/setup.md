# Cloud Console setup (service account, no OAuth consent screen)

One-time, browser-based, done by the user — there is no API to create credentials without
already having credentials. After this, everything is headless.

## 1. Create a project and enable the APIs

1. Open <https://console.cloud.google.com/projectcreate> and create a project (or pick an
   existing one from the project switcher).
2. Open <https://console.cloud.google.com/apis/library/sheets.googleapis.com> and click
   **Enable**.
3. Open <https://console.cloud.google.com/apis/library/drive.googleapis.com> and click
   **Enable** (Drive API is only used for `list` and for auto-sharing spreadsheets `create`s).

## 2. Create the service account and its key

1. Open <https://console.cloud.google.com/iam-admin/serviceaccounts>, pick the project, click
   **Create Service Account**. Any name works (e.g. "sheets-agent"); no roles need to be
   granted at the project level — access comes from sharing individual spreadsheets, not IAM
   roles.
2. Open the new service account → **Keys** tab → **Add Key** → **Create new key** → **JSON**.
   This downloads a `*.json` file — this is the only secret in this whole setup. Do not paste
   its contents anywhere, including chat with an agent.
3. Note the service account's email — it looks like
   `sheets-agent@<project-id>.iam.gserviceaccount.com` — `setup.py check` also reports it back
   as `client_email` after the key is imported.

## 3. Import the key

Give the downloaded file's local path to the agent (or run it yourself):

```bash
python3 scripts/setup.py import-service-account /path/to/downloaded-key.json
```

This copies the file into this skill's config directory with owner-only permissions and never
prints its contents.

## 4. Set the email spreadsheets should be shared back to

```bash
python3 scripts/setup.py set-user-email you@example.com
```

Spreadsheets created by `sheets_api.py create` are auto-shared (Editor) with this address so
they show up in your own Google account, since the service account technically owns them.

**`create` only works on a Google Workspace project** (a Shared Drive, or domain-wide
delegation to impersonate a real user) — the new file needs storage quota to live in, and a
standalone service account on a personal (`@gmail.com`-style) account has none. On a personal
account `create` always fails with `403 The caller does not have permission`; there is no
workaround from this skill's side. If that's your setup, create the spreadsheet yourself in
Sheets and share it with `client_email` (step 5) — `write`/`append`/`batch-update` on existing,
shared spreadsheets are unaffected, since those don't need to create new file storage.

## 5. Share existing spreadsheets

For every spreadsheet you want the agent to read or edit: open it in Google Sheets → **Share**
→ paste the service account's email (`client_email` from `setup.py check`) → **Editor** → Send.
This is the only manual step needed per spreadsheet, and it never expires or needs repeating.

## Storage layout

Two files live in the config directory (`setup.py check`'s `config_dir`):

- `service-account.json` — the secret key, 0600, only ever read to sign a JWT.
- `config.json` — everything non-secret: `client_email` (mirrored from the key, so `check` and
  `known-spreadsheets` never have to open the secret file), `user_email`, and a
  `known_spreadsheets` registry (id → title/URL/last-seen) that `list`/`info`/`create`
  auto-populate, so a spreadsheet used once can be recalled by title without re-pasting its
  link. `setup.py known-spreadsheets` prints it.

## Rotating or revoking a key

Delete the key in Cloud Console (Service Account → Keys → delete), create a new one, and run
`import-service-account` again. To remove everything this skill stored locally:

```bash
python3 scripts/setup.py remove
```

## Why not OAuth2 user consent?

The OAuth "Desktop app" flow needs a real browser and a human clicking **Allow** every time a
token is first issued, and it can browse the user's whole Drive (useful, but out of scope
here). A service account has no consent screen at all — trading full-Drive browsing for a
completely headless flow, which matches sending the agent a specific spreadsheet link rather
than asking it to browse everything you own.
