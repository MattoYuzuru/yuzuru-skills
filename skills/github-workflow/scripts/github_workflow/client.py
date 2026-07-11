"""Small GitHub REST and GraphQL client with bounded retries and output."""

from __future__ import annotations

import email.utils
import json
import random
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .errors import GitHubError


RETRY_STATUSES = {408, 429, 502, 503, 504}
DEFAULT_API_VERSION = "2022-11-28"


@dataclass
class Response:
    data: Any
    status: int
    headers: dict[str, str]
    url: str
    truncated: bool = False

    @property
    def rate_limit(self) -> dict[str, Any] | None:
        values = {
            "limit": _integer(self.headers.get("x-ratelimit-limit")),
            "remaining": _integer(self.headers.get("x-ratelimit-remaining")),
            "used": _integer(self.headers.get("x-ratelimit-used")),
            "resource": self.headers.get("x-ratelimit-resource"),
            "reset_at": _epoch_iso(self.headers.get("x-ratelimit-reset")),
        }
        return values if any(value is not None for value in values.values()) else None


def _integer(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def _epoch_iso(value: str | None) -> str | None:
    number = _integer(value)
    if number is None:
        return None
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(number))


def _headers(value: Mapping[str, str] | Any) -> dict[str, str]:
    return {str(key).lower(): str(item) for key, item in value.items()}


def _json_or_text(raw: bytes) -> Any:
    if not raw:
        return None
    text = raw.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _api_message(data: Any, fallback: str) -> tuple[str, Any]:
    if isinstance(data, dict):
        message = str(data.get("message") or fallback)
        details = data.get("errors")
        return message, details
    if isinstance(data, str) and data.strip():
        return data.strip()[:1000], None
    return fallback, None


def _next_link(header: str | None) -> str | None:
    if not header:
        return None
    for part in header.split(","):
        segments = [segment.strip() for segment in part.split(";")]
        if len(segments) < 2 or segments[1] != 'rel="next"':
            continue
        if segments[0].startswith("<") and segments[0].endswith(">"):
            return segments[0][1:-1]
    return None


