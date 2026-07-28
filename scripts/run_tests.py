#!/usr/bin/env python3
"""Run repository, standalone-skill, plugin-script, and plugin-hook unit tests."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_files() -> list[Path]:
    tests = list((ROOT / "skills").glob("*/scripts/tests/test_*.py"))
    tests.extend((ROOT / "plugins").glob("*/skills/*/scripts/tests/test_*.py"))
    tests.extend((ROOT / "plugins").glob("*/hooks/tests/test_*.py"))
    tests.extend((ROOT / "scripts" / "tests").glob("test_*.py"))
    return sorted(set(tests))


def import_root(path: Path) -> Path:
    if path.parent.name == "tests":
        return path.parent.parent
    return path.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--match", help="Run only test paths containing this text")
    args = parser.parse_args()
    tests = [path for path in test_files() if not args.match or args.match in str(path)]
    failures: list[dict[str, object]] = []
    for path in tests:
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        current = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = str(import_root(path)) + (
            os.pathsep + current if current else ""
        )
        result = subprocess.run(
            [sys.executable, "-B", str(path), "-v"],
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
