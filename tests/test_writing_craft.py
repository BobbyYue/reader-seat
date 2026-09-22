"""Synthetic corpus integrity, not a substitute for fresh generation judging."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import reader_value

class WritingCraftCorpusTests(unittest.TestCase):
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
