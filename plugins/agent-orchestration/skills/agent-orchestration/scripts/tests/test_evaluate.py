#!/usr/bin/env python3
"""Behavioral checks for honest summaries, comparability, and bounded input handling."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import evaluate


def run_record(arm="single", repetition=1, outcome="accepted", **changes):
    value = {
        "id": arm + "-" + str(repetition), "case_id": "service-contract",
        "arm": arm, "repetition": repetition, "revision": "fixture-r1",
        "host": "fixture-host", "model": "fixture-model", "effort": "default",
        "outcome": outcome, "wall_seconds": 10, "tokens": 100, "api_cost_usd": 0.1,
        "evidence": "Synthetic acceptance fixture; no model was called.",
    }
    value.update(changes)
    return value


def document(runs=None, **changes):
    value = {"version": 1, "experiment_id": "tutorial", "study_phase": "orchestration",
             "policy_revision": "policy-r1", "data_kind": "synthetic",
             "runs": runs if runs is not None else [run_record(arm) for arm in evaluate.ARMS]}
    value.update(changes)
    return value


class ResultsTests(unittest.TestCase):
    def test_balanced_runs_are_described_without_winner_claim(self):
        data = document()
        self.assertEqual(evaluate.validate_results(data), [])
        result = evaluate.summarize(data)
        self.assertTrue(result["comparability"]["structurally_comparable"])
        self.assertEqual(result["data_kind"], "synthetic")
        self.assertNotIn("winner", result)
        self.assertNotIn("speedup", result)

    def test_failure_and_timeout_costs_count_in_cost_per_accepted(self):
        runs = [run_record(), run_record(repetition=2, outcome="failed", api_cost_usd=0.3),
                run_record(repetition=3, outcome="timeout", api_cost_usd=0.6)]
        summary = evaluate.summarize(document(runs))["arms"][0]
        self.assertEqual(summary["attempts"], 3)
        self.assertEqual(summary["acceptance_rate"], 1 / 3)
        self.assertEqual(summary["all_attempt_wall_seconds"], 30)
        self.assertEqual(summary["api_cost_per_accepted"], 1.0)
        self.assertEqual(summary["tokens"]["total"], 300)
        self.assertEqual((summary["failed"], summary["timeouts"]), (1, 1))

    def test_missing_metrics_stay_unknown_with_known_subtotal(self):
        runs = [run_record(), run_record(repetition=2, tokens=None, api_cost_usd=None)]
        summary = evaluate.summarize(document(runs))["arms"][0]
        self.assertEqual(summary["tokens"], {"total": None, "known_subtotal": 100, "missing_runs": 1})
        self.assertIsNone(summary["api_cost_per_accepted"])
        self.assertIsNone(summary["native_usage"]["total"])
        self.assertEqual(summary["native_usage"]["missing_runs"], 2)

    def test_failed_only_has_no_cost_per_success_or_accepted_median(self):
        result = evaluate.summarize(document([run_record(outcome="failed")]))["arms"][0]
        self.assertIsNone(result["api_cost_per_accepted"])
        self.assertIsNone(result["median_accepted_wall_seconds"])

    def test_native_units_never_combined(self):
        data = document([run_record(native_usage={"unit": "credits", "value": 2}),
                         run_record(repetition=2, native_usage={"unit": "requests", "value": 7})])
        usage = evaluate.summarize(data)["arms"][0]["native_usage"]
        self.assertIsNone(usage["total"])
        self.assertEqual(usage["known_by_unit"], [
            {"unit": "credits", "known_subtotal": 2, "observed_runs": 1},
            {"unit": "requests", "known_subtotal": 7, "observed_runs": 1}])

    def test_single_native_unit_total_requires_every_run(self):
        data = document([run_record(native_usage={"unit": "credits", "value": 2}),
                         run_record(repetition=2, native_usage={"unit": "credits", "value": 7})])
        self.assertEqual(evaluate.summarize(data)["arms"][0]["native_usage"]["total"],
                         {"unit": "credits", "value": 9})

    def test_missing_arm_and_source_mismatch_prevent_structural_comparability(self):
        data = document([run_record(), run_record("fixed", revision="other-source")])
        issues = evaluate.summarize(data)["comparability"]
        self.assertFalse(issues["structurally_comparable"])
        self.assertEqual(issues["issue_counts"], {"input_revision_mismatch": 1, "missing_arms": 1})

    def test_orchestration_phase_exposes_model_effort_and_host_confounders(self):
        data = document()
        data["runs"][1].update(model="other-model", effort="high", host="other-host")
        issues = evaluate.summarize(data)["comparability"]["issue_counts"]
        self.assertEqual(issues, {"host_mismatch": 1, "model_effort_mismatch": 1})

    def test_routing_can_vary_models_but_reports_variation(self):
        data = document(study_phase="routing")
        data["runs"][2]["model"] = "other-model"
        result = evaluate.summarize(data)["comparability"]
        self.assertTrue(result["structurally_comparable"])
        self.assertEqual(result["model_effort_varies_in_cells"], 1)

    def test_duplicate_run_ids_and_cells_are_rejected(self):
        for runs in ([run_record(), run_record("fixed", id="single-1")],
                     [run_record(), run_record(id="unique-id")]):
            self.assertTrue(evaluate.validate_results(document(runs)))

    def test_invalid_schema_values_are_rejected(self):
        cases = [document(version=True), document(runs=[]), document(extra="ignored"),
                 document(data_kind="benchmark"), document(policy_revision="   ")]
        for key, item in [("tokens", True), ("tokens", -1), ("tokens", 1.5),
                          ("api_cost_usd", -0.1), ("wall_seconds", float("inf")),
                          ("wall_seconds", 10 ** 500), ("wall_seconds", True),
                          ("evidence", ""), ("native_usage", {"unit": "credits"}),
                          ("repetition", 0), ("unknown", "field")]:
            cases.append(document([run_record(**{key: item})]))
        for data in cases:
            with self.subTest(data=data):
                self.assertTrue(evaluate.validate_results(data))

    def test_input_bounds_and_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "input.json"
            for payload in [b'{"version":1,"version":1}', b'{"x":NaN}', b'\xff',
                            b' ' * (evaluate.MAX_BYTES + 1)]:
                target.write_bytes(payload)
                with self.assertRaises(evaluate.InvalidResults):
                    evaluate.read_results(target)

    def test_too_many_runs_and_long_labels_rejected(self):
        self.assertTrue(evaluate.validate_results(document([run_record()] * 301)))
        self.assertTrue(evaluate.validate_results(document([run_record(model="x" * 201)])))

    def test_report_limit_caps_issues_and_unit_collections(self):
        data = document([run_record(repetition=i + 1,
                                    native_usage={"unit": "unit" + str(i), "value": 1})
                         for i in range(60)])
        result = evaluate.summarize(data, limit=2)
        self.assertEqual(len(result["comparability"]["issues"]), 2)
        self.assertTrue(result["comparability"]["issues_truncated"])
        usage = result["arms"][0]["native_usage"]
        self.assertEqual(len(usage["known_by_unit"]), 2)
        self.assertTrue(usage["units_truncated"])

    def test_summaries_do_not_mutate_inputs(self):
        data = document()
        before = copy.deepcopy(data)
        evaluate.summarize(data)
        self.assertEqual(data, before)

    def test_cli_runs_from_unrelated_directory_and_has_stable_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "input.json"
            target.write_text(json.dumps(document()), encoding="utf-8")
            args = [sys.executable, "-B", str(SCRIPTS / "evaluate.py")]
            result = subprocess.run(args + ["summarize", str(target)], cwd=directory,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["run_count"], 3)
            target.write_text('{"version":1,"version":1}', encoding="utf-8")
            result = subprocess.run(args + ["validate", str(target)], cwd=directory,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertEqual(json.loads(result.stderr)["error"]["kind"], "invalid_input")

    def test_adversarial_numeric_json_returns_stable_error_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "input.json"
            original = json.dumps(document())
            cases = [original.replace('"wall_seconds": 10', '"wall_seconds": 1e9999'),
                     original.replace('"wall_seconds": 10', '"wall_seconds": ' + '9' * 1000),
                     original.replace('"wall_seconds": 10', '"wall_seconds": ' + '9' * 5000)]
            for payload in cases:
                target.write_text(payload, encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, "-B", str(SCRIPTS / "evaluate.py"), "validate", str(target)],
                    cwd=directory, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertIn(json.loads(result.stderr)["error"]["kind"],
                              {"invalid_input", "invalid_results"})
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
