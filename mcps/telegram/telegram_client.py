#!/usr/bin/env python3
"""Normalized Telegram semantics over the official TDLib JSON API."""

from __future__ import annotations

import getpass
import json
import os
import platform
import re
import secrets
import subprocess
import time
from pathlib import Path
from typing import Any

from tdjson import EXPECTED_TDLIB_VERSION, PINNED_TDLIB_COMMIT, TdJson, TelegramError


MAX_LIMIT = 100
PROFILE_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")


def bounded_limit(value: Any, default: int = 20, maximum: int = MAX_LIMIT) -> int:
    try:
        result = int(value if value is not None else default)
    except (TypeError, ValueError) as exc:
        raise TelegramError("INVALID_ARGUMENT", "limit must be an integer") from exc
    if not 1 <= result <= maximum:
        raise TelegramError("INVALID_ARGUMENT", f"limit must be between 1 and {maximum}")
    return result


def require(a: dict[str, Any], key: str) -> Any:
    value = a.get(key)
    if value is None or value == "":
        raise TelegramError("INVALID_ARGUMENT", f"missing required argument: {key}")
    return value


def profile_name() -> str:
    value = os.environ.get("TELEGRAM_PROFILE", "default")
    if not PROFILE_RE.fullmatch(value):
        raise TelegramError("INVALID_ARGUMENT", "TELEGRAM_PROFILE must be lowercase kebab-case")
    return value


def xdg_path(kind: str) -> Path:
    home = Path.home()
    defaults = {"config": home / ".config", "data": home / ".local" / "share", "cache": home / ".cache"}
    return Path(os.environ.get(f"XDG_{kind.upper()}_HOME", defaults[kind])) / "yuzuru" / "telegram" / profile_name()


class ProfileLock:
    """Prevent concurrent writers from opening one persistent TDLib profile."""

    def __init__(self) -> None:
        directory = xdg_path("data")
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = directory / "profile.lock"
        self.handle: Any = None

    def __enter__(self) -> "ProfileLock":
        self.handle = self.path.open("a+b")
        try:
            if platform.system() == "Windows":
                import msvcrt
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            self.handle.close()
            raise TelegramError("STATE_LOCKED", f"Telegram profile '{profile_name()}' is already in use") from exc
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.handle is not None:
            self.handle.close()
            self.handle = None


def config_path() -> Path:
    return xdg_path("config") / "config.json"


def keychain_account(key: str) -> str:
    return f"{profile_name()}:{key}"


def secret_get(key: str) -> str:
    env_name = f"TELEGRAM_{key.upper()}"
    if os.environ.get(env_name):
        return os.environ[env_name]
    if platform.system() == "Darwin":
        result = subprocess.run(["security", "find-generic-password", "-s", "yuzuru.telegram", "-a", keychain_account(key), "-w"], capture_output=True, text=True, timeout=10, check=False)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    raise TelegramError("STATE_KEY_UNAVAILABLE", f"missing {env_name}; run the local auth bootstrap")


def secret_store(key: str, value: str) -> None:
    if platform.system() != "Darwin":
        raise TelegramError("UNSUPPORTED_CAPABILITY", "persistent secret bootstrap currently supports macOS Keychain; use environment injection elsewhere")
    subprocess.run(["security", "add-generic-password", "-U", "-s", "yuzuru.telegram", "-a", keychain_account(key), "-w", value], capture_output=True, text=True, timeout=10, check=True)


def load_config() -> dict[str, Any]:
    path = config_path()
    if not path.is_file():
        raise TelegramError("AUTH_REQUIRED", "run `server.py auth` in a local terminal")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TelegramError("AUTH_REQUIRED", "Telegram profile configuration is invalid") from exc
    if not isinstance(value.get("api_id"), int):
        raise TelegramError("AUTH_REQUIRED", "Telegram api_id is not configured")
    return value


