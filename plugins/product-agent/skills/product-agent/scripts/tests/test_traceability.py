from __future__ import annotations

import unittest

from traceability import analyze


class TraceabilityTests(unittest.TestCase):
    def test_complete_mapping_passes(self) -> None:
        payload, ok = analyze(
            {
                "requirements": [{"id": "REQ-1"}],
                "acceptance_criteria": [{"id": "AC-1", "requirements": ["REQ-1"]}],
            }
        )
        self.assertTrue(ok)
        self.assertEqual(payload["uncovered_requirements"], [])

    def test_unknown_requirement_fails(self) -> None:
        payload, ok = analyze(
            {
                "requirements": [{"id": "REQ-1"}],
                "acceptance_criteria": [{"id": "AC-1", "requirements": ["REQ-2"]}],
            }
        )
        self.assertFalse(ok)
        self.assertIn("criterion AC-1 references unknown REQ-2", payload["errors"])


if __name__ == "__main__":
    unittest.main()
