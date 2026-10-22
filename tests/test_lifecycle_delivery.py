"""Real lifecycle/native wiring; structural fixtures are not semantic outcome evidence."""
import base64
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import checked_delivery
import lifecycle_guard
import runtime_contract
import writing_lifecycle
import test_runtime_contract as fixtures
from lifecycle_support import make_run
from execution_fixture import seed_fixture


class LifecycleDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.task = fixtures.RuntimeContractTests()
        self.task.setUp()
        self.addCleanup(self.task.tearDown)
        self.task.init_contract()
        self.artifact = self.task.write_html(language="en", body="Only the inspected period is known. Later evidence is unavailable. " * 4)
        self.task.complete_review(self.artifact)
        self.aggregate = self.task.complete_reader_review(self.artifact)
        self.args = ["verify", "--contract", str(self.task.contract), "--review", str(self.task.review),
                     "--artifact", str(self.artifact), "--actual-format", "html",
                     "--reader-review-aggregate", str(self.aggregate)]

    def run_delivery(self, args=None):
        return subprocess.run([sys.executable, "-B", str(ROOT / "scripts/deliver.py"),
                               *(self.args if args is None else args)], capture_output=True, text=True)

    def make_run(self, **kwargs):
        folder = self.task.base / f"lifecycle-{len(list(self.task.base.glob('lifecycle-*')))}"
        if kwargs.get("profile", "functional") == "functional":
            kwargs.setdefault("contract_path", self.task.contract)
        return make_run(folder, self.artifact, self.aggregate, **kwargs)

    def assert_blocked(self, run):
        result = self.run_delivery([*self.args, "--lifecycle-run", str(run)])
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.stdout, "")

    def test_missing_flag_or_missing_record_never_releases_payload(self):
        result = self.run_delivery()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assert_blocked(self.task.base / "nonexistent")
        empty = self.task.base / "empty"
        empty.mkdir()
        self.assert_blocked(empty)

    def test_missing_stages_or_unfinished_review_never_releases_payload(self):
        for stage in ("init", "unit", "candidate", "review-start"):
            with self.subTest(stage=stage):
                self.assert_blocked(self.make_run(until=stage))

    def test_wrong_profile_is_not_accepted(self):
        run = self.make_run(profile="literary", until="init")
        with self.assertRaisesRegex(ValueError, "profile"):
            lifecycle_guard.verify_lifecycle(run, self.artifact, self.aggregate)
        self.assert_blocked(run)

    def test_declared_html_without_actual_layout_is_not_finished(self):
        run = self.make_run(layout_status="unmeasured")
        with self.assertRaisesRegex(ValueError, "layout"):
            lifecycle_guard.verify_lifecycle(run, self.artifact, self.aggregate)
        self.assert_blocked(run)

    def test_old_artifact_or_changed_registered_evidence_blocks(self):
        run = self.make_run()
        before = self.artifact.read_bytes()
        self.artifact.write_bytes(before + b"<!-- a new version -->")
        self.assert_blocked(run)
        self.artifact.write_bytes(before)
        (run.parent / "unit.json").write_text('{"summary":"changed checkpoint"}')
        self.assert_blocked(run)

    def test_original_aggregate_path_not_a_copy_must_match_last_review(self):
        run = self.make_run()
        copy = self.task.base / "copied-aggregate.json"
        copy.write_bytes(self.aggregate.read_bytes())
        with self.assertRaisesRegex(ValueError, "Native final review differs"):
            lifecycle_guard.verify_lifecycle(run, self.artifact, copy)

    def test_complete_stage_records_cannot_replace_four_original_reviews(self):
        run = self.make_run()
        original = json.loads(self.aggregate.read_text())["reviews"][0]["result_path"]
        Path(original).write_text('{"status":"pass"}')
        self.assert_blocked(run)

    def test_real_guard_returns_exact_payload(self):
        run = self.make_run()
        result = self.run_delivery([*self.args, "--lifecycle-run", str(run)])
        self.assertEqual(result.returncode, 0, result.stderr)
        envelope = json.loads(result.stdout)
        self.assertEqual(envelope["delivery_state"], "checked")
        self.assertEqual(base64.b64decode(envelope["payload"]), self.artifact.read_bytes())

    def test_native_init_reuses_existing_answers_reader_source_and_format(self):
        run = self.task.base / "projected-run"
        result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/runtime_contract.py"), "init-lifecycle",
            "--contract", str(self.task.contract), "--lifecycle-run", str(run)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((run / "lifecycle.json").read_text())
        original = json.loads(self.task.answer_plan.read_text())
        task = json.loads(self.task.contract.read_text())
        self.assertEqual(state["plan"]["reader"]["need"], original["reader"]["decision"])
        self.assertEqual(state["plan"]["required_answers"][0]["expected"], original["answers"][0]["expected_information"])
        self.assertEqual(state["plan"]["format"], task["decisions"]["output_format"])
        self.assertIn(task["decisions"]["reader_validation"]["source_bundle"], state["sources"])
        self.assertEqual(state["plan"]["native_binding"]["answer_plan"],
                         task["decisions"]["reader_validation"]["answer_lock"]["plan"])

    def test_unlinked_plan_cannot_deliver_even_with_the_same_native_result(self):
        run = self.make_run(contract_path=None)
        self.assert_blocked(run)

    def test_source_metadata_does_not_change_content_identity(self):
        task = json.loads(self.task.contract.read_text())
        task["decisions"]["source_snapshot"] = {
            **task["decisions"]["reader_validation"]["source_bundle"],
            "detected_language": {"detected": "en", "latin_chars": 27},
        }
        self.task.contract.write_text(json.dumps(task))
        run = self.make_run(until="init")
        lifecycle_guard.validate_native_binding(run, self.task.contract)

    def test_source_metadata_does_not_hide_a_changed_content_hash(self):
        task = json.loads(self.task.contract.read_text())
        task["decisions"]["source_snapshot"] = {
            **task["decisions"]["reader_validation"]["source_bundle"],
            "sha256": "0" * 64,
            "detected_language": {"detected": "en"},
        }
        self.task.contract.write_text(json.dumps(task))
        run = self.make_run(until="init")
        with self.assertRaisesRegex(ValueError, "source differs"):
            lifecycle_guard.validate_native_binding(run, self.task.contract)

    def test_native_task_reader_answers_and_format_cannot_drift(self):
        for field, value in (
            ("task", "another-task"), ("format", "plain-text"),
            ("reader", {"knowledge": "Different audience", "need": "Different decision"}),
            ("required_answers", [{"id": "A1", "question": "Another question?", "expected": "Another answer",
                                   "source_location": "Synthetic source", "source_status": "supported"}]),
            ("material", {"mode": "nonfiction", "gaps": []}),
        ):
            with self.subTest(field=field):
                run = self.make_run(plan_changes={field: value})
                with self.assertRaisesRegex(ValueError, "native|boundary"):
                    lifecycle_guard.verify_lifecycle(run, self.artifact, self.aggregate, contract_path=self.task.contract)
                self.assert_blocked(run)

    def test_copied_source_is_not_the_native_locked_source(self):
        copied = self.task.base / "another-source.txt"
        copied.write_bytes(self.task.source_bundle.read_bytes())
        run = self.make_run(source_paths=[copied])
        with self.assertRaisesRegex(ValueError, "source differs"):
            lifecycle_guard.verify_lifecycle(run, self.artifact, self.aggregate, contract_path=self.task.contract)
        self.assert_blocked(run)

    def test_local_semantic_receipt_is_explicitly_partial_and_cannot_pack(self):
        receipt = self.task.base / "local-verification.json"
        result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/runtime_contract.py"),
                                 *self.args, "--receipt", str(receipt)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(receipt.read_text())
        self.assertEqual(value["status"], "pass")
        self.assertEqual(value["verification_scope"], "semantic-and-format-only")
        self.assertFalse(value["verified_finished_artifact"])
        with self.assertRaises(checked_delivery.DeliveryBlocked):
            checked_delivery.pack(self.artifact, [], lambda: value)

    def test_guard_evidence_is_watched_through_payload_construction(self):
        run = self.make_run()
        initial = lifecycle_guard.verify_lifecycle(run, self.artifact, self.aggregate)
        def mutate_after_check():
            result = lifecycle_guard.verify_lifecycle(run, self.artifact, self.aggregate)
            self.task.source_bundle.write_text("Changed during payload construction")
            return result
        with self.assertRaises(checked_delivery.DeliveryBlocked):
            checked_delivery.pack(self.artifact, initial["evidence_paths"], mutate_after_check)

    def test_cumulative_draft_keeps_native_issues_and_never_authorizes_publication(self):
        self.aggregate = self.task.complete_reader_review(self.artifact, failing_dimension="no-context", expected=1)
        run = self.make_run(rounds=3, verdict="fail")
        args = ["lifecycle-draft", "--contract", str(self.task.contract), "--artifact", str(self.artifact),
                "--reader-review-aggregate", str(self.aggregate), "--lifecycle-run", str(run)]
        result = self.run_delivery(args)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["delivery_state"], "draft")
        self.assertTrue(value["issues"])
        self.assertTrue(value["user_notice_required"])
        self.assertTrue(value["user_question_required"])
        self.assertFalse(value["external_action_authorized"])
        # The original per-batch round-three route remains stricter.
        self.assertNotEqual(self.run_delivery(["present-draft", *args[1:]]).returncode, 0)
        self.assertNotEqual(self.run_delivery(["verify", *args[1:], "--review", str(self.task.review),
                                              "--actual-format", "html"]).returncode, 0)

    def test_cumulative_draft_rejects_one_or_two_rounds(self):
        self.aggregate = self.task.complete_reader_review(self.artifact, failing_dimension="no-context", expected=1)
        for rounds in (1, 2):
            with self.subTest(rounds=rounds):
                run = self.make_run(rounds=rounds, verdict="fail")
                result = self.run_delivery(["lifecycle-draft", "--contract", str(self.task.contract),
                    "--artifact", str(self.artifact), "--reader-review-aggregate", str(self.aggregate),
                    "--lifecycle-run", str(run)])
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")

    def test_earlier_pass_does_not_hide_current_regression_or_block_current_draft(self):
        previous_pass = self.aggregate
        run = self.make_run()
        writing_lifecycle.start_review(run, self.artifact, stage="during")
        writing_lifecycle.finish_review(run, previous_pass, "pass")
        seed_fixture(run, previous_pass)
        self.aggregate = self.task.complete_reader_review(self.artifact, failing_dimension="no-context", expected=1)
        writing_lifecycle.start_review(run, self.artifact)
        writing_lifecycle.finish_review(run, self.aggregate, "fail")
        seed_fixture(run, self.aggregate)
        args = ["lifecycle-draft", "--contract", str(self.task.contract), "--artifact", str(self.artifact),
                "--reader-review-aggregate", str(self.aggregate), "--lifecycle-run", str(run)]
        result = self.run_delivery(args)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["delivery_state"], "draft")
        self.assertTrue(value["issues"])
        self.assertFalse(value["external_action_authorized"])
        self.assertNotEqual(self.run_delivery(["verify", *args[1:], "--review", str(self.task.review),
                                              "--actual-format", "html"]).returncode, 0)

    def test_action_entry_requires_lifecycle_without_an_opt_out(self):
        parsed = runtime_contract.build_parser().parse_args(["verify", *self.args[1:],
                                                            "--receipt", str(self.task.receipt)])
        self.assertIsNone(parsed.lifecycle_run)
        result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/runtime_contract.py"), "check-action",
            "--contract", str(self.task.contract), "--review", str(self.task.review), "--artifact", str(self.artifact),
            "--reader-review-aggregate", str(self.aggregate), "--action", "publish", "--target", "other",
            "--receipt", str(self.task.action_receipt)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.task.action_receipt.exists())


class ActionLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.task = fixtures.RuntimeContractTests()
        self.task.setUp()
        self.addCleanup(self.task.tearDown)
        self.task.init_contract("--explicit-format", "feishu", "--publication-target", "feishu", "--external-action", "publish",
                                "--external-action-authorized", "--authorization-evidence", "Synthetic explicit authorization")
        self.artifact = self.task.write_html(language="en", body="Only this inspected synthetic period is known. " * 5)
        self.task.complete_review(self.artifact)
        self.aggregate = self.task.complete_reader_review(self.artifact)
        self.args = ["check-action", "--contract", str(self.task.contract), "--review", str(self.task.review),
            "--artifact", str(self.artifact), "--reader-review-aggregate", str(self.aggregate),
            "--action", "publish", "--target", "feishu", "--receipt", str(self.task.action_receipt)]

    def command(self, args):
        return subprocess.run([sys.executable, "-B", str(ROOT / "scripts/runtime_contract.py"), *args],
                              capture_output=True, text=True)

    def test_complete_native_reviews_cannot_authorize_missing_lifecycle_stages(self):
        run = make_run(self.task.base / "incomplete", self.artifact, self.aggregate, until="init", contract_path=self.task.contract)
        result = self.command([*self.args, "--lifecycle-run", str(run)])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stages", result.stderr)
        self.assertFalse(self.task.action_receipt.exists())

    def preview_args(self, run):
        return ["check-action", "--contract", str(self.task.contract), "--review", str(self.task.review),
                "--artifact", str(self.artifact), "--action", "publish", "--target", "feishu",
                "--lifecycle-run", str(run), "--preview", "--receipt", str(self.task.action_receipt)]

    def test_authorized_preview_needs_no_review_pass_or_measured_layout(self):
        run = make_run(self.task.base / "preview", self.artifact, self.aggregate,
                       contract_path=self.task.contract, until="candidate", layout_status="unmeasured")
        review = json.loads(self.task.review.read_text())
        next(iter(review["checks"].values()))["status"] = "pending"
        self.task.review.write_text(json.dumps(review))
        result = self.command(self.preview_args(run))
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(self.task.action_receipt.read_text())
        self.assertEqual(value["status"], "preview-only")
        self.assertEqual(value["action_phase"], "preview")
        self.assertTrue(value["preview_write_authorized"])
        self.assertFalse(value["publishable"])
        self.assertFalse(value["verified_finished_artifact"])
        self.assertEqual(json.loads((run / "lifecycle.json").read_text())["rounds"], [])
        with self.assertRaises(checked_delivery.DeliveryBlocked):
            checked_delivery.pack(self.artifact, [], lambda: value)

    def test_preview_blocks_missing_stages_stale_candidate_and_different_native_basis(self):
        missing = make_run(self.task.base / "preview-missing", self.artifact, self.aggregate,
                           contract_path=self.task.contract, until="init")
        self.assertNotEqual(self.command(self.preview_args(missing)).returncode, 0)
        wrong = make_run(self.task.base / "preview-wrong", self.artifact, self.aggregate,
                         contract_path=self.task.contract, until="candidate", plan_changes={"task": "other"})
        self.assertNotEqual(self.command(self.preview_args(wrong)).returncode, 0)
        current = make_run(self.task.base / "preview-current", self.artifact, self.aggregate,
                           contract_path=self.task.contract, until="candidate")
        self.artifact.write_bytes(self.artifact.read_bytes() + b"<!-- stale candidate -->")
        self.assertNotEqual(self.command(self.preview_args(current)).returncode, 0)
        self.assertFalse(self.task.action_receipt.exists())

    def test_preview_cannot_change_the_existing_authorized_action(self):
        run = make_run(self.task.base / "preview-scope", self.artifact, self.aggregate,
                       contract_path=self.task.contract, until="candidate")
        args = self.preview_args(run)
        args[args.index("publish")] = "replace"
        self.assertNotEqual(self.command(args).returncode, 0)
        self.assertFalse(self.task.action_receipt.exists())

    def test_preview_cannot_invent_authorization_for_an_unlocked_external_action(self):
        other = fixtures.RuntimeContractTests()
        other.setUp()
        self.addCleanup(other.tearDown)
        other.init_contract()
        run = make_run(other.base / "unauthorized-preview", self.artifact, self.aggregate,
                       contract_path=other.contract, until="candidate")
        result = self.command(["check-action", "--contract", str(other.contract), "--review", str(other.review),
            "--artifact", str(self.artifact), "--action", "publish", "--target", "feishu",
            "--lifecycle-run", str(run), "--preview", "--receipt", str(other.action_receipt)])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not part of the locked task", result.stderr)
        self.assertFalse(other.action_receipt.exists())

    def test_preview_requires_candidate_registration_after_changed_unit_checkpoints(self):
        run = make_run(self.task.base / "preview-checkpoint", self.artifact, self.aggregate,
                       contract_path=self.task.contract, until="candidate")
        state = json.loads((run / "lifecycle.json").read_text())
        unit = self.task.base / "short-unit.txt"
        unit.write_text("Only this inspected synthetic period is known.")
        record = self.task.base / "new-unit.json"
        writing_lifecycle.write_json(record, {"unit_id": state["plan"]["reading_path"][0]["id"],
            "summary": "Synthetic incomplete unit, not full current prose",
            "observations": [{"quote": unit.read_text(), "reason": "Negative fixture: intentionally incomplete coverage"}]})
        writing_lifecycle.record_unit(run, unit, record)
        result = self.command(self.preview_args(run))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("register the complete candidate again", result.stderr)
        self.assertFalse(self.task.action_receipt.exists())

    def test_preview_receipt_never_becomes_final_even_after_full_reviews_pass(self):
        run = make_run(self.task.base / "preview-final", self.artifact, self.aggregate,
                       contract_path=self.task.contract, until="candidate")
        preview = self.command(self.preview_args(run))
        self.assertEqual(preview.returncode, 0, preview.stderr)
        writing_lifecycle.start_review(run, self.artifact)
        writing_lifecycle.finish_review(run, self.aggregate, "pass")
        result = self.command(["verify", "--contract", str(self.task.contract), "--review", str(self.task.review),
            "--artifact", str(self.artifact), "--reader-review-aggregate", str(self.aggregate),
            "--actual-format", "feishu", "--actual-publication-target", "feishu", "--actual-external-action", "publish",
            "--action-receipt", str(self.task.action_receipt), "--lifecycle-run", str(run),
            "--receipt", str(self.task.receipt)])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("preview-only receipt", result.stderr)

    def test_external_verify_cannot_use_a_bare_local_semantic_pass(self):
        result = self.command(["verify", "--contract", str(self.task.contract), "--review", str(self.task.review),
            "--artifact", str(self.artifact), "--reader-review-aggregate", str(self.aggregate),
            "--actual-format", "feishu", "--actual-publication-target", "feishu", "--actual-external-action", "publish",
            "--receipt", str(self.task.receipt)])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--lifecycle-run", result.stderr)
        self.assertFalse(json.loads(self.task.receipt.read_text())["verified_finished_artifact"])

    def test_action_receipt_is_stale_when_lifecycle_changes_even_if_latest_review_passes(self):
        run = make_run(self.task.base / "complete", self.artifact, self.aggregate, contract_path=self.task.contract)
        action = self.command([*self.args, "--lifecycle-run", str(run)])
        self.assertEqual(action.returncode, 0, action.stderr)
        writing_lifecycle.start_review(run, self.artifact)
        writing_lifecycle.finish_review(run, self.aggregate, "pass")
        verified = self.command(["verify", "--contract", str(self.task.contract), "--review", str(self.task.review),
            "--artifact", str(self.artifact), "--reader-review-aggregate", str(self.aggregate),
            "--actual-format", "feishu", "--actual-publication-target", "feishu", "--actual-external-action", "publish",
            "--action-receipt", str(self.task.action_receipt), "--lifecycle-run", str(run),
            "--receipt", str(self.task.receipt)])
        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("current lifecycle evidence", verified.stderr)


if __name__ == "__main__":
    unittest.main()
