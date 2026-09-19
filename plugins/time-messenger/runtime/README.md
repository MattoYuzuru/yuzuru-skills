# TiMe Messenger MCP runtime

This dependency-free Python MCP server maps bounded semantic messenger tools to TiMe API v4.
It keeps provider IDs intact, separates reads from explicit read-state mutation, and returns
structured unsupported outcomes for capabilities TiMe does not expose, including forum topics.

## Local setup

Run `python3 server.py auth --base-url https://YOUR-TIME-HOST` in a private local terminal and
enter a personal access token at the hidden prompt. On macOS the token is stored in Keychain;
`TIME_MESSENGER_URL` and `TIME_MESSENGER_TOKEN` are also accepted for ephemeral execution. Persistent settings
use the XDG config directory, never the clone or plugin root.

Run `python3 server.py serve` for MCP over stdio, then use the identity and capability tools for a
read-only check. Requests are restricted to the configured HTTPS origin. Reads may use bounded
retries; mutations are never retried automatically because a timeout may be ambiguous.
