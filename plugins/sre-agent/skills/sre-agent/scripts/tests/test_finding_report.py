from __future__ import annotations

import unittest

from finding_report import validate


def confirmed():
    return {
        "id": "F-1",
        "classification": "confirmed-defect",
        "severity": "high",
        "requirement": "REQ-1",
        "component": "api",
        "location": "api.py:10",
        "preconditions": ["authorized user"],
        "reproduction": ["send duplicate request"],
        "expected": "one charge",
        "actual": "two charges",
        "evidence": ["test output"],
        "impact": "duplicate charge",
        "confidence": "high",
        "suggested_correction": "enforce idempotency",
        "regression_test": "duplicate request contract test",
    }


class FindingReportTests(unittest.TestCase):
    def test_complete_confirmed_finding_passes(self) -> None:
        _, ok = validate({"findings": [confirmed()]})
        self.assertTrue(ok)

    def test_confirmed_without_reproduction_fails(self) -> None:
        finding = confirmed()
        finding["reproduction"] = []
        payload, ok = validate({"findings": [finding]})
        self.assertFalse(ok)
        self.assertIn("reproduction", payload["errors"][0])


if __name__ == "__main__":
    unittest.main()
