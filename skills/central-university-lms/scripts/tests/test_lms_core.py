from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lms_core import (
    LmsError,
    is_unfinished,
    redacted_shape,
    resolve_lms_url,
    sanitized_request_url,
    validate_submission_manifest,
    write_private_json,
)


class LmsCoreTests(unittest.TestCase):
    def test_target_is_exact_origin_and_api_path(self) -> None:
        self.assertEqual(
            resolve_lms_url("/api/micro-lms/tasks/1", require_api=True),
            "https://my.centraluniversity.ru/api/micro-lms/tasks/1",
        )
        for value in (
            "https://evil.example/api/micro-lms/tasks/1",
            "https://my.centraluniversity.ru.evil.example/api/tasks/1",
            "/learn/courses",
        ):
            with self.assertRaises(LmsError):
                resolve_lms_url(value, require_api=True)

    def test_observed_request_redacts_values(self) -> None:
        self.assertEqual(
            sanitized_request_url(
                "https://my.centraluniversity.ru/api/tasks/42?student=secret&limit=10"
            ),
            "/api/tasks/42?limit&student",
        )
        self.assertIsNone(sanitized_request_url("https://evil.example/api/tasks/42"))
        self.assertEqual(redacted_shape({"solution": {"url": "https://secret"}, "score": 5}), {
            "score": "<number>",
            "solution": {"url": "<string>"},
        })

    def test_unfinished_uses_state_and_timestamps(self) -> None:
        self.assertTrue(is_unfinished({"state": "inProgress"}))
        self.assertFalse(is_unfinished({"state": "submitted"}))
        self.assertFalse(is_unfinished({"state": "inProgress", "submitAt": "2026-07-18"}))

    def test_submission_manifest_is_bounded_and_deduplicated(self) -> None:
        result = validate_submission_manifest(
            {
                "schemaVersion": 1,
                "submissions": [
                    {"taskId": "42", "solutionUrl": "https://github.com/example/solution"}
                ],
            }
        )
        self.assertEqual(result[0]["taskId"], "42")
        with self.assertRaises(LmsError):
            validate_submission_manifest(
                {
                    "schemaVersion": 1,
                    "submissions": [
                        {"taskId": "42", "solutionUrl": "http://example.com/a"},
                    ],
                }
            )

    def test_private_json_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            write_private_json(path, {"ok": True})
            self.assertEqual(json.loads(path.read_text()), {"ok": True})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
