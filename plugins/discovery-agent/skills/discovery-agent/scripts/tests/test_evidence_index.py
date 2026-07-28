from __future__ import annotations

import unittest

from evidence_index import summarize


class EvidenceIndexTests(unittest.TestCase):
    def test_summarizes_valid_entries(self) -> None:
        payload, ok = summarize(
            [
                {
                    "id": "SRC-1",
                    "source": "https://example.test/a",
                    "claim": "A current constraint exists",
                    "confidence": "high",
                    "kind": "fact",
                    "geography": "RU",
                }
            ]
        )
        self.assertTrue(ok)
        self.assertEqual(payload["geographies"], {"RU": 1})

    def test_duplicate_id_fails(self) -> None:
        entry = {
            "id": "SRC-1",
            "source": "https://example.test/a",
            "claim": "Claim",
            "confidence": "medium",
            "kind": "inference",
        }
        payload, ok = summarize([entry, {**entry, "source": "https://example.test/b"}])
        self.assertFalse(ok)
        self.assertIn("duplicate id: SRC-1", payload["errors"])


if __name__ == "__main__":
    unittest.main()
