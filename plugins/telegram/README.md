# Telegram

Uses an official pinned TDLib user session through a self-contained semantic MCP server.

## Capabilities

- Bounded chats, history, search, members, unread state, mentions, reactions, pins, and files.
- Explicit messaging, forwarding, reactions, pins, membership, chat, topic, and read-state tools.
- Separate ordinary reply-thread and forum-topic semantics with structured unsupported outcomes.

## Trigger examples

- “Покажи непрочитанные в Telegram, не отмечая их прочитанными.”
- “Найди сообщения о релизе в архивных Telegram-чатах.”
- “Ответь в этой Telegram-теме после предпросмотра адресата.”

## Non-trigger examples

- “Проверь TiMe.”
- “Создай Telegram-бота через Bot API.”

## External effects

Reads never intentionally call `viewMessages`. Writes require explicit authorization or a narrow
session grant bound to this provider, authenticated account, action family, and stable target.
Destructive actions always require an exact fresh confirmation. Ambiguous sends are not retried.

## Platform support

Codex and Claude Code load the packaged stdio MCP declaration and portable skills. DeepSeek
Harness receives the skills only; its bundle does not currently launch the MCP server. The first
published native matrix supports macOS arm64; other targets fail closed.

## Local testing

Run `python3 -B -m unittest discover -s runtime/tests -v`,
`python3 runtime/server.py runtime-status`, and `yuzuru plugin validate telegram`. Complete local
TDLib authorization before a live, read-only smoke test.

## Limitations

TDLib cannot enumerate every ordinary reply thread, and its first-page chat listing does not
provide a stable server cursor without a maintained update index. The plugin does not reuse the
Telegram desktop application's private session or support Bot API workflows.
