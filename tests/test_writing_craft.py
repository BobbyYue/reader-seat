"""Synthetic corpus integrity, not a substitute for fresh generation judging."""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import reader_value

class WritingCraftCorpusTests(unittest.TestCase):
    def test_context_cases_map_to_optional_bank_without_new_receipt_fields(self):
        data = json.loads((ROOT / "evals/writing-craft-context-cases.json").read_text())
        self.assertIn("fictional", data["data_origin"])
        bank = (ROOT / "references/writing-craft-cases.md").read_text()
        anchors = set(re.findall(r"^## (W\d{2})\b", bank, re.M))
        self.assertEqual(anchors, {f"W{i:02}" for i in range(1, 9)})
        self.assertEqual(set(re.findall(r"\bT\d{2}\b", bank)), {f"T{i:02}" for i in range(1, 11)})
        cases = data["cases"]
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        self.assertEqual({c["kind"] for c in cases}, {"should_fix", "should_not_fix", "relation_preservation"})
        for case in cases:
            self.assertTrue(set(case["reference_cases"]) <= anchors, case["id"])
            for field in ("request", "source_material", "expected_behaviors", "forbidden_behaviors"):
                self.assertTrue(case[field], (case["id"], field))
        prepared = reader_value.template(("expression", "meaning"), "a" * 64)
        self.assertEqual(prepared["version"], 2)
        self.assertEqual(set(prepared["checks"]["expression"]["craft_checks"]),
                         {"concrete_detail", "progression", "reading_flow"})
        self.assertEqual(set(prepared["checks"]["meaning"]),
                         {"status", "action", "location", "quote", "reader_effect",
                          "protected_meaning", "source_quote", "detail_support"})

    def test_corpus_has_fix_keep_and_fidelity_cases(self):
        data = json.loads((ROOT / "evals/writing-craft-cases.json").read_text())
        self.assertIn("fictional", data["data_origin"])
        cases = data["cases"]
        self.assertEqual(len({c["id"] for c in cases}), len(cases))
        self.assertEqual({c["kind"] for c in cases}, {"should_fix", "should_not_fix", "relation_preservation"})
        for case in cases:
            for field in ("request", "source_material", "expected_behaviors", "forbidden_behaviors"):
                self.assertTrue(case[field], (case["id"], field))
    def test_runtime_guidance_exposes_each_mandatory_probe(self):
        for key in reader_value.CRAFT_GUIDANCE:
            self.assertIn(key, reader_value.GUIDANCE["expression"])
        self.assertIn("detail_support", reader_value.GUIDANCE["meaning"])
    def test_reference_is_reachable_and_preserves_scope(self):
        reference = (ROOT / "references/writing-craft.md").read_text()
        self.assertIn("fictional", reference)
        self.assertIn("existing", reference)
        entry = (ROOT / "SKILL.md").read_text()
        for path in (ROOT / "references").glob("*.md"):
            entry += path.read_text()
        self.assertIn("writing-craft.md", entry)

if __name__ == "__main__":
    unittest.main()
