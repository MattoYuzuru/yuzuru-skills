from __future__ import annotations

import subprocess
import unittest

from github_workflow.errors import GitHubError
from github_workflow.targets import parse_repository, redact_url, resolve_repository


class TargetTests(unittest.TestCase):
    def test_parse_common_repository_forms(self) -> None:
        values = [
            "octo/repo",
            "https://github.com/octo/repo.git",
            "git" + "@" + "github.com:octo/repo.git",
            "ssh://git" + "@" + "github.example.com/octo/repo.git",
        ]
        parsed = [parse_repository(value) for value in values]
        self.assertEqual(parsed[0].full_name, "octo/repo")
        self.assertEqual(parsed[1].host, "github.com")
        self.assertEqual(parsed[2].full_name, "octo/repo")
        self.assertEqual(parsed[3].host, "github.example.com")

    def test_rejects_non_repository_paths(self) -> None:
        for value in ("octo", "a/b/c", "https://github.com/a/b/issues/1"):
            with self.subTest(value=value), self.assertRaises(GitHubError):
                parse_repository(value)

    def test_redacts_https_credentials(self) -> None:
        redacted = redact_url("https://user:" + "token" + "@github.com/a/b.git")
        self.assertNotIn("token", redacted)
        self.assertIn("***", redacted)

    def test_resolve_rejects_ambiguous_upstream_and_origin(self) -> None:
        def runner(command, **kwargs):
            if command == ["git", "remote"]:
                return subprocess.CompletedProcess(command, 0, "origin\nupstream\n", "")
            url = {
                "origin": "git" + "@" + "github.com:fork/repo.git",
                "upstream": "https://github.com/base/repo.git",
            }[command[-1]]
            return subprocess.CompletedProcess(command, 0, url + "\n", "")

        with self.assertRaises(GitHubError) as caught:
            resolve_repository(None, runner=runner)
        self.assertIn("ambiguous", caught.exception.message)


if __name__ == "__main__":
    unittest.main()
