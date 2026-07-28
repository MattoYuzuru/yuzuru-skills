from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class NewPluginTests(unittest.TestCase):
    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            plugins = Path(directory) / "plugins"
            plugins.mkdir()
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "new_plugin.py"),
                    "planned-plugin",
                    "--description",
                    "Package a bounded example capability for supported agents.",
                    "--plugins-dir",
                    str(plugins),
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "dry_run")
            self.assertFalse((plugins / "planned-plugin").exists())

    def test_scaffold_has_dual_manifests_and_canonical_version(self):
        with tempfile.TemporaryDirectory() as directory:
            plugins = Path(directory) / "plugins"
            plugins.mkdir()
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "new_plugin.py"),
                    "example-plugin",
                    "--description",
                    "Package a bounded example capability for supported agents.",
                    "--plugins-dir",
                    str(plugins),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            plugin = plugins / "example-plugin"
            version = json.loads((plugin / "plugin-version.json").read_text())["version"]
            codex = json.loads((plugin / ".codex-plugin" / "plugin.json").read_text())
            claude = json.loads((plugin / ".claude-plugin" / "plugin.json").read_text())
            self.assertEqual(version, "0.1.0")
            self.assertEqual(codex["version"], version)
            self.assertEqual(claude["version"], version)


if __name__ == "__main__":
    unittest.main()
