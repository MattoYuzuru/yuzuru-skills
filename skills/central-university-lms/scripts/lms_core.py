"""Pure validation and manifest helpers for Central University LMS."""

from __future__ import annotations

import json
import os
import urllib.parse
from pathlib import Path
from typing import Any


API_BASE = "https://my.centraluniversity.ru"
FINISHED_STATES = {
    "completed",
    "evaluated",
    "graded",
    "passed",
    "submitted",
}


class LmsError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def resolve_lms_url(value: str, *, require_api: bool = False) -> str:
    url = urllib.parse.urljoin(f"{API_BASE}/", value)
    parsed = urllib.parse.urlsplit(url)
    expected = urllib.parse.urlsplit(API_BASE)
    if parsed.scheme != "https" or parsed.netloc != expected.netloc:
        raise LmsError("invalid_target", "Only https://my.centraluniversity.ru is allowed.")
    if require_api and not parsed.path.startswith("/api/"):
        raise LmsError("invalid_target", "Only Central University /api/ endpoints are allowed.")
    if parsed.username or parsed.password or parsed.fragment:
        raise LmsError("invalid_target", "Credentials and fragments are not allowed in LMS URLs.")
    return url


def sanitized_request_url(value: str) -> str | None:
    """Keep an LMS API path and query names while dropping query values."""
    try:
        url = resolve_lms_url(value, require_api=True)
    except LmsError:
        return None
    parsed = urllib.parse.urlsplit(url)
    names = sorted({key for key, _ in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)})
    suffix = f"?{'&'.join(names)}" if names else ""
    return f"{parsed.path}{suffix}"


def redacted_shape(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): redacted_shape(child) for key, child in sorted(value.items())}
    if isinstance(value, list):
        return [redacted_shape(value[0])] if value else []
    if value is None:
        return None
    if isinstance(value, bool):
        return "<boolean>"
    if isinstance(value, (int, float)):
        return "<number>"
    return "<string>"


def is_unfinished(task: dict[str, Any]) -> bool:
    state = str(task.get("state") or "").casefold()
    if task.get("submitAt") or task.get("evaluateAt"):
        return False
    return state not in FINISHED_STATES


def validate_submission_manifest(payload: object) -> list[dict[str, str | None]]:
    if not isinstance(payload, dict):
        raise LmsError("invalid_manifest", "Submission manifest must be a JSON object.")
    if payload.get("schemaVersion") != 1:
        raise LmsError("invalid_manifest", "Submission manifest schemaVersion must be 1.")
    submissions = payload.get("submissions")
    if not isinstance(submissions, list) or not submissions:
        raise LmsError("invalid_manifest", "Submission manifest must contain a non-empty submissions array.")
    if len(submissions) > 200:
        raise LmsError("invalid_manifest", "Submission manifest is limited to 200 entries.")

    normalized: list[dict[str, str | None]] = []
    seen: set[str] = set()
    for index, item in enumerate(submissions):
        if not isinstance(item, dict):
            raise LmsError("invalid_manifest", f"submissions[{index}] must be an object.")
        task_id = str(item.get("taskId") or "").strip()
        solution_url = str(item.get("solutionUrl") or "").strip()
        if not task_id:
            raise LmsError("invalid_manifest", f"submissions[{index}].taskId is required.")
        if task_id in seen:
            raise LmsError("invalid_manifest", f"Duplicate taskId: {task_id}.")
        seen.add(task_id)
        parsed = urllib.parse.urlsplit(solution_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise LmsError(
                "invalid_manifest",
                f"submissions[{index}].solutionUrl must be an HTTPS URL without credentials.",
            )
        normalized.append(
            {
                "taskId": task_id,
                "solutionUrl": solution_url,
                "expectedState": str(item["expectedState"]) if item.get("expectedState") is not None else None,
            }
        )
    return normalized


def write_private_json(path: Path, payload: object) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
        if os.name != "nt":
            os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)
