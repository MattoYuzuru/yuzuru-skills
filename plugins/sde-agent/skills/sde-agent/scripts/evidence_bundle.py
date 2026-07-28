#!/usr/bin/env python3
"""Validate completion-state consistency in a bounded evidence bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED = (
    "work_package",
    "revision",
    "commands",
    "tests",
    "artifacts",
    "findings",
    "limitations",
    "verified_environments",
    "unverified_environments",
    "release_ready",
)


def validate(document: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    bundle = document.get("evidence_bundle")
    if not isinstance(bundle, dict):
        return {"ok": False, "errors": ["missing evidence_bundle object"]}, False
    errors = [f"missing {key}" for key in REQUIRED if key not in bundle]
    for key in ("commands", "tests", "artifacts", "findings", "limitations", "verified_environments", "unverified_environments"):
        if key in bundle and not isinstance(bundle[key], list):
            errors.append(f"{key} must be an array")
        elif isinstance(bundle.get(key), list) and len(bundle[key]) > 500:
            errors.append(f"{key} exceeds 500 entries")
    failures: list[str] = []
    for section in ("commands", "tests"):
        for index, item in enumerate(bundle.get(section, [])):
            if not isinstance(item, dict):
                errors.append(f"{section}[{index}] must be an object")
                continue
            if not isinstance(item.get("command"), str) or not isinstance(item.get("exit_code"), int):
                errors.append(f"{section}[{index}] requires command and integer exit_code")
                continue
            if item["exit_code"] != 0:
                failures.append(item["command"])
    if bundle.get("release_ready") is True:
        if failures:
            errors.append("release_ready cannot be true with failed commands/tests")
        if bundle.get("unverified_environments"):
            errors.append("release_ready cannot be true with unverified environments")
        if bundle.get("limitations"):
            errors.append("release_ready requires limitations to be resolved or explicitly accepted elsewhere")
    payload = {
        "ok": not errors,
        "work_package": bundle.get("work_package"),
        "revision": bundle.get("revision"),
        "commands": len(bundle.get("commands", [])) if isinstance(bundle.get("commands"), list) else 0,
        "tests": len(bundle.get("tests", [])) if isinstance(bundle.get("tests"), list) else 0,
        "failed_executions": failures[:100],
        "release_ready": bundle.get("release_ready", False),
        "errors": errors[:100],
        "truncated": len(failures) > 100 or len(errors) > 100,
    }
    return payload, not errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    try:
        document = json.loads(args.bundle.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, separators=(",", ":")))
        return 2
    if not isinstance(document, dict):
        print(json.dumps({"ok": False, "error": "document must be an object"}, separators=(",", ":")))
        return 2
    payload, ok = validate(document)
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
