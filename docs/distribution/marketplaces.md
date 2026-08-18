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

## DeepSeek Harness profiles

DeepSeek Harness has no repository marketplace. Its native `dsh plugin --profile` command forwards
to pnpm in an isolated profile and reconciles packages declaring `dsh.bundle.patch` into the profile
layer stack. Install standalone skills and selected plugins from a clone:

```bash
pnpm dsh plugin --profile web add /absolute/path/to/yuzuru-skills/skills
pnpm dsh plugin --profile web add /absolute/path/to/yuzuru-skills/plugins/sde-agent
pnpm dsh plugin --profile web list
```

Pass several local paths to one `add` invocation for an exact finite batch. Repeat for `headless`
only when that profile should expose the same skills. Remove packages by their manifest names, such
as `yuzuru-sde-agent`; do not edit `dsh.profile.bundles` manually.

The absolute checkout path belongs only to the machine-local profile dependency. Published bundle
patches resolve their content through `node_modules/<package>/...`, never a maintainer path. The
provider and watcher load at profile boot; individual skill bodies still use native progressive
disclosure. Profile packages, enabled composition, sessions, credentials, and state stay under the
Harness home and are not repository artifacts.
