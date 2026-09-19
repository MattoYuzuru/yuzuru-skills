#!/usr/bin/env python3
"""Bounded TiMe Messenger API v4 client with normalized semantic operations."""

from __future__ import annotations

import getpass
import json
import mimetypes
import os
import platform
import re
import secrets
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any


MAX_LIMIT = 100
DEFAULT_LIMIT = 30
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
SECRET_KEYS = {"authorization", "token", "password", "api_key", "api_hash"}


class MessengerError(RuntimeError):
    def __init__(self, code: str, message: str, *, details: Any = None, ambiguous: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details
        self.ambiguous = ambiguous

    def as_dict(self) -> dict[str, Any]:
        error: dict[str, Any] = {"code": self.code, "message": redact(self.message)}
        if self.details is not None:
            error["details"] = redact(self.details)
        if self.ambiguous:
            error["ambiguous"] = True
        return {"ok": False, "error": error}


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if key.lower() in SECRET_KEYS else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[REDACTED]", value)[:4000]
    return value


def bounded_limit(value: Any, default: int = DEFAULT_LIMIT) -> int:
    try:
        parsed = int(value if value is not None else default)
    except (TypeError, ValueError) as exc:
        raise MessengerError("VALIDATION_ERROR", "limit must be an integer") from exc
    if not 1 <= parsed <= MAX_LIMIT:
        raise MessengerError("VALIDATION_ERROR", f"limit must be between 1 and {MAX_LIMIT}")
    return parsed


def require(arguments: dict[str, Any], name: str) -> Any:
    value = arguments.get(name)
    if value is None or value == "":
        raise MessengerError("VALIDATION_ERROR", f"missing required argument: {name}")
    return value


def normalize_origin(value: str) -> str:
    parsed = urllib.parse.urlsplit(value.strip())
    allow_http = os.environ.get("TIME_MESSENGER_ALLOW_HTTP") == "1"
    local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and not (allow_http and local and parsed.scheme == "http"):
        raise MessengerError("VALIDATION_ERROR", "TiMe URL must use HTTPS")
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise MessengerError("VALIDATION_ERROR", "TiMe URL must be an origin without credentials/query")
    base_path = parsed.path.rstrip("/")
    if base_path.endswith("/api/v4"):
        base_path = base_path[:-7]
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, base_path, "", ""))


def _keychain_account(origin: str) -> str:
    return urllib.parse.urlsplit(origin).netloc


