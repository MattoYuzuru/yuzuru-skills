#!/usr/bin/env python3
"""Validate and summarize a bounded discovery evidence ledger."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REQUIRED = ("id", "source", "claim", "confidence", "kind")
CONFIDENCE = {"high", "medium", "low"}
KINDS = {"fact", "reported-experience", "inference"}


def load(path: Path) -> list[dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc
    if not isinstance(value, list):
        raise ValueError("ledger must be a JSON array")
    if len(value) > 500:
        raise ValueError("ledger exceeds the 500-entry safety limit")
    if not all(isinstance(item, dict) for item in value):
        raise ValueError("every ledger entry must be an object")
    return value


def summarize(entries: list[dict[str, Any]]) -> tuple[dict[str, Any], bool]:
    errors: list[str] = []
    ids: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    confidence: Counter[str] = Counter()
    kinds: Counter[str] = Counter()
    geographies: Counter[str] = Counter()
    for index, entry in enumerate(entries):
        missing = [key for key in REQUIRED if not isinstance(entry.get(key), str) or not entry[key].strip()]
        if missing:
            errors.append(f"entry {index}: missing {', '.join(missing)}")
            continue
        ids[entry["id"].strip()] += 1
        sources[entry["source"].strip()] += 1
        confidence[entry["confidence"]] += 1
        kinds[entry["kind"]] += 1
        geography = entry.get("geography", "unspecified")
        if isinstance(geography, str):
            geographies[geography or "unspecified"] += 1
        if entry["confidence"] not in CONFIDENCE:
            errors.append(f"entry {index}: unsupported confidence {entry['confidence']!r}")
        if entry["kind"] not in KINDS:
            errors.append(f"entry {index}: unsupported kind {entry['kind']!r}")
    duplicate_ids = sorted(key for key, count in ids.items() if count > 1)
    duplicate_sources = sorted(key for key, count in sources.items() if count > 1)
    errors.extend(f"duplicate id: {value}" for value in duplicate_ids)
    return (
        {
            "ok": not errors,
            "entries": len(entries),
            "confidence": dict(sorted(confidence.items())),
            "kinds": dict(sorted(kinds.items())),
            "geographies": dict(geographies.most_common(20)),
            "duplicate_sources": duplicate_sources[:50],
            "errors": errors[:100],
            "truncated": len(errors) > 100 or len(duplicate_sources) > 50,
        },
        not errors,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path, help="JSON array of evidence entries")
    args = parser.parse_args()
    try:
        payload, ok = summarize(load(args.ledger))
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, separators=(",", ":")))
        return 2
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
