from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "search_setup.py"
SPEC = importlib.util.spec_from_file_location("search_setup", SCRIPT)
assert SPEC and SPEC.loader
search_setup = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = search_setup
SPEC.loader.exec_module(search_setup)


class SearchSetupTests(unittest.TestCase):
    def test_core_report_detects_valid_alternate_ast_grep(self) -> None:
        paths = {
            "rg": "/tools/rg",
            "sg": "/tools/sg",
            "rga": "/tools/rga",
            "jq": "/tools/jq",
            "yq": "/tools/yq",
            "brew": "/tools/brew",
            "mdfind": "/usr/bin/mdfind",
        }

        def which(command: str) -> str | None:
            return paths.get(command)

        def probe(path: str) -> str:
            if path.endswith("/sg"):
                return "ast-grep 0.44.1"
            if path.endswith("/yq"):
                return "yq version v4.53.3"
            return ""

        report = search_setup.build_report("core", "Darwin", which=which, probe=probe)
        self.assertTrue(report["complete"])
        self.assertEqual(report["routes"]["ast-grep"]["command"], "sg")
        self.assertEqual(report["indexed_search"]["command"], "mdfind")
        self.assertEqual(report["install_commands"], [])

    def test_wrong_sg_binary_is_not_accepted(self) -> None:
        paths = {"rg": "/tools/rg", "sg": "/usr/bin/sg", "apt-get": "/usr/bin/apt-get"}
        report = search_setup.build_report(
            "minimal",
            "Linux",
            which=paths.get,
            probe=lambda _path: "util-linux sg 2.40",
        )
        self.assertFalse(report["complete"])
        self.assertIn("ast-grep", report["missing"])
        self.assertIn("ast-grep", report["manual_sources"])

    def test_unrelated_python_yq_is_not_accepted(self) -> None:
        paths = {"rg": "/tools/rg", "yq": "/tools/yq"}
        report = search_setup.build_report(
            "core",
            "Linux",
            which=paths.get,
            probe=lambda path: "yq 3.4.3" if path.endswith("/yq") else "",
        )
        self.assertFalse(report["routes"]["yq"]["available"])
        self.assertIn("yq", report["missing"])

    def test_linux_uses_available_language_package_managers(self) -> None:
        paths = {
            "apt-get": "/usr/bin/apt-get",
            "npm": "/usr/bin/npm",
            "cargo": "/usr/bin/cargo",
            "snap": "/usr/bin/snap",
        }
        report = search_setup.build_report(
            "core", "Linux", which=paths.get, probe=lambda _path: ""
        )
        self.assertIn("sudo apt-get install ripgrep jq", report["install_commands"])
        self.assertIn("npm install --global @ast-grep/cli", report["install_commands"])
        self.assertIn("cargo install ripgrep_all --locked", report["install_commands"])
        self.assertIn("sudo snap install yq", report["install_commands"])
        self.assertEqual(report["manual_sources"], {})

    def test_brew_plan_is_one_non_executed_command(self) -> None:
        paths = {"brew": "/opt/homebrew/bin/brew", "mdfind": "/usr/bin/mdfind"}
        report = search_setup.build_report(
            "core", "Darwin", which=paths.get, probe=lambda _path: ""
        )
        self.assertFalse(report["baseline_ready"])
        self.assertEqual(len(report["install_commands"]), 1)
        self.assertEqual(
            report["install_commands"][0],
            "brew install ripgrep ast-grep rga jq yq",
        )

    def test_cli_emits_compact_json(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "check", "--profile", "minimal"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["profile"], "minimal")
        self.assertIn("routes", payload)


if __name__ == "__main__":
    unittest.main()
