# Repository Architecture

## Design

Yuzuru has three layers:

```text
portable capability
  SKILL.md + references + scripts + assets + schemas
             ↓
thin adapters
  Codex manifest/hooks metadata | Claude manifest/agents/hooks metadata
             ↓
distribution
  repository marketplaces + native platform managers
```

The portable layer owns reasoning, decisions, output expectations, and deterministic operations.
Adapters may expose a capability in a platform-native way, but must not become its only
implementation.

## Ownership

- Standalone skills own their complete runtime folder under `skills/<name>/`.
- Each plugin owns everything required at runtime under `plugins/<plugin-id>/`.
- Repository scripts validate and install; plugin scripts execute plugin workflows.
- Shared artifact schemas are contracts, not runtime libraries.
- `mcps/` is a registry and future server boundary. The first release has no MCP server because
  all requested capabilities are local workflows and do not require persistent authenticated tools.
- `hooks/` documents shared hook policy; runtime hooks remain inside the plugin that ships them.

Installed marketplaces copy packages into platform caches. A plugin may not depend on `../`,
maintainer paths, or a sibling package. Small safety-critical helpers may be duplicated when that
keeps the installed package self-contained.

## Runtime state

Repository CLI state uses XDG locations:

- configuration: `${XDG_CONFIG_HOME:-~/.config}/yuzuru`;
- cache: `${XDG_CACHE_HOME:-~/.cache}/yuzuru`;
- data and managed registry: `${XDG_DATA_HOME:-~/.local/share}/yuzuru`.

Plugin code reads `PLUGIN_DATA` or `CLAUDE_PLUGIN_DATA` when a host provides it. It otherwise uses
the user data directory or a temporary directory. Immutable resources resolve from the script or
plugin root, never from the current working directory.

## Extension points

A future platform adapter adds its own manifest and marketplace validator while reusing existing
skills and scripts. A future MCP server must live under `mcps/<name>/`, declare its owner plugins,
and satisfy the MCP authoring and credential boundaries before any manifest exposes it.
