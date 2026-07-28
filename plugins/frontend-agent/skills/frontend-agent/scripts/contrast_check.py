#!/usr/bin/env python3
"""Calculate WCAG contrast ratios for bounded foreground/background color pairs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")


def luminance(color: str) -> float:
    match = HEX_RE.fullmatch(color)
    if not match:
        raise ValueError(f"invalid six-digit hex color: {color}")
    raw = match.group(1)
    channels = [int(raw[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def ratio(foreground: str, background: str) -> float:
    values = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (values[0] + 0.05) / (values[1] + 0.05)


def evaluate(pairs: list[dict[str, object]]) -> tuple[dict[str, object], bool]:
    if len(pairs) > 500:
        return {"ok": False, "error": "input exceeds 500 color pairs"}, False
    results = []
    errors = []
    for index, pair in enumerate(pairs):
        if not isinstance(pair, dict):
            errors.append(f"pair {index} must be an object")
            continue
        foreground = pair.get("foreground")
        background = pair.get("background")
        if not isinstance(foreground, str) or not isinstance(background, str):
            errors.append(f"pair {index} requires foreground and background")
            continue
        try:
            value = ratio(foreground, background)
        except ValueError as exc:
            errors.append(f"pair {index}: {exc}")
            continue
        results.append(
            {
                "id": pair.get("id", str(index)),
                "foreground": foreground,
                "background": background,
                "ratio": round(value, 3),
                "aa_normal": value >= 4.5,
                "aa_large": value >= 3,
                "aaa_normal": value >= 7,
            }
        )
    return {"ok": not errors, "results": results, "errors": errors[:100]}, not errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pairs", type=Path, help="JSON array with foreground/background hex colors")
    args = parser.parse_args()
    try:
        value = json.loads(args.pairs.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, separators=(",", ":")))
        return 2
    if not isinstance(value, list):
        print(json.dumps({"ok": False, "error": "input must be an array"}, separators=(",", ":")))
        return 2
    payload, ok = evaluate(value)
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
