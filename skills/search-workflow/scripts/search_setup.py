#!/usr/bin/env python3
"""Inspect local search capabilities and emit safe installation suggestions."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable, Sequence


@dataclass(frozen=True)
class Tool:
    name: str
    commands: tuple[str, ...]
    route: str
    profiles: frozenset[str]
    url: str
    validate: str | None = None


TOOLS = (
    Tool(
        "ripgrep",
        ("rg",),
        "workspace text and file discovery",
        frozenset({"minimal", "core", "full"}),
        "https://github.com/BurntSushi/ripgrep",
    ),
    Tool(
        "ast-grep",
        ("ast-grep", "sg"),
        "syntax-aware source search",
        frozenset({"minimal", "core", "full"}),
        "https://github.com/ast-grep/ast-grep",
        validate="ast-grep",
    ),
    Tool(
        "ripgrep-all",
        ("rga",),
        "documents, archives, and adapter-backed formats",
        frozenset({"core", "full"}),
        "https://github.com/phiresky/ripgrep-all",
    ),
    Tool(
        "jq",
        ("jq",),
        "JSON structure",
        frozenset({"core", "full"}),
        "https://github.com/jqlang/jq",
    ),
    Tool(
        "yq",
        ("yq",),
        "YAML, XML, TOML, CSV, and properties structure",
        frozenset({"core", "full"}),
        "https://github.com/mikefarah/yq",
        validate="mikefarah-yq-v4",
    ),
    Tool(
        "poppler",
        ("pdftotext",),
        "PDF text adapter for ripgrep-all",
        frozenset({"full"}),
        "https://poppler.freedesktop.org/",
    ),
    Tool(
        "pandoc",
        ("pandoc",),
        "Office, ebook, and markup adapter for ripgrep-all",
        frozenset({"full"}),
        "https://pandoc.org/installing.html",
    ),
)


Which = Callable[[str], str | None]
Probe = Callable[[str], str]


def probe_version(path: str) -> str:
    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (result.stdout + "\n" + result.stderr).strip().lower()


def find_tool(tool: Tool, which: Which, probe: Probe) -> tuple[str | None, str | None]:
    for command in tool.commands:
        path = which(command)
        if not path:
            continue
        version = probe(path) if tool.validate else ""
        if tool.validate == "mikefarah-yq-v4":
            if "mikefarah" not in version and "version v4" not in version:
                continue
        elif tool.validate and tool.validate not in version:
            continue
        return command, path
    return None, None


def platform_id(system_name: str) -> str:
    normalized = system_name.casefold()
    if normalized == "darwin":
        return "macos"
    if normalized == "windows":
        return "windows"
    if normalized == "linux":
        return "linux"
    return normalized or "unknown"


def package_manager(which: Which) -> str | None:
    for manager in ("brew", "apt-get", "dnf", "pacman", "scoop", "winget"):
        if which(manager):
            return manager
    return None


def install_plan(
    missing: set[str], manager: str | None, which: Which
) -> tuple[list[str], list[str]]:
    commands: list[str] = []
    unresolved = set(missing)

    if manager == "brew":
        packages = {
            "ripgrep": "ripgrep",
            "ast-grep": "ast-grep",
            "ripgrep-all": "rga",
            "jq": "jq",
            "yq": "yq",
            "poppler": "poppler",
            "pandoc": "pandoc",
        }
        selected = [packages[name] for name in packages if name in unresolved]
        if selected:
            commands.append("brew install " + " ".join(selected))
            unresolved.difference_update(packages)
    elif manager == "apt-get":
        packages = {
            "ripgrep": "ripgrep",
            "jq": "jq",
            "poppler": "poppler-utils",
            "pandoc": "pandoc",
        }
        selected = [packages[name] for name in packages if name in unresolved]
        if selected:
            commands.append("sudo apt-get install " + " ".join(selected))
            unresolved.difference_update(packages)
    elif manager == "dnf":
        packages = {
            "ripgrep": "ripgrep",
            "jq": "jq",
            "poppler": "poppler-utils",
            "pandoc": "pandoc",
        }
        selected = [packages[name] for name in packages if name in unresolved]
        if selected:
            commands.append("sudo dnf install " + " ".join(selected))
            unresolved.difference_update(packages)
    elif manager == "pacman":
        packages = {
            "ripgrep": "ripgrep",
            "ast-grep": "ast-grep",
            "ripgrep-all": "ripgrep-all",
            "jq": "jq",
            "yq": "yq",
            "poppler": "poppler",
            "pandoc": "pandoc",
        }
        selected = [packages[name] for name in packages if name in unresolved]
        if selected:
            commands.append("sudo pacman -S " + " ".join(selected))
            unresolved.difference_update(packages)
    elif manager == "scoop":
        packages = {
            "ripgrep": "ripgrep",
            "ast-grep": "ast-grep",
            "ripgrep-all": "rga",
            "jq": "jq",
            "yq": "yq",
            "poppler": "poppler",
            "pandoc": "pandoc",
        }
        selected = [packages[name] for name in packages if name in unresolved]
        if selected:
            commands.append("scoop install " + " ".join(selected))
            unresolved.difference_update(packages)

    if "ast-grep" in unresolved:
        if which("npm"):
            commands.append("npm install --global @ast-grep/cli")
            unresolved.remove("ast-grep")
        elif which("cargo"):
            commands.append("cargo install ast-grep --locked")
            unresolved.remove("ast-grep")
    if "ripgrep-all" in unresolved and which("cargo"):
        commands.append("cargo install ripgrep_all --locked")
        unresolved.remove("ripgrep-all")
    if "yq" in unresolved and which("snap"):
        commands.append("sudo snap install yq")
        unresolved.remove("yq")

    return commands, sorted(unresolved)


def indexed_search(which: Which, system_name: str) -> dict[str, object]:
    candidates = ("mdfind",) if system_name.casefold() == "darwin" else ("plocate", "locate")
    for command in candidates:
        path = which(command)
        if path:
            return {"available": True, "command": command, "path": path}
    return {"available": False, "command": None, "path": None}


def build_report(
    profile: str,
    system_name: str,
    which: Which = shutil.which,
    probe: Probe = probe_version,
) -> dict[str, object]:
    selected = [tool for tool in TOOLS if profile in tool.profiles]
    routes: dict[str, dict[str, object]] = {}
    missing: set[str] = set()
    sources: dict[str, str] = {}

    for tool in selected:
        command, path = find_tool(tool, which, probe)
        available = path is not None
        routes[tool.name] = {
            "available": available,
            "command": command,
            "path": path,
            "route": tool.route,
        }
        sources[tool.name] = tool.url
        if not available:
            missing.add(tool.name)

    manager = package_manager(which)
    commands, unresolved = install_plan(missing, manager, which)
    return {
        "complete": not missing,
        "baseline_ready": routes.get("ripgrep", {}).get("available", False),
        "profile": profile,
        "platform": platform_id(system_name),
        "package_manager": manager,
        "routes": routes,
        "indexed_search": indexed_search(which, system_name),
        "missing": sorted(missing),
        "install_commands": commands,
        "manual_sources": {name: sources[name] for name in unresolved},
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description="Check local search tools and print non-executing installation suggestions."
    )
    subparsers = root.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="inspect tool availability")
    check.add_argument(
        "--profile",
        choices=("minimal", "core", "full"),
        default="core",
        help="minimal=rg+ast-grep; core adds documents/data; full adds rga adapters",
    )
    check.add_argument("--pretty", action="store_true", help="indent JSON output")
    return root


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command != "check":
        return 2
    report = build_report(args.profile, platform.system())
    print(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None, separators=None if args.pretty else (",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
