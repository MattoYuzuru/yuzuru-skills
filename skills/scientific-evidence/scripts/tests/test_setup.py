import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import _runtime

SPEC = importlib.util.spec_from_file_location("evidence_setup", Path(__file__).resolve().parents[1] / "setup.py")
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)


class SetupTests(unittest.TestCase):
    def test_unreadable_optional_key_does_not_disable_core(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {"XDG_CONFIG_HOME": root}, clear=True):
            path = _runtime.key_path()
            path.parent.mkdir()
            path.write_bytes(b"\xff\xfe")
            path.chmod(0o600)
            value = setup.check()
            self.assertTrue(value["ready"])
            self.assertEqual(value["openalex"]["configuration_issue"], "optional_key_unreadable")

    def test_keyless_core_remains_ready_with_optional_key_absent(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {"XDG_CONFIG_HOME": root}, clear=True):
            value = setup.check()
            self.assertTrue(value["ready"])
            self.assertFalse(value["openalex"]["key_configured"])
            self.assertEqual(value["mode"], "keyless-core")
            self.assertFalse(Path(root, "scientific-evidence").exists())

    def test_configure_never_falls_back_to_echoed_input(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {"XDG_CONFIG_HOME": root}, clear=True), \
             patch.object(sys, "argv", ["setup.py", "configure", "openalex"]), \
             patch.object(sys.stdin, "isatty", return_value=False), patch.object(setup.getpass, "getpass") as secret:
            with self.assertRaisesRegex(_runtime.EvidenceError, "hidden_terminal"):
                setup.main()
            secret.assert_not_called()

    def test_dry_run_creates_nothing_and_never_prompts(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {"XDG_CONFIG_HOME": root}, clear=True), \
             patch.object(sys, "argv", ["setup.py", "configure", "openalex", "--dry-run"]), \
             patch.object(setup.getpass, "getpass") as secret, contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(setup.main(), 0)
            self.assertTrue(json.loads(out.getvalue())["dry_run"])
            secret.assert_not_called()
            self.assertFalse(Path(root, "scientific-evidence").exists())

    def test_remove_requires_exact_action_flag_and_preserves_environment(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {"XDG_CONFIG_HOME": root, "OPENALEX_API_KEY": "environment-test-key"}, clear=True):
            path = _runtime.save_key("stored-test-key")
            with patch.object(sys, "argv", ["setup.py", "remove-key", "openalex"]):
                with self.assertRaisesRegex(_runtime.EvidenceError, "confirm_remove"):
                    setup.main()
            self.assertTrue(path.exists())
            with patch.object(sys, "argv", ["setup.py", "remove-key", "openalex", "--confirm-remove"]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(setup.main(), 0)
            self.assertFalse(path.exists())
            self.assertEqual(os.environ["OPENALEX_API_KEY"], "environment-test-key")


if __name__ == "__main__":
    unittest.main()
