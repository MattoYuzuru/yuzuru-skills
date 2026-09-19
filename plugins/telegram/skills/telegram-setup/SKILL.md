---
name: telegram-setup
description: Configure, authorize, or diagnose the Telegram TDLib MCP session without exposing credentials. Use when api_id, api_hash, login, 2FA, Keychain, profile locking, or native runtime setup is needed.
---

# Telegram Setup

Use official TDLib user authorization. Never use a bot token, copy Telegram Desktop session files,
or ask the user to paste an API hash, login code, or 2FA password into the conversation.

## Setup

1. Ask the user to create or select their own Telegram application at `my.telegram.org` and retain
   its numeric `api_id` and secret `api_hash` locally.
2. From the installed plugin root, run `python3 runtime/server.py runtime-status`.
3. On supported macOS arm64, run `python3 runtime/server.py auth --api-id NUMBER` in a private
   terminal. Enter the API hash, phone number, login code, and optional 2FA password only there.
4. Restart the host so `.mcp.json` opens the encrypted TDLib profile.
5. Call `telegram_auth_status`, `telegram_get_identity`, and `telegram_get_capabilities` for a
   read-only smoke test. Do not send or change read state during setup verification.

## Storage and lifecycle

Configuration, encrypted TDLib state, and downloaded-file cache use XDG directories. macOS
Keychain stores the API hash and stable database encryption key. `TELEGRAM_PROFILE` selects a
lowercase profile; a process lock prevents concurrent writers to one profile.

## Guardrails

- The packaged native matrix currently supports macOS arm64 and fails closed elsewhere.
- Do not rebuild or download native code at runtime.
- Do not print, log, summarize, or commit authentication material.
- Treat authorization as account access only, never as permission for messenger writes.
