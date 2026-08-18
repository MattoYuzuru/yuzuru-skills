from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import check_invariants


class InvariantTests(unittest.TestCase):
    def test_preserves_russian_dates_numbers_units_and_versions(self) -> None:
        text = "Релиз v3.14.7 вышел 18 августа 2026 г.; лимит — 1,5 ГБ, диапазон 5–7 мс."
        result = check_invariants.inspect(text, text, ["лимит"])
        self.assertTrue(result["ok"])
        self.assertFalse(result["violations"])

    def test_reports_changed_number_url_code_and_quote(self) -> None:
        source = 'Откройте https://example.com/v1 и выполните `tool --limit 10`: «Готово». Цена — 500 ₽.'
        revision = 'Откройте https://example.com/v2 и выполните `tool --limit 20`: «Сделано». Цена — 600 ₽.'
        result = check_invariants.inspect(source, revision, [])
        self.assertFalse(result["ok"])
        self.assertIn("numbers", result["violations"])
        self.assertIn("urls", result["violations"])
        self.assertIn("inline_code", result["violations"])
        self.assertIn("quotes", result["violations"])

    def test_negation_change_is_warning_not_authorship_score(self) -> None:
        result = check_invariants.inspect("Сервис не удаляет данные.", "Сервис удаляет данные.", [])
        self.assertTrue(result["ok"])
        self.assertTrue(result["negation"]["changed"])
        self.assertTrue(result["warnings"])

    def test_missing_protected_term_is_violation(self) -> None:
        result = check_invariants.inspect(
            "Повторная доставка идемпотентна.",
            "Повторная доставка безопасна.",
            ["идемпотентна"],
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["protected_terms"]["missing"], ["идемпотентна"])


if __name__ == "__main__":
    unittest.main()
