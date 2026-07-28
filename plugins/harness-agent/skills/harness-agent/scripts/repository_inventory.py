#!/usr/bin/env python3
"""Create a bounded read-only repository inventory for agent readiness."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path


IGNORED = {".git", "node_modules", ".venv", "venv", "dist", "build", "target", "__pycache__"}
LANGUAGES = {
    ".py": "Python",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".rb": "Ruby",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
}
BUILD_FILES = {
    "pyproject.toml",
    "requirements.txt",
    "package.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "Makefile",
    "justfile",
}


def inventory(root: Path, limit: int) -> dict[str, object]:
    if not root.is_dir():
        raise ValueError(f"not a directory: {root}")
    root = root.resolve()
    languages: Counter[str] = Counter()
    docs: list[str] = []
    instructions: list[str] = []
    build_files: list[str] = []
    skills: list[str] = []
    plugins: list[str] = []
    hooks: list[str] = []
    files = 0
    truncated = False
    for current, directories, filenames in os.walk(root, followlinks=False):
        directories[:] = sorted(item for item in directories if item not in IGNORED)
        base = Path(current)
        for filename in sorted(filenames):
            path = base / filename
            if path.is_symlink():
                continue
            files += 1
            if files > limit:
                truncated = True
                break
            relative = path.relative_to(root).as_posix()
            if path.suffix in LANGUAGES:
                languages[LANGUAGES[path.suffix]] += 1
            if path.suffix.lower() == ".md":
                docs.append(relative)
            if filename in {"AGENTS.md", "CLAUDE.md"}:
                instructions.append(relative)
            if filename in BUILD_FILES:
                build_files.append(relative)
            if filename == "SKILL.md":
                skills.append(relative)
            if relative.endswith((".codex-plugin/plugin.json", ".claude-plugin/plugin.json")):
                plugins.append(relative)
            if filename == "hooks.json":
                hooks.append(relative)
        if truncated:
            break
    return {
        "root": str(root),
        "revision_hint": ".git present" if (root / ".git").exists() else "not a git root",
        "files_scanned": min(files, limit),
        "truncated": truncated,
        "limit": limit,
        "languages": dict(languages.most_common()),
        "build_files": build_files[:200],
        "documentation": docs[:500],
        "instructions": instructions[:100],
        "skills": skills[:200],
        "plugin_manifests": plugins[:200],
        "hooks": hooks[:100],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--limit", type=int, default=10000)
    args = parser.parse_args()
    if not 1 <= args.limit <= 100000:
        parser.error("--limit must be between 1 and 100000")
    try:
        payload = inventory(args.root, args.limit)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
