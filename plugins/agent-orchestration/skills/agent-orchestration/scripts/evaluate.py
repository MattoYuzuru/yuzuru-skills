#!/usr/bin/env python3
"""Validate or descriptively summarize bounded orchestration runs; no model calls or writes."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import re
import statistics
import sys


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "references" / "run-results.schema.json"
MAX_BYTES = 2_000_000
MAX_ERRORS = 30
ARMS = ("single", "fixed", "adaptive")


class InvalidResults(ValueError):
    """A bounded, safe diagnostic for invalid input."""


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise InvalidResults("duplicate object key")
        value[key] = item
    return value


def reject_constant(_value):
    raise InvalidResults("non-finite JSON number")


def read_results(path):
    try:
        with Path(path).open("rb") as stream:
            payload = stream.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            raise InvalidResults("input exceeds byte limit")
        return json.loads(payload.decode("utf-8"), object_pairs_hook=unique_object,
                          parse_constant=reject_constant)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        if isinstance(exc, InvalidResults):
            raise
        raise InvalidResults("cannot read bounded UTF-8 JSON input") from exc


def validate_results(value):
    """Validate the shipped schema subset, then cross-record identity constraints."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = []

    def error(location, message):
        if len(errors) < MAX_ERRORS:
            errors.append({"location": location, "message": message})

    def visit(item, rule, location):
        if len(errors) >= MAX_ERRORS:
            return
        if "$ref" in rule:
            rule = schema["$defs"][rule["$ref"].split("/")[-1]]
        kinds = rule.get("type", [])
        kinds = [kinds] if isinstance(kinds, str) else kinds
        matches = {
            "object": isinstance(item, dict),
            "array": isinstance(item, list),
            "string": isinstance(item, str),
            "integer": isinstance(item, int) and not isinstance(item, bool),
            "number": isinstance(item, (int, float)) and not isinstance(item, bool),
            "null": item is None,
        }
        if kinds and not any(matches.get(kind, False) for kind in kinds):
            error(location, "unexpected type")
            return
        if "enum" in rule and item not in rule["enum"]:
            error(location, "value outside allowed choices")
        if isinstance(item, (int, float)) and not isinstance(item, bool):
            if isinstance(item, float) and not math.isfinite(item):
                error(location, "non-finite number")
            elif item < rule.get("minimum", item) or item > rule.get("maximum", item):
                error(location, "number outside allowed bounds")
        if isinstance(item, str):
            if not rule.get("minLength", 0) <= len(item) <= rule.get("maxLength", len(item)):
                error(location, "string outside allowed length")
            if "pattern" in rule and re.search(rule["pattern"], item) is None:
                error(location, "string does not match allowed pattern")
        if isinstance(item, list):
            if not rule.get("minItems", 0) <= len(item) <= rule.get("maxItems", len(item)):
                error(location, "array outside allowed bounds")
                return
            for index, child in enumerate(item):
                visit(child, rule.get("items", {}), location + "[" + str(index) + "]")
        if isinstance(item, dict):
            properties = rule.get("properties", {})
            if rule.get("additionalProperties") is False and set(item) - set(properties):
                error(location, "unknown object fields")
            for key in rule.get("required", []):
                if key not in item:
                    error(location, "required field missing: " + key)
            for key, child_rule in properties.items():
                if key in item:
                    visit(item[key], child_rule, location + "." + key)

    visit(value, schema, "$")
    if errors:
        return errors
    seen_ids, seen_cells = set(), set()
    for index, run in enumerate(value["runs"]):
        identity = (run["case_id"], run["arm"], run["repetition"])
        if run["id"] in seen_ids:
            error("$.runs[" + str(index) + "]", "duplicate run ID")
        if identity in seen_cells:
            error("$.runs[" + str(index) + "]", "duplicate case/arm/repetition")
        seen_ids.add(run["id"])
        seen_cells.add(identity)
    return errors


def nullable_metric(runs, field):
    values = [run[field] for run in runs if run[field] is not None]
    missing = len(runs) - len(values)
    known = sum(values)
    return {"total": None if missing else known, "known_subtotal": known, "missing_runs": missing}


