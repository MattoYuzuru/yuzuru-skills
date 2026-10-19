"""Private transport/configuration primitives; no model or search-service dependency."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request


ORIGINS = {
    "epmc": "https://www.ebi.ac.uk/europepmc/webservices/rest",
    "crossref": "https://api.crossref.org",
    "arxiv": "https://export.arxiv.org",
    "arxiv-html": "https://arxiv.org",
    "openalex": "https://api.openalex.org",
}
MAX_BYTES = 5_000_000
SETUP_URL = "https://help.openalex.org/api/authentication/"


class EvidenceError(Exception):
    def __init__(self, kind: str, *, provider: str | None = None, status: int | None = None):
        super().__init__(kind)
        self.kind, self.provider, self.status = kind, provider, status

    def result(self) -> dict:
        return {k: v for k, v in {"error": self.kind, "provider": self.provider,
                                  "status": self.status}.items() if v is not None}


def data_dir(kind: str) -> Path:
    if kind not in {"config", "cache"}:
        raise ValueError("invalid_state_kind")
    configured = os.environ.get("XDG_" + kind.upper() + "_HOME")
    if configured:
        root = Path(configured).expanduser()
        if not root.is_absolute():
            raise EvidenceError("state_directory_must_be_absolute")
    elif os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        root = Path.home() / (".config" if kind == "config" else ".cache")
    return root / "scientific-evidence"


def key_path() -> Path:
    return data_dir("config") / "openalex.key"


def validate_key(value: str) -> str:
    value = value.strip()
    if not 8 <= len(value) <= 512 or any(ord(c) < 33 or ord(c) > 126 for c in value):
        raise EvidenceError("invalid_key_format", provider="openalex")
    return value


def _check_file(path: Path) -> None:
    if path.is_symlink():
        raise EvidenceError("secret_path_is_symlink")
    mode = path.stat()
    if not stat.S_ISREG(mode.st_mode) or mode.st_size > 1024:
        raise EvidenceError("invalid_secret_file")
    if os.name != "nt" and (mode.st_uid != os.getuid() or mode.st_mode & 0o077):
        raise EvidenceError("secret_file_permissions_must_be_0600")


def load_key() -> tuple[str | None, str | None]:
    # No dotenv discovery: never inspect a project or another application's secrets.
    if "OPENALEX_API_KEY" in os.environ:
        value = os.environ["OPENALEX_API_KEY"].strip()
        return (validate_key(value), "environment") if value else (None, None)
    path = key_path()
    if not path.exists() and not path.is_symlink():
        return None, None
    try:
        _check_file(path)
        value = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise EvidenceError("optional_key_unreadable", provider="openalex") from None
    return validate_key(value), "private-config"


def save_key(value: str) -> Path:
    value = validate_key(value)
    path = key_path()
    if path.exists() or path.is_symlink():
        raise EvidenceError("key_already_exists_remove_exact_stored_key_first")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise EvidenceError("secret_directory_is_symlink")
    # Publish a complete private file atomically without replacing a concurrent writer.
    descriptor, temporary = tempfile.mkstemp(prefix=".openalex-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as target:
            target.write(value + "\n")
            target.flush()
            os.fsync(target.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            raise EvidenceError("key_already_exists_remove_exact_stored_key_first") from None
    finally:
        Path(temporary).unlink(missing_ok=True)
    return path


class SameOriginRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old, new = urllib.parse.urlsplit(req.full_url), urllib.parse.urlsplit(newurl)
        if (new.scheme, new.hostname, new.port or 443) != ("https", old.hostname, old.port or 443):
            raise EvidenceError("cross_origin_redirect_blocked")
        if new.username or new.password:
            raise EvidenceError("credential_url_blocked")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def request_state_dir() -> Path:
    """Nonsecret rate timestamps belong in the host's permitted platform temp directory."""
    owner = str(os.getuid()) if hasattr(os, "getuid") else hashlib.sha256(str(Path.home()).encode()).hexdigest()[:16]
    root = Path(tempfile.gettempdir()) / ("scientific-evidence-" + owner)
    root.mkdir(mode=0o700, exist_ok=True)
    mode = root.stat()
    if root.is_symlink() or not stat.S_ISDIR(mode.st_mode):
        raise EvidenceError("unsafe_request_state_directory")
    if os.name != "nt" and (mode.st_uid != os.getuid() or mode.st_mode & 0o077):
        raise EvidenceError("unsafe_request_state_directory")
    return root


