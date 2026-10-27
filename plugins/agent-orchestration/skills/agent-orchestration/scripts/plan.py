#!/usr/bin/env python3
"""Validate declared orchestration state and suggest a bounded, advisory dispatch batch."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys

SCHEMA = Path(__file__).resolve().parents[1] / "references" / "orchestration-plan.schema.json"
MAX_BYTES = 1024 * 1024
MAX_ERRORS = 20
STATUSES = ("pending", "running", "completed", "failed", "cancelled")


class PlanError(ValueError):
    def __init__(self, kind: str, issues: list[str]):
        super().__init__(kind)
        self.kind = kind
        self.issues = issues[:MAX_ERRORS]


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise PlanError("invalid_json", ["duplicate object key"])
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise PlanError("invalid_json", ["non-finite JSON number"])


def _integer(value: str) -> int:
    if len(value) > 32:
        raise PlanError("invalid_json", ["integer exceeds supported precision"])
    return int(value)


def _float(value: str) -> float:
    if len(value) > 128:
        raise PlanError("invalid_json", ["number exceeds supported precision"])
    result = float(value)
    if not math.isfinite(result):
        raise PlanError("invalid_json", ["non-finite JSON number"])
    return result


def load_plan(path: str) -> dict:
    try:
        if path == "-":
            payload = sys.stdin.buffer.read(MAX_BYTES + 1)
        else:
            with open(path, "rb") as stream:
                payload = stream.read(MAX_BYTES + 1)
    except OSError as error:
        raise PlanError("input_error", ["cannot read plan input"]) from error
    if len(payload) > MAX_BYTES:
        raise PlanError("input_too_large", ["plan exceeds 1 MiB"])
    try:
        return json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_object,
                          parse_constant=_invalid_constant, parse_int=_integer, parse_float=_float)
    except PlanError:
        raise
    except (UnicodeError, ValueError, RecursionError) as error:
        raise PlanError("invalid_json", ["invalid UTF-8 JSON document"]) from error


def _shape(value: object, schema: dict, at: str = "plan") -> list[str]:
    """Validate the small JSON Schema vocabulary used by the bundled contract."""
    issues: list[str] = []
    expected = schema.get("type")
    types = {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
        and (isinstance(v, int) or math.isfinite(v)),
    }
    if expected and not types[expected](value):
        return [at + ": expected " + expected]
    if "const" in schema and value != schema["const"]:
        issues.append(at + ": unexpected constant")
    if "enum" in schema and value not in schema["enum"]:
        issues.append(at + ": unknown enum value")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                issues.append(at + ": missing " + key)
        if schema.get("additionalProperties") is False and set(value) - set(properties):
            issues.append(at + ": unknown properties")
        for key, child in properties.items():
            if key in value:
                issues.extend(_shape(value[key], child, at + "." + key))
    elif isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", MAX_BYTES):
            issues.append(at + ": array size out of bounds")
        if schema.get("uniqueItems"):
            serialized = [json.dumps(item, sort_keys=True) for item in value]
            if len(set(serialized)) != len(value):
                issues.append(at + ": duplicate array items")
        for index, item in enumerate(value[:200]):
            issues.extend(_shape(item, schema.get("items", {}), at + "[" + str(index) + "]"))
    elif isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", MAX_BYTES):
            issues.append(at + ": string size out of bounds")
        if schema.get("minLength", 0) and not value.strip():
            issues.append(at + ": blank string")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            issues.append(at + ": invalid identifier")
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        if value < schema.get("minimum", -math.inf) or value > schema.get("maximum", math.inf):
            issues.append(at + ": number out of bounds")
    for branch in schema.get("allOf", []):
        if "if" in branch:
            if not _shape(value, branch["if"], at):
                issues.extend(_shape(value, branch.get("then", {}), at))
        else:
            issues.extend(_shape(value, branch, at))
    return issues[:MAX_ERRORS]


def _canonical_path(value: str) -> bool:
    path = PurePosixPath(value)
    return (not path.is_absolute() and ".." not in path.parts
            and path.as_posix() == value and "\\" not in value
            and not any(char in value for char in "*?[]{}")
            and not re.match(r"^[A-Za-z]:", value)
            and not any(ord(char) < 32 or ord(char) == 127 for char in value))


def _path_overlap(left: str, right: str) -> bool:
    a, b = PurePosixPath(left).parts, PurePosixPath(right).parts
    return a[:len(b)] == b or b[:len(a)] == a


def conflict(left: dict, right: dict) -> list[str]:
    result = []
    if left["owner"] == right["owner"]:
        result.append("owner_busy")
    if set(left["exclusive_resources"]) & set(right["exclusive_resources"]):
        result.append("exclusive_resource")
    if any(_path_overlap(a, b) for a in left["write_paths"] for b in right["write_paths"]):
        result.append("write_scope")
    return result


def validate(plan: object) -> tuple[dict[str, dict], list[str]]:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    issues = _shape(plan, schema)
    if issues:
        raise PlanError("invalid_plan", issues)
    tasks = {task["id"]: task for task in plan["tasks"]}
    if len(tasks) != len(plan["tasks"]):
        issues.append("duplicate task IDs")
    for task in plan["tasks"]:
        label = "task " + task["id"]
        if any(not _canonical_path(path) for path in task["write_paths"]):
            issues.append(label + ": write_paths must be canonical relative path prefixes without globs")
        if task.get("depth", 1) > plan["limits"]["max_depth"]:
            issues.append(label + ": depth exceeds max_depth")
        if any(dependency not in tasks for dependency in task["dependencies"]):
            issues.append(label + ": unknown dependency")
        if task["id"] in task["dependencies"]:
            issues.append(label + ": self dependency")
        if task["status"] in {"running", "completed"}:
            if any(tasks.get(dep, {}).get("status") != "completed" for dep in task["dependencies"]):
                issues.append(label + ": active/completed task has unsatisfied dependencies")
        if task["status"] == "completed":
            if any(check["outcome"] != "passed" for check in task["evidence"]["checks"]):
                issues.append(label + ": completed task has non-passing checks")
    if issues:
        raise PlanError("invalid_plan", issues)
    # Kahn ordering avoids recursion limits even for the longest permitted dependency chain.
    indegrees = {key: len(task["dependencies"]) for key, task in tasks.items()}
    children = {key: [] for key in tasks}
    for key, task in tasks.items():
        for dependency in task["dependencies"]:
            children[dependency].append(key)
    queue = sorted(key for key, count in indegrees.items() if count == 0)
    order = []
    while queue:
        key = queue.pop(0)
        order.append(key)
        for child in children[key]:
            indegrees[child] -= 1
            if indegrees[child] == 0:
                queue.append(child)
        queue.sort()
    if len(order) != len(tasks):
        issues.append("dependency cycle")
    running = [task for task in tasks.values() if task["status"] == "running"]
    if len(running) > plan["limits"]["max_concurrent"]:
        issues.append("running task count exceeds max_concurrent")
    for index, left in enumerate(running):
        for right in running[index + 1:]:
            if conflict(left, right):
                issues.append("running tasks conflict: " + left["id"] + ", " + right["id"])
    budget = plan["limits"].get("token_budget")
    if budget is not None and all("estimated_tokens" in task for task in running):
        if running and plan.get("spent_tokens", 0) + sum(task["estimated_tokens"] for task in running) > budget:
            issues.append("running token reservations exceed remaining budget")
    if issues:
        raise PlanError("invalid_plan", issues)
    return tasks, order


def duration_bounds(tasks: dict[str, dict], order: list[str], capacity: int) -> dict:
    unfinished = [task for task in tasks.values() if task["status"] != "completed"]
    result = {"critical_path_seconds": None, "total_work_seconds": None,
              "makespan_lower_bound_seconds": None,
              "assumption": "Declared remaining durations; excludes unmodeled coordination, contention and rework."}
    if any(task["status"] in {"failed", "cancelled"} for task in unfinished):
        result["unavailable_reason"] = "terminal_tasks_require_replanning"
        return result
    if any("estimated_seconds" not in task for task in unfinished):
        result["unavailable_reason"] = "missing_duration_estimates"
        return result
    longest: dict[str, float] = {}
    for key in order:
        task = tasks[key]
        seconds = 0 if task["status"] == "completed" else task["estimated_seconds"]
        longest[key] = seconds + max((longest[dep] for dep in task["dependencies"]), default=0)
    critical = max(longest.values(), default=0)
    total = sum(task["estimated_seconds"] for task in unfinished)
    result.update(critical_path_seconds=critical, total_work_seconds=total,
                  makespan_lower_bound_seconds=max(critical, total / capacity))
    return result


def analyze(plan: dict, limit: int = 20) -> dict:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
        raise PlanError("invalid_limit", ["limit must be an integer between 1 and 200"])
    tasks, order = validate(plan)
    running = sorted((task for task in tasks.values() if task["status"] == "running"), key=lambda t: t["id"])
    budget = plan["limits"].get("token_budget")
    spent = plan.get("spent_tokens", 0)
    reserved = sum(task.get("estimated_tokens", 0) for task in running)
    unknown_running = any("estimated_tokens" not in task for task in running)
    selected: list[dict] = []
    ready: list[str] = []
    blocked: list[dict] = []
    for key in sorted(tasks):
        task = tasks[key]
        if task["status"] != "pending":
            continue
        unmet = [dep for dep in task["dependencies"] if tasks[dep]["status"] != "completed"]
        if unmet:
            blocked.append({"id": key, "reasons": ["dependencies"], "dependencies": unmet[:limit],
                            "dependency_count": len(unmet)})
            continue
        ready.append(key)
        reasons = []
        if len(running) + len(selected) >= plan["limits"]["max_concurrent"]:
            reasons.append("concurrency_limit")
        for active in running + selected:
            reasons.extend(conflict(task, active))
        if budget is not None:
            if unknown_running or "estimated_tokens" not in task:
                reasons.append("missing_token_estimate")
            elif spent + reserved >= budget or spent + reserved + task["estimated_tokens"] > budget:
                reasons.append("token_budget")
        if reasons:
            blocked.append({"id": key, "reasons": sorted(set(reasons))})
        else:
            selected.append(task)
            reserved += task.get("estimated_tokens", 0)
    running_reserved = None if unknown_running else sum(task.get("estimated_tokens", 0) for task in running)
    counts = Counter(task["status"] for task in tasks.values())
    values = {"ready": ready, "dispatch": [task["id"] for task in selected],
              "running": [task["id"] for task in running], "blocked": blocked}
    return {"version": 1, "valid": True, "advisory": True,
            "counts": {key: counts[key] for key in STATUSES},
            **{key: value[:limit] for key, value in values.items()},
            "totals": {key: len(value) for key, value in values.items()},
            "truncated": {key: len(value) > limit for key, value in values.items()},
            "budget": {"token_budget": budget, "spent_tokens": spent,
                       "running_reserved_tokens": running_reserved,
                       "remaining_after_running": None if budget is None or unknown_running else max(0, budget - spent - running_reserved)},
            "estimates": duration_bounds(tasks, order, plan["limits"]["max_concurrent"]),
            "policy": "Stable task-ID order; greedy admission, not an optimal scheduler. Depth and evidence are caller declarations."}


class PlanArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # Do not echo arbitrary argument values into an agent transcript.
        print(json.dumps({"error": {"kind": "invalid_arguments", "issues": ["invalid arguments; use --help"]}},
                         separators=(",", ":")), file=sys.stderr)
        raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    parser = PlanArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "analyze"):
        command = commands.add_parser(name, help="Read-only " + name + " of a JSON plan")
        command.add_argument("plan", help="JSON file, or - for stdin (maximum 1 MiB)")
        command.add_argument("--limit", type=int, default=20, help="Maximum collection items, 1..200 (default: 20)")
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.limit <= 200:
            raise PlanError("invalid_limit", ["limit must be between 1 and 200"])
        plan = load_plan(args.plan)
        if args.command == "validate":
            tasks, _ = validate(plan)
            result = {"version": 1, "valid": True, "task_count": len(tasks), "advisory": True}
        else:
            result = analyze(plan, args.limit)
    except PlanError as error:
        print(json.dumps({"error": {"kind": error.kind, "issues": error.issues}}, separators=(",", ":")), file=sys.stderr)
        return 2
    print(json.dumps(result, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
