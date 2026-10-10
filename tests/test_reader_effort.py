"""Fixture coverage only; semantic behavior is checked by independent producers."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReaderEffortCorpusTests(unittest.TestCase):
    def test_fix_keep_and_fidelity_cases_are_ready_for_answer_blind_generation(self):
        data = json.loads((ROOT / "evals/reader-effort-cases.json").read_text())
        self.assertIn("fictional", data["data_origin"])
        cases = data["cases"]
        self.assertEqual(len(cases), len({case["id"] for case in cases}))
        self.assertEqual({case["kind"] for case in cases},
                         {"should_fix", "should_not_fix", "relation_preservation"})
        for case in cases:
            for field in ("request", "source_material", "expected_behaviors", "forbidden_behaviors"):
                self.assertTrue(case[field], (case["id"], field))
            self.assertNotIn("expected_output", case)


if __name__ == "__main__":
    unittest.main()

