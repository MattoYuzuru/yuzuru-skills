from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class LegacySkillWrapperTests(unittest.TestCase):
    def environment(self, root: Path) -> dict[str, str]:
        environment = os.environ.copy()
        environment.update(
            {
                "HOME": str(root / "home"),
                "XDG_DATA_HOME": str(root / "data"),
                "YUZURU_CODEX_SKILLS_DIR": str(root / "codex-skills"),
                "YUZURU_CLAUDE_SKILLS_DIR": str(root / "claude-skills"),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        return environment

    def test_list_remains_skill_only(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [str(ROOT / "skill"), "list"],
                cwd=ROOT,
                env=self.environment(Path(directory)),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("search-workflow", result.stdout)
            self.assertNotIn("sde-agent", result.stdout)

    def test_validate_keeps_old_command_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [str(ROOT / "skill"), "validate", "search-workflow"],
                cwd=ROOT,
                env=self.environment(Path(directory)),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("search-workflow", result.stdout)


if __name__ == "__main__":
    unittest.main()
