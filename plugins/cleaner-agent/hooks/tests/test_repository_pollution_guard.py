import unittest

from repository_pollution_guard import blocked_reason, extract_paths


class PollutionGuardTests(unittest.TestCase):
    def test_blocks_cache_and_bytecode(self):
        self.assertIsNotNone(blocked_reason("repo/__pycache__/module.pyc"))
        self.assertIsNotNone(blocked_reason("repo/module.pyc"))

    def test_allows_source_and_docs(self):
        self.assertIsNone(blocked_reason("src/module.py"))
        self.assertIsNone(blocked_reason("docs/guide.md"))
        self.assertIsNone(blocked_reason("fixtures/example.log"))

    def test_extracts_multi_edit_paths(self):
        payload = {"tool_input": {"edits": [{"file_path": "a.md"}, {"file_path": "b.md"}]}}
        self.assertEqual(extract_paths(payload), ["a.md", "b.md"])


if __name__ == "__main__":
    unittest.main()
