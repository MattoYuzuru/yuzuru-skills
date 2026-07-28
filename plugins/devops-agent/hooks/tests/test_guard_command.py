from __future__ import annotations

import unittest

from guard_command import FORBIDDEN, extract_command


class GuardCommandTests(unittest.TestCase):
    def test_extracts_hook_command(self) -> None:
        self.assertEqual(extract_command({"tool_input": {"command": "echo ok"}}), "echo ok")

    def test_blocks_root_delete(self) -> None:
        self.assertTrue(any(pattern.search("rm -rf /") for pattern in FORBIDDEN))

    def test_allows_scoped_cleanup(self) -> None:
        self.assertFalse(any(pattern.search("rm -rf /tmp/yuzuru-test-123") for pattern in FORBIDDEN))


if __name__ == "__main__":
    unittest.main()
