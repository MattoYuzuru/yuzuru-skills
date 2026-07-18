"""Shared configuration for Google AI Search."""

from __future__ import annotations

import os
from pathlib import Path


DEFAULT_MODEL = "gemini-3.1-flash-lite"
AI_STUDIO_KEY_URL = "https://aistudio.google.com/apikey"
API_KEY_ENV_VARS = ("GOOGLE_AI_SEARCH_API_KEY", "GEMINI_API_KEY")


def config_dir() -> Path:
    override = os.environ.get("GOOGLE_AI_SEARCH_CONFIG_DIR")
    if override:
        return Path(override).expanduser()

    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "yuzuru-codex-skills" / "google-ai-search"


def key_path() -> Path:
    return config_dir() / "api-key"


def load_api_key() -> tuple[str | None, str | None]:
    for variable in API_KEY_ENV_VARS:
        value = os.environ.get(variable, "").strip()
        if value:
            return value, f"environment:{variable}"

    path = key_path()
    try:
        value = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None, None
    return (value, "config_file") if value else (None, None)


def save_api_key(value: str) -> Path:
    path = key_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value.strip() + "\n")
        os.replace(temporary, path)
        if os.name != "nt":
            os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)
    return path
