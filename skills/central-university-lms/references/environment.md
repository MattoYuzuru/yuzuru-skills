# Environment Setup

Read this reference only when setting up a new device, resolving TLS inspection, or considering headless operation.

## Portable Runtime

Run `python3 scripts/bootstrap.py` from the resolved skill directory. It creates or reuses one venv
in the OS cache directory and installs the repository-pinned Playwright version:

- macOS/Linux: `~/.cache/yuzuru-codex-skills/central-university-lms/venv` unless `XDG_CACHE_HOME` is set.
- Windows: `%LOCALAPPDATA%\\yuzuru-codex-skills\\central-university-lms\\venv`.

Set `CENTRAL_UNIVERSITY_LMS_VENV` or pass `--venv` to choose another location. Use the `python` field from the command's JSON output for all later commands. Do not install into the system Python or commit the venv.

## Authentication and Browser Mode

Run `login` headed on a device where the user can complete authentication and any CAPTCHA. Keep the storage-state file outside the repository and protect it with user-only filesystem permissions.

After a valid state exists, API-only commands (`session-check`, `list-courses`, `course-overview`,
`course-progress`, `deadlines`, `task-details`, `api-health`, and `export-pending`) run headlessly by
default; this was verified against the LMS API. Pass `--headed` only for diagnostics. Do not use
headless mode to establish or refresh a session. If a command returns `reauth_required`, ask the
user to re-authenticate rather than trying to bypass the CAPTCHA.

## TLS Inspection

The Playwright request client uses Node.js TLS settings, so it may not automatically trust a corporate inspection certificate that the browser trusts. Export a PEM bundle through `NODE_EXTRA_CA_CERTS`:

```bash
export NODE_EXTRA_CA_CERTS=/path/to/trusted-corporate-root.pem
```

Use the organization's approved certificate export procedure for the host OS. On macOS, a bundle can be created from the system keychains; on Linux or Windows, use the corporate root PEM supplied by IT. Never disable TLS verification.
