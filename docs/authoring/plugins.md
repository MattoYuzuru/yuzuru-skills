# Plugin Authoring

## Required package

Every `plugins/<id>/` package contains:

- `.codex-plugin/plugin.json`;
- `.claude-plugin/plugin.json`;
- `plugin-version.json`, the canonical version source;
- `README.md`;
- one primary orchestration skill and focused supporting skills;
- deterministic helpers, references, assets, hooks, and agents only when justified.

The directory name and both manifest names must equal the stable plugin identifier. Component paths
start with `./`, remain inside the plugin root, and exist.

## Design workflow

1. Define triggers, non-triggers, use cases, output evidence, effects, and platform limits.
2. Create the package with `yuzuru plugin new` or the approved plugin scaffold.
3. Create each distinct skill with the skill scaffold; remove every placeholder.
4. Implement deterministic helpers and credential-free unit tests.
5. Write the primary skill as a proportional router over supporting skills and references.
6. Add Claude agents only for bounded specialist roles. Keep their source workflow in skills.
   Default `agents/*.md` files are auto-discovered; a manifest `agents` field is for explicit agent
   file paths, not the default directory.
7. Add hooks only for deterministic invariants and test them with fixture input.
8. Add matching marketplace entries and eval contracts.
9. Run `yuzuru plugin validate <id>`, repository tests, and official host validation when present.

## Versioning and identity

Plugin names are external API. Renames require an append-only entry in `schemas/migrations.json`.
Display names may change independently.

`plugin-version.json` is authoritative. Run `python3 scripts/sync_plugin_versions.py --check` in CI
or omit `--check` during an intentional release update. Do not manually diverge the two manifests.

## Packaging boundaries

Marketplace installation copies plugin contents to a cache. Do not reference top-level repository
helpers, sibling plugins, or absolute paths at runtime. Do not use cross-package symlinks even when
one host can dereference them; packages must remain portable to every supported host.

No plugin declares an MCP server unless a real persistent or authenticated tool exists and is
tested. Roadmap capabilities stay in documentation and out of manifests.
