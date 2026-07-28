from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from delivery_inventory import inventory


class DeliveryInventoryTests(unittest.TestCase):
    def test_detects_delivery_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".github" / "workflows").mkdir(parents=True)
            (root / ".github" / "workflows" / "ci.yml").write_text("name: ci\n")
            (root / "Dockerfile").write_text("FROM scratch\n")
            result = inventory(root, 10)
            self.assertEqual(result["categories"]["github_actions"], [".github/workflows/ci.yml"])
            self.assertEqual(result["categories"]["containers"], ["Dockerfile"])


if __name__ == "__main__":
    unittest.main()
