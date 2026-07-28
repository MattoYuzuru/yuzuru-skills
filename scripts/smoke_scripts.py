#!/usr/bin/env python3
"""Verify that public deterministic helpers expose credential-free, bounded --help."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ENV_FRAGMENTS = ("TOKEN", "SECRET", "PASSWORD", "API_KEY", "PRIVATE_KEY", "PAT")
ROOT_HELPERS = {
    "new_plugin.py",
    "new_skill.py",
    "run_evals.py",
    "run_tests.py",
    "smoke_scripts.py",
    "sync_plugin_versions.py",
    "test_native_plugins.py",
    "validate_artifact.py",
    "validate_plugins.py",
    "validate_repository.py",
    "validate_skills.py",
    "yuzuru_cli.py",
}


def public_helpers() -> list[Path]:
    helpers: list[Path] = []
    patterns = (
        "skills/*/scripts/*.py",
        "plugins/*/skills/*/scripts/*.py",
        "plugins/*/hooks/*.py",
    )
    for pattern in patterns:
        for path in ROOT.glob(pattern):
            if path.name.startswith("_") or path.name in {"api_config.py", "sheets_config.py"}:
                continue
            helpers.append(path)
    helpers.extend(ROOT / "scripts" / name for name in ROOT_HELPERS if (ROOT / "scripts" / name).is_file())
    return sorted(set(helpers))


def scrubbed_environment() -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not any(fragment in key.upper() for fragment in PRIVATE_ENV_FRAGMENTS)
    }
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=10, help="Per-helper timeout in seconds")
    args = parser.parse_args()
    if not 1 <= args.timeout <= 60:
        parser.error("--timeout must be between 1 and 60")
    failures: list[dict[str, object]] = []
    helpers = public_helpers()
    for path in helpers:
        relative = path.relative_to(ROOT)
        try:
            result = subprocess.run(
                [sys.executable, "-B", str(path), "--help"],
                cwd=path.parent,
                env=scrubbed_environment(),
                capture_output=True,
                text=True,
                timeout=args.timeout,
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

    print(json.dumps({"checked": len(helpers), "failures": failures}, separators=(",", ":")))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
