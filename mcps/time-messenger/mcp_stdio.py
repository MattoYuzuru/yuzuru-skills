#!/usr/bin/env python3
"""Small dependency-free MCP stdio transport used by the packaged server."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import Any


ToolHandler = Callable[[str, dict[str, Any]], Any]


class McpServer:
    def __init__(self, name: str, version: str, tools: list[dict[str, Any]], handler: ToolHandler) -> None:
        self.name = name
        self.version = version
        self.tools = tools
        self.handler = handler

    @staticmethod
    def _write(message: dict[str, Any]) -> None:
        sys.stdout.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n")
        sys.stdout.flush()

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

    def _dispatch(self, message: dict[str, Any]) -> dict[str, Any] | None:
        request_id = message.get("id")
        method = message.get("method")
        params = message.get("params") or {}
        if request_id is None:
            return None
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": params.get("protocolVersion", "2025-06-18"),
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": self.name, "version": self.version},
                },
            }
        if method == "ping":
            return {"jsonrpc": "2.0", "id": request_id, "result": {}}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": self.tools}}
        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments") or {}
            if not isinstance(name, str) or not isinstance(arguments, dict):
                return self._error(request_id, -32602, "invalid tool call")
            try:
                value = self.handler(name, arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(value, ensure_ascii=False, separators=(",", ":")),
                            }
                        ],
                        "structuredContent": value,
                    },
                }
            except Exception as exc:  # normalized by provider clients
                payload = exc.as_dict() if hasattr(exc, "as_dict") else {
                    "ok": False,
                    "error": {"code": "INTERNAL_ERROR", "message": str(exc)[:500]},
                }
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "isError": True,
                        "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
                        "structuredContent": payload,
                    },
                }
        return self._error(request_id, -32601, f"method not found: {method}")

    def run(self) -> None:
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                message = json.loads(line)
                if not isinstance(message, dict):
                    raise ValueError("message must be an object")
                response = self._dispatch(message)
            except (json.JSONDecodeError, ValueError) as exc:
                response = self._error(None, -32700, str(exc)[:300])
            if response is not None:
                self._write(response)
