from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yuzuru_cli


ROOT = Path(__file__).resolve().parents[2]


class YuzuruCliTests(unittest.TestCase):
    def environment(self, root: Path) -> dict[str, str]:
        environment = os.environ.copy()
        environment.update(
            {
                "HOME": str(root / "home"),
                "XDG_CONFIG_HOME": str(root / "config"),
                "XDG_CACHE_HOME": str(root / "cache"),
                "XDG_DATA_HOME": str(root / "data"),
                "YUZURU_CODEX_SKILLS_DIR": str(root / "codex-skills"),
                "YUZURU_CLAUDE_SKILLS_DIR": str(root / "claude-skills"),
                "YUZURU_BIN_DIR": str(root / "bin"),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        return environment

    def run_cli(self, environment: dict[str, str], *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts" / "yuzuru_cli.py"), *arguments],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_installs_and_uninstalls_managed_skill_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            environment = self.environment(root)
            installed = self.run_cli(
                environment, "skill", "install", "search-workflow", "--agent", "codex"
            )
            self.assertEqual(installed.returncode, 0, installed.stderr)
            destination = root / "codex-skills" / "search-workflow"
            self.assertTrue(destination.is_symlink())
            registry = json.loads((root / "data" / "yuzuru" / "registry.json").read_text())
            self.assertIn("codex/search-workflow", registry["managed_skill_links"])

            removed = self.run_cli(
                environment, "skill", "uninstall", "search-workflow", "--agent", "codex"
            )
            self.assertEqual(removed.returncode, 0, removed.stderr)
            self.assertFalse(destination.exists())
            self.assertFalse(destination.is_symlink())

    def test_refuses_unmanaged_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            environment = self.environment(root)
            destination = root / "codex-skills" / "search-workflow"
            destination.mkdir(parents=True)
            result = self.run_cli(
                environment, "skill", "install", "search-workflow", "--agent", "codex"
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("refusing to replace unmanaged", result.stderr)
            self.assertTrue(destination.is_dir())

    def test_repairs_stale_link_after_repository_move(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            environment = self.environment(root)
            destination = root / "codex-skills" / "search-workflow"
            destination.parent.mkdir(parents=True)
            destination.symlink_to("/previous/yuzuru-skills/skills/search-workflow")

            result = self.run_cli(
                environment, "skill", "install", "search-workflow", "--agent", "codex"
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("repaired", result.stdout)
            self.assertEqual(os.readlink(destination), str(ROOT / "skills" / "search-workflow"))
            self.assertFalse((root / "claude-skills" / "search-workflow").exists())

    def test_repairs_append_only_skill_rename(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skills = root / "skills"
            new_source = skills / "new-name"
            new_source.mkdir(parents=True)
            (new_source / "SKILL.md").write_text("---\nname: new-name\n---\n", encoding="utf-8")
            migrations = root / "migrations.json"
            migrations.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "skill_renames": [{"from": "old-name", "to": "new-name"}],
                        "plugin_renames": [],
                    }
                ),
                encoding="utf-8",
            )
            codex_dir = root / "codex-skills"
            codex_dir.mkdir()
            old_link = codex_dir / "old-name"
            old_link.symlink_to("/previous/yuzuru-skills/skills/old-name")
            registry = yuzuru_cli.empty_registry()
            environment = {
                "YUZURU_CODEX_SKILLS_DIR": str(codex_dir),
                "YUZURU_CLAUDE_SKILLS_DIR": str(root / "claude-skills"),
            }
            with (
                mock.patch.object(yuzuru_cli, "SKILLS_DIR", skills),
                mock.patch.object(yuzuru_cli, "MIGRATIONS_PATH", migrations),
                mock.patch.dict(os.environ, environment, clear=False),
            ):
                pending, repaired, conflicts = yuzuru_cli.repair_renamed_skill_links(registry, True)
            self.assertEqual(len(pending), 1)
            self.assertEqual(conflicts, [])
            self.assertEqual(repaired, [str(codex_dir / "new-name")])
            self.assertFalse(old_link.is_symlink())
            self.assertEqual(os.readlink(codex_dir / "new-name"), str(new_source))

    def test_dry_run_does_not_require_native_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            environment = self.environment(Path(directory))
            environment["PATH"] = str(Path(sys.executable).parent)
            result = self.run_cli(
                environment,
                "plugin",
                "install",
                "sde-agent",
                "--agent",
                "claude",
                "--dry-run",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "dry_run")
            self.assertFalse(payload["cli_available"])

    def test_parses_codex_and_claude_native_state(self):
        states = yuzuru_cli.parse_native_plugin_states(
            {
                "installed": [
                    {
                        "pluginId": "sde-agent@yuzuru-engineering",
                        "name": "sde-agent",
                        "installed": True,
                        "enabled": False,
                        "version": "0.1.0",
                    }
                ],
                "claude_example": [
                    {
                        "id": "sre-agent@yuzuru-engineering",
                        "scope": "user",
                        "enabled": True,
                        "installPath": "/tmp/cache",
                        "version": "0.1.0",
                    }
                ],
            }
        )
        self.assertEqual(states["sde-agent"]["installed"], True)
        self.assertEqual(states["sde-agent"]["enabled"], False)
        self.assertEqual(states["sre-agent"]["installed"], True)
        self.assertEqual(states["sre-agent"]["enabled"], True)

    def test_codex_disable_reports_native_interaction(self):
        with tempfile.TemporaryDirectory() as directory:
            environment = self.environment(Path(directory))
            result = self.run_cli(
                environment, "plugin", "disable", "sde-agent", "--agent", "codex", "--dry-run"
            )
            self.assertEqual(result.returncode, 2)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "interaction_required")
            self.assertIn("/plugins", payload["next_action"])

    def test_update_refuses_dirty_tree_before_git_pull(self):
        with mock.patch.object(yuzuru_cli, "git_output", return_value=" M local-file"):
            with self.assertRaisesRegex(yuzuru_cli.CliError, "repository has local changes"):
                yuzuru_cli.cmd_update(mock.Mock())


if __name__ == "__main__":
    unittest.main()
