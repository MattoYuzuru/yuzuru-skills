from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import search


class SearchTests(unittest.TestCase):
    def test_sources_are_deduplicated_and_bounded(self) -> None:
        metadata = {
            "groundingChunks": [
                {"web": {"uri": "https://example.com/1", "title": "One"}},
                {"web": {"uri": "https://example.com/1", "title": "Duplicate"}},
                {"web": {"uri": "https://example.com/2", "title": "Two"}},
            ]
        }
        self.assertEqual(search.parse_sources(metadata, 1), [{"title": "One", "url": "https://example.com/1"}])

    def test_usage_is_opt_in(self) -> None:
        payload = {
            "candidates": [
                {"content": {"parts": [{"text": "answer"}]}, "groundingMetadata": {}}
            ],
            "usageMetadata": {"totalTokenCount": 42},
        }
        base = dict(
            query="q",
            max_chars=1000,
            model="model",
            include_sources=False,
            max_sources=10,
        )
        without = search.parse_response(payload, argparse.Namespace(**base, include_usage=False))
        with_usage = search.parse_response(payload, argparse.Namespace(**base, include_usage=True))
        self.assertNotIn("usage", without)
        self.assertEqual(with_usage["usage"]["totalTokenCount"], 42)

    def test_query_and_numeric_bounds(self) -> None:
        self.assertEqual(search.bounded_query("  current docs "), "current docs")
        with self.assertRaises(argparse.ArgumentTypeError):
            search.bounded_query("")
        with self.assertRaises(argparse.ArgumentTypeError):
            search.bounded_query("x" * 2001)
        with self.assertRaises(argparse.ArgumentTypeError):
            search.bounded_int(1, 10)("11")

    def test_no_candidates_returns_a_structured_error(self) -> None:
        args = argparse.Namespace(query="q")
        result = search.parse_response(
            {"promptFeedback": {"blockReason": "SAFETY"}},
            args,
        )
        self.assertEqual(result["answer"], "")
        self.assertEqual(result["sources"], [])
        self.assertIn("SAFETY", result["error"])


if __name__ == "__main__":
    unittest.main()
