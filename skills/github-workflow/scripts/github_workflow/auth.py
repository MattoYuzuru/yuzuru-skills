"""Credential discovery without accepting or exposing tokens on the CLI."""

from __future__ import annotations

import os
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from .errors import GitHubError


DEFAULT_TOKEN_FILE = "~/.config/yuzuru-codex-skills/github-workflow/token"


@dataclass(frozen=True)
class Credential:
    token: str
    source: str
    warning: str | None = None


def _file_warning(path: Path) -> str | None:
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        return f"token file permissions are {mode:04o}; use 0600"
    return None


def discover_credential(
    host: str = "github.com",
    token_file: str | None = None,
    *,
    required: bool = False,
    allow_gh: bool = True,
    environ: Mapping[str, str] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> Credential | None:
    env = os.environ if environ is None else environ
    for name in ("GH_TOKEN", "GITHUB_TOKEN"):
        token = env.get(name, "").strip()
        if token:
            return Credential(token=token, source=name)

    path = Path(token_file or DEFAULT_TOKEN_FILE).expanduser()
    if path.is_file():
        token = path.read_text(encoding="utf-8").strip()
        if token:
            return Credential(token=token, source="config-file", warning=_file_warning(path))

    if allow_gh:
        try:
            result = runner(
                ["gh", "auth", "token", "--hostname", host],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (FileNotFoundError, subprocess.SubprocessError, OSError):
            result = None
        if result is not None and result.returncode == 0 and result.stdout.strip():
            return Credential(token=result.stdout.strip(), source="gh-auth")

    if required:
        raise GitHubError(
            "GitHub token not found in GH_TOKEN, GITHUB_TOKEN, the configured token file, or gh auth",
            kind="auth",
        )
    return None
