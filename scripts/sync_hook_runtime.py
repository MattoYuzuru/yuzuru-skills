#!/usr/bin/env python3
"""Vendor the bounded shell inspector into self-contained plugin hook packages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ("devops-agent", "sre-agent")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report drift without writing")
    args = parser.parse_args()
    source = (ROOT / "scripts/hook_shell.py").read_bytes()
    drift = []
    for name in PLUGINS:
        target = ROOT / "plugins" / name / "hooks/hook_shell.py"
        if not target.exists() or target.read_bytes() != source:
            drift.append(name)
            if not args.check:
                target.write_bytes(source)
    print(json.dumps({"ok": not (args.check and drift), "check": args.check, "drift": drift}))
    return int(args.check and bool(drift))


if __name__ == "__main__":
    raise SystemExit(main())
