#!/usr/bin/env python3
"""Block broad root/home deletion commands in plugin hook input."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys

from hook_shell import AnalysisLimit, basename, commands


def broad_target(value: str) -> bool:
    """Match the root/home itself or its immediate wildcard, not every descendant."""
    value = re.sub(r"^\$(?:HOME\b|\{HOME\})", str(Path.home()), value)
    if re.fullmatch(r"~[^/]*(?:/[*?]?)?", value):
        return True
    value = os.path.normpath(os.path.expanduser(value))
    roots = {"/", "/home", "/Users", "/root", str(Path.home())}
    if value in roots or (os.path.dirname(value) in roots and os.path.basename(value) in {"*", ".*", "?"}):
        return True
    return bool(re.fullmatch(r"/(?:home|Users)/[^/*?]+", value))


def blocked(command: str) -> bool:
    for words in commands(command):
        name = basename(words[0])
        options = []
        targets = []
        end_options = False
        for word in words[1:]:
            if word == "--" and not end_options:
                end_options = True
            elif (word.startswith("-") or (name == "del" and word.lower() == "/s")) and not end_options:
                options.append(word)
            else:
                targets.append(word)
        recursive = any(
            option == "--recursive"
            or (name == "rm" and option.startswith("-") and not option.startswith("--") and any(c in option[1:] for c in "rR"))
            or (name in {"remove-item", "del"} and option.lower() in {"-recurse", "/s"})
            for option in options
        )
        if name in {"rm", "remove-item", "del"} and recursive and any(broad_target(target) for target in targets):
            return True
    return False


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
    try:
        denied = blocked(command)
    except AnalysisLimit as exc:
        print(f"command guard: {exc}", file=sys.stderr)
        return 2
    if denied:
        print("blocked broad destructive command targeting root or a home directory", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