def td_parameters(config: dict[str, Any]) -> dict[str, Any]:
    data = xdg_path("data") / "tdlib"
    files = xdg_path("cache") / "files"
    data.mkdir(parents=True, exist_ok=True, mode=0o700)
    files.mkdir(parents=True, exist_ok=True, mode=0o700)
    return {
        "@type": "setTdlibParameters",
        "use_test_dc": False,
        "database_directory": str(data),
        "files_directory": str(files),
        "database_encryption_key": secret_get("database_key"),
        "use_file_database": True,
        "use_chat_info_database": True,
        "use_message_database": True,
        "use_secret_chats": False,
        "api_id": config["api_id"],
        "api_hash": secret_get("api_hash"),
        "system_language_code": "en",
        "device_model": "Yuzuru MCP",
        "system_version": platform.platform()[:64],
        "application_version": "0.1.0",
    }


def ensure_authorized(td: TdJson, *, interactive: bool = False) -> str:
    while True:
        state = td.request({"@type": "getAuthorizationState"})
        kind = state.get("@type")
        if kind == "authorizationStateReady":
            return kind
        if kind == "authorizationStateWaitTdlibParameters":
            td.request(td_parameters(load_config()))
            continue
        if not interactive:
            raise TelegramError("AUTH_REQUIRED", f"Telegram authorization is incomplete ({kind}); run `server.py auth`")
        if kind == "authorizationStateWaitPhoneNumber":
            phone = input("Telegram phone number (international format): ").strip()
            td.request({"@type": "setAuthenticationPhoneNumber", "phone_number": phone, "settings": None})
        elif kind in {"authorizationStateWaitCode", "authorizationStateWaitEmailCode"}:
            code = getpass.getpass("Telegram verification code: ")
            method = "checkAuthenticationEmailCode" if kind.endswith("EmailCode") else "checkAuthenticationCode"
            payload: dict[str, Any] = {"@type": method}
            if method == "checkAuthenticationEmailCode":
                payload["code"] = {"@type": "emailAddressAuthenticationCode", "code": code}
            else:
                payload["code"] = code
            td.request(payload)
        elif kind == "authorizationStateWaitPassword":
            td.request({"@type": "checkAuthenticationPassword", "password": getpass.getpass("Telegram 2FA password: ")})
        elif kind == "authorizationStateWaitOtherDeviceConfirmation":
            print("Open this QR/login link locally in Telegram:", state.get("link"))
            time.sleep(2)
        elif kind == "authorizationStateWaitRegistration":
            raise TelegramError("AUTH_REQUIRED", "new-account registration is not supported by this bootstrap")
        elif kind in {"authorizationStateLoggingOut", "authorizationStateClosing", "authorizationStateClosed"}:
            raise TelegramError("AUTH_REVOKED", f"Telegram session is {kind}")
        else:
            time.sleep(0.5)


def normalize_user(value: dict[str, Any]) -> dict[str, Any]:
    usernames = value.get("usernames") or {}
    return {"provider": "telegram", "user_id": str(value.get("id")), "display_name": " ".join(filter(None, [value.get("first_name"), value.get("last_name")])).strip(), "username": usernames.get("active_usernames", [None])[0] if usernames.get("active_usernames") else None, "phone_number": value.get("phone_number") or None, "provider_metadata": {"type": (value.get("type") or {}).get("@type"), "is_contact": value.get("is_contact")}}


def normalize_chat(value: dict[str, Any]) -> dict[str, Any]:
    kind = (value.get("type") or {}).get("@type")
    generic = "dm" if kind == "chatTypePrivate" else "channel" if kind == "chatTypeSupergroup" and (value.get("type") or {}).get("is_channel") else "group"
    return {"provider": "telegram", "conversation_id": str(value.get("id")), "kind": generic, "provider_kind": kind, "title": value.get("title"), "unread_count": value.get("unread_count"), "unread_mention_count": value.get("unread_mention_count"), "is_marked_as_unread": value.get("is_marked_as_unread"), "last_message_id": str((value.get("last_message") or {}).get("id")) if value.get("last_message") else None}


def normalize_message(value: dict[str, Any]) -> dict[str, Any]:
    content = value.get("content") or {}
    text_value = content.get("text") or content.get("caption") or {}
    text = text_value.get("text") if isinstance(text_value, dict) else ""
    topic = value.get("topic_id") or {}
    return {"provider": "telegram", "conversation_id": str(value.get("chat_id")), "topic_id": topic, "thread_id": str(value.get("message_thread_id")) if value.get("message_thread_id") else None, "message_id": str(value.get("id")), "sender_id": str((value.get("sender_id") or {}).get("user_id") or (value.get("sender_id") or {}).get("chat_id") or ""), "timestamp": value.get("date"), "edited_at": value.get("edit_date") or None, "text": text or "", "reply_to": value.get("reply_to"), "attachments": normalize_attachments(content), "reactions": (value.get("interaction_info") or {}).get("reactions"), "provider_metadata": {"content_type": content.get("@type"), "sending_state": (value.get("sending_state") or {}).get("@type")}}


