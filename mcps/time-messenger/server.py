#!/usr/bin/env python3
"""TiMe Messenger MCP server and credential bootstrap."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from mcp_stdio import McpServer
from time_client import MessengerError, TimeClient, TimeOperations, interactive_setup


def schema(properties: dict[str, Any] | None = None, required: list[str] | None = None) -> dict[str, Any]:
    return {"type": "object", "properties": properties or {}, "required": required or [], "additionalProperties": False}


S = {"type": "string"}
I = {"type": "integer"}
B = {"type": "boolean"}
SS = {"type": "array", "items": S, "maxItems": 100}


def tool(name: str, description: str, input_schema: dict[str, Any], *, read: bool = False, destructive: bool = False, idempotent: bool = False) -> dict[str, Any]:
    return {
        "name": f"time_messenger_{name}",
        "description": description,
        "inputSchema": input_schema,
        "annotations": {"readOnlyHint": read, "destructiveHint": destructive, "idempotentHint": idempotent, "openWorldHint": False},
    }


TOOLS = [
    tool("get_identity", "Return the authenticated TiMe account without secrets.", schema(), read=True),
    tool("get_capabilities", "Return the explicit semantic capability inventory.", schema(), read=True),
    tool("resolve_user", "Find bounded user candidates; stable IDs are required for writes.", schema({"query": S, "team_id": S, "limit": I}, ["query"]), read=True),
    tool("resolve_conversation", "Find bounded conversation candidates by ID or name.", schema({"query": S, "limit": I}, ["query"]), read=True),
    tool("list_conversations", "List bounded conversations without changing read state.", schema({"kind": {"type": "string", "enum": ["dm", "group", "channel"]}, "include_archived": B, "cursor": S, "limit": I}), read=True),
    tool("get_conversation", "Get normalized conversation metadata.", schema({"conversation_id": S}, ["conversation_id"]), read=True),
    tool("list_members", "List conversation members with bounded pagination.", schema({"conversation_id": S, "cursor": S, "limit": I}, ["conversation_id"]), read=True),
    tool("list_messages", "Read bounded message history without marking it read.", schema({"conversation_id": S, "page": I, "limit": I, "before": S, "after": S, "around": S, "since": I}, ["conversation_id"]), read=True),
    tool("get_message", "Get one normalized message.", schema({"message_id": S}, ["message_id"]), read=True),
    tool("search_messages", "Search bounded TiMe message history in one team.", schema({"team_id": S, "query": S, "sender_username": S, "conversation_name": S, "after": S, "before": S, "cursor": S, "limit": I}, ["team_id", "query"]), read=True),
    tool("list_threads", "List tracked TiMe root/reply threads.", schema({"team_id": S, "unread": B, "cursor": S, "limit": I}, ["team_id"]), read=True),
    tool("get_thread", "Get a bounded root/reply discussion.", schema({"thread_id": S, "limit": I}, ["thread_id"]), read=True),
    tool("list_topics", "Report TiMe topic capability explicitly.", schema({"conversation_id": S, "limit": I}, ["conversation_id"]), read=True),
    tool("get_topic", "Report TiMe topic capability explicitly.", schema({"topic_id": S}, ["topic_id"]), read=True),
    tool("inspect_unread", "Inspect bounded unread counters without marking them read.", schema({"exclude_team_id": S, "limit": I}), read=True),
    tool("inspect_mentions", "Search bounded mentions without changing read state.", schema({"team_id": S, "after": S, "before": S, "cursor": S, "limit": I}, ["team_id"]), read=True),
    tool("get_reactions", "Get reactions for one message.", schema({"message_id": S, "limit": I}, ["message_id"]), read=True),
    tool("get_pins", "Get bounded pinned messages in a conversation.", schema({"conversation_id": S, "limit": I}, ["conversation_id"]), read=True),
    tool("search_files", "Search bounded file metadata in one team.", schema({"team_id": S, "query": S, "cursor": S, "limit": I}, ["team_id", "query"]), read=True),
    tool("get_file_metadata", "Get file metadata without downloading binary content.", schema({"file_id": S}, ["file_id"]), read=True),
    tool("send_message", "Send one message to an exact conversation or thread.", schema({"conversation_id": S, "text": S, "thread_id": S, "file_ids": SS, "forward_message_id": S, "idempotency_key": S}, ["conversation_id", "text"])),
    tool("reply_message", "Reply in an exact root/reply thread.", schema({"conversation_id": S, "thread_id": S, "text": S, "file_ids": SS, "idempotency_key": S}, ["conversation_id", "thread_id", "text"])),
    tool("edit_message", "Edit one exact message.", schema({"message_id": S, "text": S}, ["message_id", "text"])),
    tool("delete_message", "Delete one exact message after exact destructive confirmation.", schema({"message_id": S, "confirm_exact": S}, ["message_id", "confirm_exact"]), destructive=True),
    tool("add_reaction", "Add a reaction to one message.", schema({"message_id": S, "emoji": S}, ["message_id", "emoji"]), idempotent=True),
    tool("remove_reaction", "Remove the authenticated user's reaction.", schema({"message_id": S, "emoji": S}, ["message_id", "emoji"]), idempotent=True),
    tool("pin_message", "Pin one exact message.", schema({"message_id": S}, ["message_id"]), idempotent=True),
    tool("unpin_message", "Unpin one exact message.", schema({"message_id": S}, ["message_id"]), idempotent=True),
    tool("create_conversation", "Create a DM, group conversation, public channel, or private channel.", schema({"kind": {"type": "string", "enum": ["dm", "group", "channel"]}, "user_id": S, "member_ids": SS, "team_id": S, "name": S, "display_name": S, "private": B, "purpose": S, "header": S}, ["kind"])),
    tool("update_conversation", "Patch supported conversation metadata.", schema({"conversation_id": S, "name": S, "display_name": S, "purpose": S, "header": S}, ["conversation_id"])),
    tool("add_members", "Add a finite list of stable user IDs and journal partial success.", schema({"conversation_id": S, "user_ids": SS}, ["conversation_id", "user_ids"])),
    tool("remove_members", "Remove a finite list of members after exact destructive confirmation.", schema({"conversation_id": S, "user_ids": SS, "confirm_exact": S}, ["conversation_id", "user_ids", "confirm_exact"]), destructive=True),
    tool("mark_read", "Explicitly mark one conversation read.", schema({"conversation_id": S, "previous_conversation_id": S}, ["conversation_id"]), idempotent=True),
    tool("mark_unread", "Explicitly mark unread from one message.", schema({"message_id": S}, ["message_id"]), idempotent=True),
    tool("upload_file", "Upload one bounded local file; send it with send_message using returned file ID.", schema({"conversation_id": S, "path": S, "max_bytes": I}, ["conversation_id", "path"])),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")
    setup = sub.add_parser("setup", help="store a TiMe PAT in the macOS Keychain")
    setup.add_argument("--url", required=True, help="HTTPS TiMe workspace origin")
    sub.add_parser("serve", help="run the MCP server over stdio")
    args = parser.parse_args()
    try:
        if args.command == "setup":
            print(json.dumps(interactive_setup(args.url), ensure_ascii=False))
            return 0
        operations = TimeOperations(TimeClient())
        McpServer("time-messenger", "0.1.0", TOOLS, operations.call).run()
        return 0
    except MessengerError as exc:
        print(json.dumps(exc.as_dict(), ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
