# Marketplace Installation and Management

The repository exposes the same nine stable plugin IDs from two catalogs:

- Codex: `.agents/plugins/marketplace.json`;
- Claude Code: `.claude-plugin/marketplace.json`.

## Register

From the clone:

```bash
yuzuru marketplace add --agent codex
yuzuru marketplace add --agent claude
```

Equivalent native commands:

```bash
codex plugin marketplace add .
claude plugin marketplace add .
```

Install one plugin:

```bash
yuzuru plugin install discovery-agent --agent codex
yuzuru plugin install discovery-agent --agent claude
```

## Refresh and inspect

```bash
yuzuru marketplace status
yuzuru marketplace update --agent codex
yuzuru marketplace update --agent claude
yuzuru plugin list
```

Codex calls refresh `upgrade`; Claude calls it `update`. The wrapper preserves each native manager
as authority.

Claude supports non-interactive enable and disable. Current Codex CLI requires `/plugins`; the
wrapper reports that interaction instead of editing user configuration.

Removing a Claude marketplace also uninstalls plugins installed from it; Codex owns its equivalent
cache/config behavior. The wrapper previews the native command with `--dry-run`; execution occurs
only when the user explicitly invokes removal.
Marketplace files remain source catalogs in Git and never store installed or enabled state.

`yuzuru plugin uninstall ... --agent claude` passes `--keep-data` to preserve persistent plugin
data. Purging user data remains an explicit native-manager action outside the wrapper.
