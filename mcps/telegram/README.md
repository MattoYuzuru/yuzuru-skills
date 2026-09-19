# Telegram MCP runtime

This dependency-free Python MCP server maps bounded semantic messenger tools to the official
TDLib JSON C API. It uses a Telegram user account, not the Bot API.

## Native runtime

The repository currently packages a first-party macOS arm64 build. The exact TDLib commit,
toolchain, dependency versions, and SHA-256 hashes are recorded in `native/manifest.json`.
`build/build_macos_arm64.sh` reproduces the build from the official TDLib repository and a
checksummed CMake release. Linux, Windows, and macOS x86_64 fail closed until equivalent
first-party artifacts are published.

TDLib is licensed under Boost Software License 1.0. The packaged OpenSSL libraries retain the
Apache License 2.0 text. See `licenses/`.

## Local setup

1. Obtain an `api_id` and `api_hash` for your own application at `my.telegram.org`.
2. Run `python3 server.py auth --api-id YOUR_ID` in a private local terminal.
3. Enter the API hash, phone number, login code, and optional 2FA password only at hidden or
   local prompts. Never paste them into an agent conversation.
4. Run `python3 server.py runtime-status`, then configure the host to launch
   `python3 server.py serve` over stdio.

Configuration is stored below the XDG config directory. TDLib state and downloaded file cache
use XDG data/cache directories. The API hash and database encryption key use macOS Keychain;
environment injection is supported for ephemeral non-macOS use. One process may hold a profile
at a time.

Read operations do not call `viewMessages`. Sending waits for TDLib's final success/failure
update, and a timeout is reported as ambiguous rather than retried. Ordinary reply threads and
forum topics remain distinct; exhaustive ordinary-thread listing is explicitly unsupported.
