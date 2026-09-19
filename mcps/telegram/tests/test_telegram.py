from __future__ import annotations

import json
import hashlib
import os
import platform
import queue
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server import TOOLS  # noqa: E402
from tdjson import TelegramError, map_error, native_library_path, platform_key  # noqa: E402
from telegram_client import ProfileLock, TelegramOperations, bounded_limit, normalize_chat, normalize_message  # noqa: E402


class FakeTd:
    def __init__(self) -> None:
        self.calls: list[tuple[dict[str, object], bool]] = []
        self.responses: dict[str, object] = {"getAuthorizationState": {"@type": "authorizationStateReady"}}
        self.updates: list[dict[str, object]] = []

    def request(self, request: dict[str, object], timeout: float = 30, *, mutation: bool = False) -> dict[str, object]:
        self.calls.append((request, mutation))
        value = self.responses.get(str(request.get("@type")), {})
        if isinstance(value, Exception):
            raise value
        return dict(value)

    def wait_update(self, predicate: object, timeout: float = 30) -> dict[str, object]:
        for item in self.updates:
            if predicate(item):
                return item
        raise TelegramError("AMBIGUOUS_MUTATION", "no final update", ambiguous=True)


class RuntimeTests(unittest.TestCase):
    def test_supported_platform_key_is_stable(self) -> None:
        with mock.patch.object(platform, "system", return_value="Darwin"), mock.patch.object(platform, "machine", return_value="arm64"):
            self.assertEqual(platform_key(), "darwin-arm64")

    def test_missing_native_runtime_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("TELEGRAM_TDJSON_LIBRARY", None)
                with self.assertRaises(TelegramError) as caught:
                    native_library_path(Path(temp))
        self.assertEqual(caught.exception.code, "NATIVE_RUNTIME_UNAVAILABLE")

    def test_error_mapping(self) -> None:
        self.assertEqual(map_error(429, "Too Many Requests"), "RATE_LIMITED")
        self.assertEqual(map_error(400, "USER_PRIVACY_RESTRICTED"), "PRIVACY_RESTRICTED")
        self.assertEqual(map_error(401, "Unauthorized"), "AUTH_REVOKED")

    def test_limits_follow_tdlib_hard_cap(self) -> None:
        self.assertEqual(bounded_limit(None), 20)
        with self.assertRaises(TelegramError):
            bounded_limit(101)

    def test_packaged_artifact_hashes_match_manifest(self) -> None:
        manifest = json.loads((ROOT / "native" / "manifest.json").read_text(encoding="utf-8"))
        for relative, expected in manifest["artifacts"].items():
            digest = hashlib.sha256((ROOT / "native" / relative).read_bytes()).hexdigest()
            self.assertEqual(digest, expected)

    def test_profile_lock_rejects_second_writer(self) -> None:
        with tempfile.TemporaryDirectory() as temp, mock.patch.dict(
            os.environ, {"XDG_DATA_HOME": temp, "TELEGRAM_PROFILE": "test"}
        ):
            with ProfileLock():
                with self.assertRaises(TelegramError) as caught:
                    with ProfileLock():
                        pass
        self.assertEqual(caught.exception.code, "STATE_LOCKED")


class NormalizationTests(unittest.TestCase):
    def test_chat_types_remain_distinct(self) -> None:
        group = normalize_chat({"id": -1, "title": "Group", "type": {"@type": "chatTypeSupergroup", "is_channel": False}})
        channel = normalize_chat({"id": -2, "title": "Channel", "type": {"@type": "chatTypeSupergroup", "is_channel": True}})
        self.assertEqual(group["kind"], "group")
        self.assertEqual(channel["kind"], "channel")
        self.assertEqual(group["provider_kind"], "chatTypeSupergroup")

    def test_topic_and_thread_are_not_flattened(self) -> None:
        value = normalize_message({"id": 9, "chat_id": -1, "date": 1, "message_thread_id": 7, "topic_id": {"@type": "messageTopicForum", "forum_topic_id": 7}, "content": {"@type": "messageText", "text": {"text": "hello"}}})
        self.assertEqual(value["thread_id"], "7")
        self.assertEqual(value["topic_id"]["@type"], "messageTopicForum")


class OperationTests(unittest.TestCase):
    def test_auth_status_does_not_require_completed_login(self) -> None:
        td = FakeTd()
        td.responses["getAuthorizationState"] = {"@type": "authorizationStateWaitPhoneNumber"}
        result = TelegramOperations(td, check_authorization=False).call("telegram_auth_status", {})
        self.assertFalse(result["result"]["ready"])

    def test_unread_inspection_never_calls_view_messages(self) -> None:
        td = FakeTd()
        td.responses["getChats"] = {"chat_ids": [1]}
        td.responses["getChat"] = {"id": 1, "title": "Unread", "type": {"@type": "chatTypePrivate"}, "unread_count": 2}
        result = TelegramOperations(td, check_authorization=False).call("telegram_inspect_unread", {"limit": 5})
        self.assertFalse(result["result"]["read_state_changed"])
        self.assertNotIn("viewMessages", [item[0].get("@type") for item in td.calls])

    def test_thread_listing_is_explicitly_unsupported(self) -> None:
        with self.assertRaises(TelegramError) as caught:
            TelegramOperations(FakeTd(), check_authorization=False).call("telegram_list_threads", {"conversation_id": "1"})
        self.assertEqual(caught.exception.code, "UNSUPPORTED_CAPABILITY")

    def test_forward_into_ordinary_thread_is_rejected(self) -> None:
        with self.assertRaises(TelegramError) as caught:
            TelegramOperations(FakeTd(), check_authorization=False).call("telegram_forward_messages", {"conversation_id": "1", "from_conversation_id": "2", "message_ids": ["3"], "thread_id": "4"})
        self.assertEqual(caught.exception.code, "UNSUPPORTED_CAPABILITY")

    def test_send_waits_for_final_success(self) -> None:
        td = FakeTd()
        td.responses["sendMessage"] = {"id": -99, "chat_id": 1, "content": {"@type": "messageText", "text": {"text": "hi"}}}
        td.updates = [{"@type": "updateMessageSendSucceeded", "old_message_id": -99, "message": {"id": 100, "chat_id": 1, "date": 1, "content": {"@type": "messageText", "text": {"text": "hi"}}}}]
        result = TelegramOperations(td, check_authorization=False).call("telegram_send_message", {"conversation_id": "1", "text": "hi"})
        self.assertEqual(result["result"]["message_id"], "100")
        self.assertTrue(td.calls[-1][1])

    def test_destructive_tools_require_confirmation(self) -> None:
        tools = {item["name"]: item for item in TOOLS}
        for name in ("telegram_delete_message", "telegram_remove_members"):
            self.assertTrue(tools[name]["annotations"]["destructiveHint"])
            self.assertIn("confirm_exact", tools[name]["inputSchema"]["required"])

    def test_capability_inventory_exposes_thread_limit(self) -> None:
        td = FakeTd()
        td.responses["getOption"] = {"value": {"value": "1.8.67"}}
        result = TelegramOperations(td, check_authorization=False).call("telegram_get_capabilities", {})
        self.assertFalse(result["result"]["capabilities"]["thread.list"])


if __name__ == "__main__":
    unittest.main()
