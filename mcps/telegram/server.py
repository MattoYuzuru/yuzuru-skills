#!/usr/bin/env python3
"""Telegram MCP server backed by the official TDLib JSON API."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from mcp_stdio import McpServer
from tdjson import TdJson, TelegramError, native_library_path
from telegram_client import ProfileLock, TelegramOperations, bootstrap_auth


def schema(properties: dict[str, Any] | None = None, required: list[str] | None = None) -> dict[str, Any]:
    return {"type": "object", "properties": properties or {}, "required": required or [], "additionalProperties": False}


S = {"type": "string"}; I = {"type": "integer"}; B = {"type": "boolean"}; SS = {"type": "array", "items": S, "maxItems": 100}; O = {"type": "object"}


def tool(name: str, description: str, inputs: dict[str, Any], *, read: bool = False, destructive: bool = False, idempotent: bool = False) -> dict[str, Any]:
    return {"name": f"telegram_{name}", "description": description, "inputSchema": inputs, "annotations": {"readOnlyHint": read, "destructiveHint": destructive, "idempotentHint": idempotent, "openWorldHint": True}}


TOOLS = [
    tool("auth_status", "Return safe TDLib authorization status.", schema(), read=True),
    tool("get_identity", "Return the authenticated Telegram account without secrets.", schema(), read=True),
    tool("get_capabilities", "Return explicit Telegram/TDLib capabilities and limitations.", schema(), read=True),
    tool("resolve_user", "Resolve bounded Telegram user candidates; never choose an ambiguous write target.", schema({"query": S, "limit": I}, ["query"]), read=True),
    tool("resolve_conversation", "Resolve bounded Telegram chat candidates.", schema({"query": S, "limit": I}, ["query"]), read=True),
    tool("list_conversations", "List a bounded first page from main, archive, or a folder without changing read state.", schema({"list": {"type": "string", "enum": ["main", "archive", "folder"]}, "folder_id": I, "limit": I}), read=True),
    tool("get_conversation", "Get normalized Telegram chat metadata.", schema({"conversation_id": S}, ["conversation_id"]), read=True),
    tool("list_members", "List members when the chat type and account rights permit it.", schema({"conversation_id": S, "cursor": S, "limit": I}, ["conversation_id"]), read=True),
    tool("list_messages", "Read bounded chat history without marking messages read.", schema({"conversation_id": S, "cursor": S, "limit": I}, ["conversation_id"]), read=True),
    tool("get_message", "Get one Telegram message by stable chat and message IDs.", schema({"conversation_id": S, "message_id": S}, ["conversation_id", "message_id"]), read=True),
    tool("search_messages", "Run bounded per-chat or global TDLib search.", schema({"conversation_id": S, "topic_id": O, "query": S, "sender_id": O, "list": S, "cursor": S, "filter": O, "min_date": I, "max_date": I, "limit": I}), read=True),
    tool("list_threads", "Report that TDLib cannot enumerate all ordinary message threads.", schema({"conversation_id": S, "limit": I}, ["conversation_id"]), read=True),
    tool("get_thread", "Get a bounded ordinary message thread from a known root message.", schema({"conversation_id": S, "root_message_id": S, "cursor": S, "limit": I}, ["conversation_id", "root_message_id"]), read=True),
    tool("list_topics", "List bounded Telegram forum topics with a structured cursor.", schema({"conversation_id": S, "query": S, "cursor": O, "limit": I}, ["conversation_id"]), read=True),
    tool("get_topic", "Get one Telegram forum topic.", schema({"conversation_id": S, "topic_id": S}, ["conversation_id", "topic_id"]), read=True),
    tool("inspect_unread", "Inspect bounded unread chat state without marking it read.", schema({"list": S, "limit": I}), read=True),
    tool("inspect_mentions", "Inspect bounded unread mentions without changing read state.", schema({"conversation_id": S, "list": S, "cursor": S, "limit": I}), read=True),
    tool("get_reactions", "Get bounded message reaction senders.", schema({"conversation_id": S, "message_id": S, "reaction_type": O, "cursor": S, "limit": I}, ["conversation_id", "message_id"]), read=True),
    tool("get_pins", "Search bounded pinned messages in one chat.", schema({"conversation_id": S, "cursor": S, "limit": I}, ["conversation_id"]), read=True),
    tool("search_files", "Search bounded document messages and optional MIME type.", schema({"conversation_id": S, "query": S, "mime_type": S, "cursor": S, "limit": I}), read=True),
    tool("get_file_metadata", "Get bounded TDLib file metadata without binary data or remote identifiers.", schema({"file_id": S}, ["file_id"]), read=True),
    tool("send_message", "Send text and wait for TDLib final send confirmation.", schema({"conversation_id": S, "thread_id": S, "reply_to_message_id": S, "text": S, "silent": B, "scheduling_state": O}, ["conversation_id", "text"])),
    tool("reply_message", "Reply to an exact message/thread and wait for final confirmation.", schema({"conversation_id": S, "thread_id": S, "reply_to_message_id": S, "text": S, "silent": B}, ["conversation_id", "reply_to_message_id", "text"])),
    tool("edit_message", "Edit one exact text message.", schema({"conversation_id": S, "message_id": S, "text": S}, ["conversation_id", "message_id", "text"])),
    tool("delete_message", "Delete one exact message after destructive confirmation.", schema({"conversation_id": S, "message_id": S, "revoke": B, "confirm_exact": S}, ["conversation_id", "message_id", "confirm_exact"]), destructive=True),
    tool("forward_messages", "Use native Telegram forwarding; never copy protected content.", schema({"conversation_id": S, "from_conversation_id": S, "message_ids": SS, "topic_id": S, "thread_id": S}, ["conversation_id", "from_conversation_id", "message_ids"])),
    tool("add_reaction", "Add one Telegram reaction.", schema({"conversation_id": S, "message_id": S, "reaction_type": O, "is_big": B}, ["conversation_id", "message_id", "reaction_type"])),
    tool("remove_reaction", "Remove one Telegram reaction.", schema({"conversation_id": S, "message_id": S, "reaction_type": O}, ["conversation_id", "message_id", "reaction_type"])),
    tool("pin_message", "Pin one exact message.", schema({"conversation_id": S, "message_id": S, "silent": B}, ["conversation_id", "message_id"])),
    tool("unpin_message", "Unpin one exact message.", schema({"conversation_id": S, "message_id": S}, ["conversation_id", "message_id"])),
    tool("create_conversation", "Create a DM, basic group, supergroup, channel, or forum.", schema({"kind": S, "user_id": S, "user_ids": SS, "title": S, "description": S}, ["kind"])),
    tool("update_conversation", "Update title/description as separate journaled effects.", schema({"conversation_id": S, "title": S, "description": S}, ["conversation_id"])),
    tool("create_topic", "Create one forum topic.", schema({"conversation_id": S, "name": S, "icon": O}, ["conversation_id", "name"])),
    tool("update_topic", "Edit one forum topic.", schema({"conversation_id": S, "topic_id": S, "name": S, "icon_custom_emoji_id": S}, ["conversation_id", "topic_id"])),
    tool("close_topic", "Close one forum topic.", schema({"conversation_id": S, "topic_id": S}, ["conversation_id", "topic_id"])),
    tool("reopen_topic", "Reopen one forum topic.", schema({"conversation_id": S, "topic_id": S}, ["conversation_id", "topic_id"])),
    tool("add_members", "Add stable user IDs and preserve TDLib partial-failure details.", schema({"conversation_id": S, "user_ids": SS}, ["conversation_id", "user_ids"])),
    tool("remove_members", "Remove members after exact destructive confirmation.", schema({"conversation_id": S, "user_ids": SS, "confirm_exact": S}, ["conversation_id", "user_ids", "confirm_exact"]), destructive=True),
    tool("mark_read", "Explicitly mark messages read.", schema({"conversation_id": S, "message_id": S}, ["conversation_id", "message_id"])),
    tool("mark_unread", "Set Telegram's manual unread marker for one chat.", schema({"conversation_id": S}, ["conversation_id"])),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command")
    auth = subs.add_parser("auth", help="perform official Telegram user authorization locally")
    auth.add_argument("--api-id", type=int, required=True, help="application api_id from my.telegram.org")
    subs.add_parser("runtime-status", help="show packaged native runtime availability")
    subs.add_parser("serve", help="run MCP over stdio")
    args = parser.parse_args()
    try:
        if args.command == "auth":
            print(json.dumps(bootstrap_auth(args.api_id), ensure_ascii=False)); return 0
        if args.command == "runtime-status":
            print(json.dumps({"ok": True, "library": str(native_library_path())}, ensure_ascii=False)); return 0
        with ProfileLock():
            td = TdJson()
            try: McpServer("telegram", "0.1.0", TOOLS, TelegramOperations(td, check_authorization=False).call).run()
            finally: td.close()
        return 0
    except TelegramError as exc:
        print(json.dumps(exc.as_dict(), ensure_ascii=False), file=sys.stderr); return 2


if __name__ == "__main__":
    raise SystemExit(main())
