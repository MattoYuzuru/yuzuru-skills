#!/usr/bin/env python3
"""Produce a bounded, non-destructive inventory of likely cleanup candidates."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

EXCLUDED_DIRS = {".git", "node_modules", ".idea"}
EXACT_NAMES = {
    ".coverage": "coverage output",
    ".DS_Store": "operating-system metadata",
    "coverage.xml": "coverage output",
    "npm-debug.log": "package-manager log",
}
DIR_NAMES = {
    "__pycache__": "Python bytecode cache",
    ".pytest_cache": "test cache",
    ".ruff_cache": "linter cache",
    ".mypy_cache": "type-checker cache",
    ".venv": "repository-local environment",
    "venv": "repository-local environment",
    "coverage": "coverage output",
}
SUFFIXES = {
    ".bak": "backup file",
    ".orig": "merge/patch backup",
    ".rej": "rejected patch",
    ".tmp": "temporary file",
    ".log": "log file",
}


def scan(root: Path, limit: int) -> dict[str, object]:
    candidates: list[dict[str, str]] = []
    truncated = False
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(name for name in dirs if name not in EXCLUDED_DIRS)
        base = Path(current)
        for dirname in list(dirs):
            if dirname in DIR_NAMES:
                candidates.append(
                    {
                        "path": str((base / dirname).relative_to(root)),
                        "kind": "directory",
                        "reason": DIR_NAMES[dirname],
                        "confidence": "candidate",
                    }
                )
        for filename in sorted(files):
            reason = EXACT_NAMES.get(filename)
            if reason is None:
                reason = next((label for suffix, label in SUFFIXES.items() if filename.endswith(suffix)), None)
            if reason:
                candidates.append(
                    {
                        "path": str((base / filename).relative_to(root)),
                        "kind": "file",
                        "reason": reason,
                        "confidence": "candidate",
                    }
                )
            if len(candidates) >= limit:
                truncated = True
                break
        if truncated:
            break
    return {
        "root": str(root),
        "effect": "read-only",
        "candidates": candidates[:limit],
        "count": min(len(candidates), limit),
        "truncated": truncated,
        "warning": "Filename matches are leads, not deletion authorization.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="Repository or directory to inspect")
    parser.add_argument("--limit", type=int, default=200, help="Maximum candidates (1-1000)")
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        parser.error(f"not a directory: {root}")
    if not 1 <= args.limit <= 1000:
        parser.error("--limit must be between 1 and 1000")
    print(json.dumps(scan(root, args.limit), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
