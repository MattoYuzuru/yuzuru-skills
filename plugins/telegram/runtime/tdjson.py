#!/usr/bin/env python3
"""Official TDLib JSON C API binding with ordered receive and @extra correlation."""

from __future__ import annotations

import ctypes
import json
import os
import platform
import queue
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable


PINNED_TDLIB_COMMIT = "d1085f9cebc5a62379991ae1652673954f229c1f"
EXPECTED_TDLIB_VERSION = "1.8.67"


class TelegramError(RuntimeError):
    def __init__(self, code: str, message: str, *, details: Any = None, ambiguous: bool = False) -> None:
        super().__init__(message)
        self.code, self.message, self.details, self.ambiguous = code, message, details, ambiguous

    def as_dict(self) -> dict[str, Any]:
        error: dict[str, Any] = {"code": self.code, "message": self.message[:500]}
        if self.details is not None:
            error["details"] = self.details
        if self.ambiguous:
            error["ambiguous"] = True
        return {"ok": False, "error": error}


def platform_key() -> str:
    system = {"Darwin": "darwin", "Linux": "linux", "Windows": "windows"}.get(platform.system())
    machine = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x86_64", "AMD64": "x86_64"}.get(platform.machine())
    if not system or not machine:
        raise TelegramError("UNSUPPORTED_PLATFORM", f"unsupported platform: {platform.system()} {platform.machine()}")
    return f"{system}-{machine}"


def native_library_path(root: Path | None = None) -> Path:
    override = os.environ.get("TELEGRAM_TDJSON_LIBRARY")
    if override:
        path = Path(override).expanduser().resolve()
    else:
        base = root or Path(__file__).resolve().parent
        filename = "tdjson.dll" if platform.system() == "Windows" else "libtdjson.dylib" if platform.system() == "Darwin" else "libtdjson.so"
        path = base / "native" / platform_key() / filename
    if not path.is_file():
        raise TelegramError("NATIVE_RUNTIME_UNAVAILABLE", f"packaged TDLib runtime is unavailable for {platform_key()}")
    return path


class TdJson:
    def __init__(self, library: Path | None = None, receive_timeout: float = 0.25) -> None:
        try:
            self.lib = ctypes.CDLL(str(library or native_library_path()))
        except OSError as exc:
            raise TelegramError("NATIVE_RUNTIME_UNAVAILABLE", "failed to load packaged TDLib runtime") from exc
        self.lib.td_create_client_id.restype = ctypes.c_int
        self.lib.td_send.argtypes = [ctypes.c_int, ctypes.c_char_p]
        self.lib.td_receive.argtypes = [ctypes.c_double]
        self.lib.td_receive.restype = ctypes.c_char_p
        self.lib.td_execute.argtypes = [ctypes.c_char_p]
        self.lib.td_execute.restype = ctypes.c_char_p
        self.lib.td_execute(self._json_bytes({"@type": "setLogVerbosityLevel", "new_verbosity_level": 1}))
        self.client_id = int(self.lib.td_create_client_id())
        self.receive_timeout = receive_timeout
        self.pending: dict[str, queue.Queue[dict[str, Any]]] = {}
        self.updates: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=2000)
        self.closed = threading.Event()
        self.thread = threading.Thread(target=self._receive_loop, name="tdlib-receive", daemon=True)
        self.thread.start()

    @staticmethod
    def _json_bytes(value: dict[str, Any]) -> bytes:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    def execute(self, request: dict[str, Any]) -> dict[str, Any]:
        raw = self.lib.td_execute(self._json_bytes(request))
        return json.loads(raw.decode("utf-8")) if raw else {}

    def _receive_loop(self) -> None:
        while not self.closed.is_set():
            raw = self.lib.td_receive(self.receive_timeout)
            if not raw:
                continue
            try:
                value = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            extra = value.get("@extra")
            waiter = self.pending.get(str(extra)) if extra is not None else None
            if waiter is not None:
                waiter.put(value)
            else:
                try:
                    self.updates.put_nowait(value)
                except queue.Full:
                    try:
                        self.updates.get_nowait()
                    except queue.Empty:
                        pass
                    self.updates.put_nowait(value)

    def request(self, request: dict[str, Any], timeout: float = 30.0, *, mutation: bool = False) -> dict[str, Any]:
        extra = uuid.uuid4().hex
        payload = dict(request)
        payload["@extra"] = extra
        waiter: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1)
        self.pending[extra] = waiter
        self.lib.td_send(self.client_id, self._json_bytes(payload))
        try:
            response = waiter.get(timeout=min(max(timeout, 1.0), 60.0))
        except queue.Empty as exc:
            code = "AMBIGUOUS_MUTATION" if mutation else "TIMEOUT"
            raise TelegramError(code, "TDLib request timed out", ambiguous=mutation) from exc
        finally:
            self.pending.pop(extra, None)
        if response.get("@type") == "error":
            provider_code = int(response.get("code") or 0)
            message = "TDLib returned a sensitive error" if provider_code == 406 else str(response.get("message") or "TDLib error")[:300]
            code = map_error(provider_code, message)
            raise TelegramError(code, message, details={"provider_code": provider_code})
        return response

    def wait_update(self, predicate: Callable[[dict[str, Any]], bool], timeout: float = 30.0) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        deferred: list[dict[str, Any]] = []
        try:
            while time.monotonic() < deadline:
                try:
                    update = self.updates.get(timeout=min(0.5, deadline - time.monotonic()))
                except queue.Empty:
                    continue
                if predicate(update):
                    return update
                deferred.append(update)
        finally:
            for update in deferred:
                try:
                    self.updates.put_nowait(update)
                except queue.Full:
                    break
        raise TelegramError("AMBIGUOUS_MUTATION", "TDLib did not confirm the final mutation state", ambiguous=True)

    def close(self) -> None:
        if self.closed.is_set():
            return
        try:
            self.request({"@type": "close"}, timeout=10)
            self.wait_update(
                lambda item: item.get("@type") == "updateAuthorizationState"
                and (item.get("authorization_state") or {}).get("@type") == "authorizationStateClosed",
                timeout=10,
            )
        except TelegramError:
            pass
        self.closed.set()
        self.thread.join(timeout=2)


def map_error(code: int, message: str) -> str:
    folded = message.casefold()
    if code == 401:
        return "AUTH_REVOKED"
    if code == 429:
        return "RATE_LIMITED"
    if code == 404:
        return "NOT_FOUND"
    if "privacy" in folded or "not mutual" in folded:
        return "PRIVACY_RESTRICTED"
    if "premium" in folded:
        return "PREMIUM_REQUIRED"
    if code == 400:
        return "INVALID_ARGUMENT"
    if code == 403:
        return "PERMISSION_DENIED"
    return "PROVIDER_UNAVAILABLE"
