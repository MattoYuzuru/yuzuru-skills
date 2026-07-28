from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from capability_inventory import build_inventory


class CapabilityInventoryTests(unittest.TestCase):
    def test_inventory_distinguishes_declaration_from_health(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill = root / "skills" / "example"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: example\ndescription: Inspect examples. Use when examples need review.\n---\n",
                encoding="utf-8",
            )
            payload = build_inventory(root, 10)
            item = payload["capabilities"][0]
            self.assertEqual(item["id"], "example")
            self.assertEqual(item["health"], "unknown")
            self.assertEqual(item["platforms"], ["portable"])

    def test_limit_is_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("one", "two"):
                skill = root / "skills" / name
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text(
                    f"---\nname: {name}\ndescription: Inspect {name}. Use when requested.\n---\n",
                    encoding="utf-8",
                )
            payload = build_inventory(root, 1)
            self.assertEqual(len(payload["capabilities"]), 1)
            self.assertTrue(payload["truncated"])


if __name__ == "__main__":
    unittest.main()
