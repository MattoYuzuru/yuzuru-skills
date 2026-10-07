from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from validate_plugins import Result, cross_validate, validate_package


ROOT = Path(__file__).resolve().parents[2]


class PluginValidationTests(unittest.TestCase):
    def test_current_marketplaces_and_identifiers_are_consistent(self):
        self.assertEqual(cross_validate([]), [])

    def test_detects_canonical_version_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "sde-agent"
            shutil.copytree(ROOT / "plugins" / "sde-agent", plugin)
            manifest_path = plugin / ".claude-plugin" / "plugin.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["version"] = "99.0.0"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = validate_package(plugin)

            self.assertTrue(any("manifest version drift" in error for error in result.errors))

    def test_manifest_loader_rejects_missing_components(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "sde-agent"
            shutil.copytree(ROOT / "plugins" / "sde-agent", plugin)
            shutil.rmtree(plugin / "skills")

            result = validate_package(plugin)

            self.assertTrue(any("missing skills path" in error for error in result.errors))

    def test_one_authored_skill_without_specialist_agent_is_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "sde-agent"
            shutil.copytree(ROOT / "plugins" / "sde-agent", plugin)
            shutil.rmtree(plugin / "agents")
            for child in (plugin / "skills").iterdir():
                if child.name != "sde-agent":
                    shutil.rmtree(child)
            (plugin / "skills" / "sde-agent" / "SKILL.md").write_text(
                "---\nname: sde-agent\ndescription: Implement bounded software behavior. "
                "Use when a concrete source change is requested.\n---\n\n"
                "Implement the local contract and run relevant checks.\n")
            result = validate_package(plugin)
            self.assertEqual(result.errors, [])


if __name__ == "__main__":
    unittest.main()