def load_token(origin: str) -> str:
    token = os.environ.get("TIME_MESSENGER_TOKEN")
    if token:
        return token
    if platform.system() == "Darwin":
        result = subprocess.run(
            ["security", "find-generic-password", "-s", "yuzuru.time-messenger", "-a", _keychain_account(origin), "-w"],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    raise MessengerError(
        "NOT_AUTHENTICATED",
        "Configure TIME_MESSENGER_TOKEN or run `server.py setup --url https://your-workspace` on macOS",
    )


def store_macos_token(origin: str, token: str) -> None:
    if platform.system() != "Darwin":
        raise MessengerError(
            "UNSUPPORTED_CAPABILITY",
            "Persistent keychain setup is currently implemented for macOS; use TIME_MESSENGER_TOKEN elsewhere",
        )
    subprocess.run(
        [
            "security",
            "add-generic-password",
            "-U",
            "-s",
            "yuzuru.time-messenger",
            "-a",
            _keychain_account(origin),
            "-w",
            token,
        ],
        text=True,
        capture_output=True,
        timeout=10,
        check=True,
    )


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        raise MessengerError("ORIGIN_REDIRECT_BLOCKED", "credential-bearing redirects are not allowed")


class TimeClient:
    def __init__(self, origin: str | None = None, token: str | None = None, timeout: float = 30.0) -> None:
        configured = origin or os.environ.get("TIME_MESSENGER_URL")
        if not configured:
            raise MessengerError("NOT_AUTHENTICATED", "TIME_MESSENGER_URL is not configured")
        self.origin = normalize_origin(configured)
        self.token = token or load_token(self.origin)
        self.timeout = min(max(float(timeout), 1.0), 60.0)
        self.opener = urllib.request.build_opener(NoRedirect())

    def request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        body: Any = None,
        raw_body: bytes | None = None,
        content_type: str = "application/json",
        mutation: bool = False,
    ) -> Any:
        encoded_path = "/".join(urllib.parse.quote(part, safe="") for part in path.split("/"))
        url = f"{self.origin}{encoded_path}"
        if query:
            cleaned = {key: str(value).lower() if isinstance(value, bool) else value for key, value in query.items() if value is not None}
            url += "?" + urllib.parse.urlencode(cleaned)
        payload = raw_body
        if body is not None:
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "User-Agent": "yuzuru-time-messenger/0.1.0",
        }
        if payload is not None:
            headers["Content-Type"] = content_type
        request = urllib.request.Request(url, data=payload, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                data = response.read(MAX_RESPONSE_BYTES + 1)
                if len(data) > MAX_RESPONSE_BYTES:
                    raise MessengerError("RESPONSE_TOO_LARGE", "TiMe response exceeded 8 MiB")
                if not data:
                    return {}
                if "application/json" not in response.headers.get("Content-Type", ""):
                    return {"content_type": response.headers.get("Content-Type"), "bytes": len(data)}
                return json.loads(data.decode("utf-8"))
        except MessengerError:
            raise
        except urllib.error.HTTPError as exc:
            data = exc.read(32_768)
            try:
                details: Any = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                details = {"status": exc.code}
            code = {
                400: "VALIDATION_ERROR",
                401: "NOT_AUTHENTICATED",
                403: "PERMISSION_DENIED",
                404: "NOT_FOUND",
                409: "CONFLICT",
                429: "RATE_LIMITED",
            }.get(exc.code, "UPSTREAM_ERROR")
            ambiguous = mutation and (exc.code == 429 or exc.code >= 500)
            if ambiguous:
                code = "AMBIGUOUS_WRITE_RESULT"
            raise MessengerError(code, f"TiMe API returned HTTP {exc.code}", details=details, ambiguous=ambiguous) from exc
        except (TimeoutError, urllib.error.URLError, ConnectionError, OSError) as exc:
            code = "AMBIGUOUS_WRITE_RESULT" if mutation else "UPSTREAM_UNAVAILABLE"
            raise MessengerError(code, "TiMe request did not complete", ambiguous=mutation) from exc


def normalize_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": "time-messenger",
        "user_id": user.get("id"),
        "display_name": " ".join(filter(None, [user.get("first_name"), user.get("last_name")])).strip() or user.get("nickname") or user.get("username"),
        "username": user.get("username"),
        "email": user.get("email"),
        "active": not bool(user.get("delete_at")),
        "provider_metadata": {"roles": user.get("roles"), "locale": user.get("locale")},
    }


def normalize_conversation(channel: dict[str, Any]) -> dict[str, Any]:
    provider_kind = channel.get("type")
    kind = {"D": "dm", "G": "group", "O": "channel", "P": "channel"}.get(provider_kind, "channel")
    return {
        "provider": "time-messenger",
        "conversation_id": channel.get("id"),
        "kind": kind,
        "provider_kind": provider_kind,
        "display_name": channel.get("display_name") or channel.get("name"),
        "name": channel.get("name"),
        "team_id": channel.get("team_id"),
        "purpose": channel.get("purpose"),
        "header": channel.get("header"),
        "archived": bool(channel.get("delete_at")),
    }


def normalize_message(post: dict[str, Any], files: dict[str, Any] | None = None) -> dict[str, Any]:
    root = post.get("root_id") or None
    file_ids = list(post.get("file_ids") or [])
    return {
        "provider": "time-messenger",
        "conversation_id": post.get("channel_id"),
        "topic_id": None,
        "thread_id": root or post.get("id"),
        "root_message_id": root,
        "message_id": post.get("id"),
        "sender_id": post.get("user_id"),
        "timestamp": post.get("create_at"),
        "edited_at": post.get("edit_at") or None,
        "text": post.get("message", ""),
        "attachments": [files.get(item, {"file_id": item}) if files else {"file_id": item} for item in file_ids],
        "reply_to": root,
        "reactions": post.get("metadata", {}).get("reactions") if isinstance(post.get("metadata"), dict) else None,
        "provider_metadata": {"type": post.get("type"), "props": post.get("props") or {}},
    }


