#!/usr/bin/env python3
"""Inventory delivery and platform files without following links or writing the project."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


PATTERNS = {
    "github_actions": (".github/workflows/*.yml", ".github/workflows/*.yaml"),
    "gitlab_ci": (".gitlab-ci.yml",),
    "containers": ("Dockerfile", "Dockerfile.*", "**/Dockerfile", "**/Dockerfile.*"),
    "compose": ("compose.yml", "compose.yaml", "docker-compose.yml", "docker-compose.yaml"),
    "kubernetes": ("**/kustomization.yaml", "**/Chart.yaml", "**/*.helm.yaml"),
    "terraform": ("**/*.tf",),
    "ansible": ("**/playbook.yml", "**/playbook.yaml", "**/roles/*/tasks/*.yml"),
    "systemd": ("**/*.service", "**/*.timer"),
    "deployment_docs": ("**/*deploy*.md", "**/*runbook*.md", "**/*rollback*.md"),
}
IGNORED = {".git", "node_modules", ".venv", "venv", "dist", "build", "target"}


def inventory(root: Path, limit: int) -> dict[str, object]:
    if not root.is_dir():
        raise ValueError(f"not a directory: {root}")
    root = root.resolve()
    results: dict[str, list[str]] = {}
    truncated = False
    for category, patterns in PATTERNS.items():
        matches: set[str] = set()
        for pattern in patterns:
            for path in root.glob(pattern):
                if path.is_symlink() or not path.is_file() or any(part in IGNORED for part in path.parts):
                    continue
                matches.add(path.relative_to(root).as_posix())
                if len(matches) >= limit:
                    truncated = True
                    break
            if len(matches) >= limit:
                break
        results[category] = sorted(matches)
    hosts = []
    if (root / ".git").exists():
        config = root / ".git" / "config"
        if config.is_file():
            text = config.read_text(encoding="utf-8", errors="replace")
            if "github.com" in text:
                hosts.append("github")
            if "gitlab" in text:
                hosts.append("gitlab")
    return {
        "root": str(root),
        "categories": results,
        "repository_hosts": hosts,
        "truncated": truncated,
        "limit_per_category": limit,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if not 1 <= args.limit <= 1000:
        parser.error("--limit must be between 1 and 1000")
    try:
        payload = inventory(args.root, args.limit)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
