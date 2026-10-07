#!/usr/bin/env python3
"""Create a dual-manifest Yuzuru plugin scaffold without external dependencies."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLUGINS_DIR = ROOT / "plugins"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("--description", required=True)
    parser.add_argument("--trigger", help="concrete user request that should select the primary skill")
    parser.add_argument("--plugins-dir", type=Path, default=DEFAULT_PLUGINS_DIR, help=argparse.SUPPRESS)
    parser.add_argument("--dry-run", action="store_true", help="validate and list files without writing")
    args = parser.parse_args()
    if not NAME_RE.fullmatch(args.name) or len(args.name) > 64:
        parser.error("name must be kebab-case and at most 64 characters")
    if len(args.description) < 40 or any(c in args.description for c in "\n\r"):
        parser.error("description must be one line with at least 40 characters")
    if args.trigger is not None and (not args.trigger.strip() or any(c in args.trigger for c in "\n\r")):
        parser.error("trigger must be a non-empty single line")
    plugin = args.plugins_dir / args.name
    if plugin.exists():
        parser.error(f"plugin already exists: {plugin}")
    skill = plugin / "skills" / args.name
    planned = [
        plugin / "plugin-version.json",
        plugin / ".codex-plugin" / "plugin.json",
        plugin / ".claude-plugin" / "plugin.json",
        plugin / "package.json",
        plugin / "cordis.patch.yml",
        skill / "SKILL.md",
        plugin / "README.md",
    ]
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
    skill.mkdir(parents=True)
    write_json(plugin / "plugin-version.json", {"version": "0.1.0"})
    base = {
        "name": args.name,
        "version": "0.1.0",
        "description": args.description,
        "skills": "./skills/",
    }
    write_json(plugin / ".codex-plugin" / "plugin.json", base)
    write_json(
        plugin / ".claude-plugin" / "plugin.json",
        {
            "$schema": "https://json.schemastore.org/claude-code-plugin-manifest.json",
            **base,
        },
    )
    write_json(plugin / "package.json", {
        "name": f"yuzuru-{args.name}", "version": "0.1.0", "private": True,
        "description": f"DeepSeek Harness skill bundle for {args.name}.",
        "dsh": {"bundle": {"patch": "./cordis.patch.yml"}},
    })
    (plugin / "cordis.patch.yml").write_text(
        f"- insert:\n    - id: yuzuru-skill-filesystem-{args.name}\n"
        "      name: '@deepseek-ai/dsh-skill-filesystem'\n"
        f"      config:\n        providerName: yuzuru-{args.name}\n"
        "        includeDefaultRoots: false\n        customSkillDirs:\n"
        "          - !!js \"process.getBuiltinModule('node:url').fileURLToPath(new URL('"
        f"node_modules/yuzuru-{args.name}/skills/', baseUrl))\"\n", encoding="utf-8")
    trigger = args.trigger or "<describe the concrete user request>"
    (skill / "SKILL.md").write_text(
        "\n".join(
            [
                "---",
                f"name: {args.name}",
                f"description: {json.dumps(args.description + ' Use when ' + trigger + '.', ensure_ascii=False)}",
                "---",
                "",
                f"# {args.name}",
                "",
                "Replace this scaffold with a compact orchestration workflow before validation.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (plugin / "README.md").write_text(
        f"# {args.name}\n\n{args.description}\n\n"
        + "\n\n".join(f"## {heading}\n\nReplace this scaffold with package-specific evidence."
                        for heading in ("Capabilities", "Trigger examples", "Non-trigger examples",
                                        "External effects", "Platform support", "Local testing", "Limitations"))
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"created": str(plugin), "next": [
        "Replace skill and README placeholders; add only necessary supporting resources.",
        "Register both marketplaces and add plugin/skill-selection eval contracts.",
        f"yuzuru plugin validate {args.name}" ]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
