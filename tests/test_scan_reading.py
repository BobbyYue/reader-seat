import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import reader_value
import scan_reading
from scan_fixture import structural_scan
from editorial_fixture import structural_review


class ScanReadingTests(unittest.TestCase):
    def setUp(self):
        self.text = "回滚验证通过后上线。测试已完成，回滚验证安排在周四。"
        self.profile = reader_value.SCAN_PROFILE
        self.record = structural_scan(self.text, self.profile)
        self.record["conditions"] = [{"quote": "回滚验证通过后", "cue_index": 0}]
        self.record["no_conditions_reason"] = ""

    def errors(self, record=None, text=None):
        return scan_reading.validate(self.record if record is None else record,
                                     self.text if text is None else text, self.profile)

    def test_bound_complete_record_passes(self):
        self.assertEqual(self.errors(), [])

    def test_missing_record_blocks(self):
        self.assertTrue(scan_reading.validate(None, self.text, self.profile))

    def test_template_is_never_auto_approved(self):
        self.assertTrue(self.errors(scan_reading.template(self.text, self.profile)))

    def test_changed_text_invalidates_record(self):
        self.assertTrue(self.errors(text=self.text + "另需审批。"))

    def test_wrong_profile_blocks(self):
        self.record["profile"] = "unknown"
        self.assertTrue(self.errors())

    def test_nonexistent_cue_blocks(self):
        self.record["cues"][0]["quote"] = "已经上线且验证成功"
        self.assertTrue(self.errors())

    def test_condition_in_body_but_not_scan_cue_blocks(self):
        self.record["cues"][0]["quote"] = "上线"
        self.assertTrue(any("selected scanning cue" in e for e in self.errors()))

    def test_condition_quote_cannot_be_invented(self):
        self.record["conditions"][0]["quote"] = "审批完成后"
        self.assertTrue(self.errors())

    def test_boolean_index_is_rejected(self):
        self.record["conditions"][0]["cue_index"] = False
        self.assertTrue(self.errors())

    def test_failed_judgment_blocks_even_with_complete_quotes(self):
        for key in scan_reading.CHECKS:
            with self.subTest(key=key):
                record = copy.deepcopy(self.record)
                record["checks"][key]["status"] = "fail"
                self.assertTrue(self.errors(record))

    def test_empty_attestation_is_rejected(self):
        for reason in ("已检查", "可以", "OK"):
            self.record["checks"]["orientation"]["reason"] = reason
            self.assertTrue(self.errors())

    def test_buried_condition_is_a_complete_negative_judgment(self):
        self.record["cues"][0]["quote"] = "测试已完成"
        self.record["conditions"] = [{"location": "body", "quote": "回滚验证通过后", "cue_index": None}]
        self.record["checks"]["conditions"]["status"] = "fail"
        errors = self.errors()
        self.assertTrue(errors)
        self.assertTrue(all("candidate_failed" in e for e in errors), errors)

    def test_omitted_condition_does_not_require_a_fabricated_quote(self):
        text = "可以上线。"
        record = structural_scan(text, self.profile)
        record["conditions"] = [{"location": "missing", "expected_condition": "验证通过后", "basis": "Supplied source requires validation before release.", "cue_index": None}]
        record["checks"]["conditions"]["status"] = "fail"
        errors = scan_reading.validate(record, text, self.profile)
        self.assertTrue(errors)
        self.assertTrue(all("candidate_failed" in e for e in errors), errors)

    def test_a_condition_failure_cannot_claim_pass(self):
        self.record["conditions"] = [{"location": "body", "quote": "回滚验证通过后", "cue_index": None}]
        self.assertTrue(any("inconsistent_judgment" in e for e in self.errors()))

    def test_malformed_receipt_types_return_errors_instead_of_crashing(self):
        for value in ([], {}, None, True, 17):
            with self.subTest(value=value):
                record = copy.deepcopy(self.record)
                record["conditions"][0]["location"] = value
                self.assertTrue(self.errors(record))
                record = copy.deepcopy(self.record)
                record["cues"][0]["kind"] = value
                self.assertTrue(self.errors(record))

    def test_invalid_profile_type_fails_closed(self):
        for value in ([], {}, None, True):
            with self.subTest(value=value):
                self.assertTrue(scan_reading.validate(self.record, self.text, value))
                with self.assertRaises(ValueError):
                    scan_reading.template(self.text, value)

    def test_missing_detail_blocks(self):
        self.record["detail_quote"] = ""
        self.assertTrue(self.errors())

    def test_no_conditions_needs_contextual_reason(self):
        self.record["conditions"] = []
        self.assertTrue(self.errors())

    def test_clear_short_message_needs_no_heading_or_invented_ask(self):
        for text in ("收到，谢谢。", "OK", "不行", "可以"):
            with self.subTest(text=text):
                record = structural_scan(text, "message")
                self.assertEqual(scan_reading.validate(record, text, "message"), [])

    def test_negative_result_and_long_explanation_can_be_kept(self):
        text = "未发现显著差异。" + "这里保留解释和具体证据，帮助读者理解。" * 40
        self.assertEqual(scan_reading.validate(structural_scan(text, self.profile), text, self.profile), [])

    def test_simulation_cannot_claim_human_evidence(self):
        self.record["evidence_kind"] = "human-eye-tracking"
        self.assertTrue(self.errors())

    def test_existing_reader_value_gate_rejects_missing_scan_record(self):
        review = structural_review(("expression",), "bound-artifact", self.text)
        self.assertEqual(reader_value.validate(review, ("expression",), "bound-artifact", self.text), [])
        del review["checks"]["expression"]["scan_reading"]
        self.assertTrue(any("scan_reading" in e for e in reader_value.validate(review, ("expression",), "bound-artifact", self.text)))

    def test_old_reader_value_version_is_stale(self):
        review = structural_review(("expression",), "bound-artifact", self.text)
        review["version"] -= 1
        self.assertTrue(reader_value.validate(review, ("expression",), "bound-artifact", self.text))


if __name__ == "__main__":
    unittest.main()
