"""Corpus checks; generation quality requires separate source-based judging."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExpressionOutcomeCorpusTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "evals/reader-expression-cases.json").read_text())
        self.cases = self.data["cases"]

    def test_cases_are_synthetic_and_keep_expected_behavior_out_of_requests(self):
        self.assertIn("fictional", self.data["data_origin"])
        self.assertEqual(len(self.cases), len({c["id"] for c in self.cases}))
        self.assertEqual({c["kind"] for c in self.cases},
                         {"should_fix", "should_not_fix", "relation_preservation"})
        for case in self.cases:
            for field in ("request", "source_material", "expected_behaviors", "forbidden_behaviors"):
                self.assertTrue(case[field], (case["id"], field))
            self.assertNotIn("expected_output", case)

    def test_four_focus_areas_and_observation_tags_are_traceable(self):
        self.assertEqual({f for c in self.cases for f in c["focus"]},
                         {"relevance", "syntax", "caveats", "progression"})
        valid = {f"H{i:02}" for i in range(1, 8)} | {f"A{i:02}" for i in range(1, 6)}
        for case in self.cases:
            self.assertTrue(case["observations"])
            self.assertLessEqual(set(case["observations"]), valid)


if __name__ == "__main__":
    unittest.main()

