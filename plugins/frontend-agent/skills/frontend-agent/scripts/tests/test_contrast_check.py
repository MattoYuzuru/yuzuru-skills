from __future__ import annotations

import unittest

from contrast_check import evaluate, ratio


class ContrastTests(unittest.TestCase):
    def test_black_white_ratio(self) -> None:
        self.assertAlmostEqual(ratio("#000000", "#ffffff"), 21.0, places=3)

    def test_low_contrast_is_reported_not_parse_error(self) -> None:
        payload, ok = evaluate(
            [{"id": "muted", "foreground": "#777777", "background": "#888888"}]
        )
        self.assertTrue(ok)
        self.assertFalse(payload["results"][0]["aa_normal"])

    def test_invalid_color_fails(self) -> None:
        _, ok = evaluate([{"foreground": "purple", "background": "#ffffff"}])
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
