from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from check_pollution import event_paths, find_pollution, pollution_reason


class PollutionTests(unittest.TestCase):
    def test_finds_runtime_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".venv").mkdir()
            self.assertEqual(find_pollution(root), [".venv"])

    def test_ignores_git_internal_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git" / "__pycache__").mkdir(parents=True)
            self.assertEqual(find_pollution(root), [])

    def test_checks_only_event_paths_in_hook_mode(self) -> None:
        event = {"tool_input": {"file_path": "project/__pycache__/module.pyc"}}
        paths = event_paths(event)
        self.assertEqual([str(path) for path in paths], ["project/__pycache__/module.pyc"])
        self.assertIsNotNone(pollution_reason(paths[0]))
        self.assertIsNone(pollution_reason(Path("project/src/module.py")))


if __name__ == "__main__":
    unittest.main()
