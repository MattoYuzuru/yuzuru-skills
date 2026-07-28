from __future__ import annotations

import json
import unittest
from pathlib import Path

from validate_artifact import SCHEMAS, validate_document


class ArtifactValidationTests(unittest.TestCase):
    def schema(self, name: str) -> dict:
        return json.loads(Path(SCHEMAS[name]).read_text(encoding="utf-8"))

    def test_accepts_minimal_work_package(self):
        value = {
            "work_package": {
                "id": "WP-1",
                "objective": "Implement a bounded behavior",
                "requirements": [],
                "architecture_decisions": [],
                "allowed_repositories": [],
                "allowed_paths": [],
                "forbidden_actions": [],
                "acceptance_checks": [],
                "evidence_required": []
            }
        }
        self.assertEqual(validate_document(value, self.schema("work_package")), [])

    def test_rejects_false_completion_bundle(self):
        value = {"evidence_bundle": {"work_package": "WP-1", "release_ready": True}}
        errors = validate_document(value, self.schema("evidence_bundle"))
        self.assertTrue(any("missing commands" in error for error in errors))
        self.assertTrue(any("missing verified_environments" in error for error in errors))

    def test_rejects_artifact_timestamp_without_timezone(self):
        value = {
            "artifact": {
                "id": "prd-1",
                "type": "prd",
                "title": "Product",
                "status": "draft",
                "created_at": "2026-07-28T12:00:00",
                "updated_at": "not-a-date",
                "owners": [],
                "source_tasks": [],
                "supersedes": [],
                "superseded_by": None,
                "assumptions": [],
                "unresolved_questions": [],
                "evidence": [],
            }
        }
        errors = validate_document(value, self.schema("artifact"))
        self.assertTrue(any("timezone" in error for error in errors))
        self.assertTrue(any("invalid date-time" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
