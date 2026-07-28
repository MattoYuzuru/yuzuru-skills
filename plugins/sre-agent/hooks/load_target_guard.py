#!/usr/bin/env python3
"""Block common load tools against non-local URLs without an exact host allowlist."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import sys
from urllib.parse import urlparse


LOAD_TOOL_RE = re.compile(r"(?:^|[;&|]\s*|\s)(k6|wrk|wrk2|hey|ab|locust)(?:\s|$)")
URL_RE = re.compile(r"https?://[^\s'\"<>]+")


def command_from_event(value: object) -> str:
    if isinstance(value, dict):
        tool_input = value.get("tool_input")
        if isinstance(tool_input, dict) and isinstance(tool_input.get("command"), str):
            return tool_input["command"]
        if isinstance(value.get("command"), str):
            return value["command"]
    return ""


def local_host(host: str) -> bool:
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost"):
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_loopback


def blocked(command: str, allowlist: str | None) -> tuple[bool, str | None]:
    if not LOAD_TOOL_RE.search(command):
        return False, None
    hosts = [urlparse(value).hostname for value in URL_RE.findall(command)]
    hosts = [host for host in hosts if host]
    for host in hosts:
        if local_host(host) or host == allowlist:
            continue
        return True, host
    return False, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", help="check one command instead of reading hook input")
    parser.add_argument("--authorized-host", help="exact allowed non-local host for a test")
    args = parser.parse_args()
    if args.check is not None:
        command = args.check
    else:
        try:
            command = command_from_event(json.load(sys.stdin))
        except json.JSONDecodeError:
            print("invalid hook input", file=sys.stderr)
            return 1
    allowlist = args.authorized_host or os.environ.get("YUZURU_LOAD_TEST_AUTHORIZED_TARGET")
    is_blocked, host = blocked(command, allowlist)
    if is_blocked:
        print(
            f"blocked load-test command for non-local host {host}; "
            "set YUZURU_LOAD_TEST_AUTHORIZED_TARGET to the exact approved host",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
