from __future__ import annotations

import unittest

from evidence_bundle import validate


def bundle(**overrides):
    value = {
        "work_package": "WP-1",
        "revision": "abc123",
        "commands": [],
        "tests": [{"command": "unit", "exit_code": 0, "result": "passed"}],
        "artifacts": [],
        "findings": [],
        "limitations": [],
        "verified_environments": ["local"],
        "unverified_environments": [],
        "release_ready": True,
    }
    value.update(overrides)
    return {"evidence_bundle": value}


class EvidenceBundleTests(unittest.TestCase):
    def test_consistent_release_ready_passes(self) -> None:
        _, ok = validate(bundle())
        self.assertTrue(ok)

    def test_failed_test_rejects_release_ready(self) -> None:
        payload, ok = validate(
            bundle(tests=[{"command": "integration", "exit_code": 1, "result": "failed"}])
        )
        self.assertFalse(ok)
        self.assertIn("integration", payload["failed_executions"])


if __name__ == "__main__":
    unittest.main()
