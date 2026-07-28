#!/usr/bin/env python3
"""Validate plugin trigger/routing/safety contracts and cross-plugin handoff cases."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ("should_trigger", "should_not_trigger", "routing", "safety", "artifact_quality")


def load(path: Path, errors: list[str]) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path.relative_to(ROOT)}: {exc}")
        return {}


def plugin_contracts(errors: list[str]) -> tuple[int, set[str]]:
    count = 0
    identifiers: set[str] = set()
    trigger_owners: dict[str, str] = {}
    for path in sorted((ROOT / "evals" / "plugins").glob("*.json")):
        value = load(path, errors)
        if not isinstance(value, dict):
            continue
        plugin = value.get("plugin")
        if plugin != path.stem or value.get("version") != 1:
            errors.append(f"{path.relative_to(ROOT)}: version/plugin mismatch")
            continue
        identifiers.add(plugin)
        count += 1
        for section in SECTIONS:
            items = value.get(section)
            minimum = 2 if section in {"should_trigger", "should_not_trigger"} else 1
            if not isinstance(items, list) or len(items) < minimum:
                errors.append(f"{path.relative_to(ROOT)}: {section} requires {minimum}+ cases")
        for prompt in value.get("should_trigger", []):
            normalized = " ".join(str(prompt).lower().split())
            owner = trigger_owners.setdefault(normalized, plugin)
            if owner != plugin:
                errors.append(f"duplicate trigger across {owner} and {plugin}: {prompt}")
    expected = {
        path.name
        for path in (ROOT / "plugins").iterdir()
        if (path / ".codex-plugin" / "plugin.json").is_file()
    }
    if identifiers != expected:
        errors.append(
            f"plugin eval coverage drift: expected {sorted(expected)}, got {sorted(identifiers)}"
        )
    return count, identifiers


def cross_contract(errors: list[str], identifiers: set[str]) -> int:
    path = ROOT / "evals" / "cross-plugin.json"
    value = load(path, errors)
    workflows = value.get("workflows") if isinstance(value, dict) else None
    if not isinstance(value, dict) or value.get("version") != 1 or not isinstance(workflows, list):
        errors.append("evals/cross-plugin.json: invalid contract")
        return 0
    seen: set[str] = set()
    for item in workflows:
        if not isinstance(item, dict):
            errors.append("evals/cross-plugin.json: workflow must be an object")
            continue
        workflow_id = item.get("id")
        if not isinstance(workflow_id, str) or workflow_id in seen:
            errors.append(f"evals/cross-plugin.json: invalid/duplicate workflow id {workflow_id!r}")
        seen.add(str(workflow_id))
        plugins = item.get("expected_plugins")
        if not isinstance(plugins, list) or not plugins:
            errors.append(f"evals/cross-plugin.json: {workflow_id} has no expected_plugins")
        elif not set(plugins) <= identifiers:
            errors.append(f"evals/cross-plugin.json: {workflow_id} references unknown plugin")
        for key in ("prompt", "handoff", "completion_evidence"):
            if not item.get(key):
                errors.append(f"evals/cross-plugin.json: {workflow_id} missing {key}")
    if len(workflows) < 9:
        errors.append("evals/cross-plugin.json: expected at least nine workflows")
    return len(workflows)


def platform_contract(errors: list[str]) -> int:
    path = ROOT / "evals" / "platform-compatibility.json"
    value = load(path, errors)
    cases = value.get("cases") if isinstance(value, dict) else None
    if not isinstance(value, dict) or value.get("version") != 1 or not isinstance(cases, list):
        errors.append("evals/platform-compatibility.json: invalid contract")
        return 0
    required = {"codex-enable", "claude-disable", "plugin-data", "marketplace-paths"}
    ids = {item.get("id") for item in cases if isinstance(item, dict)}
    missing = required - ids
    if missing:
        errors.append(f"evals/platform-compatibility.json missing {sorted(missing)}")
    return len(cases)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    errors: list[str] = []
    plugin_count, identifiers = plugin_contracts(errors)
    workflow_count = cross_contract(errors, identifiers)
    platform_count = platform_contract(errors)
    payload = {
        "ok": not errors,
        "plugin_contracts": plugin_count,
        "cross_workflows": workflow_count,
        "platform_cases": platform_count,
        "errors": errors,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    else:
        print(
            f"{'ok' if not errors else 'FAIL'}: {plugin_count} plugin contracts, "
            f"{workflow_count} cross-plugin workflows, {platform_count} platform cases"
        )
        for error in errors:
            print(f"  error: {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
