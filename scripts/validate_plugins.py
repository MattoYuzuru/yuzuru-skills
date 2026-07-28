#!/usr/bin/env python3
"""Validate self-contained dual-manifest plugin packages."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_skills import NAME_RE, validate_skill  # noqa: E402


SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?$")
PATH_FIELDS = {
    "codex": ("skills", "mcpServers", "apps", "hooks"),
    "claude": ("skills", "commands", "agents", "hooks", "mcpServers", "outputStyles", "lspServers"),
}
README_HEADINGS = (
    "## Capabilities",
    "## Trigger examples",
    "## Non-trigger examples",
    "## External effects",
    "## Platform support",
    "## Local testing",
    "## Limitations",
)
HOOK_EVENTS = {
    "PreToolUse",
    "PermissionRequest",
    "PostToolUse",
    "PreCompact",
    "PostCompact",
    "UserPromptSubmit",
    "SubagentStop",
    "Stop",
    "SessionStart",
    "SubagentStart",
    "SessionEnd",
    "Setup",
}


@dataclass
class Result:
    plugin: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def load_json(path: Path, result: Result) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        result.errors.append(f"{path.relative_to(path.parents[2])}: invalid JSON: {exc}")
        return None


def component_paths(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def validate_manifest(plugin: Path, platform: str, result: Result) -> dict[str, Any]:
    relative = f".{platform}-plugin/plugin.json"
    path = plugin / relative
    if not path.is_file():
        result.errors.append(f"missing {relative}")
        return {}
    value = load_json(path, result)
    if not isinstance(value, dict):
        result.errors.append(f"{relative} must be a JSON object")
        return {}
    for key in ("name", "version", "description"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            result.errors.append(f"{relative} missing non-empty {key}")
    if value.get("name") != plugin.name:
        result.errors.append(f"{relative} name must match {plugin.name}")
    if isinstance(value.get("version"), str) and not SEMVER_RE.fullmatch(value["version"]):
        result.errors.append(f"{relative} version must be semantic")
    for field_name in PATH_FIELDS[platform]:
        if field_name not in value:
            continue
        paths = component_paths(value[field_name])
        if not paths and field_name != "hooks":
            result.errors.append(f"{relative} {field_name} must be a path or path list")
        for component in paths:
            if not component.startswith("./") or ".." in Path(component).parts:
                result.errors.append(f"{relative} unsafe {field_name} path: {component}")
                continue
            if not (plugin / component).exists():
                result.errors.append(f"{relative} missing {field_name} path: {component}")
    return value


def validate_readme(plugin: Path, result: Result) -> None:
    path = plugin / "README.md"
    if not path.is_file():
        result.errors.append("missing README.md")
        return
    text = path.read_text(encoding="utf-8")
    for heading in README_HEADINGS:
        if heading not in text:
            result.errors.append(f"README.md missing heading: {heading}")


def validate_agents(plugin: Path, result: Result) -> None:
    agents = plugin / "agents"
    if not agents.is_dir():
        result.errors.append("missing Claude adapter agents/")
        return
    files = sorted(agents.glob("*.md"))
    if not files:
        result.errors.append("agents/ must contain at least one specialist adapter")
    for path in files:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n") or "\n---\n" not in text[4:]:
            result.errors.append(f"{path.relative_to(plugin)} missing YAML frontmatter")
            continue
        header = text.split("\n---\n", 1)[0]
        for key in ("name:", "description:"):
            if f"\n{key}" not in f"\n{header}":
                result.errors.append(f"{path.relative_to(plugin)} missing {key[:-1]}")


def validate_hooks(plugin: Path, result: Result) -> None:
    path = plugin / "hooks" / "hooks.json"
    if not path.exists():
        return
    value = load_json(path, result)
    if not isinstance(value, dict) or not isinstance(value.get("hooks"), dict):
        result.errors.append("hooks/hooks.json must contain a hooks object")
        return
    for event, groups in value["hooks"].items():
        if event not in HOOK_EVENTS:
            result.errors.append(f"hooks/hooks.json unknown event: {event}")
        if not isinstance(groups, list) or not groups:
            result.errors.append(f"hooks/hooks.json {event} must be a non-empty array")
            continue
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                result.errors.append(f"hooks/hooks.json {event} group missing hooks")
                continue
            for hook in group["hooks"]:
                if not isinstance(hook, dict) or hook.get("type") != "command":
                    result.errors.append(f"hooks/hooks.json {event} supports command hooks only")
                    continue
                command = hook.get("command")
                if not isinstance(command, str) or "PLUGIN_ROOT" not in command:
                    result.errors.append(
                        f"hooks/hooks.json {event} command must resolve a host plugin root"
                    )
                timeout = hook.get("timeout", 60)
                if not isinstance(timeout, int) or not 1 <= timeout <= 120:
                    result.errors.append(f"hooks/hooks.json {event} timeout must be 1..120")


def validate_eval(plugin: Path, result: Result) -> None:
    path = ROOT / "evals" / "plugins" / f"{plugin.name}.json"
    if not path.is_file():
        result.errors.append(f"missing evals/plugins/{plugin.name}.json")
        return
    value = load_json(path, result)
    if not isinstance(value, dict):
        return
    if value.get("version") != 1 or value.get("plugin") != plugin.name:
        result.errors.append("eval contract version/plugin mismatch")
    for key in ("should_trigger", "should_not_trigger"):
        examples = value.get(key)
        if not isinstance(examples, list) or len(examples) < 2:
            result.errors.append(f"eval contract {key} needs at least two examples")
    for key in ("routing", "safety", "artifact_quality"):
        value_list = value.get(key)
        if not isinstance(value_list, list) or not value_list:
            result.errors.append(f"eval contract {key} must be non-empty")


def validate_package(plugin: Path) -> Result:
    result = Result(plugin=plugin.name)
    if not NAME_RE.fullmatch(plugin.name):
        result.errors.append("plugin directory must be kebab-case")
    codex = validate_manifest(plugin, "codex", result)
    claude = validate_manifest(plugin, "claude", result)
    version_path = plugin / "plugin-version.json"
    version_doc = load_json(version_path, result) if version_path.is_file() else None
    if not isinstance(version_doc, dict) or not SEMVER_RE.fullmatch(str(version_doc.get("version", ""))):
        result.errors.append("plugin-version.json must contain one semantic version")
    else:
        expected = version_doc["version"]
        for label, manifest in (("codex", codex), ("claude", claude)):
            if manifest.get("version") != expected:
                result.errors.append(f"{label} manifest version drift: expected {expected}")
    if codex.get("description") != claude.get("description"):
        result.errors.append("dual manifest descriptions must match")

    skill_root = plugin / "skills"
    skills = sorted(skill_root.glob("*/SKILL.md")) if skill_root.is_dir() else []
    if len(skills) < 2:
        result.errors.append("plugin needs a primary skill and focused supporting skill")
    if not (skill_root / plugin.name / "SKILL.md").is_file():
        result.errors.append(f"missing primary skill skills/{plugin.name}/SKILL.md")
    for skill_file in skills:
        skill_result = validate_skill(skill_file.parent, ROOT / "evals" / "plugin-skills")
        result.errors.extend(f"{skill_file.parent.name}: {item}" for item in skill_result.errors)
        result.warnings.extend(f"{skill_file.parent.name}: {item}" for item in skill_result.warnings)

    validate_readme(plugin, result)
    validate_agents(plugin, result)
    validate_hooks(plugin, result)
    validate_eval(plugin, result)
    for path in plugin.rglob("*"):
        if path.is_symlink():
            result.errors.append(f"plugin packages may not contain symlinks: {path.relative_to(plugin)}")
        if path.is_file():
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if "/Users/" in text or re.search(r"/home/[^ <`]+", text):
                result.errors.append(f"maintainer-specific path: {path.relative_to(plugin)}")
            if "TODO" in text or "[TODO:" in text:
                result.errors.append(f"placeholder marker: {path.relative_to(plugin)}")
    return result


def marketplace_ids(path: Path, result: Result) -> tuple[list[str], dict[str, str]]:
    value = load_json(path, result)
    if not isinstance(value, dict) or not isinstance(value.get("plugins"), list):
        result.errors.append(f"{path}: marketplace must contain plugins")
        return [], {}
    names: list[str] = []
    sources: dict[str, str] = {}
    for item in value["plugins"]:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            result.errors.append(f"{path}: invalid plugin entry")
            continue
        name = item["name"]
        source = item.get("source")
        if isinstance(source, dict):
            source = source.get("path")
        if not isinstance(source, str):
            result.errors.append(f"{path}: {name} missing source path")
            continue
        names.append(name)
        sources[name] = source
    if len(names) != len(set(names)):
        result.errors.append(f"{path}: duplicate plugin identifiers")
    return names, sources


def cross_validate(results: list[Result]) -> list[str]:
    errors: list[str] = []
    synthetic = Result(plugin="marketplaces")
    codex_names, codex_sources = marketplace_ids(
        ROOT / ".agents" / "plugins" / "marketplace.json", synthetic
    )
    claude_names, claude_sources = marketplace_ids(
        ROOT / ".claude-plugin" / "marketplace.json", synthetic
    )
    errors.extend(synthetic.errors)
    directories = [path.name for path in sorted((ROOT / "plugins").iterdir()) if path.is_dir()]
    directories = [name for name in directories if name != ".gitkeep"]
    if codex_names != claude_names:
        errors.append("marketplace plugin ordering/identifiers differ")
    if sorted(codex_names) != sorted(directories):
        errors.append("marketplaces do not exactly cover plugin directories")
    for name in codex_names:
        expected = f"./plugins/{name}"
        if codex_sources.get(name) != expected or claude_sources.get(name) != expected:
            errors.append(f"marketplace source drift for {name}: expected {expected}")
    names: dict[str, str] = {}
    for root in [ROOT / "skills", *[path / "skills" for path in (ROOT / "plugins").iterdir() if path.is_dir()]]:
        if not root.is_dir():
            continue
        for skill in root.glob("*/SKILL.md"):
            name = skill.parent.name
            if name in names:
                errors.append(f"duplicate skill identifier {name}: {names[name]} and {skill}")
            names[name] = str(skill)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="*", help="plugin IDs or all")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    available = sorted(
        path for path in (ROOT / "plugins").iterdir() if (path / ".codex-plugin/plugin.json").is_file()
    )
    if args.names and args.names != ["all"]:
        requested = set(args.names)
        unknown = requested - {path.name for path in available}
        if unknown:
            parser.error(f"unknown plugins: {', '.join(sorted(unknown))}")
        available = [path for path in available if path.name in requested]
    results = [validate_package(path) for path in available]
    cross_errors = cross_validate(results) if not args.names or args.names == ["all"] else []
    if args.json:
        print(
            json.dumps(
                {
                    "plugins": [
                        {
                            "plugin": item.plugin,
                            "ok": item.ok,
                            "errors": item.errors,
                            "warnings": item.warnings,
                        }
                        for item in results
                    ],
                    "cross_errors": cross_errors,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    else:
        for item in results:
            print(f"{'ok' if item.ok else 'FAIL':4} {item.plugin}")
            for warning in item.warnings:
                print(f"  warning: {warning}")
            for error in item.errors:
                print(f"  error: {error}")
        for error in cross_errors:
            print(f"FAIL marketplace: {error}")
        print(
            f"validated {len(results)} plugin(s): "
            f"{sum(item.ok for item in results)} passed, {sum(not item.ok for item in results)} failed"
        )
    failed = bool(cross_errors) or any(not item.ok for item in results)
    if args.strict and any(item.warnings for item in results):
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
