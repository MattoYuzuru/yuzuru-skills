#!/usr/bin/env python3
"""Check, install, and run Google AI Search in an isolated environment."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import venv
from pathlib import Path
from typing import Any


MIN_PYTHON = (3, 9)
SKILL_DIR = Path(__file__).resolve().parent.parent
SEARCH_SCRIPT = SKILL_DIR / "scripts" / "search.py"
REQUIREMENTS = SKILL_DIR / "requirements.txt"
PLAYWRIGHT_VERSION = next(
    line.split("==", 1)[1]
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
    if line.startswith("playwright==")
)


def config_root() -> Path:
    override = os.environ.get("GOOGLE_AI_SEARCH_VENV")
    if override:
        return Path(override).expanduser()

    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "yuzuru-codex-skills" / "google-ai-search" / "venv"


def venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def browser_probe(python: Path) -> dict[str, Any]:
    probe = """
import importlib.metadata
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as playwright:
    executable = Path(playwright.chromium.executable_path)
    print(json.dumps({
        "playwright_version": importlib.metadata.version("playwright"),
        "chromium_executable": str(executable),
        "chromium_installed": executable.is_file(),
    }))
"""
    try:
        completed = subprocess.run(
            [str(python), "-c", probe],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"error": str(exc)}

    if completed.returncode != 0:
        error = (completed.stderr or completed.stdout).strip()
        return {"error": error[-1200:]}

    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"error": "Playwright probe returned invalid JSON."}


def launcher_status() -> dict[str, Any]:
    if os.name == "nt":
        return {"supported": False, "reason": "Use bootstrap.py run on Windows."}

    bin_dir = Path(os.environ.get("GOOGLE_AI_SEARCH_BIN_DIR", Path.home() / ".local" / "bin"))
    launcher = bin_dir / "google-ai-search"
    discovered = shutil.which("google-ai-search")
    on_path = discovered is not None and Path(discovered).resolve() == launcher.resolve()
    return {
        "supported": True,
        "path": str(launcher),
        "installed": launcher.is_symlink() or launcher.is_file(),
        "on_path": on_path,
    }


def collect_status() -> dict[str, Any]:
    venv_dir = config_root()
    python = venv_python(venv_dir)
    result: dict[str, Any] = {
        "ready": False,
        "platform": platform.system(),
        "host_python": sys.executable,
        "host_python_version": platform.python_version(),
        "minimum_python": ".".join(map(str, MIN_PYTHON)),
        "required_playwright_version": PLAYWRIGHT_VERSION,
        "venv": str(venv_dir),
        "venv_python": str(python),
        "venv_exists": python.is_file(),
        "launcher": launcher_status(),
        "missing": [],
    }

    missing: list[str] = result["missing"]
    if sys.version_info < MIN_PYTHON:
        missing.append("python>=3.9")
    if not python.is_file():
        missing.append("venv")
    else:
        probe = browser_probe(python)
        result.update(probe)
        if probe.get("error") or probe.get("playwright_version") != PLAYWRIGHT_VERSION:
            missing.append(f"playwright=={PLAYWRIGHT_VERSION}")
        elif not probe.get("chromium_installed"):
            missing.append("chromium")

    result["ready"] = not missing
    if missing:
        result["next_action"] = "Ask for consent, then run bootstrap.py install."
    return result


def print_json(value: dict[str, Any], *, stream: Any = sys.stdout) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2), file=stream)


def install_launcher() -> dict[str, Any]:
    if os.name == "nt":
        return {"installed": False, "reason": "Use bootstrap.py run on Windows."}

    bin_dir = Path(os.environ.get("GOOGLE_AI_SEARCH_BIN_DIR", Path.home() / ".local" / "bin"))
    bin_dir.mkdir(parents=True, exist_ok=True)
    launcher = bin_dir / "google-ai-search"
    target = SKILL_DIR / "scripts" / "search.sh"

    if launcher.exists() and not launcher.is_symlink():
        return {
            "installed": False,
            "path": str(launcher),
            "reason": "An unmanaged file already exists; it was not replaced.",
        }

    launcher.unlink(missing_ok=True)
    launcher.symlink_to(target)
    return {"installed": True, "path": str(launcher), "target": str(target)}


def install() -> int:
    if sys.version_info < MIN_PYTHON:
        print_json(
            {
                "ready": False,
                "error": f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer is required.",
                "platform": platform.system(),
            },
            stream=sys.stderr,
        )
        return 1

    venv_dir = config_root()
    python = venv_python(venv_dir)
    try:
        if not python.is_file():
            venv_dir.parent.mkdir(parents=True, exist_ok=True)
            venv.EnvBuilder(with_pip=True).create(venv_dir)

        subprocess.run(
            [str(python), "-m", "pip", "install", "-r", str(REQUIREMENTS)],
            check=True,
        )
        subprocess.run(
            [str(python), "-m", "playwright", "install", "chromium"],
            check=True,
        )
    except Exception as exc:
        print_json(
            {
                "ready": False,
                "error": str(exc),
                "platform": platform.system(),
                "venv": str(venv_dir),
                "next_action": "See references/setup.md for OS-specific prerequisites.",
            },
            stream=sys.stderr,
        )
        return 1

    launcher_install = install_launcher()
    result = collect_status()
    result["launcher_install"] = launcher_install
    print_json(result)
    return 0 if result["ready"] else 1


def run_search(search_args: list[str]) -> int:
    status = collect_status()
    if not status["ready"]:
        print_json(status, stream=sys.stderr)
        return 2

    completed = subprocess.run(
        [status["venv_python"], str(SEARCH_SCRIPT), *search_args],
        check=False,
    )
    return completed.returncode


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "run":
        return run_search(sys.argv[2:])

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check", help="Report whether the isolated environment is ready.")
    subparsers.add_parser("install", help="Create the venv and install Playwright and Chromium.")
    subparsers.add_parser("run", help="Run search.py through the isolated environment.")
    args = parser.parse_args()

    if args.command == "check":
        status = collect_status()
        print_json(status)
        return 0 if status["ready"] else 2
    if args.command == "install":
        return install()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
