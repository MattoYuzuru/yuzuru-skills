from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def snapshot(root: Path) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            result.add((relative, f"link:{os.readlink(path)}"))
        elif path.is_file():
            result.add((relative, f"file:{path.stat().st_size}"))
        elif path.is_dir():
            result.add((relative, "dir"))
    return result


class RepositoryCleanlinessTests(unittest.TestCase):
    def test_normal_read_and_inspection_commands_do_not_pollute_clone(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "repo"
            shutil.copytree(
                ROOT,
                fixture,
                symlinks=True,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            home = Path(directory) / "home"
            executable_dir = str(Path(sys.executable).parent)
            environment = {
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(home / "config"),
                "XDG_CACHE_HOME": str(home / "cache"),
                "XDG_DATA_HOME": str(home / "data"),
                "YUZURU_BIN_DIR": str(home / "bin"),
                "YUZURU_CODEX_SKILLS_DIR": str(home / "codex-skills"),
                "YUZURU_CLAUDE_SKILLS_DIR": str(home / "claude-skills"),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PATH": f"{executable_dir}:/usr/bin:/bin",
            }
            before = snapshot(fixture)
            commands = [
                ["list"],
                ["plugin", "inspect", "sde-agent"],
                ["plugin", "install", "sde-agent", "--agent", "claude", "--dry-run"],
                ["marketplace", "add", "--agent", "codex", "--dry-run"],
                ["validate", "--strict"],
                ["doctor", "--json"],
            ]
            for arguments in commands:
                result = subprocess.run(
                    [sys.executable, "-B", str(fixture / "scripts" / "yuzuru_cli.py"), *arguments],
                    cwd=fixture,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, f"{arguments}: {result.stdout}\n{result.stderr}")
            self.assertEqual(snapshot(fixture), before)


if __name__ == "__main__":
    unittest.main()
