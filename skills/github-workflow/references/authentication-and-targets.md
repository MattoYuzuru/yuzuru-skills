# Authentication And Targets

## Setup

Run from the resolved installed skill directory:

```bash
python3 scripts/github.py --help
python3 scripts/github.py auth-check
```

The helper discovers credentials in this order:

1. `GH_TOKEN`;
2. `GITHUB_TOKEN`;
3. `~/.config/yuzuru-codex-skills/github-workflow/token`;
4. `gh auth token --hostname HOST` when `gh` is available.

Never pass a token as an argument. Keep the token file at mode `0600`. The helper
prints the credential source and safe account metadata, not the token.

## Permissions

Prefer a fine-grained PAT limited to the target repository and minimum permissions.

| Operation | Permission |
|---|---|
| Repository metadata/languages | Metadata read; public reads may be anonymous |
| About and topics | Administration write |
| Issues, labels, assignees, milestones | Issues read/write |
| Pull requests | Pull requests read/write |
| HTTPS Git push | Contents write |
| Actions inspection | Actions read |
| Actions rerun/cancel/dispatch | Actions write |
| Push workflow files when required | Workflows write |
| Projects V2 | classic PAT `read:project` or `project`; equivalent app/account permission for other token types |

Endpoint 403 responses are authoritative because organization policy and token type
can change effective permissions.

## Target Resolution

Pass `--repo owner/repo` for an unambiguous target. Without it, the helper inspects
`upstream` and `origin`. If they point to different repositories, pass `--repo`
explicitly. Supported remote forms include HTTPS, SSH URL, and SCP-style Git URLs.

For GitHub Enterprise, pass the matching `--host`; override `--api-url` and
`--graphql-url` only when the installation uses nonstandard endpoints. A repository
host that differs from `--host` is rejected.

Useful global controls:

```bash
python3 scripts/github.py \
  --repo owner/repo \
  --timeout 30 --retries 4 --max-wait 60 \
  repo-info
```

Safe reads retry transient failures with bounded backoff. Writes are sent once.
Rate-limit errors include `retry_after`; do not loop around them manually.
