from contextlib import redirect_stdout
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import evidence
from _runtime import EvidenceError

SCRIPTS = Path(__file__).resolve().parents[1]
HTML = b'<article class="ltx_document"><h1 class="ltx_title_document">Title</h1><section id="S1"><h2>Results</h2><p>Observed result.</p></section></article>'


class CliTests(unittest.TestCase):
    def test_latest_arxiv_is_pinned_before_html_read(self):
        client = Mock()
        client.get.return_value = HTML
        record = {"id": "arxiv:2501.12948v2", "identifiers": {"arxiv": "2501.12948v2"}, "version": 2}
        with patch.object(evidence._sources, "resolve", return_value=record):
            result = evidence.read("arxiv:2501.12948", "S1", 500, client)
        client.get.assert_called_once_with("arxiv-html", "/html/2501.12948v2")
        self.assertEqual(result["id"], "arxiv:2501.12948v2")
        self.assertEqual(result["sections"][0]["text"], "Observed result.")

    def test_unresolved_version_cannot_be_replaced_by_latest_html(self):
        client = Mock()
        with patch.object(evidence._sources, "resolve", return_value={"id": "arxiv:2501.12948", "identifiers": {"arxiv": "2501.12948"}}):
            with self.assertRaisesRegex(EvidenceError, "version_not_resolved"):
                evidence.read("arxiv:2501.12948", None, 500, client)
        client.get.assert_not_called()

    def test_pinned_version_is_not_re_resolved(self):
        client = Mock()
        client.get.return_value = HTML
        with patch.object(evidence._sources, "resolve") as resolver:
            result = evidence.read("arxiv:2501.12948v1", "Results", 500, client)
        resolver.assert_not_called()
        client.get.assert_called_once_with("arxiv-html", "/html/2501.12948v1")
        self.assertEqual(result["id"], "arxiv:2501.12948v1")

    def test_wrong_read_identifier_never_contacts_network(self):
        for value in ["https://example.org/private", "arxiv:9913.12345", "doi:10.1234/test"]:
            client = Mock()
            with self.assertRaises((ValueError, EvidenceError)):
                evidence.read(value, None, 500, client)
            client.get.assert_not_called()

    def test_error_has_nonzero_exit_and_no_success_stdout(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / "evidence.py"), "resolve", "not-a-source"],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertEqual(json.loads(result.stderr)["error"], "invalid-identifier")

    def test_installed_helpers_do_not_write_bytecode_on_help(self):
        with tempfile.TemporaryDirectory() as root:
            copied = Path(root) / "scripts"
            shutil.copytree(SCRIPTS, copied, ignore=shutil.ignore_patterns("tests", "__pycache__"))
            for script in ["evidence.py", "setup.py"]:
                result = subprocess.run([sys.executable, str(copied / script), "--help"], capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(list(copied.rglob("*.pyc")))


if __name__ == "__main__":
    unittest.main()
