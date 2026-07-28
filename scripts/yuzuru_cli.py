#!/usr/bin/env python3
"""Canonical cross-agent CLI for Yuzuru skills, plugins, and marketplaces."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
PLUGINS_DIR = ROOT / "plugins"
MIGRATIONS_PATH = ROOT / "schemas" / "migrations.json"
MARKETPLACE_NAME = "yuzuru-engineering"
AGENTS = ("codex", "claude")
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class CliError(RuntimeError):
    """Expected user-facing failure."""


def xdg_dir(kind: str) -> Path:
    home = Path.home()
    mapping = {
        "config": ("XDG_CONFIG_HOME", home / ".config"),
        "cache": ("XDG_CACHE_HOME", home / ".cache"),
        "data": ("XDG_DATA_HOME", home / ".local" / "share"),
    }
    env_name, fallback = mapping[kind]
    return Path(os.environ.get(env_name, fallback)) / "yuzuru"


def registry_path() -> Path:
    override = os.environ.get("YUZURU_REGISTRY")
    return Path(override) if override else xdg_dir("data") / "registry.json"


def empty_registry() -> dict[str, Any]:
    return {
        "version": 1,
        "repository": str(ROOT),
        "managed_skill_links": {},
        "marketplaces": {},
        "migrations": [],
    }


def load_registry() -> dict[str, Any]:
    path = registry_path()
    if not path.exists():
        return empty_registry()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CliError(f"invalid registry {path}: {exc}") from exc
    if not isinstance(value, dict) or value.get("version") != 1:
        raise CliError(f"unsupported registry schema: {path}")
    for key, expected in (
        ("managed_skill_links", dict),
        ("marketplaces", dict),
        ("migrations", list),
    ):
        if not isinstance(value.get(key), expected):
            raise CliError(f"invalid registry field {key}: {path}")
    return value


def save_registry(value: dict[str, Any]) -> None:
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    value["repository"] = str(ROOT)
    handle, temp_name = tempfile.mkstemp(prefix=".registry-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def load_migrations() -> dict[str, list[dict[str, str]]]:
    try:
        value = json.loads(MIGRATIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CliError(f"invalid migration registry {MIGRATIONS_PATH}: {exc}") from exc
    if not isinstance(value, dict) or value.get("version") != 1:
        raise CliError(f"unsupported migration registry: {MIGRATIONS_PATH}")
    result: dict[str, list[dict[str, str]]] = {}
    for key in ("skill_renames", "plugin_renames"):
        records = value.get(key)
        if not isinstance(records, list):
            raise CliError(f"invalid migration field {key}: {MIGRATIONS_PATH}")
        parsed: list[dict[str, str]] = []
        for record in records:
            if (
                not isinstance(record, dict)
                or not isinstance(record.get("from"), str)
                or not isinstance(record.get("to"), str)
                or not NAME_RE.fullmatch(record["from"])
                or not NAME_RE.fullmatch(record["to"])
            ):
                raise CliError(f"invalid migration record in {key}: {record!r}")
            parsed.append({"from": record["from"], "to": record["to"]})
        result[key] = parsed
    return result


def run(
    command: list[str],
    *,
    check: bool = False,
    capture: bool = False,
    timeout: int = 30,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy() if env is None else env.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=capture,
        check=check,
        timeout=timeout,
    )


def compact_command(command: Iterable[str]) -> str:
    return " ".join(json.dumps(part) if any(ch.isspace() for ch in part) else part for part in command)


def emit_status(status: str, **values: Any) -> None:
    print(json.dumps({"status": status, **values}, ensure_ascii=False, separators=(",", ":")))


def command_available(name: str) -> bool:
    return shutil.which(name) is not None


def normalize_plugin_id(value: str) -> str:
    return value.split("@", 1)[0]


def parse_native_plugin_states(value: object) -> dict[str, dict[str, Any]]:
    records: list[dict[str, Any]] = []

    def visit(item: object) -> None:
        if isinstance(item, list):
            for child in item:
                visit(child)
        elif isinstance(item, dict):
            identifier = next(
                (
                    item.get(key)
                    for key in ("id", "name", "plugin", "plugin_id")
                    if isinstance(item.get(key), str)
                ),
                None,
            )
            if identifier and (
                any(key in item for key in ("installed", "enabled", "status", "version", "scope"))
                or "@" in identifier
            ):
                records.append(item)
            for child in item.values():
                if isinstance(child, (dict, list)):
                    visit(child)

    visit(value)
    states: dict[str, dict[str, Any]] = {}
    for record in records:
        identifier = next(
            str(record[key])
            for key in ("id", "name", "plugin", "plugin_id")
            if isinstance(record.get(key), str)
        )
        name = normalize_plugin_id(identifier)
        if not NAME_RE.fullmatch(name):
            continue
        raw_status = record.get("status")
        status = str(raw_status).lower() if raw_status is not None else ""
        installed_value = record.get("installed")
        enabled_value = record.get("enabled")
        installed = (
            installed_value
            if isinstance(installed_value, bool)
            else (
                status in {"installed", "enabled", "disabled", "active", "inactive"}
                or "enabled" in record
                or "installPath" in record
                or "installedAt" in record
            )
        )
        enabled = enabled_value if isinstance(enabled_value, bool) else None
        if enabled is None and status in {"enabled", "active"}:
            enabled = True
        if enabled is None and status in {"disabled", "inactive"}:
            enabled = False
        candidate = {
            "installed": bool(installed),
            "enabled": enabled,
            "version": record.get("version"),
            "status": raw_status,
        }
        previous = states.get(name)
        if previous is None or candidate["installed"]:
            states[name] = candidate
    return states


def native_plugin_states(agent: str) -> tuple[dict[str, dict[str, Any]], str | None]:
    if not command_available(agent):
        return {}, "CLI not installed"
    command = (
        ["codex", "plugin", "list", "--available", "--json"]
        if agent == "codex"
        else ["claude", "plugin", "list", "--json"]
    )
    result = run(command, capture=True, timeout=20)
    if result.returncode != 0:
        return {}, (result.stderr or result.stdout).strip()[-1000:] or "native list failed"
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {}, f"invalid native JSON: {exc}"
    states = parse_native_plugin_states(value)
    return states, None


def skill_dirs() -> list[Path]:
    return sorted(path for path in SKILLS_DIR.iterdir() if (path / "SKILL.md").is_file())


def plugin_dirs() -> list[Path]:
    return sorted(path for path in PLUGINS_DIR.iterdir() if (path / ".codex-plugin/plugin.json").is_file())


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    values: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line[:1].isspace():
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip().strip('"')
    return values


def parse_inline_list(raw: str) -> list[str]:
    return [item.strip() for item in raw.strip().strip("[]").split(",") if item.strip()]


def skill_agents(path: Path) -> list[str]:
    sidecar = path / "skill.yaml"
    if sidecar.exists():
        for line in sidecar.read_text(encoding="utf-8").splitlines():
            if line.startswith("targets:"):
                return parse_inline_list(line.split(":", 1)[1])
    legacy = frontmatter(path / "SKILL.md").get("agents")
    return parse_inline_list(legacy) if legacy else list(AGENTS)


def agent_skill_dir(agent: str) -> Path:
    if agent == "codex":
        value = os.environ.get("YUZURU_CODEX_SKILLS_DIR") or os.environ.get("YUZURU_SKILLS_DIR")
        return Path(value) if value else Path.home() / ".agents" / "skills"
    if agent == "claude":
        value = os.environ.get("YUZURU_CLAUDE_SKILLS_DIR")
        return Path(value) if value else Path.home() / ".claude" / "skills"
    raise CliError(f"unknown agent: {agent}")


def plugin_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads((path / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CliError(f"invalid plugin manifest for {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise CliError(f"invalid plugin manifest for {path.name}: expected object")
    return value


def known_skill(name: str) -> Path:
    path = SKILLS_DIR / name
    if not (path / "SKILL.md").is_file():
        raise CliError(f"unknown skill: {name}")
    return path


def known_plugin(name: str) -> Path:
    path = PLUGINS_DIR / name
    if not (path / ".codex-plugin" / "plugin.json").is_file():
        raise CliError(f"unknown plugin: {name}")
    return path


def recognizable_managed_target(target: str, name: str) -> bool:
    normalized = target.replace("\\", "/").rstrip("/")
    return normalized == str(SKILLS_DIR / name).replace("\\", "/") or normalized.endswith(
        f"/yuzuru-skills/skills/{name}"
    )


def link_status(agent: str, name: str, registry: dict[str, Any]) -> tuple[str, Path, str | None]:
    destination = agent_skill_dir(agent) / name
    expected = str(SKILLS_DIR / name)
    key = f"{agent}/{name}"
    registered = registry["managed_skill_links"].get(key)
    if destination.is_symlink():
        target = os.readlink(destination)
        if target == expected:
            return "installed", destination, target
        if not destination.exists() and (
            registered == target or recognizable_managed_target(target, name)
        ):
            return "stale", destination, target
        return "conflict", destination, target
    if destination.exists():
        return "conflict", destination, None
    return "available", destination, None


def select_skills(names: list[str]) -> list[str]:
    available = [path.name for path in skill_dirs()]
    if names == ["all"]:
        return available
    if names:
        for name in names:
            known_skill(name)
        return names
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise CliError("interactive skill install requires a terminal or explicit NAME/all")
    print("Available standalone skills:")
    for index, name in enumerate(available, start=1):
        description = frontmatter(SKILLS_DIR / name / "SKILL.md").get("description", "")
        print(f"{index:2}. {name:30} {description}")
    raw = input("Install names separated by spaces, or 'all' (empty cancels): ").strip()
    if not raw:
        return []
    return available if raw == "all" else raw.split()


def cmd_list(args: argparse.Namespace) -> int:
    registry = load_registry()
    kinds = (args.kind,) if args.kind else ("skill", "plugin")
    if "skill" in kinds:
        print("KIND   CODEX       CLAUDE      NAME                         DESCRIPTION")
        for path in skill_dirs():
            agents = skill_agents(path)
            statuses = {}
            for agent in AGENTS:
                statuses[agent] = (
                    link_status(agent, path.name, registry)[0] if agent in agents else "-"
                )
            description = frontmatter(path / "SKILL.md").get("description", "")
            if args.agent and args.agent not in agents:
                continue
            print(
                f"skill  {statuses['codex']:<11} {statuses['claude']:<11} "
                f"{path.name:<28} {description}"
            )
    if "plugin" in kinds:
        print("KIND   NAME                         VERSION   DESCRIPTION")
        for path in plugin_dirs():
            manifest = plugin_manifest(path)
            print(
                f"plugin {path.name:<28} {str(manifest.get('version', '-')):<9} "
                f"{manifest.get('description', '')}"
            )
    return 0


def cmd_skill_install(args: argparse.Namespace) -> int:
    names = select_skills(args.names)
    registry = load_registry()
    failed = False
    for name in names:
        path = known_skill(name)
        agents = [args.agent] if args.agent else skill_agents(path)
        for agent in agents:
            if agent not in skill_agents(path):
                raise CliError(f"skill {name} does not target {agent}")
            status, destination, target = link_status(agent, name, registry)
            if status == "installed":
                print(f"already installed: {name} ({agent})")
                if not args.dry_run:
                    registry["managed_skill_links"][f"{agent}/{name}"] = str(path)
            elif status in {"available", "stale"}:
                verb = "repaired" if status == "stale" else "installed"
                if args.dry_run:
                    print(f"would be {verb}: {name} ({agent}) -> {path}")
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    if status == "stale":
                        destination.unlink()
                    destination.symlink_to(path)
                    registry["managed_skill_links"][f"{agent}/{name}"] = str(path)
                    print(f"{verb}: {name} ({agent}) -> {path}")
            else:
                print(
                    f"conflict: refusing to replace unmanaged path {destination}"
                    + (f" -> {target}" if target else ""),
                    file=sys.stderr,
                )
                failed = True
    if names and not args.dry_run:
        save_registry(registry)
    return 1 if failed else 0


def cmd_skill_uninstall(args: argparse.Namespace) -> int:
    registry = load_registry()
    failed = False
    for name in args.names:
        path = known_skill(name)
        agents = [args.agent] if args.agent else skill_agents(path)
        for agent in agents:
            status, destination, target = link_status(agent, name, registry)
            registered = registry["managed_skill_links"].get(f"{agent}/{name}")
            managed = target == str(path) or (target is not None and registered == target)
            if status == "available":
                print(f"not installed: {name} ({agent})")
            elif status in {"installed", "stale"} and managed:
                if args.dry_run:
                    print(f"would uninstall: {name} ({agent}) -> {destination}")
                else:
                    destination.unlink()
                    registry["managed_skill_links"].pop(f"{agent}/{name}", None)
                    print(f"uninstalled: {name} ({agent})")
            else:
                print(f"refusing to remove unmanaged path: {destination}", file=sys.stderr)
                failed = True
    if not args.dry_run:
        save_registry(registry)
    return 1 if failed else 0


def cmd_skill_new(args: argparse.Namespace) -> int:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "new_skill.py"),
        args.name,
        "--description",
        args.description,
        "--skills-dir",
        str(SKILLS_DIR),
    ]
    if args.resources:
        command += ["--resources", args.resources]
    if args.targets:
        command += ["--targets", args.targets]
    if args.dry_run:
        command.append("--dry-run")
    return run(command).returncode


def cmd_skill_validate(args: argparse.Namespace) -> int:
    names = args.names or ["all"]
    command = [
        sys.executable,
        str(ROOT / "scripts" / "validate_skills.py"),
        "--skills-dir",
        str(SKILLS_DIR),
        "--evals-dir",
        str(ROOT / "evals"),
        *names,
    ]
    if args.strict:
        command.append("--strict")
    return run(command).returncode


def native_plugin_command(agent: str, action: str, name: str) -> list[str] | None:
    selector = f"{name}@{MARKETPLACE_NAME}"
    if agent == "codex":
        mapping = {"install": "add", "uninstall": "remove"}
        if action in mapping:
            return ["codex", "plugin", mapping[action], selector, "--json"]
        return None
    mapping = {
        "install": "install",
        "uninstall": "uninstall",
        "enable": "enable",
        "disable": "disable",
    }
    if action not in mapping:
        return None
    command = ["claude", "plugin", mapping[action], selector]
    if action == "uninstall":
        command.append("--keep-data")
    return command


def cmd_plugin_action(args: argparse.Namespace) -> int:
    known_plugin(args.name)
    command = native_plugin_command(args.agent, args.action, args.name)
    if command is None:
        emit_status(
            "interaction_required",
            agent="codex",
            action=args.action,
            plugin=args.name,
            next_action="Start `codex`, run `/plugins`, select the plugin, and press Space.",
        )
        return 2
    if args.dry_run:
        emit_status(
            "dry_run",
            effect="local-user-config-write",
            cli_available=command_available(args.agent),
            command=compact_command(command),
        )
        return 0
    if not command_available(args.agent):
        raise CliError(f"{args.agent} CLI is not installed")
    result = run(command)
    if result.returncode == 0:
        registry = load_registry()
        registry.setdefault("plugins", {})[f"{args.agent}/{args.name}"] = {
            "marketplace": MARKETPLACE_NAME,
            "last_action": args.action,
        }
        save_registry(registry)
    return result.returncode


def cmd_plugin_list(args: argparse.Namespace) -> int:
    if not args.agent:
        return cmd_list(argparse.Namespace(kind="plugin", agent=None))
    states, error = native_plugin_states(args.agent)
    print(f"NAME                         VERSION   INSTALLED  ENABLED   DESCRIPTION")
    for path in plugin_dirs():
        manifest = plugin_manifest(path)
        state = states.get(path.name, {})
        installed = state.get("installed")
        enabled = state.get("enabled")
        print(
            f"{path.name:<28} {str(manifest.get('version', '-')):<9} "
            f"{('yes' if installed else 'no'):<10} "
            f"{('yes' if enabled is True else 'no' if enabled is False else 'unknown'):<9} "
            f"{manifest.get('description', '')}"
        )
    if error:
        print(f"warning: native {args.agent} state unavailable: {error}", file=sys.stderr)
    return 0


def cmd_plugin_inspect(args: argparse.Namespace) -> int:
    path = known_plugin(args.name)
    payload = {
        "name": args.name,
        "path": str(path),
        "version": json.loads((path / "plugin-version.json").read_text())["version"],
        "codex": plugin_manifest(path),
        "claude": json.loads((path / ".claude-plugin/plugin.json").read_text()),
        "skills": sorted(item.parent.name for item in path.glob("skills/*/SKILL.md")),
        "agents": sorted(item.name for item in path.glob("agents/*.md")),
        "hooks": (path / "hooks" / "hooks.json").is_file(),
        "mcp": (path / ".mcp.json").is_file(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_plugin_validate(args: argparse.Namespace) -> int:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "validate_plugins.py"),
        *(args.names or ["all"]),
    ]
    if args.strict:
        command.append("--strict")
    return run(command).returncode


def cmd_plugin_new(args: argparse.Namespace) -> int:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "new_plugin.py"),
        args.name,
        "--description",
        args.description,
    ]
    if args.dry_run:
        command.append("--dry-run")
    return run(command).returncode


def marketplace_command(agent: str, action: str) -> list[str]:
    if agent == "codex":
        mapping = {
            "add": ["codex", "plugin", "marketplace", "add", str(ROOT), "--json"],
            "status": ["codex", "plugin", "marketplace", "list"],
            "update": ["codex", "plugin", "marketplace", "upgrade", MARKETPLACE_NAME],
            "remove": ["codex", "plugin", "marketplace", "remove", MARKETPLACE_NAME],
        }
    else:
        mapping = {
            "add": ["claude", "plugin", "marketplace", "add", str(ROOT)],
            "status": ["claude", "plugin", "marketplace", "list", "--json"],
            "update": ["claude", "plugin", "marketplace", "update", MARKETPLACE_NAME],
            "remove": ["claude", "plugin", "marketplace", "remove", MARKETPLACE_NAME],
        }
    return mapping[action]


def cmd_marketplace(args: argparse.Namespace) -> int:
    agents = [args.agent] if getattr(args, "agent", None) else list(AGENTS)
    failed = False
    for agent in agents:
        command = marketplace_command(agent, args.action)
        if getattr(args, "dry_run", False):
            emit_status(
                "dry_run",
                agent=agent,
                action=args.action,
                cli_available=command_available(agent),
                command=compact_command(command),
            )
            continue
        if not command_available(agent):
            emit_status("skipped", agent=agent, reason="CLI not installed")
            continue
        result = run(command)
        if result.returncode != 0:
            failed = True
            continue
        if args.action in {"add", "remove"}:
            registry = load_registry()
            if args.action == "add":
                registry["marketplaces"][agent] = {
                    "name": MARKETPLACE_NAME,
                    "source": str(ROOT),
                }
            else:
                registry["marketplaces"].pop(agent, None)
            save_registry(registry)
    return 1 if failed else 0


def git_output(*args: str) -> str:
    result = run(["git", "-C", str(ROOT), *args], capture=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def repair_renamed_skill_links(
    registry: dict[str, Any], repair: bool
) -> tuple[list[dict[str, str]], list[str], list[str]]:
    migrations = load_migrations()
    pending: list[dict[str, str]] = []
    repaired: list[str] = []
    conflicts: list[str] = []
    for record in migrations["skill_renames"]:
        old, new = record["from"], record["to"]
        new_source = SKILLS_DIR / new
        if not (new_source / "SKILL.md").is_file():
            conflicts.append(f"migration target missing: {new}")
            continue
        for agent in AGENTS:
            old_path = agent_skill_dir(agent) / old
            if not old_path.is_symlink():
                continue
            target = os.readlink(old_path)
            registered = registry["managed_skill_links"].get(f"{agent}/{old}")
            if not (registered == target or recognizable_managed_target(target, old)):
                conflicts.append(str(old_path))
                continue
            new_path = agent_skill_dir(agent) / new
            entry = {"agent": agent, "from": str(old_path), "to": str(new_path)}
            pending.append(entry)
            if not repair:
                continue
            if new_path.exists() or new_path.is_symlink():
                conflicts.append(str(new_path))
                continue
            new_path.parent.mkdir(parents=True, exist_ok=True)
            old_path.unlink()
            new_path.symlink_to(new_source)
            registry["managed_skill_links"].pop(f"{agent}/{old}", None)
            registry["managed_skill_links"][f"{agent}/{new}"] = str(new_source)
            registry["migrations"].append({"kind": "skill_rename", "from": old, "to": new})
            repaired.append(str(new_path))
    return pending, repaired, conflicts


def launcher_states(repair: bool) -> tuple[dict[str, dict[str, str]], list[str], list[str]]:
    bin_dir = Path(os.environ.get("YUZURU_BIN_DIR", Path.home() / ".local" / "bin"))
    states: dict[str, dict[str, str]] = {}
    repaired: list[str] = []
    conflicts: list[str] = []
    for name in ("yuzuru", "skill"):
        destination = bin_dir / name
        source = ROOT / name
        state = "available"
        target = ""
        if destination.is_symlink():
            target = os.readlink(destination)
            if target == str(source):
                state = "installed"
            elif not destination.exists() and target.replace("\\", "/").endswith(
                f"/yuzuru-skills/{name}"
            ):
                state = "stale"
                if repair:
                    destination.unlink()
                    destination.symlink_to(source)
                    state = "installed"
                    target = str(source)
                    repaired.append(str(destination))
            else:
                state = "conflict"
                conflicts.append(str(destination))
        elif destination.exists():
            state = "conflict"
            conflicts.append(str(destination))
        states[name] = {"status": state, "path": str(destination), "target": target}
    return states, repaired, conflicts


def doctor_payload(repair: bool) -> tuple[dict[str, Any], bool]:
    registry = load_registry()
    repaired: list[str] = []
    conflicts: list[str] = []
    stale: list[dict[str, str]] = []
    for path in skill_dirs():
        for agent in skill_agents(path):
            status, destination, target = link_status(agent, path.name, registry)
            if status == "conflict":
                conflicts.append(str(destination))
            if status == "stale":
                stale.append({"agent": agent, "skill": path.name, "path": str(destination)})
                if repair:
                    destination.unlink()
                    destination.symlink_to(path)
                    registry["managed_skill_links"][f"{agent}/{path.name}"] = str(path)
                    repaired.append(str(destination))
    renamed, renamed_repaired, renamed_conflicts = repair_renamed_skill_links(registry, repair)
    repaired.extend(renamed_repaired)
    conflicts.extend(renamed_conflicts)
    launchers, launcher_repaired, launcher_conflicts = launcher_states(repair)
    repaired.extend(launcher_repaired)
    conflicts.extend(launcher_conflicts)
    if repair and repaired:
        save_registry(registry)
    cli: dict[str, Any] = {}
    for agent in AGENTS:
        executable = shutil.which(agent)
        version = None
        if executable:
            result = run([agent, "--version"], capture=True)
            version = (result.stdout or result.stderr).strip()[:200]
        cli[agent] = {"available": bool(executable), "path": executable, "version": version}
        states, state_error = native_plugin_states(agent)
        cli[agent]["plugins"] = states
        cli[agent]["plugin_state_error"] = state_error
    manifest_result = run(
        [sys.executable, str(ROOT / "scripts" / "validate_repository.py"), "--json"],
        capture=True,
        timeout=60,
    )
    payload = {
        "repository": str(ROOT),
        "revision": git_output("rev-parse", "HEAD"),
        "branch": git_output("branch", "--show-current"),
        "dirty": bool(git_output("status", "--porcelain")),
        "launchers": launchers,
        "runtime": {
            "config": str(xdg_dir("config")),
            "cache": str(xdg_dir("cache")),
            "data": str(xdg_dir("data")),
            "registry": str(registry_path()),
        },
        "agents": cli,
        "stale_skill_links": stale,
        "renamed_skill_links": renamed,
        "conflicts": conflicts,
        "repaired": repaired,
        "marketplaces": registry["marketplaces"],
        "manifest_validation": {
            "ok": manifest_result.returncode == 0,
            "result": manifest_result.stdout.strip()[:4000],
        },
        "recommendations": [],
    }
    if stale and not repair:
        payload["recommendations"].append("Run `yuzuru doctor --repair` for recognized managed links.")
    if renamed and not repair:
        payload["recommendations"].append(
            "Run `yuzuru doctor --repair` for recognized append-only skill renames."
        )
    if conflicts:
        payload["recommendations"].append("Resolve unmanaged path conflicts manually after checking ownership.")
    for agent in AGENTS:
        if not cli[agent]["available"]:
            payload["recommendations"].append(f"Install {agent} CLI to run native integration checks.")
    return payload, manifest_result.returncode == 0 and not conflicts


def cmd_doctor(args: argparse.Namespace) -> int:
    payload, healthy = doctor_payload(args.repair)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"repo:      {payload['repository']}")
        print(f"revision:  {payload['revision']} ({payload['branch']})")
        print(f"dirty:     {payload['dirty']}")
        for agent, value in payload["agents"].items():
            print(f"{agent:10} {value['version'] or 'not installed'}")
        print(f"stale:     {len(payload['stale_skill_links'])}")
        print(f"conflicts: {len(payload['conflicts'])}")
        print(f"manifests: {'ok' if payload['manifest_validation']['ok'] else 'FAIL'}")
        for recommendation in payload["recommendations"]:
            print(f"recommendation: {recommendation}")
    return 0 if healthy else 1


def cmd_update(args: argparse.Namespace) -> int:
    if git_output("status", "--porcelain"):
        raise CliError("refusing update: repository has local changes")
    if args.dry_run:
        emit_status(
            "dry_run",
            effect="repository-write",
            command=compact_command(["git", "-C", str(ROOT), "pull", "--ff-only"]),
            follow_up="validate repository, repair recognized managed links, refresh marketplaces manually",
        )
        return 0
    result = run(["git", "-C", str(ROOT), "pull", "--ff-only"], timeout=120)
    if result.returncode != 0:
        return result.returncode
    validation = run([sys.executable, str(ROOT / "scripts" / "validate_repository.py")], timeout=120)
    if validation.returncode != 0:
        return validation.returncode
    payload, _ = doctor_payload(repair=True)
    print(f"updated repository: {ROOT}")
    if payload["repaired"]:
        print(f"repaired managed skill links: {len(payload['repaired'])}")
    print("refresh native marketplaces with `yuzuru marketplace update --agent <agent>`.")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    command = [sys.executable, str(ROOT / "scripts" / "validate_repository.py")]
    if args.strict:
        command.append("--strict")
    return run(command, timeout=120).returncode


def add_agent_argument(parser: argparse.ArgumentParser, *, required: bool = False) -> None:
    parser.add_argument("--agent", choices=AGENTS, required=required)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="yuzuru", description="Cross-agent extension manager")
    commands = parser.add_subparsers(dest="command", required=True)

    list_parser = commands.add_parser("list", help="list skills and plugins")
    list_parser.add_argument("--kind", choices=("skill", "plugin"))
    add_agent_argument(list_parser)
    list_parser.set_defaults(func=cmd_list)

    validate = commands.add_parser("validate", help="validate the complete repository")
    validate.add_argument("--strict", action="store_true")
    validate.set_defaults(func=cmd_validate)

    skill = commands.add_parser("skill", help="manage standalone skills")
    skill_commands = skill.add_subparsers(dest="skill_command", required=True)
    skill_install = skill_commands.add_parser("install")
    skill_install.add_argument("names", nargs="*")
    add_agent_argument(skill_install)
    skill_install.add_argument("--dry-run", action="store_true")
    skill_install.set_defaults(func=cmd_skill_install)
    skill_uninstall = skill_commands.add_parser("uninstall")
    skill_uninstall.add_argument("names", nargs="+")
    add_agent_argument(skill_uninstall)
    skill_uninstall.add_argument("--dry-run", action="store_true")
    skill_uninstall.set_defaults(func=cmd_skill_uninstall)
    skill_new = skill_commands.add_parser("new")
    skill_new.add_argument("name")
    skill_new.add_argument("--description", required=True)
    skill_new.add_argument("--resources", default="")
    skill_new.add_argument("--targets", default="")
    skill_new.add_argument("--dry-run", action="store_true")
    skill_new.set_defaults(func=cmd_skill_new)
    skill_validate = skill_commands.add_parser("validate")
    skill_validate.add_argument("names", nargs="*")
    skill_validate.add_argument("--strict", action="store_true")
    skill_validate.set_defaults(func=cmd_skill_validate)

    plugin = commands.add_parser("plugin", help="manage plugins")
    plugin_commands = plugin.add_subparsers(dest="plugin_command", required=True)
    plugin_list = plugin_commands.add_parser("list")
    add_agent_argument(plugin_list)
    plugin_list.set_defaults(func=cmd_plugin_list)
    plugin_inspect = plugin_commands.add_parser("inspect")
    plugin_inspect.add_argument("name")
    plugin_inspect.set_defaults(func=cmd_plugin_inspect)
    plugin_validate = plugin_commands.add_parser("validate")
    plugin_validate.add_argument("names", nargs="*")
    plugin_validate.add_argument("--strict", action="store_true")
    plugin_validate.set_defaults(func=cmd_plugin_validate)
    plugin_new = plugin_commands.add_parser("new")
    plugin_new.add_argument("name")
    plugin_new.add_argument("--description", required=True)
    plugin_new.add_argument("--dry-run", action="store_true")
    plugin_new.set_defaults(func=cmd_plugin_new)
    for action in ("install", "uninstall", "enable", "disable"):
        action_parser = plugin_commands.add_parser(action)
        action_parser.add_argument("name")
        add_agent_argument(action_parser, required=True)
        action_parser.add_argument("--dry-run", action="store_true")
        action_parser.set_defaults(func=cmd_plugin_action, action=action)

    marketplace = commands.add_parser("marketplace", help="manage native marketplace registration")
    marketplace_commands = marketplace.add_subparsers(dest="marketplace_command", required=True)
    for action in ("add", "update", "remove"):
        action_parser = marketplace_commands.add_parser(action)
        add_agent_argument(action_parser, required=True)
        action_parser.add_argument("--dry-run", action="store_true")
        action_parser.set_defaults(func=cmd_marketplace, action=action)
    marketplace_status = marketplace_commands.add_parser("status")
    add_agent_argument(marketplace_status)
    marketplace_status.set_defaults(func=cmd_marketplace, action="status")

    update = commands.add_parser("update", help="fast-forward repository safely")
    update.add_argument("--dry-run", action="store_true")
    update.set_defaults(func=cmd_update)
    doctor = commands.add_parser("doctor", help="diagnose repository and installations")
    doctor.add_argument("--repair", action="store_true")
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(func=cmd_doctor)
    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        return int(args.func(args))
    except CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except subprocess.TimeoutExpired as exc:
        print(f"error: command timed out after {exc.timeout}s", file=sys.stderr)
        return 124
    except KeyboardInterrupt:
        print("cancelled", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
