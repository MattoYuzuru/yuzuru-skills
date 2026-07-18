from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class NewSkillTests(unittest.TestCase):
    def test_codex_target_gets_valid_ui_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory) / "skills"
            skills_dir.mkdir()
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "new_skill.py"),
                    "example-workflow",
                    "--description",
                    "Perform a deterministic example workflow. Use when the user requests an example.",
                    "--skills-dir",
                    str(skills_dir),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            metadata = (skills_dir / "example-workflow" / "agents" / "openai.yaml").read_text()
            self.assertIn('display_name: "Example Workflow"', metadata)
            self.assertIn("$example-workflow", metadata)

    def test_claude_only_target_omits_codex_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory) / "skills"
            skills_dir.mkdir()
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "new_skill.py"),
                    "claude-example",
                    "--description",
                    "Perform a deterministic Claude workflow. Use when the user requests it.",
                    "--targets",
                    "claude",
                    "--skills-dir",
                    str(skills_dir),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((skills_dir / "claude-example" / "agents").exists())


if __name__ == "__main__":
    unittest.main()
