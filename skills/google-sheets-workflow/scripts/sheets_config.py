"""Shared configuration and headless service-account auth for Google Sheets Workflow.

No browser, no consent screen: this signs a short-lived JWT with the service account's
private key (google.auth.crypt, pure-Python RSA backend) and exchanges it for an access
token over a plain HTTPS POST (stdlib urllib). Never print the private key or an access
token.
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

TOKEN_URL = "https://oauth2.googleapis.com/token"
GRANT_TYPE = "urn:ietf:params:oauth:grant-type:jwt-bearer"
TOKEN_SKEW_SECONDS = 60


class SheetsConfigError(RuntimeError):
    pass


def config_dir() -> Path:
    override = os.environ.get("GOOGLE_SHEETS_CONFIG_DIR")
    if override:
        return Path(override).expanduser()

    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "yuzuru-codex-skills" / "google-sheets-workflow"


def service_account_key_path() -> Path:
    return config_dir() / "service-account.json"


def user_email_path() -> Path:
    return config_dir() / "user-email"


def token_cache_path() -> Path:
    return config_dir() / "token-cache.json"


def _write_private(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(data)
        os.replace(temporary, path)
        if os.name != "nt":
            os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def save_service_account_key(source_path: Path) -> dict[str, Any]:
    text = source_path.read_text(encoding="utf-8")
    info = json.loads(text)
    if info.get("type") != "service_account":
        raise SheetsConfigError(
            f"{source_path} does not look like a service-account key "
            f"(expected \"type\": \"service_account\")."
        )
    for field in ("client_email", "private_key", "token_uri"):
        if not info.get(field):
            raise SheetsConfigError(f"Service-account key is missing required field '{field}'.")
    _write_private(service_account_key_path(), text)
    token_cache_path().unlink(missing_ok=True)
    return {"client_email": info["client_email"]}


def load_service_account_info() -> dict[str, Any] | None:
    path = service_account_key_path()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def save_user_email(email: str) -> None:
    email = email.strip()
    if "@" not in email:
        raise SheetsConfigError(f"'{email}' does not look like an email address.")
    _write_private(user_email_path(), email + "\n")


def load_user_email() -> str | None:
    try:
        return user_email_path().read_text(encoding="utf-8").strip() or None
    except FileNotFoundError:
        return None


def remove_all() -> None:
    service_account_key_path().unlink(missing_ok=True)
    user_email_path().unlink(missing_ok=True)
    token_cache_path().unlink(missing_ok=True)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _build_signed_jwt(info: dict[str, Any], scopes: list[str]) -> str:
    try:
        from google.auth.crypt import RSASigner
    except ImportError as exc:
        raise SheetsConfigError(
            "google-auth is not installed. Run scripts/bootstrap.py and use its 'python' "
            "for every later command."
        ) from exc

    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {
        "iss": info["client_email"],
        "scope": " ".join(scopes),
        "aud": info.get("token_uri", TOKEN_URL),
        "iat": now,
        "exp": now + 3600,
    }
    signing_input = f"{_b64url(json.dumps(header).encode())}.{_b64url(json.dumps(claims).encode())}"
    signer = RSASigner.from_service_account_info(info)
    signature = signer.sign(signing_input.encode("utf-8"))
    return f"{signing_input}.{_b64url(signature)}"


def _exchange_jwt_for_token(assertion: str, token_uri: str) -> dict[str, Any]:
    body = urllib.parse.urlencode({"grant_type": GRANT_TYPE, "assertion": assertion}).encode()
    request = urllib.request.Request(
        token_uri,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SheetsConfigError(f"Token exchange failed ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise SheetsConfigError(f"Token exchange connection error: {exc.reason}") from exc


def get_access_token(scopes: list[str]) -> str:
    cache_key = " ".join(sorted(scopes))
    try:
        cached = json.loads(token_cache_path().read_text(encoding="utf-8"))
        if cached.get("scope_key") == cache_key and cached.get("expires_at", 0) - TOKEN_SKEW_SECONDS > time.time():
            return cached["access_token"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass

    info = load_service_account_info()
    if info is None:
        raise SheetsConfigError(
            "No service-account key configured. Run scripts/setup.py check for setup instructions."
        )

    assertion = _build_signed_jwt(info, scopes)
    token_response = _exchange_jwt_for_token(assertion, info.get("token_uri", TOKEN_URL))
    access_token = token_response.get("access_token")
    if not access_token:
        raise SheetsConfigError(f"Token exchange response had no access_token: {token_response}")

    expires_at = int(time.time()) + int(token_response.get("expires_in", 3600))
    _write_private(
        token_cache_path(),
        json.dumps({"access_token": access_token, "expires_at": expires_at, "scope_key": cache_key}),
    )
    return access_token
