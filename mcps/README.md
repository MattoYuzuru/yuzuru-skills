# MCP Registry

| Server | Owning plugin | Protocol/runtime | Shipped target |
|---|---|---|---|
| `time-messenger` | `plugins/time-messenger` | TiMe API v4, Python stdio MCP | Python 3 with HTTPS TiMe origin |
| `telegram` | `plugins/telegram` | TDLib JSON C API, Python stdio MCP | macOS arm64 native bundle |

Canonical source and credential-free tests live here. Each owning plugin contains a complete copy
of its runtime because marketplace installation cannot depend on this registry or sibling paths.
Runtime state uses XDG or host data/cache locations, not either source tree.

The Telegram manifest records the exact TDLib commit, build inputs, and artifact hashes. Targets
without a reviewed first-party native artifact fail closed. TiMe and Telegram credentials are
entered locally and stored in the OS keychain where supported; no server reuses desktop app
storage.

Future servers must follow `docs/authoring/mcp.md`, declare owning plugins, and pass isolated tests
before any manifest references them.
