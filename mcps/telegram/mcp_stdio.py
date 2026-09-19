#!/usr/bin/env python3
"""Small dependency-free MCP stdio transport used by the packaged server."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import Any


class McpServer:
    def __init__(self, name: str, version: str, tools: list[dict[str, Any]], handler: Callable[[str, dict[str, Any]], Any]) -> None:
        self.name, self.version, self.tools, self.handler = name, version, tools, handler

    @staticmethod
    def _write(value: dict[str, Any]) -> None:
        sys.stdout.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
        sys.stdout.flush()

    def _dispatch(self, message: dict[str, Any]) -> dict[str, Any] | None:
        request_id, method, params = message.get("id"), message.get("method"), message.get("params") or {}
        if request_id is None:
            return None
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": request_id, "result": {"protocolVersion": params.get("protocolVersion", "2025-06-18"), "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": self.name, "version": self.version}}}
        if method == "ping":
            return {"jsonrpc": "2.0", "id": request_id, "result": {}}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": self.tools}}
        if method != "tools/call":
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"method not found: {method}"}}
        try:
            result = self.handler(str(params.get("name", "")), params.get("arguments") or {})
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, separators=(",", ":"))}], "structuredContent": result}}
        except Exception as exc:
            result = exc.as_dict() if hasattr(exc, "as_dict") else {"ok": False, "error": {"code": "INTERNAL_ERROR", "message": str(exc)[:500]}}
            return {"jsonrpc": "2.0", "id": request_id, "result": {"isError": True, "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}], "structuredContent": result}}

    def run(self) -> None:
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                value = json.loads(line)
                response = self._dispatch(value)
            except (json.JSONDecodeError, ValueError) as exc:
                response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)[:300]}}
            if response is not None:
                self._write(response)
