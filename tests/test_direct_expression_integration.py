"""SYNTHETIC before/during/after wiring tests, not reader-quality evidence."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import direct_expression
import lifecycle_guard
import reader_value
import writing_lifecycle as lifecycle
import test_runtime_contract as runtime_fixtures
from editorial_fixture import structural_review
from expression_fixture import structural_expression
from lifecycle_support import make_run


TEXT = "请先完成回滚验证。\n不能省略的责任：记录结果。\n不能省略的责任：复核条件。"


class BeforeExpressionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = runtime_fixtures.RuntimeContractTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.plan = json.loads(self.fixture.answer_plan.read_text())

    def init(self, plan, expected=0):
        self.fixture.answer_plan.write_text(json.dumps(plan), encoding="utf-8")
        return self.fixture.run_cli(
            "init", "--contract", str(self.fixture.contract), "--review", str(self.fixture.review),
            "--scenario", "news", "--operation", "create", "--channel", "artifact",
            "--source-language", "en", expected=expected)

    def test_runtime_init_requires_expression_preplan_before_creating_contract(self):
        del self.plan["expression_plan"]
        result = self.init(self.plan, expected=2)
        self.assertIn("expression_plan", result.stderr)
        self.assertFalse(self.fixture.contract.exists())
        self.assertFalse(self.fixture.review.exists())

    def test_runtime_init_rejects_unknown_lead_and_boundary_answers(self):
        for field in ("lead", "boundary"):
            with self.subTest(field=field):
                plan = copy.deepcopy(self.plan)
                if field == "lead":
                    plan["expression_plan"]["lead_answer_ids"] = ["removed-answer"]
                else:
                    plan["expression_plan"]["essential_boundaries"] = [{
                        "answer_id": "removed-answer", "placement": "claim-adjacent",
                        "reason": "SYNTHETIC: the answer was removed after this plan was written."}]
                result = self.init(plan, expected=2)
                self.assertIn("expression_plan", result.stderr)
                self.assertFalse(self.fixture.contract.exists())

    def test_runtime_init_rejects_malformed_expression_plan_without_traceback(self):
        for bad in (None, [], False, {"lead_answer_ids": [{}], "opening_move": []}):
            with self.subTest(value=bad):
                plan = copy.deepcopy(self.plan)
                plan["expression_plan"] = bad
                result = self.init(plan, expected=2)
                self.assertIn("expression_plan", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_runtime_init_locks_exact_plan_and_projects_it_into_lifecycle(self):
        self.init(self.plan)
        projected, _ = lifecycle_guard.native_plan(self.fixture.contract)
        self.assertEqual(projected["expression_plan"], self.plan["expression_plan"])
        run = self.fixture.base / "native-run"
        lifecycle_guard.init_native_run(run, self.fixture.contract)
        with lifecycle.session(run) as state:
            self.assertEqual(state["plan"]["expression_plan"], self.plan["expression_plan"])
        self.assertTrue(lifecycle_guard.validate_native_binding(run, self.fixture.contract))

    def test_changed_preplan_reason_cannot_reuse_native_answer_lock(self):
        self.init(self.plan)
        self.plan["expression_plan"]["opening_reason"] = "SYNTHETIC: changed audience and opening intent."
        self.fixture.answer_plan.write_text(json.dumps(self.plan), encoding="utf-8")
        with self.assertRaises(ValueError):
            lifecycle_guard.native_plan(self.fixture.contract)

    def test_native_binding_rejects_expression_plan_changed_only_in_lifecycle(self):
        self.init(self.plan)
        plan, sources = lifecycle_guard.native_plan(self.fixture.contract)
        plan["expression_plan"]["opening_reason"] = "SYNTHETIC: a different valid reason is still not the locked plan."
        changed = self.fixture.base / "changed-plan.json"
        lifecycle.write_json(changed, plan)
        run = self.fixture.base / "changed-run"
        lifecycle.init_run(run, changed, "functional", [item["path"] for item in sources])
        with self.assertRaises(ValueError):
            lifecycle_guard.validate_native_binding(run, self.fixture.contract)


class DuringExpressionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.text = TEXT
        self.artifact = self.root / "draft.txt"
        self.artifact.write_text(self.text, encoding="utf-8")
        self.run = make_run(self.root / "flow", self.artifact, self.root / "unused-result.json",
                            format="text", until="init")
        self.record_path = self.root / "unit.json"
        self.record = {
            "unit_id": "body", "summary": "SYNTHETIC complete-unit checkpoint, not a real editorial review.",
            "observations": [{"quote": self.text.splitlines()[0], "reason": "SYNTHETIC exact-text anchor."}],
            "expression_review": structural_expression(self.text, "during"),
        }

    def register(self, record):
        lifecycle.write_json(self.record_path, record)
        return lifecycle.record_unit(self.run, self.artifact, self.record_path)

    def assert_blocked_without_state_change(self, record):
        state_path = self.run / "lifecycle.json"
        before = state_path.read_bytes()
        with self.assertRaises(lifecycle.LifecycleError):
            self.register(record)
        self.assertEqual(state_path.read_bytes(), before)

    def test_functional_lifecycle_init_requires_preplan(self):
        plan = lifecycle.load_json(self.run.parent / "plan.json")
        del plan["expression_plan"]
        path = self.root / "missing-plan.json"
        lifecycle.write_json(path, plan)
        run = self.root / "rejected-run"
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.init_run(run, path, "functional", [self.artifact])
        self.assertFalse(run.exists())

    def test_register_unit_accepts_current_during_review_and_retains_it(self):
        self.assertEqual(self.register(self.record)["status"], "unit-recorded")
        with lifecycle.session(self.run) as state:
            self.assertEqual(len(state["units"]), 1)
            self.assertEqual(state["units"][0]["record"]["expression_review"], self.record["expression_review"])

    def test_register_unit_rejects_missing_review_without_recording_a_unit(self):
        del self.record["expression_review"]
        self.assert_blocked_without_state_change(self.record)

    def test_register_unit_rejects_stale_text_stage_and_version(self):
        for field, value in (("text_sha256", "stale"), ("stage", "after"), ("version", 0)):
            with self.subTest(field=field):
                record = copy.deepcopy(self.record)
                record["expression_review"][field] = value
                self.assert_blocked_without_state_change(record)

    def test_register_unit_rejects_changed_text_even_with_current_observation(self):
        self.artifact.write_text(self.text + "\n发布日期待定。", encoding="utf-8")
        self.record["observations"] = [{"quote": "发布日期待定。", "reason": "SYNTHETIC new observation, stale expression review."}]
        self.assert_blocked_without_state_change(self.record)

    def test_register_unit_rejects_missing_alternative_and_repeated_family(self):
        for omission in ("alternative", "clusters"):
            with self.subTest(omission=omission):
                record = copy.deepcopy(self.record)
                review = record["expression_review"]
                if omission == "alternative":
                    del review["comparisons"][0]["alternative"]
                else:
                    review["whole_text"]["clusters"] = []
                self.assert_blocked_without_state_change(record)

    def test_register_unit_rejects_revise_despite_complete_other_observations(self):
        self.record["expression_review"]["comparisons"][0]["decision"] = "revise"
        self.assert_blocked_without_state_change(self.record)

    def test_register_unit_rejects_malformed_review_without_crashing(self):
        for bad in ([], False, 9, {"opening": []}, None):
            with self.subTest(value=bad):
                record = copy.deepcopy(self.record)
                record["expression_review"] = bad
                self.assert_blocked_without_state_change(record)

    def test_init_binds_current_direct_expression_helper_hash(self):
        with lifecycle.session(self.run) as state:
            self.assertEqual(state["implementation"]["direct_expression"],
                             lifecycle.sha(Path(direct_expression.__file__).read_bytes()))
            self.assertEqual(state["implementation"], lifecycle.implementation())

    def test_changed_helper_bytes_invalidate_session_without_editing_scripts(self):
        original = Path(direct_expression.__file__).read_bytes()
        helper = self.root / "SYNTHETIC-direct-expression.py"
        helper.write_bytes(original)
        with patch.object(direct_expression, "__file__", str(helper)):
            with lifecycle.session(self.run):
                pass
            helper.write_bytes(original + b"\n# SYNTHETIC helper change, not executed.\n")
            with self.assertRaises(lifecycle.LifecycleError):
                with lifecycle.session(self.run):
                    pass
            self.assert_blocked_without_state_change(self.record)
        with lifecycle.session(self.run) as state:
            self.assertEqual(state["units"], [])

    def test_missing_helper_binding_fails_even_with_valid_state_digest(self):
        path = self.run / "lifecycle.json"
        state = lifecycle.load_json(path)
        del state["implementation"]["direct_expression"]
        state["state_digest"] = lifecycle.seal(state)
        lifecycle.write_json(path, state)
        with self.assertRaises(lifecycle.LifecycleError):
            with lifecycle.session(self.run):
                pass


class AfterExpressionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.text = TEXT
        self.binding = "a" * 64
        self.axes = ("expression",)
        self.record = structural_review(self.axes, self.binding, self.text)

    def errors(self, record):
        return reader_value.validate(record, self.axes, self.binding, self.text)

    def test_reader_value_v5_requires_current_after_record(self):
        self.assertEqual(self.record["version"], 5)
        self.assertEqual(self.record["checks"]["expression"]["direct_expression"]["stage"], "after")
        self.assertEqual(self.errors(self.record), [])

    def test_parent_pass_cannot_hide_missing_after_review(self):
        del self.record["checks"]["expression"]["direct_expression"]
        self.assertTrue(self.errors(self.record))

    def test_stale_after_data_cannot_be_rescued_by_current_artifact_binding(self):
        for field, value in (("text_sha256", "stale"), ("version", 0), ("stage", "during")):
            with self.subTest(field=field):
                record = copy.deepcopy(self.record)
                record["checks"]["expression"]["direct_expression"][field] = value
                self.assertTrue(self.errors(record))
        self.record["version"] = 4
        self.assertTrue(self.errors(self.record))

    def test_missing_alternative_or_family_is_final_semantic_failure(self):
        for omission in ("alternative", "clusters"):
            with self.subTest(omission=omission):
                record = copy.deepcopy(self.record)
                review = record["checks"]["expression"]["direct_expression"]
                if omission == "alternative":
                    del review["comparisons"][0]["alternative"]
                else:
                    review["whole_text"]["clusters"] = []
                self.assertTrue(self.errors(record))

    def test_revise_is_final_semantic_failure_despite_parent_and_craft_pass(self):
        item = self.record["checks"]["expression"]
        self.assertEqual(item["status"], "pass")
        self.assertEqual(item["action"], "keep")
        self.assertTrue(all(check["status"] == "pass" for check in item["craft_checks"].values()))
        item["direct_expression"]["whole_text"]["decision"] = "revise"
        self.assertTrue(self.errors(self.record))

    def test_no_signal_final_text_still_requires_opening_and_whole_review(self):
        self.text = "请周五前提交回滚记录。"
        record = structural_review(self.axes, self.binding, self.text)
        self.assertEqual(self.errors(record), [])
        for field in ("opening", "whole_text"):
            with self.subTest(field=field):
                missing = copy.deepcopy(record)
                del missing["checks"]["expression"]["direct_expression"][field]
                self.assertTrue(self.errors(missing))

    def test_malformed_after_review_is_rejected_without_crashing(self):
        for bad in (None, [], False, 9, {"comparisons": [None]}):
            with self.subTest(value=bad):
                record = copy.deepcopy(self.record)
                record["checks"]["expression"]["direct_expression"] = bad
                self.assertTrue(self.errors(record))


if __name__ == "__main__":
    unittest.main()
