from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repository_inventory import inventory


class RepositoryInventoryTests(unittest.TestCase):
    def test_finds_docs_build_and_language(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# Test\n")
            (root / "pyproject.toml").write_text("[build-system]\n")
            (root / "main.py").write_text("print('ok')\n")
            result = inventory(root, 100)
            self.assertEqual(result["languages"], {"Python": 1})
            self.assertIn("README.md", result["documentation"])
            self.assertIn("pyproject.toml", result["build_files"])


if __name__ == "__main__":
    unittest.main()
