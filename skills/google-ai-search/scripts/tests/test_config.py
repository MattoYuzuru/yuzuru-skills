from __future__ import annotations

import contextlib
import io
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import api_config
import search
import setup


class ModelConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.environment = mock.patch.dict(
            os.environ,
            {
                "GOOGLE_AI_SEARCH_CONFIG_DIR": self.temporary.name,
                "GOOGLE_AI_SEARCH_API_KEY": "test-key",
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.saved_env_model = os.environ.pop("GOOGLE_AI_SEARCH_MODEL", None)
        self.addCleanup(self._restore_env_model)

    def _restore_env_model(self) -> None:
        if self.saved_env_model is not None:
            os.environ["GOOGLE_AI_SEARCH_MODEL"] = self.saved_env_model

    def test_default_and_saved_model(self) -> None:
        self.assertEqual(api_config.resolve_model(), ("gemini-2.5-flash-lite", "default"))
        path = api_config.save_model("custom-model")
        self.assertEqual(api_config.resolve_model(), ("custom-model", "saved_config"))
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)

    def test_resolution_precedence(self) -> None:
        api_config.save_model("saved-model")
        os.environ["GOOGLE_AI_SEARCH_MODEL"] = "environment-model"
        self.assertEqual(api_config.resolve_model(), ("environment-model", "env"))
        self.assertEqual(api_config.resolve_model("cli-model"), ("cli-model", "cli"))

    def test_invalid_saved_model_and_unreadable_config(self) -> None:
        api_config.model_path().write_text("bad/model\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Invalid saved model"):
            api_config.resolve_model()
        api_config.model_path().write_bytes(b"\xff")
        with self.assertRaisesRegex(ValueError, "Cannot read saved model"):
            api_config.resolve_model()
        api_config.model_path().unlink()
        api_config.model_path().mkdir()
        with self.assertRaisesRegex(ValueError, "Cannot read saved model"):
            api_config.resolve_model()

    def test_invalid_environment_and_cli_model(self) -> None:
        os.environ["GOOGLE_AI_SEARCH_MODEL"] = ""
        with self.assertRaises(ValueError):
            api_config.resolve_model()
        with self.assertRaises(ValueError):
            api_config.resolve_model("bad/model")
        self.assertEqual(api_config.resolve_model("safe-model"), ("safe-model", "cli"))

    def test_check_json_reports_model_source_without_key(self) -> None:
        api_config.save_model("saved-model")
        output = io.StringIO()
        with mock.patch.object(sys, "argv", ["setup.py", "check"]), contextlib.redirect_stdout(output):
            self.assertEqual(setup.main(), 0)
        status = json.loads(output.getvalue())
        self.assertEqual((status["model"], status["model_source"]), ("saved-model", "saved_config"))
        self.assertNotIn("test-key", output.getvalue())

    def test_check_json_reports_invalid_saved_model(self) -> None:
        api_config.model_path().write_text("bad/model", encoding="utf-8")
        output = io.StringIO()
        with mock.patch.object(sys, "argv", ["setup.py", "check"]), contextlib.redirect_stdout(output):
            self.assertEqual(setup.main(), 2)
        status = json.loads(output.getvalue())
        self.assertFalse(status["ready"])
        self.assertIsNone(status["model_source"])
        self.assertIn("Invalid saved model", status["error"])

    def test_configure_enter_accepts_default_and_saves_key(self) -> None:
        output = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["setup.py", "configure"]),
            mock.patch.object(setup.getpass, "getpass", return_value="test-key"),
            mock.patch.object(setup, "validate_api_key", return_value=(True, None)),
            mock.patch("builtins.input", return_value=""),
            mock.patch.object(setup, "install_launcher", return_value={"installed": True}),
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(setup.main(), 0)
        self.assertEqual(api_config.resolve_model(), (api_config.DEFAULT_MODEL, "saved_config"))
        self.assertEqual(api_config.key_path().read_text(encoding="utf-8"), "test-key\n")
        self.assertNotIn("test-key", output.getvalue())

    def test_configure_custom_model_persists(self) -> None:
        with (
            mock.patch.object(setup.getpass, "getpass", return_value="test-key"),
            mock.patch.object(setup, "validate_api_key", return_value=(True, None)),
            mock.patch("builtins.input", return_value="custom-model"),
            mock.patch.object(setup, "install_launcher", return_value={"installed": True}),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(setup.configure(mock.Mock(skip_validation=False, timeout=1)), 0)
        self.assertEqual(api_config.resolve_model(), ("custom-model", "saved_config"))

    def test_search_cli_override_is_resolved_before_request(self) -> None:
        api_config.save_model("saved-model")
        os.environ["GOOGLE_AI_SEARCH_MODEL"] = "environment-model"
        observed = {}

        def fake_run(args):
            observed["model"] = args.model
            return {"answer": "ok"}

        with (
            mock.patch.object(sys, "argv", ["search.py", "--query", "q", "--model", "cli-model"]),
            mock.patch.object(search, "run", side_effect=fake_run),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(search.main(), 0)
        self.assertEqual(observed["model"], "cli-model")


if __name__ == "__main__":
    unittest.main()
