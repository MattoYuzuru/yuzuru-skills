"""Shared configuration for Google AI Search."""

from __future__ import annotations

import os
import re
from pathlib import Path


DEFAULT_MODEL = "gemini-2.5-flash-lite"
AI_STUDIO_KEY_URL = "https://aistudio.google.com/apikey"
API_KEY_ENV_VARS = ("GOOGLE_AI_SEARCH_API_KEY", "GEMINI_API_KEY")
MODEL_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


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


def model_path() -> Path:
    return config_dir() / "model"


def validate_model(value: str) -> str:
    model = value.strip()
    if not MODEL_PATTERN.fullmatch(model):
        raise ValueError("Model must be 1-128 characters: letters, digits, dots, underscores, or hyphens.")
    return model


def resolve_model(override: str | None = None) -> tuple[str, str]:
    if override is not None:
        return validate_model(override), "cli"
    if "GOOGLE_AI_SEARCH_MODEL" in os.environ:
        return validate_model(os.environ["GOOGLE_AI_SEARCH_MODEL"]), "env"
    try:
        saved = model_path().read_text(encoding="utf-8")
    except FileNotFoundError:
        return DEFAULT_MODEL, "default"
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"Cannot read saved model configuration: {exc}") from exc
    try:
        return validate_model(saved), "saved_config"
    except ValueError as exc:
        raise ValueError(f"Invalid saved model configuration at {model_path()}: {exc}") from exc


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
    return _save_private_text(key_path(), value.strip())


def save_model(value: str) -> Path:
    return _save_private_text(model_path(), validate_model(value))


def _save_private_text(path: Path, value: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value + "\n")
        os.replace(temporary, path)
        if os.name != "nt":
            os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)
    return path
