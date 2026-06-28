#!/usr/bin/env python3
"""Run grounded web research through the Gemini API."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from api_config import AI_STUDIO_KEY_URL, DEFAULT_MODEL, key_path, load_api_key


API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"


def clean_text(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def parse_sources(metadata: dict[str, Any]) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    seen: set[str] = set()
    for chunk in metadata.get("groundingChunks", []):
        web = chunk.get("web", {})
        url = web.get("uri", "")
        if not url or url in seen:
            continue
        seen.add(url)
        sources.append({"title": web.get("title") or url, "url": url})
    return sources


def parse_response(payload: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    candidates = payload.get("candidates", [])
    if not candidates:
        feedback = payload.get("promptFeedback", {})
        return {
            "query": args.query,
            "answer": "",
            "sources": [],
            "error": f"Gemini returned no candidates: {feedback or 'unknown reason'}",
        }

    candidate = candidates[0]
    parts = candidate.get("content", {}).get("parts", [])
    answer = "\n".join(part.get("text", "") for part in parts if part.get("text")).strip()
    metadata = candidate.get("groundingMetadata", {})
    result: dict[str, Any] = {
        "query": args.query,
        "answer": clean_text(answer, args.max_chars),
        "model": args.model,
        "search_queries": metadata.get("webSearchQueries", []),
        "sources": parse_sources(metadata) if args.include_sources else [],
    }
    if payload.get("usageMetadata"):
        result["usage"] = payload["usageMetadata"]
    if not answer:
        result["error"] = "Gemini returned an empty answer."
    return result


def api_error_message(error: urllib.error.HTTPError) -> str:
    try:
        payload = json.loads(error.read().decode("utf-8"))
        return payload.get("error", {}).get("message") or str(error)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return str(error)


def run(args: argparse.Namespace) -> dict[str, Any]:
    api_key, _ = load_api_key()
    if not api_key:
        return {
            "query": args.query,
            "answer": "",
            "sources": [],
            "error": "Gemini API key is not configured.",
            "setup_url": AI_STUDIO_KEY_URL,
            "config_path": str(key_path()),
        }

    prompt = (
        f"Research the following query with Google Search. Answer concisely in language code {args.lang}. "
        "Prefer primary and authoritative sources, distinguish facts from inference, and do not invent citations.\n\n"
        f"Query: {args.query}"
    )
    request_body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": args.max_output_tokens},
    }
    url = f"{API_ROOT}/{urllib.parse.quote(args.model, safe='')}:generateContent"
    request = urllib.request.Request(
        url,
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "yuzuru-google-ai-search/2",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        message = api_error_message(exc)
        if exc.code == 429:
            message = f"Free-tier quota or rate limit reached: {message}"
        return {"query": args.query, "answer": "", "sources": [], "error": message}
    except urllib.error.URLError as exc:
        return {"query": args.query, "answer": "", "sources": [], "error": str(exc.reason)}
    except (TimeoutError, json.JSONDecodeError) as exc:
        return {"query": args.query, "answer": "", "sources": [], "error": str(exc)}

    return parse_response(payload, args)


def main() -> int:
    parser = argparse.ArgumentParser(description="Grounded Google web research through Gemini API")
    parser.add_argument("--query", "-q", required=True)
    parser.add_argument("--lang", "-l", default="en")
    parser.add_argument("--model", default=os.environ.get("GOOGLE_AI_SEARCH_MODEL", DEFAULT_MODEL))
    parser.add_argument("--max-chars", type=int, default=5000)
    parser.add_argument("--max-output-tokens", type=int, default=2048)
    parser.add_argument("--include-sources", "-s", action="store_true")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get("error") else 0


if __name__ == "__main__":
    raise SystemExit(main())
