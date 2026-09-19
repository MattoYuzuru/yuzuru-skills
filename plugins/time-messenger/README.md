# TiMe Messenger

Uses TiMe API v4 through a self-contained semantic MCP server and a portable safety workflow.

## Capabilities

- Bounded chat, message, thread, member, unread, mention, reaction, pin, and file inspection.
- Explicit message, reaction, pin, membership, conversation, read-state, and upload operations.
- Stable-ID resolution, structured pagination, normalized records, and capability reporting.

## Trigger examples

- “Покажи непрочитанные в TiMe, не отмечая их прочитанными.”
- “Найди сообщения о релизе в TiMe.”
- “Отправь этот файл в подтверждённый канал TiMe.”

## Non-trigger examples

- “Проверь Telegram.”
- “Отредактируй локальный Markdown-файл.”

## External effects

Reads never intentionally change read state. Writes require explicit authorization or a narrow
session grant bound to this provider, authenticated account, action family, and stable target.
Destructive actions always require an exact fresh confirmation. Ambiguous writes are not retried.

## Platform support

Codex and Claude Code load the packaged stdio MCP declaration and portable skills. DeepSeek
Harness receives the skills only; its bundle does not currently launch the MCP server. Runtime
credentials are supported through macOS Keychain or explicit environment injection.

## Local testing

Run `python3 -B -m unittest discover -s runtime/tests -v`, then
`yuzuru plugin validate time-messenger`. Complete setup in a private terminal before a live,
read-only smoke test.

## Limitations

TiMe forum topics are not exposed by the verified API surface. Server-specific permissions and
deployment configuration may narrow other capabilities. The package does not reuse the desktop
application's private session or storage.
