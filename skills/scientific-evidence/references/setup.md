# Keyless readiness and optional credentials

Run from the resolved skill directory:

```bash
python3 -B scripts/setup.py check
```

This is a local check: it neither contacts a provider nor validates authentication. It reports
keyless core readiness and optional OpenAlex configuration without revealing values. An absent or
malformed optional key does not prevent Europe PMC, arXiv or Crossref use. No project `.env` is
searched or created. Keys configured for unrelated apps are not inspected.

## When a free key is useful

[OpenAlex authentication](https://help.openalex.org/api/authentication/) describes free keyless
basic use and larger free-key budgets/cursor paging. Offer configuration only for a concrete quota
or graph-search need; missing optional credentials are not a reason to pause other research.

After the user chooses it, give the official link and this command to run in their own terminal:

```bash
python3 -B scripts/setup.py configure openalex
```

The command requires protected terminal input, validates with a small read-only request, then
atomically publishes a private file outside the repository. It never accepts a key in arguments,
prints a key, registers an account or sends an activation email. A non-interactive terminal fails
instead of falling back to echoed input. Never ask the user to paste a key into chat.

`OPENALEX_API_KEY` takes precedence over this skill's stored key. An explicitly empty variable
selects keyless operation. File fallback is `XDG_CONFIG_HOME/scientific-evidence/openalex.key`,
otherwise `~/.config/scientific-evidence/openalex.key`; Windows uses LocalAppData when XDG is unset.
Stored files are private (0600 on POSIX), symlinks/insecure files are rejected, and existing keys
are not silently replaced. API requests use an Authorization header and block origin-changing
redirects. Provider authentication/activation/quota failures remain visible.

Preview configuration with `configure openalex --dry-run`. Removing the skill's exact stored file
requires the explicit destructive action:

```bash
python3 -B scripts/setup.py remove-key openalex --dry-run
python3 -B scripts/setup.py remove-key openalex --confirm-remove
```

Removal does not revoke the provider key or edit an environment variable. Remote rotation,
revocation and account creation are separate user-authorized operations. Never infer permission
for them from a login, a loaded skill or a key's presence.
