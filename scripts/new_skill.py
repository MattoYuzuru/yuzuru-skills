#!/usr/bin/env python3
"""Create a repository skill skeleton without external dependencies."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ALLOWED_RESOURCES = {"scripts", "references", "assets"}
ALLOWED_TARGETS = {"codex", "claude"}


def parse_resources(value: str) -> list[str]:
    resources = [item.strip() for item in value.split(",") if item.strip()]
    unknown = sorted(set(resources) - ALLOWED_RESOURCES)
    if unknown:
        raise argparse.ArgumentTypeError(
            f"unknown resources: {', '.join(unknown)}; expected scripts,references,assets"
        )
    return resources


def parse_targets(value: str) -> list[str]:
    targets = [item.strip() for item in value.split(",") if item.strip()]
    unknown = sorted(set(targets) - ALLOWED_TARGETS)
    if unknown or not targets:
        expected = "codex,claude"
        detail = f"unknown targets: {', '.join(unknown)}; " if unknown else ""
        raise argparse.ArgumentTypeError(f"{detail}expected a non-empty subset of {expected}")
    return list(dict.fromkeys(targets))


def title_from_name(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("-"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a new Yuzuru skill skeleton")
    parser.add_argument("name", help="skill name in kebab-case")
    parser.add_argument("--description", required=True, help="capability and trigger description")
    parser.add_argument(
        "--resources",
        type=parse_resources,
        default=[],
        help="comma-separated optional directories: scripts,references,assets",
    )
    parser.add_argument(
        "--targets",
        type=parse_targets,
        default=["codex", "claude"],
        help="comma-separated target agents: codex,claude (default: both)",
    )
    parser.add_argument("--skills-dir", type=Path, required=True, help=argparse.SUPPRESS)
    args = parser.parse_args()

    if not NAME_RE.fullmatch(args.name) or len(args.name) > 64:
        parser.error("name must be kebab-case, contain only lowercase ASCII letters/digits, and be <=64 characters")
    if "use when" not in args.description.lower():
        parser.error("description must state trigger conditions with 'Use when ...'")
    if "\n" in args.description or "\r" in args.description:
        parser.error("description must be a single line")

    skill_dir = args.skills_dir / args.name
    if skill_dir.exists():
        parser.error(f"skill already exists: {skill_dir}")

    skill_dir.mkdir(parents=True)
    for resource in args.resources:
        (skill_dir / resource).mkdir()

    title = title_from_name(args.name)
    body = f"""---
name: {args.name}
description: {args.description}
---

# {title}

## Overview

Describe the capability and its scope in one short paragraph.

## Workflow

1. Resolve this installed skill directory.
2. Select the relevant route and load only its required reference.
3. Run deterministic helpers from `scripts/` when available.
4. Return a compact result in the user's language.

## Guardrails

- Classify external operations as read, write, or destructive.
- Require explicit authorization before write or destructive operations.
"""
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")
    if set(args.targets) != ALLOWED_TARGETS:
        targets = ", ".join(args.targets)
        (skill_dir / "skill.yaml").write_text(f"targets: [{targets}]\n", encoding="utf-8")

    print(f"created: {skill_dir}")
    print("next: replace the template text, add only required resources, then run:")
    print(f"  ./skill validate {args.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
