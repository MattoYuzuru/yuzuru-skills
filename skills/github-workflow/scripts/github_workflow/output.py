"""Compact stdout/stderr envelope helpers."""

from __future__ import annotations

import json
import sys
from typing import Any

from .client import Response
from .errors import GitHubError
from .targets import RepositoryTarget


def emit_success(
    command: str,
    data: Any,
    *,
    target: RepositoryTarget | None = None,
    response: Response | None = None,
    pagination: dict[str, Any] | None = None,
) -> None:
    result = {
        "ok": True,
        "command": command,
        "target": target.as_dict() if target else None,
        "data": data,
        "pagination": pagination,
        "rate_limit": response.rate_limit if response else None,
        "partial": response.partial if response else False,
        "warnings": response.errors if response and response.errors else None,
    }
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))


def emit_error(error: GitHubError) -> None:
    print(
        json.dumps({"ok": False, "error": error.as_dict()}, ensure_ascii=False, separators=(",", ":")),
        file=sys.stderr,
    )
