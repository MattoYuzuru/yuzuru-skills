import tempfile
import unittest
from pathlib import Path

from cleanup_candidates import scan


class CleanupCandidatesTests(unittest.TestCase):
    def test_finds_runtime_artifacts_without_deleting_them(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cached = root / "__pycache__"
            cached.mkdir()
            log = root / "run.log"
            log.write_text("diagnostic", encoding="utf-8")

            result = scan(root, 10)

            paths = {item["path"] for item in result["candidates"]}
            self.assertIn("__pycache__", paths)
            self.assertIn("run.log", paths)
            self.assertTrue(cached.exists())
            self.assertTrue(log.exists())

    def test_bounds_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index in range(3):
                (root / f"{index}.tmp").write_text("", encoding="utf-8")
            result = scan(root, 2)
            self.assertEqual(result["count"], 2)
            self.assertTrue(result["truncated"])


if __name__ == "__main__":
    unittest.main()
