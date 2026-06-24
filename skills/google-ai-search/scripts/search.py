#!/usr/bin/env python3
"""Run a compact Google AI Mode search through Playwright."""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse


def clean_text(text: str, max_chars: int) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def parse_sources(items: list[dict[str, str]]) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    seen: set[str] = set()
    blocked_hosts = ("google.", "gstatic.", "googleusercontent.", "accounts.google.")

    for item in items:
        href = item.get("href", "")
        title = clean_text(item.get("title", ""), 160)
        if not href.startswith("http"):
            continue
        host = urllib.parse.urlparse(href).netloc.lower()
        if any(part in host for part in blocked_hosts):
            continue
        if href in seen:
            continue
        seen.add(href)
        sources.append({"title": title or href, "url": href})
        if len(sources) >= 10:
            break
    return sources


def run(args: argparse.Namespace) -> dict[str, object]:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "query": args.query,
            "answer": "",
            "sources": [],
            "error": "Playwright is not installed. Run: python3 -m pip install playwright && python3 -m playwright install chromium",
        }

    url = "https://www.google.com/search?" + urllib.parse.urlencode(
        {"q": args.query, "udm": "50", "hl": args.lang}
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=args.timeout)
            page.wait_for_timeout(args.settle_ms)
            body_text = page.locator("body").inner_text(timeout=args.timeout)
            anchors = page.eval_on_selector_all(
                "a[href]",
                """els => els.map(a => ({
                    title: (a.innerText || a.getAttribute('aria-label') || '').trim(),
                    href: a.href
                }))""",
            )
        except PlaywrightTimeoutError as exc:
            browser.close()
            return {"query": args.query, "answer": "", "sources": [], "error": f"Google page timeout: {exc}"}
        finally:
            if not page.is_closed():
                page.close()
            browser.close()

    answer = clean_text(body_text, args.max_chars)
    result: dict[str, object] = {"query": args.query, "answer": answer}
    result["sources"] = parse_sources(anchors) if args.include_sources else []
    if "captcha" in answer.lower() or "unusual traffic" in answer.lower():
        result["error"] = "Google may have blocked the request with CAPTCHA or unusual-traffic protection."
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Token-efficient Google AI Mode search")
    parser.add_argument("--query", "-q", required=True)
    parser.add_argument("--lang", "-l", default="en")
    parser.add_argument("--max-chars", type=int, default=4000)
    parser.add_argument("--include-sources", "-s", action="store_true")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--timeout", type=int, default=25000)
    parser.add_argument("--settle-ms", type=int, default=3000)
    args = parser.parse_args()

    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get("error") else 0


if __name__ == "__main__":
    raise SystemExit(main())

