"""SYNTHETIC regression cases; passing validates records, not writing quality."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import direct_expression as expression
from expression_fixture import structural_expression, structural_expression_plan


BADCASE = ("不是扩大试点，而是先补齐回滚验证。\n"
           "不能省略的责任：记录回滚结果。\n"
           "不能省略的责任：复核发布条件。\n"
           "不按旧流程提交。")


class ExpressionPlanTests(unittest.TestCase):
    def setUp(self):
        self.answers = [{"id": "A1"}, {"id": "A2"}]
        self.plan = structural_expression_plan()
        self.plan["essential_boundaries"] = [{
            "answer_id": "A2", "placement": "claim-adjacent",
            "reason": "SYNTHETIC: the pilot scope must accompany the result to avoid a production claim."}]

    def test_complete_plan_uses_existing_required_answers(self):
        self.assertEqual(expression.plan_errors(self.plan, self.answers), [])

    def test_empty_boundaries_are_valid_when_none_are_needed(self):
        self.plan["essential_boundaries"] = []
        self.assertEqual(expression.plan_errors(self.plan, self.answers), [])

    def test_missing_preplan_is_rejected(self):
        self.assertIn("expression_plan is required before drafting", expression.plan_errors(None, self.answers))

    def test_missing_each_required_preplan_field_is_rejected(self):
        for field in self.plan:
            with self.subTest(field=field):
                record = copy.deepcopy(self.plan)
                del record[field]
                self.assertTrue(expression.plan_errors(record, self.answers))

    def test_stale_lead_and_boundary_answer_ids_are_rejected(self):
        for key in ("lead", "boundary"):
            with self.subTest(key=key):
                record = copy.deepcopy(self.plan)
                if key == "lead":
                    record["lead_answer_ids"] = ["deleted-answer"]
                else:
                    record["essential_boundaries"][0]["answer_id"] = "deleted-answer"
                self.assertTrue(expression.plan_errors(record, self.answers))

    def test_duplicate_leads_and_boundaries_are_rejected(self):
        for field in ("lead_answer_ids", "essential_boundaries"):
            with self.subTest(field=field):
                record = copy.deepcopy(self.plan)
                record[field] *= 2
                self.assertTrue(expression.plan_errors(record, self.answers))

    def test_real_correction_can_be_planned_without_forcing_direct_opening(self):
        self.plan.update(opening_move="correction", opening_reason=(
            "SYNTHETIC: the reader requested full rollout after mistaking pilot results for capacity evidence."))
        self.assertEqual(expression.plan_errors(self.plan, self.answers), [])

    def test_malformed_preplan_fields_fail_without_crashing(self):
        for field in self.plan:
            for bad in (None, False, 7, {}, [[], {}]):
                with self.subTest(field=field, value=bad):
                    record = copy.deepcopy(self.plan)
                    record[field] = bad
                    self.assertTrue(expression.plan_errors(record, self.answers))
        for field in ("answer_id", "placement", "reason"):
            for bad in (None, False, 7, {}, []):
                with self.subTest(boundary_field=field, value=bad):
                    record = copy.deepcopy(self.plan)
                    record["essential_boundaries"][0][field] = bad
                    self.assertTrue(expression.plan_errors(record, self.answers))

    def test_empty_attestations_cannot_replace_opening_reason(self):
        for bad in ("", " ", "PASS", "OK", "已检查"):
            with self.subTest(value=bad):
                self.plan["opening_reason"] = bad
                self.assertTrue(expression.plan_errors(self.plan, self.answers))


class DirectExpressionTests(unittest.TestCase):
    def setUp(self):
        self.text = BADCASE
        self.record = structural_expression(self.text)

    def errors(self, record):
        return expression.validate(record, self.text, "after")

    def test_complete_synthetic_record_is_structurally_valid(self):
        self.assertEqual(self.errors(self.record), [])
        self.assertIn("SYNTHETIC", self.record["opening"]["reader_gain"])

    def test_prepare_is_pending_at_every_review_level(self):
        for stage in ("during", "after"):
            with self.subTest(stage=stage):
                record = expression.template(self.text, stage)
                self.assertEqual(record["stage"], stage)
                self.assertEqual(record["opening"]["decision"], "pending")
                self.assertEqual(record["whole_text"]["decision"], "pending")
                self.assertTrue(all(item["decision"] == "pending" for item in record["comparisons"]))
                self.assertTrue(all(item["decision"] == "pending" for item in record["whole_text"]["clusters"]))
                self.assertTrue(expression.validate(record, self.text, stage))

    def test_badcase_families_and_exact_unicode_offsets_are_detected(self):
        probes = expression.probes(self.text)
        self.assertEqual(len(probes), 4)
        self.assertIn("contrast", probes[0]["signals"])
        self.assertIn("qualification", probes[0]["signals"])
        self.assertTrue(all("restriction" in item["signals"] for item in probes[1:]))
        for item in probes:
            self.assertEqual(item["occurrences"], [self.text.index(item["quote"])])
        self.assertEqual(expression.clusters(probes), [{
            "family": "restriction", "item_ids": [item["id"] for item in probes[1:]]}])

    def test_identical_responsibility_headings_keep_all_occurrences(self):
        quote = "不能省略的责任"
        text = "  " + quote + "\n说明一。\n" + quote + "\n说明二。"
        items = expression.probes(text)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["quote"], quote)
        self.assertEqual(items[0]["occurrences"], [text.index(quote), text.rindex(quote)])
        self.assertEqual(expression.clusters(items), [{"family": "restriction", "item_ids": [items[0]["id"]]}])

    def test_missing_and_stale_review_are_rejected(self):
        self.assertTrue(self.errors(None))
        for field, value in (("version", 0), ("version", True), ("text_sha256", "stale"), ("stage", "during")):
            with self.subTest(field=field, value=value):
                record = copy.deepcopy(self.record)
                record[field] = value
                self.assertTrue(self.errors(record))

    def test_changed_text_invalidates_even_an_unchanged_opening(self):
        self.assertIn("direct_expression stale text or wrong stage", expression.validate(
            self.record, self.text + "\n新增已确认的发布条件。"))

    def test_missing_direct_alternative_is_rejected(self):
        del self.record["comparisons"][0]["alternative"]
        self.assertIn("direct_expression comparison missing alternative", self.errors(self.record))

    def test_every_comparison_requires_preservation_gain_context_and_reason(self):
        for field in ("protected_meaning", "reader_gain", "prior_context", "reason"):
            with self.subTest(field=field):
                record = copy.deepcopy(self.record)
                del record["comparisons"][0][field]
                self.assertIn("direct_expression comparison missing " + field, self.errors(record))

    def test_detected_statement_cannot_be_omitted_or_duplicated(self):
        record = copy.deepcopy(self.record)
        record["comparisons"].pop()
        self.assertIn("direct_expression detected statement lacks direct comparison", self.errors(record))
        self.record["comparisons"].append(copy.deepcopy(self.record["comparisons"][0]))
        self.assertIn("direct_expression duplicate or invalid comparison", self.errors(self.record))

    def test_changed_occurrence_offsets_quote_or_signals_are_rejected(self):
        for field, value in (("occurrences", [1]), ("occurrences", []),
                             ("quote", "not the detected quote"), ("signals", [])):
            with self.subTest(field=field, value=value):
                record = copy.deepcopy(self.record)
                record["comparisons"][0][field] = value
                self.assertIn("direct_expression detected statement or occurrences changed", self.errors(record))

    def test_boolean_occurrence_cannot_impersonate_integer_offset(self):
        self.assertEqual(self.record["comparisons"][0]["occurrences"], [0])
        self.record["comparisons"][0]["occurrences"] = [False]
        self.assertTrue(self.errors(self.record))

    def test_missing_repeated_family_review_is_rejected(self):
        self.record["whole_text"]["clusters"] = []
        self.assertIn("direct_expression repeated family lacks whole-text review", self.errors(self.record))

    def test_repeated_family_requires_all_members_and_cumulative_reason(self):
        for field, value in (("item_ids", []), ("reading_effect", ""), ("reason", "PASS")):
            with self.subTest(field=field):
                record = copy.deepcopy(self.record)
                record["whole_text"]["clusters"][0][field] = value
                self.assertTrue(self.errors(record))

    def test_revise_stays_failure_at_each_review_level(self):
        for target in ("opening", "comparison", "cluster", "whole_text"):
            with self.subTest(target=target):
                record = copy.deepcopy(self.record)
                item = {"opening": record["opening"], "comparison": record["comparisons"][0],
                        "cluster": record["whole_text"]["clusters"][0], "whole_text": record["whole_text"]}[target]
                item["decision"] = "revise"
                self.assertIn("direct_expression unresolved reader effort", self.errors(record))

    def test_badcase_direct_alternatives_do_not_approve_unrepaired_text(self):
        cases = [
            ("不是扩大试点，而是先补齐回滚验证。", "先补齐回滚验证，暂缓扩大试点。",
             "The next action precedes the rollout boundary instead of a correction the reader did not request."),
            ("不能省略的责任：记录回滚结果。\n不能省略的责任：复核发布条件。",
             "记录回滚结果，并复核发布条件。",
             "The repeated heading adds another warning before each required action without adding a distinct boundary."),
            ("不按旧流程提交，改用已确认的新流程。", "按已确认的新流程提交。",
             "The confirmed new process directly answers how to submit; the old path adds no new instruction here."),
        ]
        for text, alternative, reason in cases:
            with self.subTest(text=text):
                record = structural_expression(text)
                for item in record["comparisons"]:
                    item.update(alternative=alternative, decision="revise", reason="SYNTHETIC case: " + reason,
                                reader_gain="SYNTHETIC case: " + reason,
                                prior_context="SYNTHETIC case: no preceding reader misconception was supplied.",
                                protected_meaning="SYNTHETIC case: retain the stated action, applicable scope and instruction force.")
                self.assertIn("direct_expression unresolved reader effort", expression.validate(record, text))
                self.assertEqual(expression.validate(structural_expression(alternative), alternative), [])

    def test_no_signal_still_requires_opening_and_whole_text_review(self):
        text = "请周五前提交回滚记录。"
        record = structural_expression(text)
        self.assertEqual(record["comparisons"], [])
        self.assertEqual(record["whole_text"]["clusters"], [])
        self.assertEqual(expression.validate(record, text), [])
        for field in ("opening", "whole_text"):
            with self.subTest(field=field):
                missing = copy.deepcopy(record)
                del missing[field]
                self.assertTrue(expression.validate(missing, text))
                pending = copy.deepcopy(record)
                pending[field]["decision"] = "pending"
                self.assertTrue(expression.validate(pending, text))

    def test_counts_only_route_review_and_never_force_failure(self):
        for count in (1, 2, 40):
            with self.subTest(count=count):
                text = "\n".join(["不要关闭审计日志。"] * count)
                record = structural_expression(text)
                self.assertEqual(len(record["comparisons"][0]["occurrences"]), count)
                self.assertEqual(expression.validate(record, text), [])

    def test_legitimate_refusal_prohibition_and_negative_finding_can_be_kept(self):
        cases = [
            ("我不能提供他人的登录凭证。", "refusal", "The speaker refuses disclosure of another person's credentials; an affirmative instruction would lose that refusal."),
            ("不要关闭审计日志。", "prohibition", "The reader must keep audit logging active; a suggestion would weaken the explicit prohibition."),
            ("本轮抽样未发现丢失记录。", "negative-finding", "The finding is absence of observed loss in this sample, not proof of no loss everywhere."),
        ]
        for text, function, reason in cases:
            with self.subTest(function=function):
                record = structural_expression(text)
                item = record["comparisons"][0]
                item.update(function=function, alternative_kind="original-required", alternative=item["quote"],
                            reason="SYNTHETIC case: " + reason, protected_meaning=reason,
                            reader_gain="SYNTHETIC case: the opening directly states the bounded " + function,
                            prior_context="SYNTHETIC case: this is the only statement; no earlier distinction exists.")
                self.assertEqual(expression.validate(record, text), [])
                item["reason"] = "OK"
                self.assertIn("direct_expression comparison missing reason", expression.validate(record, text))

    def test_original_required_does_not_allow_claim_or_changed_original(self):
        item = self.record["comparisons"][0]
        item.update(alternative_kind="original-required", alternative=item["quote"], function="claim")
        self.assertIn("direct_expression original-required lacks a protected function", self.errors(self.record))
        item.update(function="correction", alternative="Changed statement")
        self.assertIn("direct_expression original-required must retain the exact original", self.errors(self.record))

    def test_identical_rewrite_is_not_a_direct_alternative(self):
        self.record["comparisons"][0]["alternative"] = self.record["comparisons"][0]["quote"]
        self.assertIn("direct_expression unchanged wording needs a protected original-required reason", self.errors(self.record))

    def test_manual_comparison_must_anchor_to_actual_text(self):
        manual = copy.deepcopy(self.record["comparisons"][0])
        manual.update(id="manual-synthetic", quote="Unobserved invented wording.")
        self.record["comparisons"].append(manual)
        self.assertIn("direct_expression manual comparison quote is not anchored", self.errors(self.record))

    def test_opening_cannot_quote_a_distant_body_passage(self):
        text = "先完成回滚验证。\n" + "已有记录。" * 200 + "\n请记录最终结果。"
        record = structural_expression(text)
        record["opening"]["quote"] = "请记录最终结果。"
        self.assertIn("direct_expression opening quote must be in the actual opening", expression.validate(record, text))

    def test_malformed_top_level_and_nested_records_fail_without_crashing(self):
        for bad in (None, False, 7, [], "record"):
            with self.subTest(record=bad):
                self.assertTrue(self.errors(bad))
        for field in ("opening", "comparisons", "whole_text"):
            for bad in (None, False, 7, "record"):
                with self.subTest(field=field, value=bad):
                    record = copy.deepcopy(self.record)
                    record[field] = bad
                    self.assertTrue(self.errors(record))
        for container, fields in (
            ("opening", ("quote", "reader_gain", "decision")),
            ("comparison", ("id", "quote", "signals", "occurrences", "function", "alternative",
                            "alternative_kind", "protected_meaning", "reader_gain", "prior_context", "reason", "decision")),
            ("whole_text", ("decision", "reading_effect", "clusters")),
            ("cluster", ("family", "item_ids", "reading_effect", "reason", "decision")),
        ):
            for field in fields:
                for bad in (None, False, 7, {}, []):
                    with self.subTest(container=container, field=field, value=bad):
                        record = copy.deepcopy(self.record)
                        item = {"opening": record["opening"], "comparison": record["comparisons"][0],
                                "whole_text": record["whole_text"], "cluster": record["whole_text"]["clusters"][0]}[container]
                        item[field] = bad
                        self.assertTrue(self.errors(record))

    def test_malformed_array_members_fail_without_crashing(self):
        for container in ("comparisons", "clusters"):
            for bad in (None, False, 7, [], "item"):
                with self.subTest(container=container, value=bad):
                    record = copy.deepcopy(self.record)
                    target = record if container == "comparisons" else record["whole_text"]
                    target[container].append(bad)
                    self.assertTrue(self.errors(record))

    def test_cli_prepare_and_check_respect_stage_and_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "text.txt", root / "review.json"
            source.write_text(self.text, encoding="utf-8")
            args = ["--text", str(source), "--stage", "during", "--output", str(output)]
            def run(mode):
                return subprocess.run([sys.executable, "-B", str(ROOT / "scripts/direct_expression.py"), mode, *args],
                                      capture_output=True, text=True, check=False)
            prepared = run("prepare")
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            self.assertEqual(json.loads(prepared.stdout)["status"], "pending")
            self.assertEqual(json.loads(output.read_text())["stage"], "during")
            self.assertEqual(run("check").returncode, 1)
            original = output.read_bytes()
            self.assertNotEqual(run("prepare").returncode, 0)
            self.assertEqual(output.read_bytes(), original)
            output.write_text(json.dumps(structural_expression(self.text, "during")), encoding="utf-8")
            checked = run("check")
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertEqual(json.loads(checked.stdout)["status"], "record-checks-satisfied")


if __name__ == "__main__":
    unittest.main()
