from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from github_workflow.auth import discover_credential
from github_workflow.errors import GitHubError


class AuthTests(unittest.TestCase):
    def test_environment_precedence(self) -> None:
        credential = discover_credential(
            environ={"GH_TOKEN": " first ", "GITHUB_TOKEN": "second"}, allow_gh=False
        )
        self.assertEqual((credential.token, credential.source), ("first", "GH_TOKEN"))

    def test_token_file_and_permissions_warning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "token"
            path.write_text("secret\n", encoding="utf-8")
            os.chmod(path, 0o644)
            credential = discover_credential(token_file=str(path), environ={}, allow_gh=False)
        self.assertEqual(credential.source, "config-file")
        self.assertIn("0600", credential.warning)

    def test_gh_fallback(self) -> None:
        def runner(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 0, "from-gh\n", "")

        credential = discover_credential(environ={}, runner=runner)
        self.assertEqual((credential.token, credential.source), ("from-gh", "gh-auth"))

    def test_required_credential_raises_sanitized_error(self) -> None:
        with self.assertRaises(GitHubError) as caught:
            discover_credential(environ={}, allow_gh=False, required=True)
        self.assertEqual(caught.exception.kind, "auth")


if __name__ == "__main__":
    unittest.main()