def summarize(value, limit=20):
    """Describe observations without ranking arms or inferring a causal benefit."""
    by_arm = defaultdict(list)
    cells = defaultdict(list)
    for run in value["runs"]:
        by_arm[run["arm"]].append(run)
        cells[(run["case_id"], run["repetition"])].append(run)
    summaries = []
    for arm in ARMS:
        runs = by_arm.get(arm, [])
        if not runs:
            continue
        accepted = [run for run in runs if run["outcome"] == "accepted"]
        api = nullable_metric(runs, "api_cost_usd")
        native = defaultdict(list)
        missing_native = 0
        for run in runs:
            usage = run.get("native_usage")
            if usage is None:
                missing_native += 1
            else:
                native[usage["unit"]].append(usage["value"])
        all_native_known = missing_native == 0 and len(native) == 1
        summaries.append({
            "arm": arm, "attempts": len(runs), "accepted": len(accepted),
            "failed": sum(run["outcome"] == "failed" for run in runs),
            "timeouts": sum(run["outcome"] == "timeout" for run in runs),
            "acceptance_rate": len(accepted) / len(runs),
            "all_attempt_wall_seconds": sum(run["wall_seconds"] for run in runs),
            "median_accepted_wall_seconds": statistics.median(
                run["wall_seconds"] for run in accepted) if accepted else None,
            "tokens": nullable_metric(runs, "tokens"), "api_cost_usd": api,
            "api_cost_per_accepted": api["total"] / len(accepted)
            if api["total"] is not None and accepted else None,
            "native_usage": {
                "total": {"unit": next(iter(native)), "value": sum(next(iter(native.values())))}
                if all_native_known else None,
                "known_by_unit": [{"unit": unit, "known_subtotal": sum(values),
                                   "observed_runs": len(values)}
                                  for unit, values in sorted(native.items())][:limit],
                "units_total": len(native), "units_truncated": len(native) > limit,
                "missing_runs": missing_native,
            },
        })
    issues = []
    counts = defaultdict(int)
    varying_configurations = 0

    def issue(case_id, repetition, kind, detail=None):
        counts[kind] += 1
        if len(issues) < limit:
            item = {"case_id": case_id, "repetition": repetition, "kind": kind}
            if detail is not None:
                item["missing_arms"] = detail
            issues.append(item)

    for (case_id, repetition), runs in sorted(cells.items()):
        missing = sorted(set(ARMS) - {run["arm"] for run in runs})
        if missing:
            issue(case_id, repetition, "missing_arms", missing)
        if len({run["revision"] for run in runs}) > 1:
            issue(case_id, repetition, "input_revision_mismatch")
        if len({run["host"] for run in runs}) > 1:
            issue(case_id, repetition, "host_mismatch")
        configurations = {(run["model"], run["effort"]) for run in runs}
        if len(configurations) > 1:
            varying_configurations += 1
            if value["study_phase"] == "orchestration":
                issue(case_id, repetition, "model_effort_mismatch")
    return {
        "ok": True, "operation": "summarize", "experiment_id": value["experiment_id"],
        "data_kind": value["data_kind"], "study_phase": value["study_phase"],
        "policy_revision": value["policy_revision"], "run_count": len(value["runs"]),
        "arms": summaries,
        "comparability": {
            "structurally_comparable": not counts, "case_repetitions": len(cells),
            "issue_counts": dict(sorted(counts.items())), "issues": issues,
            "issues_truncated": sum(counts.values()) > len(issues),
            "model_effort_varies_in_cells": varying_configurations,
        },
        "limitations": [
            "Descriptive statistics only; no causal winner or speedup is established.",
            "All-attempt totals include failed and timed-out runs; accepted medians condition on success.",
            "Missing metrics remain unknown; native units are never converted to tokens or API cost.",
            "Structural comparability does not establish randomization, independence, or adequate sample size.",
            "Validation checks declared records, not whether the recorded execution or acceptance evidence is true.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)
    for operation in ("validate", "summarize"):
        command = subparsers.add_parser(operation, help="Read and " + operation + " a run-results JSON file")
        command.add_argument("results", type=Path)
        command.add_argument("--limit", type=int, default=20, help="Maximum reported issues/units (1..50)")
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 50:
        parser.error("--limit must be between 1 and 50")
    try:
        value = read_results(args.results)
        errors = validate_results(value)
    except InvalidResults as exc:
        print(json.dumps({"ok": False, "error": {"kind": "invalid_input", "message": str(exc)}},
                         separators=(",", ":")), file=sys.stderr)
        return 2
    if errors:
        print(json.dumps({"ok": False, "error": {"kind": "invalid_results", "issues": errors}},
                         separators=(",", ":")), file=sys.stderr)
        return 2
    payload = summarize(value, args.limit) if args.operation == "summarize" else {
        "ok": True, "operation": "validate", "run_count": len(value["runs"]),
        "data_kind": value["data_kind"],
    }
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
