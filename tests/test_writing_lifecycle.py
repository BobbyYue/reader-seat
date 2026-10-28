"""Executable stage, measurement and negative tests using synthetic text."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import writing_lifecycle as lifecycle
from lifecycle_fixture import prepare_flow, save


class WritingLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.artifact = self.root / "draft.txt"
        self.artifact.write_text("回滚演练未完成，暂不发布。\n完成后还要评审，发布日期待定。", encoding="utf-8")

    def flow(self, **kwargs):
        return prepare_flow(lifecycle, self.root, self.artifact, **kwargs)

    def test_defensive_signals_reach_prewrite_unit_and_measurement(self):
        f = self.flow()
        state = lifecycle.load_json(f["run"] / "lifecycle.json")
        packet = lifecycle.load_json(f["run"] / "task-packet.json")
        self.assertEqual(set(packet["defensive_expression"]), {"before", "during", "after"})
        self.assertIn("defensive_expression", state["units"][-1])
        report = lifecycle.measure_data(state, self.artifact.read_text())
        self.assertIn("defensive_expression", report["metrics"])
        self.assertIsNone(report["metrics"]["defensive_expression"]["data"]["D"])

    def test_missing_run_blocks(self):
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.verify_delivery(self.root / "missing", self.artifact, "functional")

    def test_complete_functional_flow_binds_actual_file(self):
        f = self.flow()
        result = lifecycle.verify_delivery(f["run"], self.artifact, "functional", review_evidence=[f["result"]])
        self.assertEqual(result["status"], "pass")
        self.assertFalse(result["external_action_authorized"])
        self.assertEqual(result["artifact_sha256"], lifecycle.sha(self.artifact.read_bytes()))

    def test_wrong_profile_cannot_reuse_pass(self):
        f = self.flow()
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.verify_delivery(f["run"], self.artifact, "literary")

    def test_changed_artifact_blocks(self):
        f = self.flow()
        self.artifact.write_text("现在可以发布。", encoding="utf-8")
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.verify_delivery(f["run"], self.artifact, "functional")

    def test_changed_source_blocks(self):
        f = self.flow()
        f["source"].write_text("来源发生变化", encoding="utf-8")
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.verify_delivery(f["run"], self.artifact, "functional")

    def test_changed_original_review_blocks(self):
        f = self.flow()
        save(f["result"], {"status": "pass", "issues": [], "modified": True})
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.verify_delivery(f["run"], self.artifact, "functional")

    def test_other_native_result_cannot_substitute(self):
        f = self.flow()
        other = save(self.root / "other.json", {"status": "pass"})
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.verify_delivery(f["run"], self.artifact, "functional", review_evidence=[other])

    def test_provisional_plan_allows_work_but_not_complete_acceptance(self):
        f = self.flow(authority="provisional")
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.verify_delivery(f["run"], self.artifact, "functional")

    def test_three_round_fallback_is_only_draft(self):
        f = self.flow(rounds=3, verdict="fail")
        result = lifecycle.verify_delivery(f["run"], self.artifact, "functional", draft=True)
        self.assertEqual(result["status"], "review-incomplete-draft")
        self.assertTrue(result["user_question_required"])
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.start_review(f["run"], self.artifact)
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.verify_delivery(f["run"], self.artifact, "functional")

    def test_one_failure_is_not_three_round_fallback(self):
        f = self.flow(verdict="fail")
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.verify_delivery(f["run"], self.artifact, "functional", draft=True)

    def test_previous_pass_does_not_hide_current_third_round_failure(self):
        f = self.flow()
        for number in (2, 3):
            lifecycle.start_review(f["run"], self.artifact)
            result = save(self.root / ("failure-"+str(number)+".json"), {"status": "fail", "issues": [{"impact": "Newly discovered condition"}]})
            lifecycle.finish_review(f["run"], result, "fail")
        self.assertEqual(lifecycle.verify_delivery(f["run"], self.artifact, "functional", draft=True)["status"], "review-incomplete-draft")

    def test_no_unit_checkpoint_cannot_start_review(self):
        f = self.flow()
        state = lifecycle.load_json(f["run"] / "lifecycle.json")
        new = self.root / "prewrite-only"
        lifecycle.init_run(new, f["plan"], "functional", [f["source"]])
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.start_review(new, self.artifact)

    def test_changed_plan_is_not_silently_reaccepted(self):
        f = self.flow()
        plan = lifecycle.load_json(f["plan"])
        plan["purpose"] = "A different goal"
        save(f["plan"], plan)
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.verify_delivery(f["run"], self.artifact, "functional")

    def test_state_edit_without_valid_integrity_is_rejected(self):
        f = self.flow()
        state = lifecycle.load_json(f["run"] / "lifecycle.json")
        state["profile"] = "literary"
        save(f["run"] / "lifecycle.json", state)
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.verify_delivery(f["run"], self.artifact, "literary")

    def test_literal_occurrences_are_not_unique_word_types(self):
        self.artifact.write_text("相关。相关。方面。", encoding="utf-8")
        f = self.flow()
        report = lifecycle.load_json(f["report"])
        self.assertEqual(report["metrics"]["verbosity"]["data"]["occurrences"], 3)
        self.assertEqual(report["metrics"]["verbosity"]["data"]["unique_terms"], 2)
        self.assertEqual(report["metrics"]["reading_efficiency"]["data"]["exact_duplicate_sentences"], 1)

    def test_unloaded_wordlists_and_layout_do_not_get_fake_scores(self):
        f = self.flow()
        report = lifecycle.load_json(f["report"])
        self.assertEqual(report["metrics"]["vocabulary"]["measurement_status"], "not-measured")
        self.assertEqual(report["metrics"]["reading_burden"]["measurement_status"], "not-measured")
        self.assertEqual(report["metrics"]["reading_efficiency"]["data"]["human_30_second_comprehension"], "not-tested")

    def test_long_sentence_is_retained_with_reason_not_auto_failure(self):
        self.artifact.write_text("母亲把那把椅子往外拉了拉，又轻轻推回去，等女儿把门带上，才坐到桌边，摸了摸已经凉了的碗。", encoding="utf-8")
        f = self.flow(profile="literary")
        self.assertEqual(lifecycle.verify_delivery(f["run"], self.artifact, "literary")["status"], "pass")
        report = lifecycle.load_json(f["report"])
        self.assertTrue(report["metrics"]["sentence_length"]["signals"])

    def test_literary_blind_packet_excludes_author_intention(self):
        f = self.flow(profile="literary")
        with lifecycle.session(f["run"]) as state:
            packet = lifecycle.load_json(state["rounds"][-1]["packets"]["reader"]["path"])
        self.assertNotIn("literary_intent", packet)
        self.assertNotIn("constraints", packet)
        self.assertNotIn("required_answers", packet)
        self.assertEqual(packet["text"], lifecycle.visible(self.artifact))

    def test_literary_reviewer_contexts_cannot_repeat(self):
        f = self.flow(profile="literary", verdict="fail")
        previous = lifecycle.load_json(f["result"])["reviewer_records"]
        started = lifecycle.start_review(f["run"], self.artifact)
        for item in previous:
            item["packet_sha256"] = started["packets"][item["role"]]["sha256"]
        changed = save(self.root / "reused-context.json", {"reviewer_records": previous, "issues": [{"impact": "Fixture"}]})
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.finish_review(f["run"], changed, "fail")

    def test_missing_metric_assessment_is_not_complete(self):
        f = self.flow()
        record = lifecycle.load_json(f["record"])
        record["observations"][0]["metrics"].remove("time")
        path = save(self.root / "missing-time.json", record)
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.register_candidate(f["run"], self.artifact, self.artifact, f["report"], path)

    def test_blanket_not_applicable_cannot_skip_core_standards(self):
        f = self.flow()
        record = lifecycle.load_json(f["record"])
        record["observations"] = []
        record["not_applicable"] = {m: "Synthetic blanket waiver" for m in lifecycle.load_json(f["report"])["metrics"]}
        path = save(self.root / "waive-everything.json", record)
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.register_candidate(f["run"], self.artifact, self.artifact, f["report"], path)

    def test_ignored_signal_cannot_be_discarded(self):
        f = self.flow()
        record = lifecycle.load_json(f["record"])
        record["dispositions"] = []
        path = save(self.root / "ignored-signals.json", record)
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.register_candidate(f["run"], self.artifact, self.artifact, f["report"], path)

    def test_missing_real_layout_blocks_finished_visual_artifact(self):
        f = self.flow(plan_updates={"format": "html"}, layout_status="unmeasured")
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.verify_delivery(f["run"], self.artifact, "functional")

    def test_critical_gap_cannot_be_hidden_by_a_passing_review(self):
        f = self.flow(plan_updates={"material": {"mode": "source-grounded", "gaps": [{"critical": True, "handling": "draft-only", "reason": "Core release condition is unknown"}]}})
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.verify_delivery(f["run"], self.artifact, "functional")

    def test_english_sentence_length_counts_words_not_characters(self):
        self.artifact.write_text("The launch is blocked. A new review is required after rollback testing.", encoding="utf-8")
        f = self.flow(plan_updates={"language": "en"})
        entry = lifecycle.load_json(f["report"])["metrics"]["sentence_length"]
        self.assertEqual(entry["data"]["unit"], "words")
        self.assertEqual(entry["data"]["count"], 2)
        self.assertEqual(entry["data"]["max"], 8)

    def test_geometry_calculates_five_measures_from_actual_line_inputs(self):
        geometry = save(self.root / "geometry.json", {"text_sha256": lifecycle.sha(self.artifact.read_bytes()),
            "target": "Synthetic fixture geometry, not real render evidence", "capture_method": "test coordinates", "state": "default",
            "viewport_height": 100, "content_height": 250, "unmeasured_content": [], "lines": [
                {"id": "L1", "block_id": "P1", "text": "一二三四", "y": 0, "height": 20, "font_size": 10, "line_height": 20, "paragraph_gap": 10},
                {"id": "L2", "block_id": "P1", "text": "五六", "y": 100, "height": 20, "font_size": 10, "line_height": 20},
                {"id": "L3", "block_id": "P2", "text": "七", "y": 200, "height": 20, "font_size": 10, "line_height": 20}]})
        data = lifecycle.measure_geometry(geometry, lifecycle.sha(self.artifact.read_bytes()))
        self.assertEqual(data["per_screen_characters"], [4, 2, 1])
        self.assertEqual(data["maximum_block_lines"], 2)
        self.assertEqual(data["total_screens"], 2.5)
        self.assertEqual(data["line_characters_median"], 2)
        self.assertEqual(data["line_spacing_ratio_median"], 2)
        self.assertEqual(data["paragraph_spacing_ratio_median"], .5)

    def test_duplicate_geometry_lines_do_not_double_count(self):
        line = {"id": "same", "block_id": "p", "text": "字", "y": 0, "height": 20, "font_size": 10, "line_height": 20}
        geometry = save(self.root / "duplicate-geometry.json", {"text_sha256": "abc", "target": "fixture", "capture_method": "test", "state": "default",
            "viewport_height": 100, "content_height": 100, "unmeasured_content": [], "lines": [line, line]})
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.measure_geometry(geometry, "abc")

    def test_balanced_but_misordered_brackets_are_candidates(self):
        self.artifact.write_text("]先关后开[。", encoding="utf-8")
        f = self.flow()
        kinds = {s["kind"] for s in lifecycle.load_json(f["report"])["metrics"]["grammar"]["signals"]}
        self.assertIn("delimiter-order-mismatch", kinds)

    def test_unknown_extension_cannot_bypass_text_binding(self):
        f = self.flow()
        wrong = self.root / "wrong.out"
        wrong.write_text("演练完成，明日发布。", encoding="utf-8")
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.register_candidate(f["run"], wrong, self.artifact, f["report"], f["record"])

    def test_appended_scene_needs_current_complete_unit(self):
        f = self.flow(profile="literary")
        self.artifact.write_text(self.artifact.read_text()+"\n母亲把鱼放进她碗里。", encoding="utf-8")
        new_report = self.root / "new-report.json"
        data = lifecycle.measure(f["run"], self.artifact, new_report)
        record = lifecycle.load_json(f["record"])
        record.update(text_sha256=data["text_sha256"], report_sha256=lifecycle.ref(new_report)["sha256"])
        record["dispositions"] = [{"signal_id": s["id"], "decision": "retain", "reason": "Test only"}
            for m in data["metrics"].values() for s in m["signals"]]
        new_record = save(self.root / "new-assessment.json", record)
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.register_candidate(f["run"], self.artifact, self.artifact, new_report, new_record)

    def test_old_assessment_is_rejected_even_after_remeasurement(self):
        f = self.flow()
        self.artifact.write_text(self.artifact.read_text()+"\n补充条件。", encoding="utf-8")
        new_report = self.root / "recomputed.json"
        lifecycle.measure(f["run"], self.artifact, new_report)
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.register_candidate(f["run"], self.artifact, self.artifact, new_report, f["record"])

    def test_closing_quotes_do_not_create_duplicate_sentences(self):
        self.artifact.write_text("女儿说：“今晚不住。”\n母亲说：“好。”\n她问：“还吃吗？”", encoding="utf-8")
        f = self.flow(profile="literary")
        report = lifecycle.load_json(f["report"])
        self.assertEqual(report["metrics"]["sentence_length"]["data"]["count"], 3)
        self.assertEqual(report["metrics"]["reading_efficiency"]["data"]["exact_duplicate_sentences"], 0)
        self.assertFalse(any(s["quote"] == "”" for m in report["metrics"].values() for s in m["signals"]))

    def test_actual_word_content_is_extracted_not_assumed(self):
        import zipfile
        path = self.root / "draft.docx"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("word/document.xml", '<w:document xmlns:w="urn:w"><w:body><w:p><w:r><w:t>暂不发布。</w:t></w:r></w:p></w:body></w:document>')
        self.assertEqual(lifecycle.artifact_text(path), "暂不发布。")


if __name__ == "__main__":
    unittest.main()