@contextmanager
def request_slot(provider: str, *, wait_limit: float = 60):
    """Cross-process one-request-at-a-time gate, held through the entire response."""
    provider = "arxiv" if provider == "arxiv-html" else provider
    interval = 3.1 if provider == "arxiv" else 1.05
    root = request_state_dir() / "requests"
    root.mkdir(mode=0o700, exist_ok=True)
    path = root / (provider + ".lock")
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "r+b", buffering=0) as target:
        deadline = time.monotonic() + wait_limit
        locked = False
        try:
            while not locked:
                try:
                    target.seek(0)
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(target.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(target, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                except (BlockingIOError, PermissionError):
                    if time.monotonic() >= deadline:
                        raise EvidenceError("provider_busy", provider=provider)
                    time.sleep(0.1)
            target.seek(0)
            try:
                previous = float(target.read(64).decode("ascii"))
            except (ValueError, UnicodeDecodeError):
                previous = 0
            # Bound wall-clock skew instead of sleeping for an arbitrary corrupt timestamp.
            delay = min(interval, max(0, interval - (time.time() - previous)))
            time.sleep(delay)
            target.seek(0)
            target.write(str(time.time()).encode("ascii"))
            target.truncate()
            yield
        finally:
            if locked:
                target.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(target.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(target, fcntl.LOCK_UN)


class HttpClient:
    def __init__(self, *, timeout: float = 20, openalex_key: str | None = None):
        self.timeout = timeout
        self.openalex_key = openalex_key
        self.requests: list[dict] = []
        self.opener = urllib.request.build_opener(SameOriginRedirect())

    def get(self, provider: str, path: str, params: dict | None = None) -> bytes:
        if provider not in ORIGINS or not path.startswith("/") or path.startswith("//"):
            raise EvidenceError("invalid_request_target")
        decoded = urllib.parse.unquote(path)
        if any(x in decoded for x in ("?", "#", "\\", "\r", "\n")) or ".." in decoded.split("/"):
            raise EvidenceError("invalid_request_path")
        params = params or {}
        if any(k.lower() in {"api_key", "key", "token", "access_token"} for k in params):
            raise EvidenceError("secrets_in_query_blocked")
        url = ORIGINS[provider] + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {"User-Agent": "yuzuru-scientific-evidence/1.0", "Accept": "application/json, application/xml, text/html"}
        if provider == "openalex":
            key = self.openalex_key or load_key()[0]
            if key:
                headers["Authorization"] = "Bearer " + key
        for attempt in range(3):
            retry_delay = 1 + attempt
            try:
                with request_slot(provider):
                    request = urllib.request.Request(url, headers=headers, method="GET")
                    with self.opener.open(request, timeout=self.timeout) as response:
                        raw = response.read(MAX_BYTES + 1)
                        if len(raw) > MAX_BYTES:
                            raise EvidenceError("response_too_large", provider=provider)
                        self.requests.append({"provider": provider, "url": url, "bytes": len(raw),
                                              "retrieved_at": datetime.now(timezone.utc).isoformat()})
                        return raw
            except urllib.error.HTTPError as exc:
                status = exc.code
                try:
                    retry_delay = min(5, max(0, float(exc.headers.get("Retry-After", retry_delay))))
                except (ValueError, TypeError):
                    pass
                exc.close()
                if status not in {429, 500, 502, 503, 504} or attempt == 2:
                    kind = "quota_or_rate_limit" if status == 429 else "upstream_http"
                    raise EvidenceError(kind, provider=provider, status=status) from None
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                if attempt == 2:
                    raise EvidenceError("network_unavailable", provider=provider) from None
            time.sleep(retry_delay)
        raise EvidenceError("network_unavailable", provider=provider)


def emit(value: dict, *, stream=None):
    import sys
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")), file=stream or sys.stdout)
