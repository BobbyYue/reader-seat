"""Depth contract tests use synthetic evidence, not model-quality proxies."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import reader_answers as answers
import test_reader_answers as answer_tests
import test_runtime_contract as runtime_tests


class DepthPlanTests(unittest.TestCase):
    def setUp(self):
        self.plan = {
            "version": answers.CONTRACT_VERSION,
            "reader": {"profile": "New teammate", "known_context": "No pilot history", "decision": "Understand why internal testing precedes expansion"},
            "depth": {"mode": "explanation", "reason": "The substantive discussion includes a rationale needed to interpret the pilot choice"},
            "surfaces": [{"id": "body", "mode": "full", "reason": "A short complete explanation is needed for this task"}],
            "answers": [{"id": "A1", "kind": "reason", "question": "Why test internally?", "expected_information": "Experienced support staff can catch policy errors before they affect employees", "source_location": "Source paragraph one", "source_status": "supported", "required_on": ["body"]}]
        }

    def test_explanation_plan_passes_without_length_quota(self):
        self.assertEqual(answers.plan_errors(self.plan, require_depth=True), [])

    def test_no_depth_is_rejected_when_required(self):
        del self.plan["depth"]
        self.assertTrue(answers.plan_errors(self.plan, require_depth=True))
        self.assertEqual(answers.plan_errors(self.plan), [])

    def test_explanation_cannot_be_only_takeaways(self):
        self.plan["answers"][0]["kind"] = "takeaway"
        self.assertTrue(answers.plan_errors(self.plan, require_depth=True))

    def test_explicit_outline_can_use_orientation(self):
        self.plan["depth"] = {"mode": "orientation", "reason": "The user asks only for a list of topics"}
        self.plan["answers"][0]["kind"] = "takeaway"
        self.plan["surfaces"][0] = {"id": "body", "mode": "headings"}
        self.assertEqual(answers.plan_errors(self.plan, require_depth=True), [])

    def test_unknown_explanation_must_not_be_invented(self):
        self.plan["answers"][0].update(source_status="unknown", expected_information="The source does not explain the reason")
        self.assertEqual(answers.plan_errors(self.plan, require_depth=True), [])

    def test_headings_are_not_automatically_bad(self):
        self.plan["surfaces"][0] = {"id": "body", "mode": "headings"}
        self.assertEqual(answers.plan_errors(self.plan, require_depth=True), [])

    def test_execution_requires_action(self):
        self.plan["depth"]["mode"] = "execution"
        self.assertTrue(answers.plan_errors(self.plan, require_depth=True))
        self.plan["answers"][0]["kind"] = "action"
        self.assertEqual(answers.plan_errors(self.plan, require_depth=True), [])

    def test_malformed_depth_and_role_are_rejected(self):
        for value in (None, [], "explanation", {"mode": []}, {"mode": "explanation", "reason": "PASS"}):
            candidate = copy.deepcopy(self.plan)
            candidate["depth"] = value
            self.assertTrue(answers.plan_errors(candidate, require_depth=True))
        self.plan["answers"][0]["kind"] = []
        self.assertTrue(answers.plan_errors(self.plan, require_depth=True))


class DepthReplayTests(unittest.TestCase):
    def setUp(self):
        self.fixture = answer_tests.ReaderAnswersTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        f.plan["depth"] = {"mode": "explanation", "reason": "Test the supplied finding and the meaning of its eligibility boundary"}
        for answer in f.plan["answers"]:
            answer["kind"] = "evidence" if answer["id"] == "result" else "condition"
        f.prepare()
        f.evaluation["depth_fit"] = {"mode": "explanation", "status": "pass", "reason": "STRUCTURAL FIXTURE, not a semantic judgment", "reader_quote": f.responses[0]["findings"][0], "source_quote": f.source_path.read_text().strip()}

    def test_complete_bound_evidence_passes(self):
        self.assertEqual(self.fixture.validate(), [])

    def test_blanket_answer_coverage_does_not_replace_depth(self):
        del self.fixture.evaluation["depth_fit"]
        self.assertTrue(self.fixture.validate())

    def test_recognized_overcompression_blocks_even_when_all_labels_match(self):
        self.fixture.evaluation["depth_fit"]["status"] = "fail"
        self.assertTrue(self.fixture.validate())

    def test_mode_or_quotes_cannot_be_faked(self):
        for field, value in (("mode", "orientation"), ("source_quote", "Invented source evidence"), ("reader_quote", "The author supplied this but reader never said it"), ("reason", "PASS")):
            original = copy.deepcopy(self.fixture.evaluation["depth_fit"])
            self.fixture.evaluation["depth_fit"][field] = value
            self.assertTrue(self.fixture.validate())
            self.fixture.evaluation["depth_fit"] = original


class DepthRuntimeTests(unittest.TestCase):
    def test_init_refuses_legacy_artifact_plan(self):
        fixture = runtime_tests.RuntimeContractTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        plan = answers.load(fixture.answer_plan)
        del plan["depth"]
        answers.save(fixture.answer_plan, plan)
        result = fixture.run_cli("init", "--contract", str(fixture.contract), "--review", str(fixture.review), "--scenario", "news", "--operation", "create", "--channel", "artifact", "--source-language", "en", expected=2)
        self.assertIn("depth", result.stdout + result.stderr)

    def test_aggregate_requires_depth_evidence(self):
        fixture = runtime_tests.RuntimeContractTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        fixture.init_contract()
        artifact = fixture.base / "report.html"
        artifact.write_text("<html><body>Observed changes in the pilot only.</body></html>")
        aggregate_path = fixture.complete_reader_review(artifact)
        import reader_review
        aggregate = answers.load(aggregate_path)
        manifest = answers.load(aggregate["manifest_path"])
        record = next(r for r in aggregate["reviews"] if r["dimension"] == "source-reliability")
        result_path = Path(record["result_path"])
        result = answers.load(result_path)
        del result["answer_evaluation"]["depth_fit"]
        answers.save(result_path, result)
        errors, _ = reader_review.validate_aggregate_for_artifact(aggregate_path, answers.load(fixture.contract), artifact)
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
