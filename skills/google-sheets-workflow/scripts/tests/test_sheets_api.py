from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sheets_api
import sheets_config


class SheetsApiTests(unittest.TestCase):
    def test_only_get_retries_rate_limit(self) -> None:
        error = sheets_api.SheetsApiError("rate limited", status=429)
        with mock.patch.object(sheets_api, "request_json", side_effect=[error, {"ok": True}]) as request:
            with mock.patch.object(sheets_api.time, "sleep"):
                self.assertEqual(
                    sheets_api.request_json_bounded_retry("token", "GET", "https://example.test"),
                    {"ok": True},
                )
            self.assertEqual(request.call_count, 2)

        with mock.patch.object(sheets_api, "request_json", side_effect=error) as request:
            with self.assertRaises(sheets_api.SheetsApiError):
                sheets_api.request_json_bounded_retry("token", "POST", "https://example.test", {})
            self.assertEqual(request.call_count, 1)

    def test_batch_file_rejects_destructive_operations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "requests.json"
            path.write_text(json.dumps([{"deleteSheet": {"sheetId": 1}}]))
            with self.assertRaises(sheets_api.SheetsApiError):
                sheets_api.load_requests(argparse.Namespace(requests_file=path))
            path.write_text(json.dumps([{"repeatCell": {"fields": "userEnteredFormat"}}]))
            self.assertEqual(
                sheets_api.load_requests(argparse.Namespace(requests_file=path))[0],
                {"repeatCell": {"fields": "userEnteredFormat"}},
            )

    def test_values_are_bounded(self) -> None:
        bounded = sheets_api.bound_values({"range": "A1:B3", "values": [[1, 2], [3, 4], [5, 6]]}, 4)
        self.assertEqual(bounded["values"], [[1, 2], [3, 4]])
        self.assertTrue(bounded["truncated"])
        self.assertEqual(bounded["maxCells"], 4)

    def test_write_and_destructive_confirmation(self) -> None:
        with self.assertRaises(sheets_api.SheetsApiError):
            sheets_api.require_confirmation(
                argparse.Namespace(command="write", dry_run=False, confirm_write=False)
            )
        sheets_api.require_confirmation(
            argparse.Namespace(command="write", dry_run=False, confirm_write=True)
        )
        with self.assertRaises(sheets_api.SheetsApiError):
            sheets_api.require_confirmation(
                argparse.Namespace(command="trash", dry_run=False, confirm_destructive=False)
            )

    def test_service_account_rejects_untrusted_token_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "key.json"
            source.write_text(
                json.dumps(
                    {
                        "type": "service_account",
                        "client_email": "service@example.test",
                        "private_key": "secret",
                        "token_uri": "https://evil.example/token",
                    }
                )
            )
            with mock.patch.dict(
                sheets_config.os.environ,
                {"GOOGLE_SHEETS_CONFIG_DIR": str(Path(directory) / "config")},
                clear=False,
            ):
                with self.assertRaises(sheets_config.SheetsConfigError):
                    sheets_config.save_service_account_key(source)


if __name__ == "__main__":
    unittest.main()
