#!/usr/bin/env python3
"""Create or reuse the isolated Python environment used by this skill."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def default_venv() -> Path:
    cache_home = os.environ.get("XDG_CACHE_HOME")
    if not cache_home:
        cache_home = os.environ.get("LOCALAPPDATA") if os.name == "nt" else str(Path.home() / ".cache")
    return Path(cache_home) / "yuzuru-codex-skills" / "google-sheets-workflow" / "venv"


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run(command: list[str]) -> None:
    subprocess.run(command, check=True, stdout=sys.stderr, stderr=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create or reuse a venv and install google-auth (pure-Python RSA signer)."
    )
    parser.add_argument(
        "--venv",
        type=Path,
        default=Path(os.environ.get("GOOGLE_SHEETS_VENV", default_venv())),
        help="venv path (default: GOOGLE_SHEETS_VENV or an OS cache directory)",
    )
    parser.add_argument(
        "--python",
        default=os.environ.get("PYTHON_BIN", sys.executable),
        help="Python used only to create a missing venv",
    )
    args = parser.parse_args()

    python = venv_python(args.venv)
    created = False
    if not python.exists():
        print(f"Creating virtual environment at {args.venv}", file=sys.stderr)
        run([args.python, "-m", "venv", str(args.venv)])
        created = True

    version_check = subprocess.run(
        [str(python), "-c", "import sys; raise SystemExit(sys.version_info < (3, 10))"],
        capture_output=True,
    )
    if version_check.returncode:
        print("Python 3.10 or newer is required by sheets_api.py", file=sys.stderr)
        return 1

    if subprocess.run([str(python), "-c", "import google.auth"], capture_output=True).returncode:
        print(f"Installing google-auth into {args.venv}", file=sys.stderr)
        run([str(python), "-m", "pip", "install", "--upgrade", "google-auth"])

    print(json.dumps({"venv": str(args.venv), "python": str(python), "created": created}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
