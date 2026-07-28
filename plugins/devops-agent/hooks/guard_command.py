#!/usr/bin/env python3
"""Block broad root/home deletion commands in plugin hook input."""

from __future__ import annotations

import argparse
import json
import re
import sys


FORBIDDEN = (
    re.compile(r"\brm\s+(?:-[A-Za-z]*r[A-Za-z]*f[A-Za-z]*|-[A-Za-z]*f[A-Za-z]*r[A-Za-z]*)\s+/(?:\s|$)"),
    re.compile(r"\brm\s+(?:-[A-Za-z]*r[A-Za-z]*f[A-Za-z]*|-[A-Za-z]*f[A-Za-z]*r[A-Za-z]*)\s+~(?:/|\s|$)"),
    re.compile(r"\b(?:Remove-Item|del)\b[^\n]*(?:\$HOME|\\\\Users\\\\)[^\n]*(?:-Recurse|/s)", re.I),
)


def extract_command(value: object) -> str:
    if not isinstance(value, dict):
        return ""
    tool_input = value.get("tool_input")
    if isinstance(tool_input, dict) and isinstance(tool_input.get("command"), str):
        return tool_input["command"]
    if isinstance(value.get("command"), str):
        return value["command"]
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", help="check one command instead of reading hook JSON on stdin")
    args = parser.parse_args()
    if args.check is not None:
        command = args.check
    else:
        try:
            command = extract_command(json.load(sys.stdin))
        except json.JSONDecodeError:
            print("invalid hook input", file=sys.stderr)
            return 1
    if any(pattern.search(command) for pattern in FORBIDDEN):
        print("blocked broad destructive command targeting root or a home directory", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
