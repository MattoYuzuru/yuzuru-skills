#!/usr/bin/env python3
"""Behavioral checks for declared-state admission and completion evidence."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plan


def task(key, dependencies=None, **extra):
    result = {"id": key, "objective": "Implement " + key, "dependencies": dependencies or [],
              "status": "pending", "owner": key + "-owner", "write_paths": ["services/" + key],
              "exclusive_resources": [], "acceptance_checks": ["Exercise observable behavior."]}
    result.update(extra)
    return result


def document(*tasks, **extra):
    result = {"version": 1, "objective": "Deliver integrated behavior.",
              "limits": {"max_concurrent": 2, "max_depth": 2}, "tasks": list(tasks)}
    result.update(extra)
    return result


def complete(value):
    value["status"] = "completed"
    value["evidence"] = {"summary": "Acceptance checks passed.", "revision": "fixture-sha",
                         "environment": "isolated fixture",
                         "checks": [{"command": "python3 -m unittest fixture", "outcome": "passed"}]}
    return value


class PlanTests(unittest.TestCase):
    def invalid(self, value, fragment):
        with self.assertRaises(plan.PlanError) as caught:
            plan.validate(value)
        self.assertEqual(caught.exception.kind, "invalid_plan")
        self.assertTrue(any(fragment in message for message in caught.exception.issues), caught.exception.issues)

    def test_example_parallelizes_services_after_contract(self):
        root = Path(plan.__file__).resolve().parents[1]
        value = plan.load_plan(str(root / "assets" / "example-plan.json"))
        result = plan.analyze(value)
        self.assertEqual(result["dispatch"], ["service-a", "service-b"])
        self.assertEqual(result["blocked"][0]["dependencies"], ["service-a", "service-b"])
        self.assertEqual(result["estimates"]["critical_path_seconds"], 120)
        self.assertEqual(result["estimates"]["total_work_seconds"], 180)
        self.assertEqual(result["estimates"]["makespan_lower_bound_seconds"], 120)

    def test_single_task_is_valid_and_no_minimum_team_is_imposed(self):
        value = document(task("one"))
        value["limits"]["max_concurrent"] = 1
        self.assertEqual(plan.analyze(value)["dispatch"], ["one"])

    def test_input_order_does_not_change_admission(self):
        left, right = task("a"), task("b")
        self.assertEqual(plan.analyze(document(right, left))["dispatch"], ["a", "b"])

    def test_dependency_prevents_premature_dispatch(self):
        result = plan.analyze(document(task("a"), task("b", ["a"])))
        self.assertEqual(result["ready"], ["a"])
        self.assertEqual(result["dispatch"], ["a"])

    def test_completed_prerequisite_releases_consumer(self):
        self.assertEqual(plan.analyze(document(complete(task("a")), task("b", ["a"])))["dispatch"], ["b"])

    def test_failed_and_cancelled_dependencies_do_not_release_consumer(self):
        for status in ("failed", "cancelled"):
            with self.subTest(status=status):
                result = plan.analyze(document(task("a", status=status), task("b", ["a"])))
                self.assertEqual(result["dispatch"], [])
                self.assertEqual(result["estimates"]["unavailable_reason"], "terminal_tasks_require_replanning")

    def test_duplicate_ids_are_rejected(self):
        self.invalid(document(task("a"), task("a")), "duplicate task IDs")

    def test_unknown_dependency_is_rejected(self):
        self.invalid(document(task("a", ["missing"])), "unknown dependency")

    def test_self_dependency_and_cycles_are_rejected(self):
        self.invalid(document(task("a", ["a"])), "self dependency")
        self.invalid(document(task("a", ["b"]), task("b", ["a"])), "dependency cycle")

    def test_running_task_requires_completed_dependencies(self):
        self.invalid(document(task("a"), task("b", ["a"], status="running")), "unsatisfied dependencies")

    def test_completed_task_requires_completed_dependencies(self):
        self.invalid(document(task("a"), complete(task("b", ["a"]))), "unsatisfied dependencies")

    def test_completed_evidence_is_required_and_passed(self):
        value = task("a", status="completed")
        self.invalid(document(value), "missing evidence")
        value = complete(task("a"))
        for outcome in ("failed", "skipped"):
            value["evidence"]["checks"][0]["outcome"] = outcome
            self.invalid(document(value), "non-passing checks")

    def test_completion_evidence_is_not_just_a_status_label(self):
        value = complete(task("a"))
        del value["evidence"]["revision"]
        self.invalid(document(value), "missing revision")
        value = complete(task("a"))
        value["evidence"]["checks"] = []
        self.invalid(document(value), "array size")

    def test_unknown_properties_are_rejected_at_each_level(self):
        for level in ("root", "limits", "task", "evidence", "check"):
            value = document(complete(task("a")))
            target = {"root": value, "limits": value["limits"], "task": value["tasks"][0],
                      "evidence": value["tasks"][0]["evidence"],
                      "check": value["tasks"][0]["evidence"]["checks"][0]}[level]
            target["surprise"] = "unrecognized"
            self.invalid(value, "unknown properties")

    def test_boolean_numbers_and_nonfinite_estimates_are_rejected(self):
        for field, invalid in (("depth", True), ("estimated_seconds", float("inf")),
                               ("estimated_seconds", float("nan")), ("estimated_tokens", False),
                               ("estimated_seconds", 10 ** 500)):
            self.invalid(document(task("a", **{field: invalid})), "bounds" if isinstance(invalid, int) and not isinstance(invalid, bool) else "expected")
        value = document(task("a"))
        value["version"] = True
        self.invalid(value, "expected integer")

    def test_blank_strings_are_rejected(self):
        self.invalid(document(task("a", owner="  ")), "blank string")

    def test_duplicate_dependencies_are_rejected(self):
        self.invalid(document(task("a"), task("b", ["a", "a"])), "duplicate array")

    def test_path_normalization_rejects_escape_and_globs(self):
        for path in ("../a", "/a", "a/../b", "a/*", "a/**", "a\\b", "a//b", "./a", "a/", "C:/a", "a\x00b", "a\nb", "a\x7fb", ""):
            with self.subTest(path=path):
                self.invalid(document(task("a", write_paths=[path])), "write_paths" if path else "string size")

    def test_write_conflicts_are_component_prefixes_not_string_prefixes(self):
        result = plan.analyze(document(task("a", write_paths=["service"]), task("b", write_paths=["service-b"])))
        self.assertEqual(result["dispatch"], ["a", "b"])
        result = plan.analyze(document(task("a", write_paths=["service"]), task("b", write_paths=["service/api.py"])))
        self.assertEqual(result["dispatch"], ["a"])
        self.assertIn("write_scope", result["blocked"][0]["reasons"])

    def test_whole_tree_scope_conflicts_with_all_writers(self):
        result = plan.analyze(document(task("a", write_paths=["."]), task("b")))
        self.assertEqual(result["dispatch"], ["a"])

    def test_future_overlapping_writes_are_valid_when_sequential(self):
        value = document(task("a", write_paths=["src"]), task("b", ["a"], write_paths=["src"]))
        plan.validate(value)
        self.assertEqual(plan.analyze(value)["dispatch"], ["a"])

    def test_read_only_branches_have_no_artificial_write_conflict(self):
        result = plan.analyze(document(task("a", write_paths=[]), task("b", write_paths=[])))
        self.assertEqual(result["dispatch"], ["a", "b"])

    def test_exclusive_resources_prevent_competing_mutations(self):
        value = document(task("a", exclusive_resources=["stack:fixture"]),
                         task("b", exclusive_resources=["stack:fixture"]))
        result = plan.analyze(value)
        self.assertEqual(result["dispatch"], ["a"])
        self.assertIn("exclusive_resource", result["blocked"][0]["reasons"])

    def test_owner_cannot_work_two_concurrent_tasks(self):
        result = plan.analyze(document(task("a", owner="worker"), task("b", owner="worker")))
        self.assertEqual(result["dispatch"], ["a"])
        self.assertIn("owner_busy", result["blocked"][0]["reasons"])

    def test_running_tasks_occupy_slots_and_resources(self):
        value = document(task("a", status="running", exclusive_resources=["db"]),
                         task("b", exclusive_resources=["db"]), task("c"))
        result = plan.analyze(value)
        self.assertEqual(result["dispatch"], ["c"])
        self.assertIn("exclusive_resource", result["blocked"][0]["reasons"])
        value["limits"]["max_concurrent"] = 1
        self.assertEqual(plan.analyze(value)["dispatch"], [])

    def test_inconsistent_running_state_fails_instead_of_becoming_a_suggestion(self):
        value = document(task("a", status="running"), task("b", status="running"))
        value["limits"]["max_concurrent"] = 1
        self.invalid(value, "exceeds max_concurrent")
        value["limits"]["max_concurrent"] = 2
        value["tasks"][1]["write_paths"] = ["services/a"]
        self.invalid(value, "running tasks conflict")

    def test_declared_depth_is_independent_of_dependency_depth(self):
        value = document(complete(task("a")), complete(task("b", ["a"])), task("c", ["b"]))
        value["limits"]["max_depth"] = 1
        self.assertEqual(plan.analyze(value)["dispatch"], ["c"])
        value["tasks"][2]["depth"] = 2
        self.invalid(value, "depth exceeds")

    def test_budget_counts_spent_and_running_reservations(self):
        value = document(task("a", status="running", estimated_tokens=20),
                         task("b", estimated_tokens=40), task("c", estimated_tokens=30), spent_tokens=50)
        value["limits"]["token_budget"] = 100
        result = plan.analyze(value)
        self.assertEqual(result["dispatch"], ["c"])
        self.assertEqual(result["budget"]["remaining_after_running"], 30)
        self.assertIn("token_budget", result["blocked"][0]["reasons"])

    def test_unknown_running_token_estimate_blocks_new_budgeted_admission(self):
        value = document(task("a", status="running"), task("b", estimated_tokens=1))
        value["limits"]["token_budget"] = 100
        result = plan.analyze(value)
        self.assertEqual(result["dispatch"], [])
        self.assertIsNone(result["budget"]["running_reserved_tokens"])
        self.assertIsNone(result["budget"]["remaining_after_running"])
        self.assertIn("missing_token_estimate", result["blocked"][0]["reasons"])

    def test_unknown_candidate_estimate_is_not_treated_as_zero(self):
        value = document(task("a"), task("b", estimated_tokens=1))
        value["limits"]["token_budget"] = 100
        self.assertEqual(plan.analyze(value)["dispatch"], ["b"])

    def test_budget_zero_exhaustion_and_oversubscribed_running(self):
        value = document(task("a", estimated_tokens=1))
        value["limits"]["token_budget"] = 0
        self.assertEqual(plan.analyze(value)["dispatch"], [])
        value["tasks"][0]["status"] = "running"
        self.invalid(value, "running token reservations exceed")

    def test_exhausted_budget_rejects_even_zero_estimate_candidates(self):
        for budget, spent in ((0, 0), (100, 100), (100, 101)):
            with self.subTest(budget=budget, spent=spent):
                value = document(task("a", estimated_tokens=0), spent_tokens=spent)
                value["limits"]["token_budget"] = budget
                result = plan.analyze(value)
                self.assertEqual(result["dispatch"], [])
                self.assertIn("token_budget", result["blocked"][0]["reasons"])

    def test_running_and_selected_reservations_can_exhaust_admission(self):
        value = document(task("a", status="running", estimated_tokens=20),
                         task("b", estimated_tokens=0), spent_tokens=80)
        value["limits"]["token_budget"] = 100
        self.assertEqual(plan.analyze(value)["dispatch"], [])
        value = document(task("a", estimated_tokens=100), task("b", estimated_tokens=0))
        value["limits"]["token_budget"] = 100
        result = plan.analyze(value)
        self.assertEqual(result["dispatch"], ["a"])
        self.assertIn("token_budget", result["blocked"][0]["reasons"])

    def test_missing_estimate_remains_explicit_at_budget_exhaustion(self):
        value = document(task("a"))
        value["limits"]["token_budget"] = 0
        self.assertIn("missing_token_estimate", plan.analyze(value)["blocked"][0]["reasons"])

    def test_zero_estimate_can_be_admitted_while_budget_remains(self):
        value = document(task("a", estimated_tokens=0))
        value["limits"]["token_budget"] = 1
        self.assertEqual(plan.analyze(value)["dispatch"], ["a"])

    def test_batch_budget_is_shared_across_candidates(self):
        value = document(task("a", estimated_tokens=60), task("b", estimated_tokens=60))
        value["limits"]["token_budget"] = 100
        self.assertEqual(plan.analyze(value)["dispatch"], ["a"])

    def test_estimates_are_null_when_durations_are_unknown(self):
        result = plan.analyze(document(task("a")))
        self.assertIsNone(result["estimates"]["makespan_lower_bound_seconds"])
        self.assertEqual(result["estimates"]["unavailable_reason"], "missing_duration_estimates")

    def test_work_bound_can_dominate_critical_path(self):
        value = document(*(task(key, estimated_seconds=10) for key in ("a", "b", "c")))
        bounds = plan.analyze(value)["estimates"]
        self.assertEqual(bounds["critical_path_seconds"], 10)
        self.assertEqual(bounds["makespan_lower_bound_seconds"], 15)

    def test_completed_tasks_do_not_need_remaining_duration(self):
        bounds = plan.analyze(document(complete(task("a"))))["estimates"]
        self.assertEqual(bounds["critical_path_seconds"], 0)

    def test_output_pagination_reports_hidden_counts(self):
        result = plan.analyze(document(task("a"), task("b"), task("c")), limit=1)
        self.assertEqual(result["ready"], ["a"])
        self.assertEqual(result["totals"]["ready"], 3)
        self.assertTrue(result["truncated"]["ready"])
        self.assertEqual(result["totals"]["dispatch"], 2)
        self.assertTrue(result["truncated"]["dispatch"])
        self.assertTrue(result["advisory"])

    def test_analysis_does_not_mutate_input_or_claim_native_enforcement(self):
        value = document(task("a"))
        before = copy.deepcopy(value)
        result = plan.analyze(value)
        self.assertEqual(value, before)
        self.assertTrue(result["advisory"])
        self.assertIn("caller declarations", result["policy"])

    def test_invalid_limits_and_excessive_task_count_fail(self):
        for limit in (0, 201, True, "20"):
            with self.assertRaises(plan.PlanError):
                plan.analyze(document(task("a")), limit)
        self.invalid(document(*(task("t" + str(i)) for i in range(201))), "array size")


class CLITests(unittest.TestCase):
    def run_cli(self, payload, *args):
        return subprocess.run([sys.executable, "-B", str(Path(plan.__file__)), *args, "-"],
                              input=payload, text=True, capture_output=True, timeout=10)

    def test_stdin_and_no_artifact_side_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, "-B", plan.__file__, "analyze", "-"],
                                    input=json.dumps(document(task("a"))), text=True, capture_output=True,
                                    cwd=directory, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["dispatch"], ["a"])
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_malformed_json_has_stable_error_and_no_success_stdout(self):
        for payload in ('{"version":' + "9" * 5000 + "}", '{"estimated_seconds":1e999}', '{"version":1,"version":1}', '{"x":NaN}', '{"x":Infinity}', '{', '[' * 10000):
            with self.subTest(payload=payload[:20]):
                result = self.run_cli(payload, "validate")
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertEqual(json.loads(result.stderr)["error"]["kind"], "invalid_json")
                self.assertNotIn("Traceback", result.stderr)

    def test_oversized_input_is_rejected_before_parsing(self):
        result = self.run_cli(" " * (plan.MAX_BYTES + 1), "validate")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)["error"]["kind"], "input_too_large")

    def test_missing_file_returns_stable_input_error(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, "-B", plan.__file__, "validate", str(Path(directory) / "missing")],
                                    capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)["error"]["kind"], "input_error")

    def test_argument_errors_have_stable_kind_without_echoing_values(self):
        result = subprocess.run([sys.executable, "-B", plan.__file__, "analyze", "-", "--limit", "private-value"],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(json.loads(result.stderr)["error"]["kind"], "invalid_arguments")
        self.assertNotIn("private-value", result.stderr)

    def test_validation_summary_is_bounded(self):
        result = self.run_cli(json.dumps(document(task("a"))), "validate")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["task_count"], 1)
        self.assertLess(len(result.stdout), 200)


if __name__ == "__main__":
    unittest.main()