class GitHubClient:
    def __init__(
        self,
        *,
        token: str | None = None,
        api_url: str = "https://api.github.com",
        graphql_url: str | None = None,
        api_version: str = DEFAULT_API_VERSION,
        timeout: float = 30.0,
        retries: int = 4,
        max_wait: float = 60.0,
        max_response_bytes: int = 4 * 1024 * 1024,
        urlopen: Callable[..., Any] = urllib.request.urlopen,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        self.token = token
        self.api_url = api_url.rstrip("/")
        self.graphql_url = graphql_url or f"{self.api_url}/graphql"
        self.api_version = api_version
        self.timeout = timeout
        self.retries = max(1, retries)
        self.max_wait = max(0.0, max_wait)
        self.max_response_bytes = max_response_bytes
        self.urlopen = urlopen
        self.sleeper = sleeper
        self.clock = clock
        self.jitter = jitter

    def _url(self, path: str, query: Mapping[str, Any] | None) -> str:
        if path.startswith(("https://", "http://")):
            url = path
        else:
            url = f"{self.api_url}/{path.lstrip('/')}"
        if query:
            separator = "&" if urllib.parse.urlparse(url).query else "?"
            url += separator + urllib.parse.urlencode(query, doseq=True)
        return url

    def _request_headers(self, accept: str) -> dict[str, str]:
        headers = {
            "Accept": accept,
            "User-Agent": "yuzuru-github-workflow/1",
            "X-GitHub-Api-Version": self.api_version,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _read(self, stream: Any, limit: int) -> tuple[bytes, bool]:
        raw = stream.read(limit + 1)
        return raw[:limit], len(raw) > limit

    def _retry_delay(self, status: int | None, headers: dict[str, str], data: Any, attempt: int) -> float | None:
        retry_after = headers.get("retry-after")
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                try:
                    parsed = email.utils.parsedate_to_datetime(retry_after).timestamp()
                    return max(0.0, parsed - self.clock())
                except (TypeError, ValueError, OverflowError):
                    pass

        remaining = headers.get("x-ratelimit-remaining")
        reset = headers.get("x-ratelimit-reset")
        if remaining == "0" and reset:
            try:
                return max(0.0, float(reset) - self.clock())
            except ValueError:
                pass

        message, _ = _api_message(data, "")
        if status in {403, 429} and "secondary rate limit" in message.lower():
            return 60.0
        if status in RETRY_STATUSES or status is None:
            return min(8.0, 2.0**attempt) + min(0.25, max(0.0, self.jitter()) * 0.25)
        return None

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, Any] | None = None,
        payload: Any = None,
        accept: str = "application/vnd.github+json",
        raw: bool = False,
        max_bytes: int | None = None,
        retry_safe: bool | None = None,
    ) -> Response:
        verb = method.upper()
        url = self._url(path, query)
        body = None
        headers = self._request_headers(accept)
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        safe = verb in {"GET", "HEAD"} if retry_safe is None else retry_safe
        attempts = self.retries if safe else 1
        waited = 0.0
        limit = self.max_response_bytes if max_bytes is None else max_bytes

        for attempt in range(attempts):
            request = urllib.request.Request(url, data=body, headers=headers, method=verb)
            try:
                with self.urlopen(request, timeout=self.timeout) as response:
                    raw_body, truncated = self._read(response, limit)
                    response_headers = _headers(response.headers)
                    data = raw_body if raw else _json_or_text(raw_body)
                    return Response(data, response.status, response_headers, response.geturl(), truncated)
            except urllib.error.HTTPError as exc:
                try:
                    raw_body, _ = self._read(exc, min(limit, 256 * 1024))
                    response_headers = _headers(exc.headers)
                finally:
                    exc.close()
                data = _json_or_text(raw_body)
                delay = self._retry_delay(exc.code, response_headers, data, attempt)
                if safe and delay is not None and attempt + 1 < attempts and waited + delay <= self.max_wait:
                    self.sleeper(delay)
                    waited += delay
                    continue
                message, details = _api_message(data, f"GitHub API returned HTTP {exc.code}")
                kind = "rate-limit" if delay is not None and exc.code in {403, 429} else {
                    401: "auth", 403: "permission", 404: "not-found", 422: "validation"
                }.get(exc.code, "github")
                raise GitHubError(
                    message,
                    kind=kind,
                    status=exc.code,
                    retryable=safe and delay is not None,
                    retry_after=delay,
                    details=details,
                ) from None
            except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
                delay = self._retry_delay(None, {}, None, attempt)
                if safe and delay is not None and attempt + 1 < attempts and waited + delay <= self.max_wait:
                    self.sleeper(delay)
                    waited += delay
                    continue
                reason = getattr(exc, "reason", None) or str(exc) or exc.__class__.__name__
                raise GitHubError(
                    f"GitHub API connection failed: {reason}",
                    kind="network",
                    retryable=safe,
                    retry_after=delay,
                ) from None

        raise GitHubError("GitHub request exhausted retries", kind="network", retryable=True)

    def paginate(
        self,
        path: str,
        *,
        query: Mapping[str, Any] | None = None,
        limit: int = 20,
        item_key: str | None = None,
    ) -> tuple[list[Any], Response]:
        if not 1 <= limit <= 100:
            raise GitHubError("--limit must be between 1 and 100", kind="validation")
        params = dict(query or {})
        params.setdefault("per_page", min(100, limit))
        url = path
        collected: list[Any] = []
        last: Response | None = None
        first = True

        while len(collected) < limit:
            response = self.request("GET", url, query=params if first else None)
            first = False
            last = response
            page = response.data.get(item_key) if item_key and isinstance(response.data, dict) else response.data
            if not isinstance(page, list):
                raise GitHubError("GitHub collection response is not a list", kind="github")
            collected.extend(page[: limit - len(collected)])
            next_url = _next_link(response.headers.get("link"))
            if not next_url or not page or len(collected) >= limit:
                break
            if urllib.parse.urlparse(next_url).netloc != urllib.parse.urlparse(self.api_url).netloc:
                raise GitHubError("GitHub pagination redirected to an unexpected host", kind="github")
            url = next_url

        if last is None:
            raise GitHubError("GitHub pagination returned no response", kind="github")
        return collected, last

    def graphql(self, query: str, variables: Mapping[str, Any], *, mutation: bool = False) -> Response:
        response = self.request(
            "POST",
            self.graphql_url,
            payload={"query": query, "variables": dict(variables)},
            retry_safe=not mutation,
        )
        if not isinstance(response.data, dict):
            raise GitHubError("GitHub GraphQL response is not an object", kind="graphql")
        errors = response.data.get("errors")
        data = response.data.get("data")
        if errors and data is None:
            message = str(errors[0].get("message", "GraphQL request failed")) if isinstance(errors, list) and errors else "GraphQL request failed"
            raise GitHubError(message, kind="graphql", details=errors)
        if errors:
            response.data = {"data": data, "errors": errors, "partial": True}
        else:
            response.data = data
        return response
