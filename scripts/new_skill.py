#!/usr/bin/env python3
"""Create a repository skill skeleton without external dependencies."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ALLOWED_RESOURCES = {"scripts", "references", "assets"}
ALLOWED_TARGETS = {"codex", "claude", "dsh"}


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
        expected = "codex,claude,dsh"
        detail = f"unknown targets: {', '.join(unknown)}; " if unknown else ""
        raise argparse.ArgumentTypeError(f"{detail}expected a non-empty subset of {expected}")
    return list(dict.fromkeys(targets))


def title_from_name(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("-"))


def short_description(description: str) -> str:
    capability = re.split(r"\bUse when\b", description, maxsplit=1, flags=re.IGNORECASE)[0]
    capability = capability.strip().rstrip(".")
    if len(capability) < 25:
        capability = f"{capability} agent workflow"
    if len(capability) > 64:
        capability = capability[:61].rstrip() + "..."
    return capability


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


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
        default=["codex", "claude", "dsh"],
        help="comma-separated target agents: codex,claude,dsh (default: all)",
    )
    parser.add_argument("--skills-dir", type=Path, required=True, help=argparse.SUPPRESS)
    parser.add_argument("--dry-run", action="store_true", help="validate and list files without writing")
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

    planned = [skill_dir / "SKILL.md"]
    planned.extend(skill_dir / resource for resource in args.resources)
    if set(args.targets) != ALLOWED_TARGETS:
        planned.append(skill_dir / "skill.yaml")
    if "codex" in args.targets:
        planned.append(skill_dir / "agents" / "openai.yaml")
    if args.dry_run:
        print(
            json.dumps(
                {
                    "status": "dry_run",
                    "effect": "local-write",
                    "would_create": [str(path) for path in planned],
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        return 0

    skill_dir.mkdir(parents=True)
    for resource in args.resources:
        (skill_dir / resource).mkdir()

    title = title_from_name(args.name)
    body = f"""---
name: {args.name}
description: {yaml_string(args.description)}
---

# {title}

State the outcome and non-obvious domain context needed to complete the task.

## Decisions and resources

Replace this section with the decisions that change this workflow. Link a supporting reference
only when a distinct mode needs it; a self-contained skill needs no router. Resolve installed paths
before executing helpers. Keep exact sequences for fragile protocols and real effect boundaries.

## Completion and effects

Replace this section with observable completion evidence and the actual read, write, or destructive
operations. Reuse existing authorization within its finite scope. Do not create a universal approval
gate, mandatory plan, or extra output artifact for ordinary local work.
"""
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")
    if set(args.targets) != ALLOWED_TARGETS:
        targets = ", ".join(args.targets)
        (skill_dir / "skill.yaml").write_text(f"targets: [{targets}]\n", encoding="utf-8")
    if "codex" in args.targets:
        agents_dir = skill_dir / "agents"
        agents_dir.mkdir()
        openai_yaml = "\n".join(
            [
                "interface:",
                f"  display_name: {yaml_string(title)}",
                f"  short_description: {yaml_string(short_description(args.description))}",
                f"  default_prompt: {yaml_string(f'Use ${args.name} for the requested workflow.')}",
                "",
            ]
        )
        (agents_dir / "openai.yaml").write_text(openai_yaml, encoding="utf-8")

    print(f"created: {skill_dir}")
    print("next: replace the template text, add only required resources, then run:")
    print(f"  yuzuru skill validate {args.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