def normalize_posts(payload: dict[str, Any], limit: int) -> dict[str, Any]:
    posts = payload.get("posts") or {}
    files = payload.get("files") or {}
    order = list(payload.get("order") or posts.keys())[:limit]
    items = [normalize_message(posts[item], files) for item in order if item in posts]
    return {
        "items": items,
        "next_cursor": order[-1] if len(order) == limit else None,
        "truncated": len(order) == limit,
    }


CAPABILITIES = {
    "conversation.list": True,
    "conversation.search": True,
    "conversation.create": True,
    "conversation.update": True,
    "conversation.photo": False,
    "message.history": True,
    "message.search": True,
    "message.send": True,
    "message.reply": True,
    "message.edit": True,
    "message.delete": True,
    "message.forward": True,
    "thread.list": True,
    "thread.get": True,
    "thread.reply": True,
    "topic.list": False,
    "topic.get": False,
    "topic.create": False,
    "topic.update": False,
    "unread.inspect": True,
    "mentions.inspect": True,
    "reaction.read": True,
    "reaction.write": True,
    "pin.read": True,
    "pin.write": True,
    "attachment.read": True,
    "attachment.send": True,
    "membership.list": True,
    "membership.add": True,
    "membership.remove": True,
    "read_state.write": True,
}


class TimeOperations:
    def __init__(self, client: TimeClient) -> None:
        self.client = client

    def call(self, name: str, a: dict[str, Any]) -> Any:
        method = getattr(self, name.removeprefix("time_messenger_"), None)
        if method is None or name == "time_messenger_call":
            raise MessengerError("UNSUPPORTED_CAPABILITY", f"unknown tool: {name}")
        return {"ok": True, "provider": "time-messenger", "result": method(a)}

    def get_identity(self, a: dict[str, Any]) -> Any:
        return {"account": normalize_user(self.client.request("GET", "/api/v4/users/me")), "origin": self.client.origin}

    def get_capabilities(self, a: dict[str, Any]) -> Any:
        return {"api": "v4", "capabilities": CAPABILITIES, "unsupported_outcome": "UNSUPPORTED_CAPABILITY"}

    def resolve_user(self, a: dict[str, Any]) -> Any:
        query = str(require(a, "query"))
        limit = bounded_limit(a.get("limit"), 10)
        users = self.client.request("POST", "/api/v4/users/search", body={"term": query, "team_id": a.get("team_id"), "limit": limit})
        candidates = [normalize_user(item) for item in users[:limit]]
        exact = [item for item in candidates if query.casefold() in {str(item.get("user_id", "")).casefold(), str(item.get("username", "")).casefold(), str(item.get("email", "")).casefold()}]
        return {"candidates": candidates, "exact": exact[0] if len(exact) == 1 else None, "ambiguous": len(candidates) > 1 and len(exact) != 1}

    def resolve_conversation(self, a: dict[str, Any]) -> Any:
        query = str(require(a, "query"))
        limit = bounded_limit(a.get("limit"), 10)
        channels = self.client.request("POST", "/api/v4/channels/search", body={"term": query, "page": "0", "per_page": str(limit), "include_search_by_id": True})
        candidates = [normalize_conversation(item) for item in channels[:limit]]
        exact = [item for item in candidates if query.casefold() in {str(item.get("conversation_id", "")).casefold(), str(item.get("name", "")).casefold()}]
        return {"candidates": candidates, "exact": exact[0] if len(exact) == 1 else None, "ambiguous": len(candidates) > 1 and len(exact) != 1}

    def list_conversations(self, a: dict[str, Any]) -> Any:
        limit = bounded_limit(a.get("limit"))
        channels = self.client.request("GET", "/api/v4/users/me/channels", query={"include_deleted": bool(a.get("include_archived", False))})
        offset = int(a.get("cursor") or 0)
        filtered = [normalize_conversation(item) for item in channels]
        if a.get("kind"):
            filtered = [item for item in filtered if item["kind"] == a["kind"]]
        items = filtered[offset: offset + limit]
        return {"items": items, "next_cursor": str(offset + limit) if offset + limit < len(filtered) else None, "truncated": offset + limit < len(filtered)}

    def get_conversation(self, a: dict[str, Any]) -> Any:
        return normalize_conversation(self.client.request("GET", f"/api/v4/channels/{require(a, 'conversation_id')}"))

    def list_members(self, a: dict[str, Any]) -> Any:
        limit = bounded_limit(a.get("limit"))
        page = int(a.get("cursor") or 0)
        channel_id = require(a, "conversation_id")
        members = self.client.request("GET", f"/api/v4/channels/{channel_id}/members", query={"page": page, "per_page": limit})
        user_ids = [item.get("user_id") for item in members if item.get("user_id")]
        users = self.client.request("POST", "/api/v4/users/ids", body=user_ids) if user_ids else []
        return {"items": [normalize_user(item) for item in users], "next_cursor": str(page + 1) if len(members) == limit else None, "truncated": len(members) == limit}

    def list_messages(self, a: dict[str, Any]) -> Any:
        limit = bounded_limit(a.get("limit"))
        query = {"per_page": limit, "page": int(a.get("page") or 0), "before": a.get("before"), "after": a.get("after"), "around": a.get("around"), "since": a.get("since")}
        payload = self.client.request("GET", f"/api/v4/channels/{require(a, 'conversation_id')}/posts", query=query)
        return normalize_posts(payload, limit)

    def get_message(self, a: dict[str, Any]) -> Any:
        payload = self.client.request("GET", f"/api/v4/posts/{require(a, 'message_id')}")
        return normalize_message(payload)

    def search_messages(self, a: dict[str, Any]) -> Any:
        limit = bounded_limit(a.get("limit"))
        terms = str(require(a, "query"))
        if a.get("sender_username"):
            terms += f" from:{a['sender_username']}"
        if a.get("conversation_name"):
            terms += f" in:{a['conversation_name']}"
        if a.get("after"):
            terms += f" after:{a['after']}"
        if a.get("before"):
            terms += f" before:{a['before']}"
        payload = self.client.request("POST", f"/api/v4/teams/{require(a, 'team_id')}/posts/search", body={"terms": terms, "is_or_search": False, "page": int(a.get("cursor") or 0), "per_page": limit})
        return normalize_posts(payload, limit)

    def list_threads(self, a: dict[str, Any]) -> Any:
        limit = bounded_limit(a.get("limit"))
        payload = self.client.request("GET", f"/api/v4/users/me/teams/{require(a, 'team_id')}/threads", query={"pageSize": limit, "before": a.get("cursor"), "unread": a.get("unread"), "extended": False, "threadsOnly": True})
        threads = list(payload.get("threads") or [])[:limit]
        return {"items": threads, "next_cursor": threads[-1].get("id") if len(threads) == limit else None, "truncated": len(threads) == limit}

    def get_thread(self, a: dict[str, Any]) -> Any:
        payload = self.client.request("GET", f"/api/v4/posts/{require(a, 'thread_id')}/thread", query={"perPage": bounded_limit(a.get("limit"))})
        return normalize_posts(payload, bounded_limit(a.get("limit")))

    def list_topics(self, a: dict[str, Any]) -> Any:
        raise MessengerError("UNSUPPORTED_CAPABILITY", "TiMe API v4 has root/reply threads but no distinct topic resource")

    get_topic = list_topics

    def inspect_unread(self, a: dict[str, Any]) -> Any:
        values = self.client.request("GET", "/api/v4/users/me/teams/unread", query={"exclude_team": a.get("exclude_team_id")})
        limit = bounded_limit(a.get("limit"))
        items = list(values)[:limit]
        return {"items": items, "truncated": len(values) > limit, "read_state_changed": False}

    def inspect_mentions(self, a: dict[str, Any]) -> Any:
        identity = normalize_user(self.client.request("GET", "/api/v4/users/me"))
        forwarded = dict(a)
        forwarded["query"] = f"@{identity['username']}"
        return {**self.search_messages(forwarded), "read_state_changed": False}

    def get_reactions(self, a: dict[str, Any]) -> Any:
        values = self.client.request("GET", f"/api/v4/posts/{require(a, 'message_id')}/reactions")
        return {"items": values[:bounded_limit(a.get("limit"))]}

    def get_pins(self, a: dict[str, Any]) -> Any:
        limit = bounded_limit(a.get("limit"))
        return normalize_posts(self.client.request("GET", f"/api/v4/channels/{require(a, 'conversation_id')}/pinned"), limit)

    def search_files(self, a: dict[str, Any]) -> Any:
        limit = bounded_limit(a.get("limit"))
        body = {"terms": str(require(a, "query")), "is_or_search": False, "page": int(a.get("cursor") or 0), "per_page": limit}
        payload = self.client.request("POST", f"/api/v4/teams/{require(a, 'team_id')}/files/search", body=body)
        items = list(payload.get("file_infos") or payload.get("items") or [])[:limit]
        return {"items": items, "next_cursor": str(int(a.get("cursor") or 0) + 1) if len(items) == limit else None, "truncated": len(items) == limit}

    def get_file_metadata(self, a: dict[str, Any]) -> Any:
        value = self.client.request("GET", f"/api/v4/files/{require(a, 'file_id')}/info")
        return {key: value.get(key) for key in ("id", "user_id", "post_id", "create_at", "name", "extension", "size", "mime_type", "width", "height")}

    def send_message(self, a: dict[str, Any]) -> Any:
        body = {"channel_id": require(a, "conversation_id"), "message": str(require(a, "text")), "root_id": a.get("thread_id") or "", "file_ids": a.get("file_ids") or [], "forwarded_post_id": a.get("forward_message_id"), "idempotency_key": a.get("idempotency_key") or str(uuid.uuid4())}
        return normalize_message(self.client.request("POST", "/api/v4/posts", body=body, mutation=True))

    reply_message = send_message

    def edit_message(self, a: dict[str, Any]) -> Any:
        value = self.client.request("PUT", f"/api/v4/posts/{require(a, 'message_id')}/patch", body={"message": str(require(a, "text"))}, mutation=True)
        return normalize_message(value)

    def delete_message(self, a: dict[str, Any]) -> Any:
        require(a, "confirm_exact")
        return self.client.request("DELETE", f"/api/v4/posts/{require(a, 'message_id')}", mutation=True)

    def add_reaction(self, a: dict[str, Any]) -> Any:
        body = {"user_id": "me", "post_id": require(a, "message_id"), "emoji_name": require(a, "emoji")}
        return self.client.request("POST", "/api/v4/reactions", body=body, mutation=True)

    def remove_reaction(self, a: dict[str, Any]) -> Any:
        return self.client.request("DELETE", f"/api/v4/users/me/posts/{require(a, 'message_id')}/reactions/{require(a, 'emoji')}", mutation=True)

    def pin_message(self, a: dict[str, Any]) -> Any:
        return self.client.request("POST", f"/api/v4/posts/{require(a, 'message_id')}/pin", mutation=True)

    def unpin_message(self, a: dict[str, Any]) -> Any:
        return self.client.request("POST", f"/api/v4/posts/{require(a, 'message_id')}/unpin", mutation=True)

    def create_conversation(self, a: dict[str, Any]) -> Any:
        kind = require(a, "kind")
        members = list(a.get("member_ids") or [])
        if kind == "dm":
            me = normalize_user(self.client.request("GET", "/api/v4/users/me"))["user_id"]
            value = self.client.request("POST", "/api/v4/channels/direct", body=[me, require(a, "user_id")], mutation=True)
        elif kind == "group":
            me = normalize_user(self.client.request("GET", "/api/v4/users/me"))["user_id"]
            value = self.client.request("POST", "/api/v4/channels/group", body=list(dict.fromkeys([me, *members])), mutation=True)
        elif kind == "channel":
            body = {"team_id": require(a, "team_id"), "name": require(a, "name"), "display_name": require(a, "display_name"), "type": "P" if a.get("private") else "O", "purpose": a.get("purpose", ""), "header": a.get("header", "")}
            value = self.client.request("POST", "/api/v4/channels", body=body, mutation=True)
        else:
            raise MessengerError("VALIDATION_ERROR", "kind must be dm, group, or channel")
        return normalize_conversation(value)

    def update_conversation(self, a: dict[str, Any]) -> Any:
        allowed = {key: a[key] for key in ("name", "display_name", "purpose", "header") if key in a}
        if not allowed:
            raise MessengerError("VALIDATION_ERROR", "no supported update fields supplied")
        value = self.client.request("PUT", f"/api/v4/channels/{require(a, 'conversation_id')}/patch", body=allowed, mutation=True)
        return normalize_conversation(value)

    def add_members(self, a: dict[str, Any]) -> Any:
        channel_id = require(a, "conversation_id")
        results = []
        for user_id in list(require(a, "user_ids"))[:MAX_LIMIT]:
            try:
                value = self.client.request("POST", f"/api/v4/channels/{channel_id}/members", body={"user_id": user_id}, mutation=True)
                results.append({"user_id": user_id, "ok": True, "state": value})
            except MessengerError as exc:
                results.append({"user_id": user_id, **exc.as_dict()})
                if exc.ambiguous:
                    break
        return {"items": results, "partial": any(not item.get("ok") for item in results)}

    def remove_members(self, a: dict[str, Any]) -> Any:
        require(a, "confirm_exact")
        channel_id = require(a, "conversation_id")
        results = []
        for user_id in list(require(a, "user_ids"))[:MAX_LIMIT]:
            try:
                value = self.client.request("DELETE", f"/api/v4/channels/{channel_id}/members/{user_id}", mutation=True)
                results.append({"user_id": user_id, "ok": True, "state": value})
            except MessengerError as exc:
                results.append({"user_id": user_id, **exc.as_dict()})
                if exc.ambiguous:
                    break
        return {"items": results, "partial": any(not item.get("ok") for item in results)}

    def mark_read(self, a: dict[str, Any]) -> Any:
        body = {"channel_id": require(a, "conversation_id"), "prev_channel_id": a.get("previous_conversation_id", "")}
        return self.client.request("POST", "/api/v4/channels/members/me/view", body=body, mutation=True)

    def mark_unread(self, a: dict[str, Any]) -> Any:
        return self.client.request("POST", f"/api/v4/users/me/posts/{require(a, 'message_id')}/set_unread", mutation=True)

    def upload_file(self, a: dict[str, Any]) -> Any:
        path = Path(str(require(a, "path"))).expanduser().resolve()
        if not path.is_file():
            raise MessengerError("VALIDATION_ERROR", "upload path must be an existing file")
        max_bytes = min(int(a.get("max_bytes") or 25 * 1024 * 1024), 25 * 1024 * 1024)
        data = path.read_bytes()
        if len(data) > max_bytes:
            raise MessengerError("VALIDATION_ERROR", f"file exceeds {max_bytes} bytes")
        boundary = "----yuzuru" + secrets.token_hex(12)
        fields = [("channel_id", str(require(a, "conversation_id")))]
        chunks: list[bytes] = []
        for key, value in fields:
            chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n".encode())
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        safe_name = path.name.replace('"', "")
        chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"files\"; filename=\"{safe_name}\"\r\nContent-Type: {mime}\r\n\r\n".encode())
        chunks.extend([data, f"\r\n--{boundary}--\r\n".encode()])
        value = self.client.request("POST", "/api/v4/files", raw_body=b"".join(chunks), content_type=f"multipart/form-data; boundary={boundary}", mutation=True)
        files = value.get("file_infos") or []
        return {"items": [{key: item.get(key) for key in ("id", "name", "size", "mime_type")} for item in files]}


def interactive_setup(url: str) -> dict[str, Any]:
    origin = normalize_origin(url)
    token = getpass.getpass("TiMe Personal Access Token: ")
    if not token:
        raise MessengerError("VALIDATION_ERROR", "token cannot be empty")
    client = TimeClient(origin, token)
    identity = normalize_user(client.request("GET", "/api/v4/users/me"))
    store_macos_token(origin, token)
    return {"ok": True, "origin": origin, "account": identity, "stored_in": "macOS Keychain"}
