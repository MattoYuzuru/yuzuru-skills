#!/usr/bin/env python3
"""Validate implicit skill-selection cases or score externally observed runs; no model calls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "evals" / "skill-selection.json"


def validate_contract(value: object, expected_paths: set[str]) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict) or value.get("version") != 1 or not isinstance(value.get("skills"), list):
        return ["skill-selection contract needs version 1 and a skills array"]
    paths: list[str] = []
    names: list[str] = []
    for item in value["skills"]:
        if not isinstance(item, dict):
            errors.append("skill-selection entry must be an object")
            continue
        name, path = item.get("skill"), item.get("path")
        if not isinstance(name, str) or not isinstance(path, str) or Path(path).parent.name != name:
            errors.append("skill-selection identity/path mismatch")
            continue
        paths.append(path)
        names.append(name)
        if item.get("status") not in {"active", "deferred"}:
            errors.append(f"{name}: status must be active or deferred")
        examples = {}
        for key in ("should_trigger", "should_not_trigger", "expectations"):
            items = item.get(key)
            minimum = 1 if key == "expectations" else 2
            if not isinstance(items, list) or len(items) < minimum or not all(
                    isinstance(s, str) and s.strip() for s in items):
                errors.append(f"{name}: {key} needs {minimum}+ non-empty strings")
                continue
            normalized = [" ".join(s.casefold().split()) for s in items]
            if len(set(normalized)) != len(normalized):
                errors.append(f"{name}: duplicate {key} example")
            examples[key] = set(normalized)
        if examples.get("should_trigger", set()) & examples.get("should_not_trigger", set()):
            errors.append(f"{name}: positive and negative cases overlap")
    if len(set(names)) != len(names) or len(set(paths)) != len(paths):
        errors.append("skill-selection entries must be unique")
    if set(paths) != expected_paths:
        errors.append(f"skill-selection coverage drift: missing={sorted(expected_paths - set(paths))}; "
                      f"unknown={sorted(set(paths) - expected_paths)}")
    return errors


def cases(value: dict, skill: str | None = None) -> list[dict]:
    result = []
    for item in value["skills"]:
        if skill and item["skill"] != skill:
            continue
        for kind, field in (("positive", "should_trigger"), ("negative", "should_not_trigger")):
            for index, prompt in enumerate(item[field], start=1):
                result.append({"case_id": f"{item['skill']}:{kind}:{index}", "skill": item["skill"],
                               "path": item["path"], "should_load": kind == "positive", "prompt": prompt,
                               "status": item["status"], "expectations": item["expectations"]})
    return result


def score(expected: list[dict], results: object, allow_partial: bool = False) -> dict:
    if not isinstance(results, dict) or results.get("version") != 1 or not isinstance(results.get("runs"), list):
        return {"ok": False, "errors": ["results need version 1 and a runs array"]}
    for field in ("model", "revision", "effort"):
        if not isinstance(results.get(field), str) or not results[field].strip():
            return {"ok": False, "errors": [f"results need non-empty {field}"]}
    lookup = {case["case_id"]: case for case in expected if case["status"] == "active"}
    seen = set()
    failures = []
    errors = []
    counts = {"true_positive": 0, "false_positive": 0, "true_negative": 0, "false_negative": 0}
    quality_checks = 0
    quality_failures = 0
    for run in results["runs"]:
        if not isinstance(run, dict) or not isinstance(run.get("case_id"), str):
            errors.append("run needs a case_id")
            continue
        identity = run["case_id"]
        if identity not in lookup or identity in seen:
            errors.append(f"unknown, deferred, or duplicate case: {identity}")
            continue
        seen.add(identity)
        loaded = run.get("loaded_skills")
        if not isinstance(loaded, list) or not all(isinstance(s, str) for s in loaded):
            errors.append(f"{identity}: loaded_skills must be observed skill identifiers")
            continue
        case = lookup[identity]
        parts = Path(case["path"]).parts
        valid_ids = {case["skill"]}
        if parts[0] == "plugins":
            valid_ids.add(f"{parts[1]}:{case['skill']}")
        observed = bool(valid_ids & set(loaded))
        category = ("true_" if observed == case["should_load"] else "false_") + (
            "positive" if observed else "negative")
        counts[category] += 1
        if observed != case["should_load"]:
            failures.append(identity)
        quality = run.get("expectations_passed")
        if quality is not None:
            if not isinstance(quality, bool):
                errors.append(f"{identity}: expectations_passed must be a reviewer-assessed boolean")
            else:
                quality_checks += 1
                quality_failures += not quality
                if not quality and identity not in failures:
                    failures.append(identity)
    missing = sorted(set(lookup) - seen)
    if missing and not allow_partial:
        errors.append("incomplete run; use --allow-partial to report partial coverage explicitly")
    evaluated = sum(counts.values())
    return {"ok": not errors and not failures, "model": results["model"], "effort": results["effort"],
            "revision": results["revision"], "evaluated_cases": evaluated, "total_cases": len(lookup),
            "complete": not missing and not errors, "selection": counts, "quality_checks": quality_checks,
            "quality_failures": quality_failures, "missing_cases": missing, "failures": failures,
            "errors": errors, "limitation": "Selection counts do not prove workflow quality; quality labels require observed review evidence."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="emit prompt cases for a host/reviewer to run")
    parser.add_argument("--skill", help="filter listed/scored cases by skill identifier")
    parser.add_argument("--results", type=Path, help="score a local JSON of observed model runs")
    parser.add_argument("--allow-partial", action="store_true", help="report partial coverage without claiming a complete run")
    args = parser.parse_args()
    value = json.loads(CONTRACT.read_text(encoding="utf-8"))
    paths = {str(p.relative_to(ROOT)) for pattern in ("skills/*/SKILL.md", "plugins/*/skills/*/SKILL.md")
             for p in ROOT.glob(pattern)}
    errors = validate_contract(value, paths)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, separators=(",", ":")))
        return 1
    selected = cases(value, args.skill)
    if not selected:
        parser.error("unknown skill identifier")
    if args.results:
        try:
            result = score(selected, json.loads(args.results.read_text(encoding="utf-8")), args.allow_partial)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            parser.error("cannot read results as UTF-8 JSON")
    elif args.list:
        result = {"cases": selected}
    else:
        result = {"ok": True, "contract_skills": len(value["skills"]), "cases": len(selected),
                  "mode": "contract-validation", "behavioral_runs": 0}
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
