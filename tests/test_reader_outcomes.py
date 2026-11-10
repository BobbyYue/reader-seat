"""Synthetic binding/count tests, not human comprehension measurements."""
import copy
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import reader_answers as ra
import reader_outcomes as outcomes
import test_reader_answers as fixtures


class OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ReaderAnswersTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.prepare()

    def result(self):
        f = self.fixture
        return outcomes.summarize(f.manifest, f.responses, f.evaluation)

    def add_question(self, text, *, kind="detail", group="G1", answer_ids=(), surface=0, disclosure=None):
        f = self.fixture
        response = f.responses[surface]
        index = len(response["remaining_questions"])
        response["remaining_questions"].append(text)
        row = {"surface_id": response["surface_id"], "index": index, "group_id": group,
               "answer_ids": list(answer_ids), "classification": kind,
               "rationale": "Synthetic source-review classification for this fixed reader task."}
        if disclosure is not None:
            row["disclosure_quote"] = disclosure
        f.evaluation["questions"].append(row)
        f.rebind_responses()
        return row

    def test_no_questions_is_zero_followups_not_proof_of_comprehension(self):
        result = self.result()
        self.assertEqual(result["questions"]["total"], 3)
        self.assertEqual(result["questions"]["correct"], 3)
        self.assertEqual(result["followups"]["avoidable_count"], 0)
        self.assertEqual(result["comparison"]["status"], "not_measured")
        self.fixture.evaluation["answers"][0]["status"] = "fail"
        self.assertEqual(self.result()["questions"]["correct"], 2)

    def test_one_question_on_two_surfaces_is_not_double_counted(self):
        self.fixture.evaluation["answers"][-1]["status"] = "fail"
        result = self.result()
        self.assertEqual(result["questions"], {"total": 3, "correct": 2, "incorrect": 1,
            "unassessed": 0, "correct_rate": 2 / 3, "complete": True,
            "states": {"result": "pass", "next": "pass", "uncertainty": "fail"}})

    def test_pending_answers_remain_in_denominator(self):
        self.fixture.evaluation["answers"][0]["status"] = "unassessed"
        result = self.result()
        self.assertEqual(result["questions"]["correct_rate"], 2 / 3)
        self.assertEqual(result["status"], "partial")
        self.assertFalse(result["questions"]["complete"])

    def test_paraphrased_followups_share_one_gap(self):
        self.fixture.evaluation["answers"][0]["status"] = "fail"
        self.add_question("What changed?", kind="missing_required_answer", answer_ids=["result"])
        self.add_question("Which result changed?", kind="missing_required_answer", answer_ids=["result"])
        result = self.result()
        self.assertEqual(result["followups"]["raw_count"], 2)
        self.assertEqual(result["followups"]["avoidable_count"], 1)
        self.assertTrue(ra.validate_answers(self.fixture.manifest, self.fixture.responses, self.fixture.evaluation))

    def test_mapped_missing_answer_cannot_coexist_with_all_passed_or_pending(self):
        self.add_question("What changed?", kind="missing_required_answer", answer_ids=["result"])
        with self.assertRaisesRegex(ValueError, "needs a failed required answer"):
            self.result()
        self.fixture.evaluation["answers"][0]["status"] = "unassessed"
        with self.assertRaisesRegex(ValueError, "needs a failed required answer"):
            self.result()

    def test_disclosed_unknown_and_optional_detail_are_not_defects(self):
        self.add_question("When will eligibility be established?", kind="source_unknown", answer_ids=["uncertainty"], disclosure="Eligibility remains unknown")
        self.add_question("Who coined the pilot name?", group="G2")
        result = self.result()
        self.assertEqual(result["followups"]["avoidable_count"], 0)
        self.assertEqual(result["followups"]["source_unknown_count"], 1)
        self.assertEqual(result["followups"]["detail_count"], 1)
        self.assertEqual(ra.validate_answers(self.fixture.manifest, self.fixture.responses, self.fixture.evaluation), [])

    def test_known_required_answer_cannot_be_labeled_unknown(self):
        self.add_question("What changed?", kind="source_unknown", answer_ids=["result"], disclosure="Eligibility remains unknown")
        with self.assertRaisesRegex(ValueError, "known required"):
            self.result()

    def test_unknown_requires_disclosure_on_read_surface(self):
        self.add_question("Is eligibility established?", kind="source_unknown", answer_ids=["uncertainty"], disclosure="Unseen invented disclosure")
        with self.assertRaisesRegex(ValueError, "visible uncertainty"):
            self.result()

    def test_unresolved_required_question_is_not_optional(self):
        self.fixture.evaluation["answers"][0]["status"] = "fail"
        self.add_question("What changed?", answer_ids=["result"])
        with self.assertRaisesRegex(ValueError, "optional detail"):
            self.result()

    def test_missing_question_classification_is_not_zero(self):
        self.fixture.responses[0]["remaining_questions"] = ["What changed?"]
        self.fixture.rebind_responses()
        with self.assertRaisesRegex(ValueError, "every raw follow-up"):
            self.result()

    def test_identical_questions_cannot_inflate_group_count(self):
        self.add_question("What changed?")
        self.add_question("What changed?", group="G2")
        with self.assertRaisesRegex(ValueError, "identical follow-up"):
            self.result()

    def test_different_classifications_cannot_share_group(self):
        self.add_question("An optional detail?")
        self.add_question("What changed?", kind="missing_required_answer")
        with self.assertRaisesRegex(ValueError, "mix classifications"):
            self.result()

    def test_response_tamper_and_fake_quote_are_rejected(self):
        self.fixture.responses[0]["findings"].append("An injected answer")
        with self.assertRaisesRegex(ValueError, "raw answers"):
            self.result()
        self.fixture.rebind_responses()
        self.fixture.evaluation["answers"][0]["reader_quote"] = "Author-provided expected answer"
        with self.assertRaisesRegex(ValueError, "actual blind"):
            self.result()

    def test_compare_retains_regressions_and_rejects_context_reuse(self):
        baseline = self.result()
        candidate = copy.deepcopy(baseline)
        candidate["reader_ids"] = ["fresh-candidate-context"]
        candidate["artifact_sha256"] = "different-candidate-sha"
        candidate["questions"]["states"]["result"] = "fail"
        candidate["questions"]["correct"] = 2
        candidate["questions"]["correct_rate"] = 2 / 3
        comparison = outcomes.compare(baseline, candidate)
        self.assertAlmostEqual(comparison["correct_rate_change"], -1 / 3)
        self.assertEqual(comparison["regressed_answer_ids"], ["result"])
        candidate["reader_ids"] = baseline["reader_ids"]
        with self.assertRaisesRegex(ValueError, "independent reading"):
            outcomes.compare(baseline, candidate)

    def test_changed_task_and_pending_comparison_rejected(self):
        baseline = self.result()
        candidate = copy.deepcopy(baseline)
        candidate["reader_ids"] = ["fresh-candidate-context"]
        candidate["artifact_sha256"] = "different-candidate-sha"
        candidate["basis"]["reader"]["decision"] = "Another decision"
        candidate["basis_sha256"] = ra.object_digest(candidate["basis"])
        with self.assertRaisesRegex(ValueError, "changed"):
            outcomes.compare(baseline, candidate)
        candidate = copy.deepcopy(baseline)
        candidate["reader_ids"] = ["fresh-candidate-context"]
        candidate["artifact_sha256"] = "different-candidate-sha"
        candidate["questions"]["complete"] = False
        with self.assertRaisesRegex(ValueError, "Pending"):
            outcomes.compare(baseline, candidate)

    def test_verify_receipt_contains_recomputed_outcomes_and_rejects_tamper(self):
        f = self.fixture
        paths = f.write_evidence_files()
        receipt = f.base / "receipt.json"
        process = f.run_cli("verify", "--manifest", str(paths["manifest"]), "--responses", str(paths["responses"]),
            "--evaluation", str(paths["evaluation"]), "--output", str(receipt))
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertEqual(outcomes.from_receipt(receipt)["questions"]["correct"], 3)
        data = ra.load(receipt)
        data["reader_outcomes"]["questions"]["correct"] = 99
        ra.save(receipt, data)
        self.assertTrue(ra.validate_receipt(receipt))
        with self.assertRaisesRegex(ValueError, "differ"):
            outcomes.from_receipt(receipt)

    def test_compare_cli_requires_baseline(self):
        process = subprocess.run([sys.executable, "-B", str(Path(outcomes.__file__)), "compare", "--candidate-receipt", "x", "--output", "y"], text=True, capture_output=True)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("baseline-receipt", process.stderr)

    def test_compare_cli_reopens_two_version_receipts_including_failed_baseline(self):
        old = self.fixture
        old.evaluation["answers"][0]["status"] = "fail"
        old_paths = old.write_evidence_files()
        old_receipt = old.base / "old-receipt.json"
        process = old.run_cli("verify", "--manifest", str(old_paths["manifest"]), "--responses", str(old_paths["responses"]),
            "--evaluation", str(old_paths["evaluation"]), "--output", str(old_receipt))
        self.assertNotEqual(process.returncode, 0)
        new = fixtures.ReaderAnswersTests()
        new.setUp()
        self.addCleanup(new.doCleanups)
        new.artifact_path.write_text(new.artifact_path.read_text() + "\n", encoding="utf-8")
        new.prepare()
        for response in new.responses:
            response["reader_id"] += "-fresh-version"
        new.rebind_responses()
        new_paths = new.write_evidence_files()
        new_receipt = new.base / "new-receipt.json"
        process = new.run_cli("verify", "--manifest", str(new_paths["manifest"]), "--responses", str(new_paths["responses"]),
            "--evaluation", str(new_paths["evaluation"]), "--output", str(new_receipt))
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        output = new.base / "comparison.json"
        process = subprocess.run([sys.executable, "-B", str(Path(outcomes.__file__)), "compare",
            "--baseline-receipt", str(old_receipt), "--candidate-receipt", str(new_receipt), "--output", str(output)], text=True, capture_output=True)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertAlmostEqual(ra.load(output)["correct_rate_change"], 1 / 3)
        self.assertEqual(ra.load(output)["regressed_answer_ids"], [])

    def test_legacy_lock_does_not_fabricate_results(self):
        f = self.fixture
        lock = ra.load(f.lock_path)
        del lock["reader_outcomes_version"]
        ra.save(f.lock_path, lock)
        record = ra.outcome_record(f.manifest, f.responses, f.evaluation)
        self.assertEqual(record["status"], "not_measured")

    def test_reader_aggregate_recomputes_outcomes_before_delivery(self):
        import test_runtime_contract as runtime_tests
        import reader_review
        fixture = runtime_tests.RuntimeContractTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        fixture.init_contract()
        artifact = fixture.base / "report.html"
        artifact.write_text("<html><body>Observed changes in the pilot only.</body></html>")
        aggregate_path = fixture.complete_reader_review(artifact)
        aggregate = ra.load(aggregate_path)
        self.assertEqual(aggregate["reader_outcomes"]["questions"]["correct"], 1)
        aggregate["reader_outcomes"]["followups"]["avoidable_count"] = 99
        ra.save(aggregate_path, aggregate)
        errors, _ = reader_review.validate_aggregate_for_artifact(aggregate_path, ra.load(fixture.contract), artifact)
        self.assertIn("outcomes differ", "\n".join(errors))

    def test_capability_validation_rejects_missing_outcomes_or_extra_rounds(self):
        import validate_skill
        contract = ra.load(Path(validate_skill.ROOT) / "config/skill-contract.json")
        errors = []
        validate_skill.check_reader_outcomes_contract(contract, errors)
        self.assertEqual(errors, [])
        contract["reader_outcomes"]["new_reviewers_or_rounds"] = True
        validate_skill.check_reader_outcomes_contract(contract, errors)
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
