"""Stable, sanitized error types for the GitHub helper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class GitHubError(RuntimeError):
    message: str
    kind: str = "github"
    status: int | None = None
    retryable: bool = False
    retry_after: float | None = None
    details: Any = None

    def __str__(self) -> str:
        return self.message

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "kind": self.kind,
            "status": self.status,
            "message": self.message,
            "retryable": self.retryable,
        }
        if self.retry_after is not None:
            result["retry_after"] = round(self.retry_after, 3)
        if self.details is not None:
            result["details"] = self.details
        return result
