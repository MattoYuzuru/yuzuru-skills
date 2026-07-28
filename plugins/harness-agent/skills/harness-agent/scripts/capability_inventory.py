#!/usr/bin/env python3
"""Generate a bounded capability inventory without reading credential values."""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from pathlib import Path


FRONTMATTER_END = "\n---\n"
CREDENTIAL_NAME = re.compile(r"\b[A-Z][A-Z0-9_]{2,}(?:TOKEN|SECRET|PASSWORD|API_KEY|PRIVATE_KEY|PAT)\b")


def skill_metadata(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---\n") or FRONTMATTER_END not in text[4:]:
        return path.parent.name, "No valid trigger metadata"
    header = text[4:].split(FRONTMATTER_END, 1)[0]
    values: dict[str, str] = {}
    for line in header.splitlines():
        if ":" in line and not line[:1].isspace():
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return values.get("name", path.parent.name), values.get("description", "No trigger declared")


def credentials(text: str) -> list[str]:
    return sorted(set(CREDENTIAL_NAME.findall(text)))[:100]


def script_trigger(text: str) -> str:
    try:
        document = ast.get_docstring(ast.parse(text))
    except SyntaxError:
        document = None
    return document.splitlines()[0] if document else "Deterministic repository helper"


def revision(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else "unknown"


def build_inventory(root: Path, limit: int) -> dict[str, object]:
    root = root.resolve()
    capabilities: list[dict[str, object]] = []

    def add(item: dict[str, object]) -> None:
        if len(capabilities) < limit:
            capabilities.append(item)

    skill_files = list(root.glob("skills/*/SKILL.md"))
    skill_files.extend(root.glob("plugins/*/skills/*/SKILL.md"))
    for path in sorted(skill_files):
        name, trigger = skill_metadata(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        add(
            {
                "id": name,
                "kind": "skill",
                "trigger": trigger,
                "invoke": f"${name}",
                "effect": "mixed",
                "credentials": credentials(text),
                "health": "unknown",
                "documentation": path.relative_to(root).as_posix(),
                "platforms": ["portable"],
            }
        )

    for path in sorted(root.glob("plugins/*/.codex-plugin/plugin.json")):
        plugin = path.parents[1]
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}
        name = plugin.name
        add(
            {
                "id": name,
                "kind": "plugin",
                "trigger": str(manifest.get("description", "No description")),
                "invoke": f"yuzuru plugin install {name} --agent <agent>",
                "effect": "local-write",
                "credentials": [],
                "health": "unknown",
                "documentation": (plugin / "README.md").relative_to(root).as_posix(),
                "platforms": ["codex", "claude"],
            }
        )

    for path in sorted(root.glob("plugins/*/hooks/hooks.json")):
        plugin = path.parents[1].name
        add(
            {
                "id": f"{plugin}:hooks",
                "kind": "hook",
                "trigger": "Runs on declared host hook events after plugin trust",
                "invoke": "automatic after native plugin enablement",
                "effect": "read",
                "credentials": [],
                "health": "unknown",
                "documentation": path.relative_to(root).as_posix(),
                "platforms": ["codex", "claude"],
            }
        )

    script_files = list(root.glob("skills/*/scripts/*.py"))
    script_files.extend(root.glob("plugins/*/skills/*/scripts/*.py"))
    script_files.extend(root.glob("plugins/*/hooks/*.py"))
    for path in sorted(script_files):
        if path.name.startswith("_"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        add(
            {
                "id": path.relative_to(root).as_posix(),
                "kind": "script",
                "trigger": script_trigger(text),
                "invoke": f"python3 {path.relative_to(root).as_posix()} --help",
                "effect": "unknown",
                "credentials": credentials(text),
                "health": "unknown",
                "documentation": path.relative_to(root).as_posix(),
                "platforms": ["portable"],
            }
        )

    mcp_files = sorted(root.glob("plugins/*/.mcp.json"))
    for path in mcp_files:
        add(
            {
                "id": f"{path.parent.name}:mcp",
                "kind": "mcp",
                "trigger": "Declared structured external or persistent tools",
                "invoke": "automatic after native plugin enablement",
                "effect": "unknown",
                "credentials": [],
                "health": "unknown",
                "documentation": path.relative_to(root).as_posix(),
                "platforms": ["codex", "claude"],
            }
        )
    total = len(skill_files) + len(list(root.glob("plugins/*/.codex-plugin/plugin.json")))
    total += len(list(root.glob("plugins/*/hooks/hooks.json"))) + len(script_files) + len(mcp_files)
    return {
        "revision": revision(root),
        "generated_from": str(root),
        "capabilities": capabilities,
        "truncated": total > limit,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()
    if not args.root.is_dir():
        parser.error(f"not a directory: {args.root}")
    if not 1 <= args.limit <= 2000:
        parser.error("--limit must be between 1 and 2000")
    print(json.dumps(build_inventory(args.root, args.limit), ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
