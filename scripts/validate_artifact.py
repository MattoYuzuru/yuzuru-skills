#!/usr/bin/env python3
"""Validate a JSON artifact against the repository's bounded shared contract subset."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {
    "artifact": ROOT / "schemas" / "artifacts" / "artifact-metadata.schema.json",
    "capability_inventory": ROOT / "schemas" / "capability-inventory.schema.json",
    "decision": ROOT / "schemas" / "artifacts" / "decision-record.schema.json",
    "work_package": ROOT / "schemas" / "artifacts" / "work-package.schema.json",
    "evidence_bundle": ROOT / "schemas" / "artifacts" / "evidence-bundle.schema.json",
}


def type_matches(value: object, expected: object) -> bool:
    names = expected if isinstance(expected, list) else [expected]
    checks = {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "boolean": lambda item: isinstance(item, bool),
        "null": lambda item: item is None,
    }
    return any(name in checks and checks[name](value) for name in names)


def validate_value(
    value: object,
    schema: dict[str, object],
    location: str,
    errors: list[str],
    root_schema: dict[str, object],
) -> None:
    reference = schema.get("$ref")
    if isinstance(reference, str) and reference.startswith("#/$defs/"):
        definition = reference.removeprefix("#/$defs/")
        definitions = root_schema.get("$defs", {})
        resolved = definitions.get(definition) if isinstance(definitions, dict) else None
        if not isinstance(resolved, dict):
            errors.append(f"{location}: unresolved schema reference {reference}")
            return
        validate_value(value, resolved, location, errors, root_schema)
        return
    expected = schema.get("type")
    if expected is not None and not type_matches(value, expected):
        errors.append(f"{location}: expected {expected}")
        return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{location}: value is not in enum")
    if isinstance(value, str):
        if len(value) < int(schema.get("minLength", 0)):
            errors.append(f"{location}: string is too short")
        if len(value) > int(schema.get("maxLength", len(value))):
            errors.append(f"{location}: string is too long")
        if isinstance(schema.get("pattern"), str) and not re.fullmatch(str(schema["pattern"]), value):
            errors.append(f"{location}: string does not match pattern")
        if schema.get("format") == "date-time":
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"{location}: invalid date-time")
            else:
                if parsed.tzinfo is None:
                    errors.append(f"{location}: date-time must include a timezone")
    if isinstance(value, list):
        if len(value) < int(schema.get("minItems", 0)):
            errors.append(f"{location}: array is too small")
        if len(value) > int(schema.get("maxItems", len(value))):
            errors.append(f"{location}: array is too large")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                validate_value(item, item_schema, f"{location}[{index}]", errors, root_schema)
    if isinstance(value, dict):
        required = schema.get("required", [])
        if isinstance(required, list):
            for key in required:
                if key not in value:
                    errors.append(f"{location}: missing {key}")
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            if schema.get("additionalProperties") is False:
                for key in value:
                    if key not in properties:
                        errors.append(f"{location}: unexpected {key}")
            for key, child in properties.items():
                if key in value and isinstance(child, dict):
                    validate_value(value[key], child, f"{location}.{key}", errors, root_schema)


def validate_document(document: object, schema: dict[str, object]) -> list[str]:
    errors: list[str] = []
    validate_value(document, schema, "$", errors, schema)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=sorted(SCHEMAS))
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        document = json.loads(args.artifact.read_text(encoding="utf-8"))
        schema = json.loads(SCHEMAS[args.kind].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    errors = validate_document(document, schema)
    payload = {"ok": not errors, "kind": args.kind, "artifact": str(args.artifact), "errors": errors}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    else:
        print(f"{'ok' if not errors else 'FAIL'} {args.artifact}")
        for error in errors:
            print(f"  error: {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
