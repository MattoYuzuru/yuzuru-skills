#!/usr/bin/env python3
"""Run every skill-local unittest file with the correct script import path."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    tests = sorted((ROOT / "skills").glob("*/scripts/tests/test_*.py"))
    failures: list[dict[str, object]] = []
    for path in tests:
        scripts_dir = path.parents[1]
        environment = os.environ.copy()
        current = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = str(scripts_dir) + (os.pathsep + current if current else "")
        result = subprocess.run(
            [sys.executable, str(path), "-v"],
            cwd=ROOT,
            env=environment,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            failures.append({"test": str(path.relative_to(ROOT)), "returncode": result.returncode})

    print(
        json.dumps(
            {"test_files": len(tests), "failures": failures},
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
