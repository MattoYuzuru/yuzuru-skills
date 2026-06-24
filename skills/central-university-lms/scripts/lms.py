#!/usr/bin/env python3
"""Read-only Central University LMS helper."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any


DEFAULT_URL = "https://my.centraluniversity.ru/learn/courses/view/actual/all"
DEFAULT_STATE = Path("~/.config/yuzuru-codex-skills/central-university-lms/storage-state.json").expanduser()
DEADLINE_RE = re.compile(
    r"(?i)(дедлайн|deadline|домаш|homework|assignment|задани|сдать|до\s+\d{1,2}[./]\d{1,2}|"
    r"\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?)"
)


def ensure_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is not installed. Run: python3 -m pip install playwright && python3 -m playwright install chromium"
        ) from exc
    return sync_playwright


def state_path(value: str | None) -> Path:
    return Path(value).expanduser() if value else DEFAULT_STATE


def print_json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def login(args: argparse.Namespace) -> int:
    sync_playwright = ensure_playwright()
    storage = state_path(args.storage_state)
    storage.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(args.url, wait_until="domcontentloaded", timeout=args.timeout)
        print("Log in to Central University LMS in the opened browser window.")
        print("After the courses page is visible, return here and press Enter.")
        input()
        context.storage_state(path=str(storage))
        browser.close()

    os.chmod(storage, 0o600)
    print_json({"status": "saved", "storage_state": str(storage)})
    return 0


def context_with_state(p: Any, args: argparse.Namespace):
    storage = state_path(args.storage_state)
    if not storage.exists():
        raise RuntimeError(f"Storage state not found: {storage}. Run login first.")
    browser = p.chromium.launch(headless=args.headless)
    context = browser.new_context(storage_state=str(storage))
    return browser, context


def extract_snapshot(page: Any) -> dict[str, object]:
    return page.evaluate(
        """() => {
            const clean = s => (s || '').replace(/\\s+/g, ' ').trim();
            const links = [...document.querySelectorAll('a[href]')]
                .map(a => ({ text: clean(a.innerText), href: a.href }))
                .filter(x => x.text.length > 0)
                .slice(0, 300);
            const blocks = [...document.querySelectorAll('article, li, tr, section, div')]
                .map((el, index) => ({ index, text: clean(el.innerText), href: el.querySelector('a[href]')?.href || '' }))
                .filter(x => x.text.length >= 8 && x.text.length <= 1500)
                .slice(0, 500);
            return {
                title: document.title,
                url: location.href,
                links,
                blocks
            };
        }"""
    )


def snapshot(args: argparse.Namespace) -> int:
    sync_playwright = ensure_playwright()
    with sync_playwright() as p:
        browser, context = context_with_state(p, args)
        page = context.new_page()
        page.goto(args.url, wait_until="networkidle", timeout=args.timeout)
        data = extract_snapshot(page)
        browser.close()
    print_json(data)
    return 0


def deadlines(args: argparse.Namespace) -> int:
    sync_playwright = ensure_playwright()
    with sync_playwright() as p:
        browser, context = context_with_state(p, args)
        page = context.new_page()
        page.goto(args.url, wait_until="networkidle", timeout=args.timeout)
        data = extract_snapshot(page)
        browser.close()

    matches = []
    seen = set()
    for block in data.get("blocks", []):
        text = block.get("text", "")
        if not DEADLINE_RE.search(text):
            continue
        key = text[:240]
        if key in seen:
            continue
        seen.add(key)
        matches.append(
            {
                "text": text,
                "url": block.get("href") or data.get("url"),
                "inferred": True,
            }
        )
        if len(matches) >= args.limit:
            break

    print_json({"url": data.get("url"), "matches": matches})
    return 0


def discover_api(args: argparse.Namespace) -> int:
    sync_playwright = ensure_playwright()
    observed: list[dict[str, object]] = []

    with sync_playwright() as p:
        browser, context = context_with_state(p, args)
        page = context.new_page()

        def on_request(request: Any) -> None:
            if request.resource_type in {"xhr", "fetch"}:
                observed.append({"method": request.method, "url": request.url, "type": request.resource_type})

        page.on("request", on_request)
        page.goto(args.url, wait_until="domcontentloaded", timeout=args.timeout)
        page.wait_for_timeout(args.seconds * 1000)
        browser.close()

    deduped = []
    seen = set()
    for item in observed:
        key = (item["method"], item["url"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    print_json({"url": args.url, "requests": deduped})
    return 0


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--storage-state")
    parser.add_argument("--timeout", type=int, default=30000)
    parser.add_argument("--headless", action="store_true")


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Central University LMS helper")
    sub = parser.add_subparsers(dest="command", required=True)

    login_parser = sub.add_parser("login")
    add_common(login_parser)

    snapshot_parser = sub.add_parser("snapshot")
    add_common(snapshot_parser)

    deadlines_parser = sub.add_parser("deadlines")
    add_common(deadlines_parser)
    deadlines_parser.add_argument("--limit", type=int, default=50)

    discover_parser = sub.add_parser("discover-api")
    add_common(discover_parser)
    discover_parser.add_argument("--seconds", type=int, default=20)

    args = parser.parse_args()
    try:
        if args.command == "login":
            return login(args)
        if args.command == "snapshot":
            return snapshot(args)
        if args.command == "deadlines":
            return deadlines(args)
        if args.command == "discover-api":
            return discover_api(args)
    except Exception as exc:
        print_json({"error": str(exc)})
        return 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())

