#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

TERMINAL_STATUSES = {"completed", "completed_with_errors", "failed"}
MAX_BATCH_SIZE = 32
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class ClientError(RuntimeError):
    pass


def origin(url: str) -> tuple[str, str, int | None]:
    parsed = urllib.parse.urlsplit(url)
    return parsed.scheme.lower(), (parsed.hostname or "").lower(), parsed.port


def validate_public_url(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError(f"only absolute HTTPS URLs are accepted: {url}")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"URL credentials are forbidden: {url}")
    hostname = parsed.hostname.lower()
    if hostname == "localhost" or hostname.endswith(".local"):
        raise ValueError(f"local hostnames are forbidden: {url}")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return
    if not address.is_global:
        raise ValueError(f"non-public IP literals are forbidden: {url}")


class SameOriginRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, allowed_origin: tuple[str, str, int | None]) -> None:
        super().__init__()
        self.allowed_origin = allowed_origin

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        if origin(newurl) != self.allowed_origin:
            raise ClientError("bridge attempted a cross-origin redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch allowlisted public documentation through a configured bridge."
    )
    parser.add_argument("urls", nargs="+", help="Public HTTPS documentation URLs")
    parser.add_argument(
        "--base-url",
        default=os.getenv("SKY_BRIDGE_URL", ""),
        help="Bridge coordinator URL (or SKY_BRIDGE_URL)",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("SKY_BRIDGE_TOKEN", ""),
        help="Coordinator bearer token (or SKY_BRIDGE_TOKEN)",
    )
    parser.add_argument("--output-dir", help="Destination; defaults to a temporary directory")
    parser.add_argument("--poll-interval", type=float, default=0.75)
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args()
    if not args.base_url:
        parser.error("--base-url or SKY_BRIDGE_URL is required")
    if not args.token:
        parser.error("--token or SKY_BRIDGE_TOKEN is required")
    bridge_url = urllib.parse.urlsplit(args.base_url)
    is_local_http = bridge_url.scheme == "http" and bridge_url.hostname in {
        "127.0.0.1",
        "localhost",
        "::1",
    }
    if not bridge_url.hostname or (bridge_url.scheme != "https" and not is_local_http):
        parser.error("bridge URL must use HTTPS (loopback HTTP is allowed for testing)")
    if bridge_url.username is not None or bridge_url.password is not None:
        parser.error("bridge URL credentials are forbidden")
    if args.poll_interval <= 0 or args.timeout <= 0:
        parser.error("poll interval and timeout must be positive")
    if len(args.urls) > MAX_BATCH_SIZE:
        parser.error(f"at most {MAX_BATCH_SIZE} URLs are accepted per batch")
    for url in args.urls:
        try:
            validate_public_url(url)
        except ValueError as exc:
            parser.error(str(exc))
    return args


def request(
    base_url: str,
    token: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> tuple[bytes, dict[str, str]]:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    allowed_origin = origin(base_url)
    if origin(url) != allowed_origin:
        raise ClientError("bridge returned a cross-origin artifact URL")
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Accept": "application/json, text/markdown",
        "Authorization": f"Bearer {token}",
        "User-Agent": "PublicDocsBridgeSkill/1.0",
    }
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    opener = urllib.request.build_opener(SameOriginRedirectHandler(allowed_origin))
    try:
        with opener.open(req, timeout=30) as response:
            if origin(response.geturl()) != allowed_origin:
                raise ClientError("bridge response crossed the configured origin")
            content = response.read(MAX_RESPONSE_BYTES + 1)
            if len(content) > MAX_RESPONSE_BYTES:
                raise ClientError("bridge response exceeded the 8 MiB client limit")
            return content, {
                key.lower(): value for key, value in response.headers.items()
            }
    except urllib.error.HTTPError as exc:
        detail = exc.read(4096).decode("utf-8", errors="replace")
        raise ClientError(f"bridge returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise ClientError(f"could not reach bridge: {exc.reason}") from exc


def request_json(
    base_url: str,
    token: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body, _ = request(base_url, token, path, method=method, payload=payload)
    try:
        value = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ClientError("bridge returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise ClientError("bridge returned an unexpected JSON value")
    return value


def safe_name(index: int, item: dict[str, Any]) -> str:
    host = urllib.parse.urlsplit(str(item.get("url", "documentation"))).hostname
    title = str(item.get("title") or host or "documentation")
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", title).strip("-.").lower()[:80]
    return f"{index:02d}-{slug or 'documentation'}.md"


def main() -> int:
    args = parse_args()
    output_dir = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir
        else Path(tempfile.mkdtemp(prefix="public-docs-"))
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        batch = request_json(
            args.base_url,
            args.token,
            "/v1/batches",
            method="POST",
            payload={"urls": args.urls},
        )
        batch_id = str(batch["id"])
        deadline = time.monotonic() + args.timeout
        while batch.get("status") not in TERMINAL_STATUSES:
            if time.monotonic() >= deadline:
                raise ClientError(
                    f"batch {batch_id} did not finish within {args.timeout:g}s"
                )
            time.sleep(args.poll_interval)
            batch = request_json(args.base_url, args.token, f"/v1/batches/{batch_id}")

        files: list[dict[str, str]] = []
        failed: list[dict[str, str]] = []
        for index, item in enumerate(batch.get("items", []), start=1):
            if item.get("status") != "succeeded":
                failed.append(
                    {
                        "url": str(item.get("url", "")),
                        "code": str(item.get("error_code", "unknown_error")),
                        "error": str(item.get("error", "fetch failed")),
                    }
                )
                continue
            artifact_url = str(item["artifact_url"])
            content, _ = request(args.base_url, args.token, artifact_url)
            destination = output_dir / safe_name(index, item)
            with destination.open("xb") as output:
                output.write(content)
            files.append(
                {
                    "url": str(item.get("url", "")),
                    "path": str(destination),
                    "source": str(item.get("source", "")),
                }
            )

        print(
            json.dumps(
                {
                    "batch_id": batch_id,
                    "status": batch.get("status"),
                    "output_dir": str(output_dir),
                    "files": files,
                    "failed": failed,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2 if failed else 0
    except (ClientError, KeyError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
