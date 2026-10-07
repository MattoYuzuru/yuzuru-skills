from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sync_plugin_versions as sync


class PluginVersionTests(unittest.TestCase):
    def test_check_and_sync_cover_all_three_hosts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plugin = root / "plugins" / "example"
            plugin.mkdir(parents=True)
            (plugin / "plugin-version.json").write_text(json.dumps({"version": "0.1.1"}))
            for relative in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json", "package.json"):
                path = plugin / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"name": "example", "version": "0.1.0", "private": True}))
            with patch.object(sync, "ROOT", root), patch("sys.argv", ["sync", "--check"]):
                self.assertEqual(sync.main(), 1)
            with patch.object(sync, "ROOT", root), patch("sys.argv", ["sync"]):
                self.assertEqual(sync.main(), 0)
            for relative in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json", "package.json"):
                value = json.loads((plugin / relative).read_text())
                self.assertEqual(value["version"], "0.1.1")
                self.assertTrue(value["private"])


if __name__ == "__main__":
    unittest.main()