def normalize_attachments(content: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("document", "photo", "video", "audio", "voice_note", "animation"):
        if key not in content:
            continue
        item = content[key]
        file_value = item.get(key) if isinstance(item, dict) and isinstance(item.get(key), dict) else item.get("file") if isinstance(item, dict) else None
        return [{"kind": key, "file_id": str((file_value or {}).get("id")), "file_name": item.get("file_name") if isinstance(item, dict) else None, "mime_type": item.get("mime_type") if isinstance(item, dict) else None}]
    return []


CAPABILITIES: dict[str, Any] = {
    "conversation.list": True, "conversation.search": True, "conversation.create": True, "conversation.update": True, "conversation.photo": True,
    "message.history": True, "message.search": True, "message.send": True, "message.reply": True, "message.edit": True, "message.delete": True, "message.forward": "conditional",
    "thread.list": False, "thread.get": "conditional", "thread.reply": "conditional",
    "topic.list": True, "topic.get": True, "topic.create": True, "topic.update": True,
    "unread.inspect": True, "mentions.inspect": True, "reaction.read": True, "reaction.write": True, "pin.read": True, "pin.write": True,
    "attachment.metadata": True, "attachment.download": True, "attachment.send": True, "membership.list": "conditional", "membership.add": "conditional", "membership.remove": "conditional", "schedule.message": "conditional",
}


class TelegramOperations:
    def __init__(self, td: TdJson, *, check_authorization: bool = True) -> None:
        self.td = td
        if check_authorization:
            ensure_authorized(td)

    def call(self, name: str, a: dict[str, Any]) -> Any:
        method = getattr(self, name.removeprefix("telegram_"), None)
        if method is None:
            raise TelegramError("UNSUPPORTED_CAPABILITY", f"unknown tool: {name}")
        if name not in {"telegram_auth_status", "telegram_get_capabilities"}:
            ensure_authorized(self.td)
        return {"ok": True, "provider": "telegram", "result": method(a)}

    def auth_status(self, a: dict[str, Any]) -> Any:
        state = self.td.request({"@type": "getAuthorizationState"})
        return {"state": state.get("@type"), "ready": state.get("@type") == "authorizationStateReady"}

    def get_identity(self, a: dict[str, Any]) -> Any:
        return normalize_user(self.td.request({"@type": "getMe"}))

    def get_capabilities(self, a: dict[str, Any]) -> Any:
        version = self.td.request({"@type": "getOption", "name": "version"}).get("value", {}).get("value")
        return {"tdlib_version": version, "expected_tdlib_version": EXPECTED_TDLIB_VERSION, "tdlib_commit": PINNED_TDLIB_COMMIT, "capabilities": CAPABILITIES, "unsupported_outcome": "UNSUPPORTED_CAPABILITY"}

    def resolve_user(self, a: dict[str, Any]) -> Any:
        query = str(require(a, "query")); limit = bounded_limit(a.get("limit"), 10)
        candidates: list[dict[str, Any]] = []
        if query.startswith("@"):
            chat = self.td.request({"@type": "searchPublicChat", "username": query[1:]})
            if (chat.get("type") or {}).get("@type") == "chatTypePrivate":
                user = self.td.request({"@type": "getUser", "user_id": (chat["type"])["user_id"]})
                candidates.append(normalize_user(user))
        else:
            found = self.td.request({"@type": "searchContacts", "query": query, "limit": limit})
            for user_id in found.get("user_ids") or []:
                candidates.append(normalize_user(self.td.request({"@type": "getUser", "user_id": user_id})))
        exact = [item for item in candidates if query.lstrip("@").casefold() in {str(item.get("user_id", "")).casefold(), str(item.get("username", "")).casefold()}]
        return {"candidates": candidates[:limit], "exact": exact[0] if len(exact) == 1 else None, "ambiguous": len(candidates) > 1 and len(exact) != 1}

    def resolve_conversation(self, a: dict[str, Any]) -> Any:
        query = str(require(a, "query")); limit = bounded_limit(a.get("limit"), 10)
        request = {"@type": "searchPublicChat", "username": query[1:]} if query.startswith("@") else {"@type": "searchChatsOnServer", "query": query, "limit": limit}
        found = self.td.request(request)
        ids = [found.get("id")] if found.get("@type") == "chat" else found.get("chat_ids") or []
        candidates = [normalize_chat(self.td.request({"@type": "getChat", "chat_id": chat_id})) for chat_id in ids[:limit]]
        exact = [item for item in candidates if query.casefold() in {item["conversation_id"].casefold(), str(item.get("title", "")).casefold()}]
        return {"candidates": candidates, "exact": exact[0] if len(exact) == 1 else None, "ambiguous": len(candidates) > 1 and len(exact) != 1}

    @staticmethod
    def chat_list(kind: str, folder_id: Any = None) -> dict[str, Any]:
        if kind == "main": return {"@type": "chatListMain"}
        if kind == "archive": return {"@type": "chatListArchive"}
        if kind == "folder": return {"@type": "chatListFolder", "chat_folder_id": int(folder_id)}
        raise TelegramError("INVALID_ARGUMENT", "list must be main, archive, or folder")

    def list_conversations(self, a: dict[str, Any]) -> Any:
        limit = bounded_limit(a.get("limit")); chat_list = self.chat_list(str(a.get("list") or "main"), a.get("folder_id"))
        found = self.td.request({"@type": "getChats", "chat_list": chat_list, "limit": limit})
        items = [normalize_chat(self.td.request({"@type": "getChat", "chat_id": chat_id})) for chat_id in (found.get("chat_ids") or [])[:limit]]
        return {"items": items, "next_cursor": None, "truncated": len(items) == limit, "pagination_note": "TDLib getChats exposes a bounded first page; stable continuation requires a maintained update index"}

    def get_conversation(self, a: dict[str, Any]) -> Any:
        return normalize_chat(self.td.request({"@type": "getChat", "chat_id": int(require(a, "conversation_id"))}))

    def list_messages(self, a: dict[str, Any]) -> Any:
        limit = bounded_limit(a.get("limit")); chat_id = int(require(a, "conversation_id")); from_id = int(a.get("cursor") or 0)
        result = self.td.request({"@type": "getChatHistory", "chat_id": chat_id, "from_message_id": from_id, "offset": 0, "limit": limit, "only_local": False})
        messages = result.get("messages") or []
        return {"items": [normalize_message(item) for item in messages], "next_cursor": str(messages[-1]["id"]) if messages else None, "truncated": len(messages) == limit}

    def get_message(self, a: dict[str, Any]) -> Any:
        return normalize_message(self.td.request({"@type": "getMessage", "chat_id": int(require(a, "conversation_id")), "message_id": int(require(a, "message_id"))}))

    def search_messages(self, a: dict[str, Any]) -> Any:
        limit = bounded_limit(a.get("limit")); query = str(a.get("query") or "")
        if a.get("conversation_id"):
            result = self.td.request({"@type": "searchChatMessages", "chat_id": int(a["conversation_id"]), "topic_id": a.get("topic_id"), "query": query, "sender_id": a.get("sender_id"), "from_message_id": int(a.get("cursor") or 0), "offset": 0, "limit": limit, "filter": a.get("filter")})
            next_cursor = result.get("next_from_message_id")
        else:
            result = self.td.request({"@type": "searchMessages", "chat_list": self.chat_list(str(a.get("list") or "main")), "query": query, "offset": str(a.get("cursor") or ""), "limit": limit, "filter": a.get("filter"), "chat_type_filter": None, "min_date": int(a.get("min_date") or 0), "max_date": int(a.get("max_date") or 0)})
            next_cursor = result.get("next_offset")
        messages = result.get("messages") or []
        return {"items": [normalize_message(item) for item in messages], "next_cursor": str(next_cursor) if next_cursor else None, "truncated": len(messages) == limit}

    def list_threads(self, a: dict[str, Any]) -> Any:
        raise TelegramError("UNSUPPORTED_CAPABILITY", "TDLib has no exhaustive ordinary-thread enumeration; use get_thread with a known root")

    def get_thread(self, a: dict[str, Any]) -> Any:
        info = self.td.request({"@type": "getMessageThread", "chat_id": int(require(a, "conversation_id")), "message_id": int(require(a, "root_message_id"))})
        limit = bounded_limit(a.get("limit")); result = self.td.request({"@type": "getMessageThreadHistory", "chat_id": info["chat_id"], "message_id": info["message_thread_id"], "from_message_id": int(a.get("cursor") or 0), "offset": 0, "limit": limit})
        messages = result.get("messages") or []
        return {"thread": {"conversation_id": str(info.get("chat_id")), "thread_id": str(info.get("message_thread_id")), "unread_count": info.get("unread_message_count")}, "items": [normalize_message(item) for item in messages], "next_cursor": str(messages[-1]["id"]) if messages else None}

    def list_topics(self, a: dict[str, Any]) -> Any:
        limit = bounded_limit(a.get("limit")); cursor = a.get("cursor") or {}
        result = self.td.request({"@type": "getForumTopics", "chat_id": int(require(a, "conversation_id")), "query": str(a.get("query") or ""), "offset_date": int(cursor.get("date") or 0), "offset_message_id": int(cursor.get("message_id") or 0), "offset_message_thread_id": int(cursor.get("thread_id") or 0), "limit": limit})
        topics = result.get("topics") or []
        next_cursor = None
        if topics:
            last = topics[-1]; next_cursor = {"date": (last.get("last_message") or {}).get("date", 0), "message_id": (last.get("last_message") or {}).get("id", 0), "thread_id": last.get("info", {}).get("message_thread_id", 0)}
        return {"items": topics, "next_cursor": next_cursor, "truncated": len(topics) == limit}

    def get_topic(self, a: dict[str, Any]) -> Any:
        return self.td.request({"@type": "getForumTopic", "chat_id": int(require(a, "conversation_id")), "message_thread_id": int(require(a, "topic_id"))})

    def inspect_unread(self, a: dict[str, Any]) -> Any:
        result = self.list_conversations({"list": a.get("list", "main"), "limit": a.get("limit", 20)})
        result["items"] = [item for item in result["items"] if (item.get("unread_count") or 0) > 0 or item.get("is_marked_as_unread")]
        result["read_state_changed"] = False
        return result

    def inspect_mentions(self, a: dict[str, Any]) -> Any:
        args = dict(a); args["query"] = ""; args["filter"] = {"@type": "searchMessagesFilterUnreadMention"}
        result = self.search_messages(args); result["read_state_changed"] = False
        return result

    def get_pins(self, a: dict[str, Any]) -> Any:
        args = dict(a); args["query"] = ""; args["filter"] = {"@type": "searchMessagesFilterPinned"}
        return self.search_messages(args)

    def get_reactions(self, a: dict[str, Any]) -> Any:
        result = self.td.request({"@type": "getMessageAddedReactions", "chat_id": int(require(a, "conversation_id")), "message_id": int(require(a, "message_id")), "reaction_type": a.get("reaction_type"), "offset": str(a.get("cursor") or ""), "limit": bounded_limit(a.get("limit"))})
        return {"items": result.get("reactions") or [], "next_cursor": result.get("next_offset")}

    def search_files(self, a: dict[str, Any]) -> Any:
        args = dict(a); args["filter"] = {"@type": "searchMessagesFilterDocument"}
        result = self.search_messages(args)
        if a.get("mime_type"):
            result["items"] = [item for item in result["items"] if any(att.get("mime_type") == a["mime_type"] for att in item["attachments"])]
        return result

    def get_file_metadata(self, a: dict[str, Any]) -> Any:
        value = self.td.request({"@type": "getFile", "file_id": int(require(a, "file_id"))})
        return {"file_id": str(value.get("id")), "size": value.get("size"), "expected_size": value.get("expected_size"), "local": {"can_download": (value.get("local") or {}).get("can_be_downloaded"), "downloaded": (value.get("local") or {}).get("is_downloading_completed")}, "remote": {"uploading": (value.get("remote") or {}).get("is_uploading_active")}}

    def download_file(self, a: dict[str, Any]) -> Any:
        file_id = int(require(a, "file_id")); max_bytes = int(a.get("max_bytes") or 50 * 1024 * 1024)
        if not 1 <= max_bytes <= 100 * 1024 * 1024:
            raise TelegramError("INVALID_ARGUMENT", "max_bytes must be between 1 and 104857600")
        metadata = self.td.request({"@type": "getFile", "file_id": file_id})
        expected = int(metadata.get("expected_size") or metadata.get("size") or 0)
        if expected > max_bytes:
            raise TelegramError("INVALID_ARGUMENT", f"file exceeds {max_bytes} bytes")
        value = self.td.request({"@type": "downloadFile", "file_id": file_id, "priority": 1, "offset": 0, "limit": 0, "synchronous": True})
        local = value.get("local") or {}; path = str(local.get("path") or "")
        if not local.get("is_downloading_completed") or not path:
            raise TelegramError("PROVIDER_UNAVAILABLE", "TDLib did not complete the bounded download")
        size = Path(path).stat().st_size
        if size > max_bytes:
            raise TelegramError("INVALID_ARGUMENT", f"downloaded file exceeds {max_bytes} bytes")
        return {"file_id": str(value.get("id")), "path": path, "size": size, "cache_managed": True}

    def _send_content(self, a: dict[str, Any], content: dict[str, Any]) -> Any:
        sending_id = secrets.randbelow(2_000_000_000) + 1
        request = {"@type": "sendMessage", "chat_id": int(require(a, "conversation_id")), "message_thread_id": int(a.get("thread_id") or 0), "reply_to": {"@type": "inputMessageReplyToMessage", "message_id": int(a["reply_to_message_id"]), "quote": None, "checklist_task_id": 0} if a.get("reply_to_message_id") else None, "options": {"@type": "messageSendOptions", "disable_notification": bool(a.get("silent", False)), "from_background": False, "protect_content": False, "update_order_of_installed_sticker_sets": False, "scheduling_state": a.get("scheduling_state"), "sending_id": sending_id, "only_preview": False}, "reply_markup": None, "input_message_content": content}
        temporary = self.td.request(request, mutation=True)
        old_id = temporary.get("id")
        update = self.td.wait_update(lambda item: item.get("@type") in {"updateMessageSendSucceeded", "updateMessageSendFailed"} and (item.get("old_message_id") == old_id or (item.get("message") or {}).get("sending_state", {}).get("sending_id") == sending_id), timeout=30)
        if update.get("@type") == "updateMessageSendFailed":
            error = update.get("error") or {}; raise TelegramError("PROVIDER_UNAVAILABLE", str(error.get("message") or "send failed")[:300], details={"provider_code": error.get("code")})
        return normalize_message(update.get("message") or temporary)

    def send_message(self, a: dict[str, Any]) -> Any:
        content = {"@type": "inputMessageText", "text": {"@type": "formattedText", "text": str(require(a, "text")), "entities": []}, "link_preview_options": None, "clear_draft": True}
        return self._send_content(a, content)

    reply_message = send_message

    def send_file(self, a: dict[str, Any]) -> Any:
        path = Path(str(require(a, "path"))).expanduser().resolve(); max_bytes = int(a.get("max_bytes") or 50 * 1024 * 1024)
        if not path.is_file():
            raise TelegramError("INVALID_ARGUMENT", "attachment path must be an existing file")
        if not 1 <= max_bytes <= 100 * 1024 * 1024 or path.stat().st_size > max_bytes:
            raise TelegramError("INVALID_ARGUMENT", f"attachment exceeds the allowed {max_bytes} bytes")
        content = {"@type": "inputMessageDocument", "document": {"@type": "inputFileLocal", "path": str(path)}, "thumbnail": None, "disable_content_type_detection": False, "caption": {"@type": "formattedText", "text": str(a.get("caption") or ""), "entities": []}}
        return self._send_content(a, content)

    def edit_message(self, a: dict[str, Any]) -> Any:
        content = {"@type": "inputMessageText", "text": {"@type": "formattedText", "text": str(require(a, "text")), "entities": []}, "link_preview_options": None, "clear_draft": False}
        return normalize_message(self.td.request({"@type": "editMessageText", "chat_id": int(require(a, "conversation_id")), "message_id": int(require(a, "message_id")), "reply_markup": None, "input_message_content": content}, mutation=True))

    def delete_message(self, a: dict[str, Any]) -> Any:
        require(a, "confirm_exact")
        return self.td.request({"@type": "deleteMessages", "chat_id": int(require(a, "conversation_id")), "message_ids": [int(require(a, "message_id"))], "revoke": bool(a.get("revoke", True))}, mutation=True)

    def forward_messages(self, a: dict[str, Any]) -> Any:
        if a.get("thread_id"):
            raise TelegramError("UNSUPPORTED_CAPABILITY", "TDLib does not support forwarding into an ordinary message thread")
        ids = [int(item) for item in list(require(a, "message_ids"))[:MAX_LIMIT]]
        return self.td.request({"@type": "forwardMessages", "chat_id": int(require(a, "conversation_id")), "message_thread_id": int(a.get("topic_id") or 0), "from_chat_id": int(require(a, "from_conversation_id")), "message_ids": ids, "options": None, "send_copy": False, "remove_caption": False}, mutation=True)

    def add_reaction(self, a: dict[str, Any]) -> Any:
        return self.td.request({"@type": "addMessageReaction", "chat_id": int(require(a, "conversation_id")), "message_id": int(require(a, "message_id")), "reaction_type": require(a, "reaction_type"), "is_big": bool(a.get("is_big", False)), "update_recent_reactions": True}, mutation=True)

    def remove_reaction(self, a: dict[str, Any]) -> Any:
        return self.td.request({"@type": "removeMessageReaction", "chat_id": int(require(a, "conversation_id")), "message_id": int(require(a, "message_id")), "reaction_type": require(a, "reaction_type")}, mutation=True)

    def pin_message(self, a: dict[str, Any]) -> Any:
        return self.td.request({"@type": "pinChatMessage", "chat_id": int(require(a, "conversation_id")), "message_id": int(require(a, "message_id")), "disable_notification": bool(a.get("silent", False)), "only_for_self": False}, mutation=True)

    def unpin_message(self, a: dict[str, Any]) -> Any:
        return self.td.request({"@type": "unpinChatMessage", "chat_id": int(require(a, "conversation_id")), "message_id": int(require(a, "message_id"))}, mutation=True)

    def create_conversation(self, a: dict[str, Any]) -> Any:
        kind = str(require(a, "kind"))
        if kind == "dm": request = {"@type": "createPrivateChat", "user_id": int(require(a, "user_id")), "force": False}
        elif kind == "group": request = {"@type": "createNewBasicGroupChat", "user_ids": [int(x) for x in a.get("user_ids") or []], "title": str(require(a, "title")), "message_auto_delete_time": 0}
        elif kind in {"supergroup", "channel", "forum"}: request = {"@type": "createNewSupergroupChat", "title": str(require(a, "title")), "is_forum": kind == "forum", "is_channel": kind == "channel", "description": str(a.get("description") or ""), "location": None, "message_auto_delete_time": 0, "for_import": False}
        else: raise TelegramError("INVALID_ARGUMENT", "kind must be dm, group, supergroup, channel, or forum")
        value = self.td.request(request, mutation=True); chat = value.get("chat") or value
        return normalize_chat(chat)

    def update_conversation(self, a: dict[str, Any]) -> Any:
        chat_id = int(require(a, "conversation_id")); journal = []
        for field, method, key in (("title", "setChatTitle", "title"), ("description", "setChatDescription", "description")):
            if field in a:
                try: self.td.request({"@type": method, "chat_id": chat_id, key: a[field]}, mutation=True); journal.append({"step": field, "ok": True})
                except TelegramError as exc: journal.append({"step": field, **exc.as_dict()}); break
        return {"conversation": normalize_chat(self.td.request({"@type": "getChat", "chat_id": chat_id})), "journal": journal, "partial": any(not x.get("ok") for x in journal)}

    def create_topic(self, a: dict[str, Any]) -> Any:
        return self.td.request({"@type": "createForumTopic", "chat_id": int(require(a, "conversation_id")), "name": str(require(a, "name")), "icon": a.get("icon")}, mutation=True)

    def update_topic(self, a: dict[str, Any]) -> Any:
        return self.td.request({"@type": "editForumTopic", "chat_id": int(require(a, "conversation_id")), "message_thread_id": int(require(a, "topic_id")), "name": str(a.get("name") or ""), "edit_icon_custom_emoji_id": bool(a.get("icon_custom_emoji_id")), "icon_custom_emoji_id": int(a.get("icon_custom_emoji_id") or 0)}, mutation=True)

    def close_topic(self, a: dict[str, Any]) -> Any:
        return self.td.request({"@type": "toggleForumTopicIsClosed", "chat_id": int(require(a, "conversation_id")), "message_thread_id": int(require(a, "topic_id")), "is_closed": True}, mutation=True)

    def reopen_topic(self, a: dict[str, Any]) -> Any:
        return self.td.request({"@type": "toggleForumTopicIsClosed", "chat_id": int(require(a, "conversation_id")), "message_thread_id": int(require(a, "topic_id")), "is_closed": False}, mutation=True)

    def list_members(self, a: dict[str, Any]) -> Any:
        chat = self.td.request({"@type": "getChat", "chat_id": int(require(a, "conversation_id"))}); chat_type = chat.get("type") or {}; kind = chat_type.get("@type")
        if kind == "chatTypeBasicGroup": result = self.td.request({"@type": "getBasicGroupFullInfo", "basic_group_id": chat_type["basic_group_id"]}); members = result.get("members") or []
        elif kind == "chatTypeSupergroup": result = self.td.request({"@type": "getSupergroupMembers", "supergroup_id": chat_type["supergroup_id"], "filter": None, "offset": int(a.get("cursor") or 0), "limit": bounded_limit(a.get("limit"), 20, 200)}); members = result.get("members") or []
        else: raise TelegramError("UNSUPPORTED_CAPABILITY", "member enumeration is unavailable for this chat type")
        return {"items": members, "next_cursor": str(int(a.get("cursor") or 0) + len(members)) if members else None}

    def add_members(self, a: dict[str, Any]) -> Any:
        ids = [int(x) for x in list(require(a, "user_ids"))[:100]]
        return self.td.request({"@type": "addChatMembers", "chat_id": int(require(a, "conversation_id")), "user_ids": ids}, mutation=True)

    def remove_members(self, a: dict[str, Any]) -> Any:
        require(a, "confirm_exact"); chat_id = int(require(a, "conversation_id")); journal = []
        for user_id in list(require(a, "user_ids"))[:100]:
            try: self.td.request({"@type": "setChatMemberStatus", "chat_id": chat_id, "member_id": {"@type": "messageSenderUser", "user_id": int(user_id)}, "status": {"@type": "chatMemberStatusLeft"}}, mutation=True); journal.append({"user_id": str(user_id), "ok": True})
            except TelegramError as exc: journal.append({"user_id": str(user_id), **exc.as_dict()}); break
        return {"journal": journal, "partial": any(not item.get("ok") for item in journal)}

    def mark_read(self, a: dict[str, Any]) -> Any:
        return self.td.request({"@type": "viewMessages", "chat_id": int(require(a, "conversation_id")), "message_ids": [int(require(a, "message_id"))], "source": None, "force_read": True}, mutation=True)

    def mark_unread(self, a: dict[str, Any]) -> Any:
        return self.td.request({"@type": "toggleChatIsMarkedAsUnread", "chat_id": int(require(a, "conversation_id")), "is_marked_as_unread": True}, mutation=True)


def bootstrap_auth(api_id: int) -> dict[str, Any]:
    config = config_path(); config.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    secret_store("api_hash", getpass.getpass("Telegram api_hash: "))
    try: secret_get("database_key")
    except TelegramError: secret_store("database_key", secrets.token_hex(32))
    config.write_text(json.dumps({"api_id": api_id, "tdlib_commit": PINNED_TDLIB_COMMIT}, indent=2) + "\n", encoding="utf-8")
    os.chmod(config, 0o600)
    with ProfileLock():
        td = TdJson()
        try:
            ensure_authorized(td, interactive=True)
            return {"ok": True, "profile": profile_name(), "state": "authorizationStateReady", "account": normalize_user(td.request({"@type": "getMe"}))}
        finally:
            td.close()
