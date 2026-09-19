from __future__ import annotations

import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcp_stdio import McpServer  # noqa: E402
from server import TOOLS  # noqa: E402
from time_client import (  # noqa: E402
    MessengerError,
    TimeClient,
    TimeOperations,
    bounded_limit,
    normalize_origin,
    redact,
)


class FakeClient:
    origin = "https://chat.example.test"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, object]]] = []
        self.responses: dict[tuple[str, str], object] = {}

    def request(self, method: str, path: str, **kwargs: object) -> object:
        self.calls.append((method, path, kwargs))
        value = self.responses.get((method, path), {})
        if isinstance(value, Exception):
            raise value
        return value


class TimeClientTests(unittest.TestCase):
    def test_origin_requires_https(self) -> None:
        with self.assertRaises(MessengerError) as caught:
            normalize_origin("http://chat.example.test")
        self.assertEqual(caught.exception.code, "VALIDATION_ERROR")
        self.assertEqual(normalize_origin("https://chat.example.test/api/v4/"), "https://chat.example.test")

    def test_local_http_is_test_only(self) -> None:
        with mock.patch.dict(os.environ, {"TIME_MESSENGER_ALLOW_HTTP": "1"}):
            self.assertEqual(normalize_origin("http://127.0.0.1:8065"), "http://127.0.0.1:8065")

    def test_limit_is_bounded(self) -> None:
        self.assertEqual(bounded_limit(None), 30)
        for value in (0, 101, "no"):
            with self.assertRaises(MessengerError):
                bounded_limit(value)

    def test_redaction_removes_bearer_and_secret_fields(self) -> None:
        value = redact({"token": "secret", "message": "Bearer abc.def", "nested": {"password": "x"}})
        self.assertEqual(value["token"], "[REDACTED]")
        self.assertEqual(value["nested"]["password"], "[REDACTED]")
        self.assertNotIn("abc.def", value["message"])

    def test_mutation_timeout_is_ambiguous_and_not_retried(self) -> None:
        client = TimeClient("https://chat.example.test", "secret")
        opener = mock.Mock()
        opener.open.side_effect = TimeoutError()
        client.opener = opener
        with self.assertRaises(MessengerError) as caught:
            client.request("POST", "/api/v4/posts", body={"message": "x"}, mutation=True)
        self.assertEqual(caught.exception.code, "AMBIGUOUS_WRITE_RESULT")
        self.assertEqual(opener.open.call_count, 1)


class OperationTests(unittest.TestCase):
    def test_history_is_bounded_and_preserves_read_state(self) -> None:
        client = FakeClient()
        client.responses[("GET", "/api/v4/channels/c1/posts")] = {
            "order": ["p2", "p1"],
            "posts": {
                "p2": {"id": "p2", "channel_id": "c1", "user_id": "u2", "message": "new"},
                "p1": {"id": "p1", "channel_id": "c1", "user_id": "u1", "message": "old"},
            },
        }
        result = TimeOperations(client).call("time_messenger_list_messages", {"conversation_id": "c1", "limit": 1})
        self.assertEqual([item["message_id"] for item in result["result"]["items"]], ["p2"])
        self.assertEqual(client.calls[0][0:2], ("GET", "/api/v4/channels/c1/posts"))
        self.assertFalse(any("/view" in path for _, path, _ in client.calls))

    def test_topic_is_explicitly_unsupported(self) -> None:
        with self.assertRaises(MessengerError) as caught:
            TimeOperations(FakeClient()).call("time_messenger_list_topics", {"conversation_id": "c1"})
        self.assertEqual(caught.exception.code, "UNSUPPORTED_CAPABILITY")

    def test_send_has_idempotency_key(self) -> None:
        client = FakeClient()
        client.responses[("POST", "/api/v4/posts")] = {"id": "p1", "channel_id": "c1", "message": "hello"}
        TimeOperations(client).call("time_messenger_send_message", {"conversation_id": "c1", "text": "hello"})
        body = client.calls[0][2]["body"]
        self.assertTrue(body["idempotency_key"])
        self.assertTrue(client.calls[0][2]["mutation"])

    def test_partial_member_batch_stops_after_ambiguous_result(self) -> None:
        client = FakeClient()
        client.responses[("POST", "/api/v4/channels/c1/members")] = MessengerError(
            "AMBIGUOUS_WRITE_RESULT", "timeout", ambiguous=True
        )
        result = TimeOperations(client).call(
            "time_messenger_add_members", {"conversation_id": "c1", "user_ids": ["u1", "u2"]}
        )
        self.assertTrue(result["result"]["partial"])
        self.assertEqual(len(client.calls), 1)

    def test_destructive_tools_require_exact_confirmation_field(self) -> None:
        names = {item["name"]: item for item in TOOLS}
        for name in ("time_messenger_delete_message", "time_messenger_remove_members"):
            self.assertTrue(names[name]["annotations"]["destructiveHint"])
            self.assertIn("confirm_exact", names[name]["inputSchema"]["required"])


class McpProtocolTests(unittest.TestCase):
    def test_initialize_and_tool_list(self) -> None:
        server = McpServer("test", "1", TOOLS[:1], lambda _name, _args: {"ok": True})
        initialized = server._dispatch({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
        self.assertEqual(initialized["result"]["serverInfo"]["name"], "test")
        listed = server._dispatch({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        self.assertEqual(listed["result"]["tools"][0]["name"], "time_messenger_get_identity")

    def test_tool_errors_are_structured_and_redacted(self) -> None:
        def fail(_name: str, _arguments: dict[str, object]) -> object:
            raise MessengerError("NOT_AUTHENTICATED", "Bearer abc.secret")

        server = McpServer("test", "1", TOOLS[:1], fail)
        result = server._dispatch({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "x", "arguments": {}}})
        self.assertTrue(result["result"]["isError"])
        self.assertNotIn("abc.secret", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
