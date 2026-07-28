#!/usr/bin/env python3
"""Validate bounded SRE finding classification and confirmation evidence."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


CLASSIFICATIONS = {
    "confirmed-defect",
    "probable-defect",
    "design-risk",
    "missing-evidence",
    "documentation-inconsistency",
    "intentional-behavior",
    "unverified-hypothesis",
}
CONFIRMED_FIELDS = (
    "severity",
    "requirement",
    "component",
    "location",
    "preconditions",
    "reproduction",
    "expected",
    "actual",
    "evidence",
    "impact",
    "confidence",
    "suggested_correction",
    "regression_test",
)


def present(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    return value is not None


def validate(document: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    findings = document.get("findings")
    if not isinstance(findings, list):
        return {"ok": False, "errors": ["findings must be an array"]}, False
    if len(findings) > 500:
        return {"ok": False, "errors": ["findings exceeds 500 entries"]}, False
    errors: list[str] = []
    ids: Counter[str] = Counter()
    classes: Counter[str] = Counter()
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            errors.append(f"finding {index} must be an object")
            continue
        identifier = finding.get("id")
        classification = finding.get("classification")
        if not isinstance(identifier, str) or not identifier.strip():
            errors.append(f"finding {index} missing id")
        else:
            ids[identifier] += 1
        if classification not in CLASSIFICATIONS:
            errors.append(f"finding {identifier or index} invalid classification")
            continue
        classes[classification] += 1
        if classification == "confirmed-defect":
            missing = [field for field in CONFIRMED_FIELDS if not present(finding.get(field))]
            if missing:
                errors.append(f"finding {identifier or index} confirmed without {', '.join(missing)}")
    errors.extend(f"duplicate finding id: {key}" for key, count in ids.items() if count > 1)
    payload = {
        "ok": not errors,
        "findings": len(findings),
        "classifications": dict(sorted(classes.items())),
        "errors": errors[:100],
        "truncated": len(errors) > 100,
    }
    return payload, not errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        document = json.loads(args.report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, separators=(",", ":")))
        return 2
    if not isinstance(document, dict):
        print(json.dumps({"ok": False, "error": "report must be an object"}, separators=(",", ":")))
        return 2
    payload, ok = validate(document)
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
