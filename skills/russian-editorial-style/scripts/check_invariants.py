#!/usr/bin/env python3
"""Compare protected textual artifacts before and after a Russian edit."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Pattern


MONTHS = (
    "января|февраля|марта|апреля|мая|июня|июля|августа|"
    "сентября|октября|ноября|декабря"
)
PATTERNS: dict[str, Pattern[str]] = {
    "dates": re.compile(
        rf"(?<!\w)(?:\d{{4}}[-./]\d{{1,2}}[-./]\d{{1,2}}|"
        rf"\d{{1,2}}[-./]\d{{1,2}}[-./]\d{{2,4}}|"
        rf"\d{{1,2}}\s+(?:{MONTHS})(?:\s+\d{{4}}(?:\s*г\.?)?)?)(?!\w)",
        re.IGNORECASE,
    ),
    "numbers": re.compile(
        r"(?<![\w])(?:v|версия\s*)?\d+(?:[.,]\d+)*(?:\s*[–—-]\s*\d+(?:[.,]\d+)*)?"
        r"(?:\s*(?:%|₽|\$|€|руб\.?|коп\.?|мс|сек\.?|мин\.?|ч(?:ас(?:а|ов)?)?|"
        r"дн(?:я|ей)?|байт|КБ|МБ|ГБ|ТБ|кбит/с|Мбит/с|Гбит/с|мм|см|км|м|кг|г))?(?![\w])",
        re.IGNORECASE,
    ),
    "urls": re.compile(r"https?://[^\s<>()\[\]{}\"'«»]+(?<![.,;:!?])", re.IGNORECASE),
    "emails": re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-zА-Яа-яЁё]{2,}(?![\w.-])"),
    "fenced_code": re.compile(r"```[^\n]*\n.*?```", re.DOTALL),
    "inline_code": re.compile(r"(?<!`)`[^`\n]+`(?!`)"),
    "quotes": re.compile(r"«[^»\n]+»|“[^”\n]+”|(?<!\w)\"[^\"\n]+\""),
}
NEGATIONS = re.compile(r"\b(?:не|ни|нет|нельзя|без|никогда|никто|ничто)\b", re.IGNORECASE)


def read_text(value: str) -> str:
    if value == "-":
        return sys.stdin.read()
    try:
        return Path(value).expanduser().read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read {value}: {exc}") from exc


def counter(pattern: Pattern[str], text: str) -> Counter[str]:
    return Counter(match.group(0) for match in pattern.finditer(text))


def delta(pattern: Pattern[str], source: str, revision: str) -> dict[str, dict[str, int]]:
    before = counter(pattern, source)
    after = counter(pattern, revision)
    removed = before - after
    added = after - before
    return {
        "removed": dict(sorted(removed.items())),
        "added": dict(sorted(added.items())),
    }


def inspect(source: str, revision: str, terms: list[str]) -> dict[str, object]:
    changes = {name: delta(pattern, source, revision) for name, pattern in PATTERNS.items()}
    violations = [
        name for name, change in changes.items()
        if change["removed"] or change["added"]
    ]
    missing_terms = [term for term in terms if term and source.count(term) > revision.count(term)]
    if missing_terms:
        violations.append("protected_terms")

    before_negations = counter(NEGATIONS, source)
    after_negations = counter(NEGATIONS, revision)
    negation_changed = before_negations != after_negations
    warnings = []
    if negation_changed:
        warnings.append("Negation markers changed; inspect scope and meaning manually.")

    return {
        "ok": not violations,
        "violations": violations,
        "changes": changes,
        "protected_terms": {"missing": missing_terms},
        "negation": {
            "changed": negation_changed,
            "before": dict(sorted(before_negations.items())),
            "after": dict(sorted(after_negations.items())),
        },
        "warnings": warnings,
        "limitations": [
            "Artifact equality does not prove semantic preservation.",
            "Review causality, modality, attribution, and conditions manually.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare numbers, dates, links, code, quotations, negation markers, and protected terms."
    )
    parser.add_argument("source", help="UTF-8 source file")
    parser.add_argument("revision", help="UTF-8 revision file")
    parser.add_argument("--term", action="append", default=[], help="exact protected term; repeat as needed")
    parser.add_argument("--pretty", action="store_true", help="indent JSON output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.source == "-" and args.revision == "-":
        print(json.dumps({"ok": False, "error": "only one input may use stdin"}), file=sys.stderr)
        return 2
    try:
        result = inspect(read_text(args.source), read_text(args.revision), args.term)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
