"""Check corpus separation and reuse of the existing editorial contract.

These tests do not certify semantic quality; fresh producer outputs are reviewed
separately during maintenance.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import reader_value


class WritingJudgmentTests(unittest.TestCase):
    def test_cases_cover_edit_keep_and_scope_without_expected_output(self):
        data = json.loads((ROOT / "evals/writing-judgment-cases.json").read_text())
        self.assertIn("fictional", data["data_origin"])
        cases = data["cases"]
        self.assertEqual(len({c["id"] for c in cases}), len(cases))
        self.assertEqual({c["kind"] for c in cases},
                         {"should_fix", "should_not_fix", "relation_preservation"})
        for case in cases:
            self.assertTrue(case["request"])
            self.assertTrue(case["source_material"])
            self.assertTrue(case["expected_behaviors"])
            self.assertTrue(case["forbidden_behaviors"])
            self.assertNotIn("expected_output", case)

    def test_existing_evidence_is_required_without_new_style_fields(self):
        review = reader_value.template(("expression", "selection", "meaning"), "f" * 64)
        checks = review["checks"]
        self.assertEqual(review["version"], 2)
        self.assertEqual(set(checks["expression"]["craft_checks"]),
                         {"concrete_detail", "progression", "reading_flow"})
        self.assertNotIn("literary_score", checks["expression"])
        text = "The result is still unknown."
        for check in checks.values():
            check.update(status="pass", action="keep", location="opening",
                         quote=text, reader_effect="Preserves the unknown result.",
                         protected_meaning="No result has been established.")
        for probe in checks["expression"]["craft_checks"].values():
            probe.update(status="pass", quote=text, reason="The reader can identify the missing result.")
        checks["selection"]["removal_effect"] = "Removing this hides the unknown result."
        checks["meaning"].update(source_quote=text, detail_support="No extra result was added.")
        self.assertEqual(reader_value.validate(review, tuple(checks), "f" * 64, text, source=text), [])
        checks["expression"]["craft_checks"]["reading_flow"]["reason"] = ""
        self.assertTrue(reader_value.validate(review, tuple(checks), "f" * 64, text, source=text))

    def test_complete_examples_are_conditionally_routed(self):
        entry = (ROOT / "SKILL.md").read_text()
        craft = (ROOT / "references/writing-craft.md").read_text()
        bank = ROOT / "references/writing-composition-examples.md"
        self.assertTrue(bank.is_file())
        self.assertIn("writing-composition-examples.md", craft)
        self.assertNotIn("writing-composition-examples.md", entry)


if __name__ == "__main__":
    unittest.main()

