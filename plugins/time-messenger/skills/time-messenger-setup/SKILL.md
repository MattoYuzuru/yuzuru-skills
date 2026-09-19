---
name: time-messenger-setup
description: Configure or diagnose the TiMe Messenger MCP connection without exposing credentials. Use when TiMe URL, PAT, Keychain storage, authentication, or runtime startup needs setup.
---

# TiMe Messenger Setup

Keep credential entry in a private local terminal. Never ask the user to paste a PAT into the
conversation, a repository file, a command argument, or an MCP tool call.

## Setup

1. Confirm the exact HTTPS TiMe workspace origin with the user.
2. From the installed plugin root, run
   `python3 runtime/server.py setup --url https://workspace.example`.
3. Let the hidden prompt store the PAT in macOS Keychain. For ephemeral automation, the user may
   instead inject `TIME_MESSENGER_URL` and `TIME_MESSENGER_TOKEN` into the MCP process environment.
4. Restart the host so it reloads `.mcp.json`.
5. Call `time_messenger_get_identity` and `time_messenger_get_capabilities` as a read-only smoke
   test. Do not send, react, pin, or alter read state during setup verification.

## Guardrails

- Accept HTTPS origins only; do not weaken redirect or origin validation.
- Do not inspect TiMe desktop application databases, cookies, memory, or private storage.
- Do not print, log, summarize, or commit secrets.
- Treat missing/revoked credentials as `AUTH_REQUIRED` or `AUTH_REVOKED` and stop.
- A successful login grants service access, not authorization for messenger writes.
