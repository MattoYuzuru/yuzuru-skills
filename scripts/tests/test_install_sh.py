from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class InstallerTests(unittest.TestCase):
    def run_installer(self, home: Path, bin_dir: Path) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["HOME"] = str(home)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [str(ROOT / "install.sh"), "--bin-dir", str(bin_dir)],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_installs_both_launchers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            result = self.run_installer(root / "home", bin_dir)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(os.readlink(bin_dir / "yuzuru"), str(ROOT / "yuzuru"))
            self.assertEqual(os.readlink(bin_dir / "skill"), str(ROOT / "skill"))

    def test_repairs_only_dangling_launcher_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            (bin_dir / "yuzuru").symlink_to("/previous/yuzuru-skills/yuzuru")
            (bin_dir / "skill").symlink_to("/previous/yuzuru-skills/skill")
            result = self.run_installer(root / "home", bin_dir)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("repaired stale symlink", result.stdout)
            self.assertEqual(os.readlink(bin_dir / "yuzuru"), str(ROOT / "yuzuru"))

    def test_refuses_unmanaged_launcher_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            unmanaged = bin_dir / "yuzuru"
            unmanaged.write_text("#!/bin/sh\n", encoding="utf-8")
            result = self.run_installer(root / "home", bin_dir)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not a symlink managed by this repo", result.stderr)
            self.assertTrue(unmanaged.is_file())

    def test_refuses_unrecognized_dangling_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            unmanaged = bin_dir / "yuzuru"
            unmanaged.symlink_to("/some-other-tool/yuzuru")
            result = self.run_installer(root / "home", bin_dir)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(os.readlink(unmanaged), "/some-other-tool/yuzuru")

    def test_dry_run_does_not_create_bin_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            environment = os.environ.copy()
            environment["HOME"] = str(root / "home")
            result = subprocess.run(
                [str(ROOT / "install.sh"), "--bin-dir", str(bin_dir), "--dry-run"],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("would install", result.stdout)
            self.assertFalse(bin_dir.exists())


if __name__ == "__main__":
    unittest.main()
