"""Executable evidence-contract tests; fresh forward runs test writing quality."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import reader_value
from editorial_fixture import structural_review


class ReaderValueTests(unittest.TestCase):
    def setUp(self):
        self.axes = ("expression", "selection", "meaning", "presentation", "unit_roles")
        self.text = "Only old links failed. The pilot does not establish production capacity."
        self.source = self.text
        self.binding = "a" * 64
        self.render = "/tmp/structural-fixture.png"
        self.review = structural_review(self.axes, self.binding, self.text, self.source, self.render)

    def errors(self, review):
        return reader_value.validate(review, self.axes, self.binding, self.text,
                                     source=self.source, renders=[self.render])

    def test_complete_evidence_passes(self):
        self.assertEqual(self.errors(self.review), [])

    def test_missing_evidence_blocks(self):
        self.assertTrue(self.errors(None))
        for axis in self.axes:
            review = copy.deepcopy(self.review)
            del review["checks"][axis]
            self.assertTrue(self.errors(review))

    def test_stale_binding_blocks(self):
        self.review["artifact_binding"] = "b" * 64
        self.assertTrue(self.errors(self.review))

    def test_unlocated_or_invented_quote_blocks(self):
        for field, value in (("quote", "Invented unobserved outcome"), ("quote", ""), ("location", ""), ("reader_effect", ""), ("protected_meaning", "")):
            review = copy.deepcopy(self.review)
            review["checks"]["expression"][field] = value
            self.assertTrue(self.errors(review))

    def test_selection_requires_removal_consequence(self):
        del self.review["checks"]["selection"]["removal_effect"]
        self.assertTrue(self.errors(self.review))

    def test_fail_cannot_be_papered_over_with_pass(self):
        for action in ("revise", "remove", "defer"):
            review = copy.deepcopy(self.review)
            review["checks"]["selection"]["action"] = action
            self.assertTrue(self.errors(review))
        self.review["checks"]["expression"]["status"] = "fail"
        self.assertTrue(self.errors(self.review))

    def test_source_and_render_must_be_supplied_evidence(self):
        self.review["checks"]["meaning"]["source_quote"] = "Unobserved causal proof"
        self.assertTrue(self.errors(self.review))
        self.review["checks"]["meaning"]["source_quote"] = self.source
        self.review["checks"]["presentation"]["render_path"] = "/tmp/other.png"
        self.assertTrue(self.errors(self.review))

    def test_three_units_remain_required(self):
        del self.review["checks"]["unit_roles"]["roles"]["picture"]
        self.assertTrue(self.errors(self.review))

    def test_legitimate_contrast_and_caveat_not_blacklisted(self):
        self.text = "Not all users: only old links fail. No load test has been completed."
        self.source = self.text
        review = structural_review(self.axes, self.binding, self.text, self.source, self.render)
        self.assertEqual(self.errors(review), [])

    def test_html_anchor_ignores_code_and_reads_visible_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.html"
            path.write_text('<style>.hidden{}</style><p>Visible <b>conclusion</b>.</p><script>fakeEvidence()</script>')
            text = reader_value.read_text(path)
            self.assertIn("conclusion", text)
            self.assertNotIn("fakeEvidence", text)
            self.assertNotIn("hidden", text)

    def test_native_entities_multiline_and_hidden_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            xml = root / "native.xml"
            xml.write_text("<document><p>R&amp;D owns the release.</p></document>")
            self.assertEqual(reader_value.read_text(xml), "R&D owns the release.")
            native = root / "native.json"
            native.write_text('{"owner":"hidden-owner","blocks":[{"text":"First line.\\nSecond line."}]}')
            self.assertEqual(reader_value.read_text(native), "First line.\nSecond line.")
            html = root / "native.html"
            html.write_text('<p>Visible.</p><p hidden>Secret1.</p><p style="display: none">Secret2.</p><p>End.</p>')
            self.assertEqual(reader_value.read_text(html), "Visible. End.")

    def test_malformed_fields_and_empty_attestations_fail_closed(self):
        for field, value in (("status", []), ("action", {}), ("reader_effect", "OK"), ("protected_meaning", None)):
            review = copy.deepcopy(self.review)
            review["checks"]["expression"][field] = value
            self.assertTrue(self.errors(review))
        self.review["version"] = True
        self.assertTrue(self.errors(self.review))

    def test_ok_can_be_a_real_message_quote(self):
        self.text = self.source = "OK"
        review = structural_review(self.axes, self.binding, self.text, self.source, self.render)
        self.assertEqual(self.errors(review), [])

    def test_css_hidden_content_requires_actual_rendered_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.html"
            path.write_text('<style>.hidden {display:none}</style><p class="hidden">Hidden qualifier</p><p>Visible</p>')
            with self.assertRaisesRegex(ValueError, "rendered-text"):
                reader_value.read_text(path)

    def test_visual_blocks_are_not_confused_with_native_text_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "visual.json"
            path.write_text('{"blocks":[{"type":"bar","title":"A responds faster","items":[{"label":"A","value":2}]}]}')
            self.assertIn("A responds faster", reader_value.read_text(path))


if __name__ == "__main__":
    unittest.main()
