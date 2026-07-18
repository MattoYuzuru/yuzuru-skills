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


def config_path() -> Path:
    """Non-secret metadata: client_email (mirrored from the key), user_email, and the
    known-spreadsheets registry. Kept separate from the service-account key so the secret
    and everything else can be reasoned about (and deleted) independently."""
    return config_dir() / "config.json"


def token_cache_path() -> Path:
    return config_dir() / "token-cache.json"


def _load_config() -> dict[str, Any]:
    try:
        return json.loads(config_path().read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_config(data: dict[str, Any]) -> None:
    _write_private(config_path(), json.dumps(data, indent=2))


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
    if info["token_uri"] != TOKEN_URL:
        raise SheetsConfigError(
            f"Service-account token_uri must be the official Google endpoint {TOKEN_URL}."
        )
    _write_private(service_account_key_path(), text)
    token_cache_path().unlink(missing_ok=True)
    config = _load_config()
    config["client_email"] = info["client_email"]
    _save_config(config)
    return {"client_email": info["client_email"]}


def load_service_account_info() -> dict[str, Any] | None:
    path = service_account_key_path()
    try:
        info = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        raise SheetsConfigError(f"Stored service-account key is not valid JSON: {exc}") from exc
    if info.get("token_uri") != TOKEN_URL:
        raise SheetsConfigError("Stored service-account key has an untrusted token_uri; import a valid Google key.")
    return info


def load_client_email() -> str | None:
    """Fast path for the (non-secret) service-account email — reads config.json instead of
    opening the private key file, so 'check' and 'known-spreadsheets' never touch the secret."""
    return _load_config().get("client_email")


def save_user_email(email: str) -> None:
    email = email.strip()
    if "@" not in email:
        raise SheetsConfigError(f"'{email}' does not look like an email address.")
    config = _load_config()
    config["user_email"] = email
    _save_config(config)


def load_user_email() -> str | None:
    return _load_config().get("user_email")


def remember_spreadsheet(spreadsheet_id: str, *, title: str | None = None, url: str | None = None) -> None:
    """Cache id -> {title, url, last_seen} so a spreadsheet seen once via list/info/create can
    be recalled by title later without asking the user to re-paste the link."""
    config = _load_config()
    known = config.setdefault("known_spreadsheets", {})
    entry = known.get(spreadsheet_id, {})
    if title:
        entry["title"] = title
    if url:
        entry["url"] = url
    entry["last_seen"] = int(time.time())
    known[spreadsheet_id] = entry
    _save_config(config)


def load_known_spreadsheets() -> dict[str, Any]:
    return _load_config().get("known_spreadsheets", {})


def remove_all() -> None:
    service_account_key_path().unlink(missing_ok=True)
    config_path().unlink(missing_ok=True)
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
        "aud": TOKEN_URL,
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
    token_response = _exchange_jwt_for_token(assertion, TOKEN_URL)
    access_token = token_response.get("access_token")
    if not access_token:
        raise SheetsConfigError("Token exchange response had no access_token.")

    expires_at = int(time.time()) + int(token_response.get("expires_in", 3600))
    _write_private(
        token_cache_path(),
        json.dumps({"access_token": access_token, "expires_at": expires_at, "scope_key": cache_key}),
    )
    return access_token
