#!/usr/bin/env python3
"""Verify that every public Python helper exposes credential-free --help."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ENV_FRAGMENTS = ("TOKEN", "SECRET", "PASSWORD", "API_KEY", "PRIVATE_KEY", "PAT")


def public_helpers() -> list[Path]:
    helpers: list[Path] = []
    for path in sorted((ROOT / "skills").glob("*/scripts/*.py")):
        if path.name.startswith("_") or path.name in {"api_config.py", "sheets_config.py"}:
            continue
        helpers.append(path)
    return helpers


def scrubbed_environment() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if not any(fragment in key.upper() for fragment in PRIVATE_ENV_FRAGMENTS)
    }


def main() -> int:
    failures: list[dict[str, object]] = []
    for path in public_helpers():
        relative = path.relative_to(ROOT)
        try:
            result = subprocess.run(
                [sys.executable, str(path), "--help"],
                cwd=path.parent,
                env=scrubbed_environment(),
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except subprocess.TimeoutExpired:
            failures.append({"script": str(relative), "error": "--help timed out"})
            continue
        if result.returncode != 0:
            failures.append(
                {
                    "script": str(relative),
                    "returncode": result.returncode,
                    "stderr": result.stderr[-1000:],
                }
            )

    payload = {
        "checked": len(public_helpers()),
        "failures": failures,
    }
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
