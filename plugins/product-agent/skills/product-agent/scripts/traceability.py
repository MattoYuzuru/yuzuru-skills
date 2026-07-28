#!/usr/bin/env python3
"""Validate a bounded product requirements traceability document."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def analyze(document: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    requirements = document.get("requirements")
    criteria = document.get("acceptance_criteria")
    if not isinstance(requirements, list) or not isinstance(criteria, list):
        return {"ok": False, "errors": ["requirements and acceptance_criteria must be arrays"]}, False
    if len(requirements) > 500 or len(criteria) > 1000:
        return {"ok": False, "errors": ["traceability input exceeds safety limits"]}, False
    req_ids = [item.get("id") for item in requirements if isinstance(item, dict)]
    criterion_ids = [item.get("id") for item in criteria if isinstance(item, dict)]
    errors: list[str] = []
    for label, values in (("requirement", req_ids), ("criterion", criterion_ids)):
        missing = sum(not isinstance(value, str) or not value.strip() for value in values)
        if missing:
            errors.append(f"{missing} {label} IDs are missing")
        duplicates = sorted(
            key for key, count in Counter(value for value in values if isinstance(value, str)).items()
            if count > 1
        )
        errors.extend(f"duplicate {label} ID: {value}" for value in duplicates)
    known = {value for value in req_ids if isinstance(value, str)}
    mapped: Counter[str] = Counter()
    orphans: list[str] = []
    for criterion in criteria:
        if not isinstance(criterion, dict):
            errors.append("acceptance criterion must be an object")
            continue
        linked = criterion.get("requirements", [])
        if not isinstance(linked, list) or not linked:
            orphans.append(str(criterion.get("id", "<missing>")))
            continue
        for requirement_id in linked:
            if requirement_id not in known:
                errors.append(
                    f"criterion {criterion.get('id', '<missing>')} references unknown {requirement_id}"
                )
            elif isinstance(requirement_id, str):
                mapped[requirement_id] += 1
    uncovered = sorted(known - set(mapped))
    payload = {
        "ok": not errors and not orphans and not uncovered,
        "requirements": len(requirements),
        "acceptance_criteria": len(criteria),
        "uncovered_requirements": uncovered[:100],
        "unmapped_criteria": orphans[:100],
        "errors": errors[:100],
        "truncated": len(uncovered) > 100 or len(orphans) > 100 or len(errors) > 100,
    }
    return payload, payload["ok"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path, help="JSON traceability document")
    args = parser.parse_args()
    try:
        document = json.loads(args.document.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, separators=(",", ":")))
        return 2
    if not isinstance(document, dict):
        print(json.dumps({"ok": False, "error": "document must be an object"}, separators=(",", ":")))
        return 2
    payload, ok = analyze(document)
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
