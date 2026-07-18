from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import jira_api


class JiraApiTests(unittest.TestCase):
    def test_host_and_issue_keys_are_validated(self) -> None:
        self.assertEqual(
            jira_api.require_host({"JIRA_HOST": "jira.example.com"}),
            "https://jira.example.com",
        )
        with self.assertRaises(jira_api.JiraError):
            jira_api.require_host({"JIRA_HOST": "https://jira.example.com/path"})
        self.assertEqual(jira_api.issue_key("lp-42"), "LP-42")
        with self.assertRaises(jira_api.JiraError):
            jira_api.issue_key("../../myself")

    def test_createmeta_uses_jira_9_granular_endpoints(self) -> None:
        responses = [
            {"values": [{"id": "10001", "name": "Task"}], "isLast": True},
            {
                "values": [
                    {"fieldId": "summary", "name": "Summary", "required": True, "schema": {"type": "string"}}
                ],
                "isLast": True,
            },
        ]
        with mock.patch.object(jira_api, "request_json", side_effect=responses) as request:
            result = jira_api.create_metadata("https://jira.example.com", "token", "LP", ["Task"])
        paths = [call.args[3] for call in request.call_args_list]
        self.assertEqual(paths[0], "/rest/api/2/issue/createmeta/LP/issuetypes")
        self.assertEqual(paths[1], "/rest/api/2/issue/createmeta/LP/issuetypes/10001")
        self.assertEqual(result["issuetypes"][0]["fields"][0]["id"], "summary")

    def test_create_dry_run_needs_no_pat(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / "jira.env"
            env_file.write_text("JIRA_HOST=jira.example.com\nPROJECT_KEY=LP\n")
            os.chmod(env_file, 0o600)
            argv = [
                "jira_api.py",
                "--env-file",
                str(env_file),
                "create",
                "--issuetype-id",
                "10001",
                "--summary",
                "Test",
                "--dry-run",
            ]
            with mock.patch.object(sys, "argv", argv):
                with mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
                    self.assertEqual(jira_api.main(), 0)
        self.assertIn('"dry_run": true', stdout.getvalue())

    def test_write_requires_confirmation_before_credentials(self) -> None:
        argv = [
            "jira_api.py",
            "create",
            "--issuetype-id",
            "10001",
            "--summary",
            "Test",
        ]
        with mock.patch.object(sys, "argv", argv):
            with mock.patch("sys.stderr", new_callable=io.StringIO) as stderr:
                self.assertEqual(jira_api.main(), 1)
        self.assertIn("--confirm-write", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
