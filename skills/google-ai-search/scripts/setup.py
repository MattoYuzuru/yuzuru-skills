#!/usr/bin/env python3
"""Configure and inspect the Gemini API key used by Google AI Search."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from api_config import AI_STUDIO_KEY_URL, DEFAULT_MODEL, key_path, load_api_key, save_api_key


SCRIPT_DIR = Path(__file__).resolve().parent


def setup_command() -> str:
    executable = "py -3" if os.name == "nt" else "python3"
    return f'{executable} "{SCRIPT_DIR / "setup.py"}" configure'


def launcher_status() -> dict[str, Any]:
    if os.name == "nt":
        return {"supported": False, "reason": "Run scripts\\search.py with py -3."}

    bin_dir = Path(os.environ.get("GOOGLE_AI_SEARCH_BIN_DIR", Path.home() / ".local" / "bin"))
    launcher = bin_dir / "google-ai-search"
    discovered = shutil.which("google-ai-search")
    on_path = discovered is not None and Path(discovered).absolute() == launcher.absolute()
    return {
        "supported": True,
        "path": str(launcher),
        "installed": launcher.is_symlink() or launcher.is_file(),
        "on_path": on_path,
    }


def collect_status() -> dict[str, Any]:
    key, source = load_api_key()
    configured = key is not None
    result: dict[str, Any] = {
        "ready": configured,
        "model": os.environ.get("GOOGLE_AI_SEARCH_MODEL", DEFAULT_MODEL),
        "api_key_configured": configured,
        "api_key_source": source,
        "config_path": str(key_path()),
        "launcher": launcher_status(),
    }
    if not configured:
        result["setup_url"] = AI_STUDIO_KEY_URL
        result["next_action"] = setup_command()
    return result


def print_json(value: dict[str, Any], *, stream: Any = sys.stdout) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2), file=stream)


def api_error_message(error: urllib.error.HTTPError) -> str:
    try:
        payload = json.loads(error.read().decode("utf-8"))
        return payload.get("error", {}).get("message") or str(error)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return str(error)


def validate_api_key(api_key: str, timeout: float) -> tuple[bool, str | None]:
    request = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1",
        headers={"x-goog-api-key": api_key, "User-Agent": "yuzuru-google-ai-search/2"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status == 200, None
    except urllib.error.HTTPError as exc:
        return False, api_error_message(exc)
    except urllib.error.URLError as exc:
        return False, str(exc.reason)


def install_launcher() -> dict[str, Any]:
    if os.name == "nt":
        return {"installed": False, "reason": "Use py -3 scripts\\search.py on Windows."}

    bin_dir = Path(os.environ.get("GOOGLE_AI_SEARCH_BIN_DIR", Path.home() / ".local" / "bin"))
    bin_dir.mkdir(parents=True, exist_ok=True)
    launcher = bin_dir / "google-ai-search"
    target = SCRIPT_DIR / "search.sh"

    if launcher.exists() and not launcher.is_symlink():
        return {
            "installed": False,
            "path": str(launcher),
            "reason": "An unmanaged file already exists; it was not replaced.",
        }

    launcher.unlink(missing_ok=True)
    launcher.symlink_to(target)
    return {"installed": True, "path": str(launcher), "target": str(target)}


def configure(args: argparse.Namespace) -> int:
    api_key = getpass.getpass("Paste Gemini API key (input hidden): ").strip()
    if not api_key:
        print_json({"ready": False, "error": "API key cannot be empty."}, stream=sys.stderr)
        return 1

    if not args.skip_validation:
        valid, error = validate_api_key(api_key, args.timeout)
        if not valid:
            print_json(
                {
                    "ready": False,
                    "error": f"Gemini API key validation failed: {error}",
                    "setup_url": AI_STUDIO_KEY_URL,
                },
                stream=sys.stderr,
            )
            return 1

    path = save_api_key(api_key)
    launcher_install = install_launcher()
    result = collect_status()
    result["config_path"] = str(path)
    result["key_validated"] = not args.skip_validation
    result["launcher_install"] = launcher_install
    print_json(result)
    return 0


def remove_key() -> int:
    path = key_path()
    path.unlink(missing_ok=True)
    print_json({"removed": True, "config_path": str(path)})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check", help="Report whether an API key is configured.")
    configure_parser = subparsers.add_parser("configure", help="Validate and save an API key securely.")
    configure_parser.add_argument("--skip-validation", action="store_true")
    configure_parser.add_argument("--timeout", type=float, default=15.0)
    subparsers.add_parser("remove-key", help="Delete the key stored in the config file.")
    args = parser.parse_args()

    if args.command == "check":
        status = collect_status()
        print_json(status)
        return 0 if status["ready"] else 2
    if args.command == "configure":
        return configure(args)
    return remove_key()


if __name__ == "__main__":
    raise SystemExit(main())
