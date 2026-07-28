#!/usr/bin/env python3
"""Warn when a file tool writes common transient runtime paths."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


FORBIDDEN = {".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache"}


def find_pollution(root: Path, limit: int = 20) -> list[str]:
    if not root.is_dir():
        return []
    found: list[str] = []
    for current, directories, filenames in os.walk(root, followlinks=False):
        if ".git" in Path(current).parts:
            directories[:] = []
            continue
        for directory in list(directories):
            if directory in FORBIDDEN:
                found.append((Path(current) / directory).relative_to(root).as_posix())
                directories.remove(directory)
                if len(found) >= limit:
                    return found
        for filename in filenames:
            if filename == ".coverage" or filename.endswith(".pyc"):
                found.append((Path(current) / filename).relative_to(root).as_posix())
                if len(found) >= limit:
                    return found
    return found


def event_paths(event: object) -> list[Path]:
    if not isinstance(event, dict) or not isinstance(event.get("tool_input"), dict):
        return []
    tool_input = event["tool_input"]
    values: list[str] = []
    for key in ("file_path", "path"):
        if isinstance(tool_input.get(key), str):
            values.append(tool_input[key])
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        for edit in edits:
            if isinstance(edit, dict) and isinstance(edit.get("file_path"), str):
                values.append(edit["file_path"])
    return [Path(value) for value in values]


def pollution_reason(path: Path) -> str | None:
    if any(part in FORBIDDEN for part in path.parts):
        return "runtime cache or repository-local dependency directory"
    if path.name == ".coverage" or path.suffix == ".pyc":
        return "runtime output"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="explicitly scan a project root (audit/test mode)")
    args = parser.parse_args()
    if args.root is not None:
        found = find_pollution(args.root.resolve())
    else:
        try:
            event = json.load(sys.stdin)
        except json.JSONDecodeError:
            event = {}
        found = [
            str(path) for path in event_paths(event) if pollution_reason(path) is not None
        ][:20]
    if found:
        print(
            "repository runtime artifact written; prefer temporary/user cache storage: "
            + ", ".join(found),
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
