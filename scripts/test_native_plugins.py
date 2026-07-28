#!/usr/bin/env python3
"""Exercise local marketplace and one plugin lifecycle in isolated temporary agent homes."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = "yuzuru-engineering"


def execute(command: list[str], environment: dict[str, str], timeout: int) -> dict[str, object]:
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"command": command, "ok": False, "returncode": 124, "error": "timeout"}
    return {
        "command": command,
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout[-2000:],
        "stderr": result.stderr[-2000:],
    }


def lifecycle(agent: str, plugin: str, environment: dict[str, str], timeout: int) -> list[dict[str, object]]:
    selector = f"{plugin}@{MARKETPLACE}"
    if agent == "codex":
        commands = [
            ["codex", "plugin", "marketplace", "add", str(ROOT), "--json"],
            ["codex", "plugin", "list", "--marketplace", MARKETPLACE, "--available", "--json"],
            ["codex", "plugin", "add", selector, "--json"],
            ["codex", "plugin", "list", "--marketplace", MARKETPLACE, "--json"],
            ["codex", "plugin", "remove", selector, "--json"],
            ["codex", "plugin", "marketplace", "remove", MARKETPLACE],
        ]
    else:
        commands = [
            ["claude", "plugin", "validate", str(ROOT), "--strict"],
            ["claude", "plugin", "validate", str(ROOT / "plugins" / plugin), "--strict"],
            ["claude", "plugin", "marketplace", "add", str(ROOT)],
            ["claude", "plugin", "marketplace", "list", "--json"],
            ["claude", "plugin", "install", selector, "--scope", "user"],
            ["claude", "plugin", "list", "--json"],
            ["claude", "plugin", "disable", selector, "--scope", "user"],
            ["claude", "plugin", "enable", selector, "--scope", "user"],
            ["claude", "plugin", "uninstall", selector, "--scope", "user", "--keep-data"],
            ["claude", "plugin", "marketplace", "remove", MARKETPLACE],
        ]
    results: list[dict[str, object]] = []
    for command in commands:
        result = execute(command, environment, timeout)
        results.append(result)
        if not result["ok"]:
            break
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=("both", "codex", "claude"), default="both")
    parser.add_argument("--plugin", default="discovery-agent")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    plugin_path = ROOT / "plugins" / args.plugin
    if not (plugin_path / ".codex-plugin" / "plugin.json").is_file():
        parser.error(f"unknown plugin: {args.plugin}")
    if not 5 <= args.timeout <= 300:
        parser.error("--timeout must be between 5 and 300")
    requested = ["codex", "claude"] if args.agent == "both" else [args.agent]
    payload: dict[str, object] = {
        "effect": "isolated-local-user-config",
        "plugin": args.plugin,
        "agents": {},
    }
    failed = False
    with tempfile.TemporaryDirectory(prefix="yuzuru-native-plugins-") as directory:
        root = Path(directory)
        home = root / "home"
        for path in (
            home,
            home / ".codex",
            home / ".claude",
            root / "config",
            root / "cache",
            root / "data",
        ):
            path.mkdir(parents=True)
        environment = os.environ.copy()
        environment.update(
            {
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(root / "config"),
                "XDG_CACHE_HOME": str(root / "cache"),
                "XDG_DATA_HOME": str(root / "data"),
                "CODEX_HOME": str(home / ".codex"),
                "CLAUDE_CONFIG_DIR": str(home / ".claude"),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        agent_results: dict[str, object] = {}
        for agent in requested:
            if shutil.which(agent) is None:
                agent_results[agent] = {"status": "skipped", "reason": "CLI not installed"}
                continue
            results = lifecycle(agent, args.plugin, environment, args.timeout)
            ok = bool(results) and all(item["ok"] for item in results)
            agent_results[agent] = {"status": "passed" if ok else "failed", "steps": results}
            failed = failed or not ok
        payload["agents"] = agent_results
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
