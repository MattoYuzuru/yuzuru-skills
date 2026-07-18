from __future__ import annotations

import io
import sys
import unittest
from unittest import mock

import gitlab_api


class GitLabApiTests(unittest.TestCase):
    def test_host_must_be_https_origin(self) -> None:
        self.assertEqual(gitlab_api.validate_host("https://gitlab.example.com/"), "https://gitlab.example.com")
        for host in (
            "http://gitlab.example.com",
            "https://user:pass@gitlab.example.com",
            "https://gitlab.example.com/path",
        ):
            with self.assertRaises(gitlab_api.GitLabError):
                gitlab_api.validate_host(host)

    def test_cross_origin_redirect_is_rejected(self) -> None:
        request = mock.Mock(full_url="https://gitlab.example.com/api/v4/user")
        with self.assertRaises(gitlab_api.GitLabError):
            gitlab_api.SameOriginRedirectHandler().redirect_request(
                request, None, 302, "Found", {}, "https://evil.example/collect"
            )

    def test_write_dry_run_needs_no_token(self) -> None:
        argv = [
            "gitlab_api.py",
            "--host",
            "https://gitlab.example.com",
            "fork-create",
            "group/repo",
            "--dry-run",
        ]
        with mock.patch.object(sys, "argv", argv):
            with mock.patch.object(gitlab_api, "load_token", side_effect=AssertionError("token loaded")):
                with mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
                    self.assertEqual(gitlab_api.main(), 0)
        self.assertIn('"dry_run": true', stdout.getvalue())

    def test_write_requires_confirmation(self) -> None:
        argv = [
            "gitlab_api.py",
            "--host",
            "https://gitlab.example.com",
            "fork-create",
            "group/repo",
        ]
        with mock.patch.object(sys, "argv", argv):
            with mock.patch("sys.stderr", new_callable=io.StringIO) as stderr:
                self.assertEqual(gitlab_api.main(), 1)
        self.assertIn("--confirm-write", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
