#!/usr/bin/env python3
"""Block file-tool writes to common mutable runtime artifact paths."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import PurePath

BLOCKED_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "node_modules",
    "coverage",
}
BLOCKED_NAMES = {".coverage", "coverage.xml", "npm-debug.log"}
BLOCKED_SUFFIXES = {".pyc", ".pyo"}


def extract_paths(payload: dict[str, object]) -> list[str]:
    tool_input = payload.get("tool_input", {})
    if not isinstance(tool_input, dict):
        return []
    paths: list[str] = []
    for key in ("file_path", "path"):
        value = tool_input.get(key)
        if isinstance(value, str):
            paths.append(value)
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        for edit in edits:
            if isinstance(edit, dict) and isinstance(edit.get("file_path"), str):
                paths.append(edit["file_path"])
    return paths


def blocked_reason(path_text: str) -> str | None:
    path = PurePath(path_text)
    if any(part in BLOCKED_PARTS for part in path.parts):
        return "runtime cache or dependency directory"
    if path.name in BLOCKED_NAMES or path.suffix in BLOCKED_SUFFIXES:
        return "mutable runtime output"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", help="JSON event instead of stdin (test/debug only)")
    args = parser.parse_args()
    try:
        payload = json.loads(args.event) if args.event else json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError) as exc:
        print(f"cleaner-agent hook: invalid JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(payload, dict):
        print("cleaner-agent hook: event must be an object", file=sys.stderr)
        return 2
    for path in extract_paths(payload):
        reason = blocked_reason(path)
        if reason:
            print(
                f"cleaner-agent blocked writing {path!r}: {reason}; use a temporary or user cache directory",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
