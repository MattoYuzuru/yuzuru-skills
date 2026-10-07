from __future__ import annotations

import unittest

from skill_eval import cases, score, validate_contract


def contract():
    return {"version": 1, "skills": [{"skill": "example", "path": "skills/example/SKILL.md",
            "status": "active", "should_trigger": ["Perform A", "Perform B"],
            "should_not_trigger": ["Explain C", "Explain D"], "expectations": ["Preserve scope"]}]}


class SkillEvalTests(unittest.TestCase):
    def test_qualified_plugin_identity_is_accepted_but_wrong_namespace_is_not(self):
        value = contract()
        value["skills"][0]["path"] = "plugins/example-plugin/skills/example/SKILL.md"
        expected = cases(value)
        data = {"version": 1, "model": "test-model", "effort": "test", "revision": "fixture",
                "runs": [{"case_id": expected[0]["case_id"], "loaded_skills": ["example-plugin:example"]}]}
        self.assertEqual(score(expected, data, True)["selection"]["true_positive"], 1)
        data["runs"][0]["loaded_skills"] = ["wrong-plugin:example"]
        self.assertEqual(score(expected, data, True)["selection"]["false_negative"], 1)
    def test_coverage_drift_and_duplicate_entries_are_rejected(self):
        value = contract()
        self.assertEqual(validate_contract(value, {"skills/example/SKILL.md"}), [])
        self.assertTrue(validate_contract(value, {"skills/other/SKILL.md"}))
        value["skills"].append(value["skills"][0])
        self.assertTrue(validate_contract(value, {"skills/example/SKILL.md"}))

    def test_observed_selection_distinguishes_false_positive_and_negative(self):
        expected = cases(contract())
        result = score(expected, {"version": 1, "model": "test-model", "effort": "test",
                       "revision": "fixture", "runs": [
                           {"case_id": expected[0]["case_id"], "loaded_skills": ["example"]},
                           {"case_id": expected[1]["case_id"], "loaded_skills": []},
                           {"case_id": expected[2]["case_id"], "loaded_skills": ["example"]},
                           {"case_id": expected[3]["case_id"], "loaded_skills": ["other"]}]})
        self.assertFalse(result["ok"])
        self.assertEqual(result["selection"], {"true_positive": 1, "false_positive": 1,
                                               "true_negative": 1, "false_negative": 1})
        self.assertEqual(result["quality_checks"], 0)

    def test_partial_duplicate_deferred_and_quality_failure(self):
        expected = cases(contract())
        data = {"version": 1, "model": "test-model", "effort": "test", "revision": "fixture",
                "runs": [{"case_id": expected[0]["case_id"], "loaded_skills": ["example"],
                          "expectations_passed": True}]}
        self.assertFalse(score(expected, data)["ok"])
        result = score(expected, data, allow_partial=True)
        self.assertTrue(result["ok"])
        self.assertFalse(result["complete"])
        data["runs"][0]["expectations_passed"] = False
        self.assertEqual(score(expected, data, True)["quality_failures"], 1)
        data["runs"].append(data["runs"][0])
        self.assertTrue(score(expected, data, True)["errors"])
        for item in expected:
            item["status"] = "deferred"
        self.assertTrue(score(expected, data, True)["errors"])


if __name__ == "__main__":
    unittest.main()
