"""Synthetic protocol tests, not measured model judgment or human comprehension."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import reader_answers as ra
import reader_outcomes


class JudgmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.txt"
        self.artifact = self.root / "artifact.md"
        self.source.write_text("SYNTHETIC: five of twelve apps older than a year include only first install. Release date is unknown. Check the callback before enabling.")
        self.artifact.write_text("Five of twelve apps include only first install. Release date is unknown. Check the callback before enabling.")
        self.plan_path, self.lock_path = self.root / "plan.json", self.root / "lock.json"
        self.plan = {"version": ra.CONTRACT_VERSION,
            "reader": {"profile": "Analyst", "known_context": "Understands install categories", "decision": "Identify coverage scope requiring inspection"},
            "depth": {"mode": "orientation", "reason": "The requested output is one bounded observed finding"},
            "surfaces": [{"id": "main", "mode": "full", "reason": "This fixture is one short message"}],
            "answers": [{"id": "A1", "kind": "takeaway", "question": "Which mature apps only include first install, and how many?",
                "reader_use": "Locate the size of the coverage-check population",
                "expected_information": "Five of twelve mature apps include only first install", "source_location": "Synthetic source",
                "source_status": "supported", "required_on": ["main"]}]}

    def prepare(self):
        ra.save(self.plan_path, self.plan)
        ra.save(self.lock_path, ra.lock_plan(self.plan_path, self.source, require_depth=True))
        self.manifest = ra.prepare(self.lock_path, self.artifact, self.root / "surfaces")
        surface = self.manifest["surfaces"][0]
        self.raw = [{"surface_id": "main", "surface_sha256": surface["sha256"], "reader_id": "synthetic-blind-reader",
                     "findings": [self.artifact.read_text()], "remaining_questions": []}]
        self.judgment = {"question_fit": "pass", "answer_fit": "pass", "support_fit": "pass", "form": "fact", "inference": False,
                         "candidate_quote": "Five of twelve apps include only first install.", "source_quote": "five of twelve apps older than a year include only first install.",
                         "bridge": "", "rationale": "Synthetic declared judgment: the bounded count answers this task", "repair": ""}
        self.evaluation = {"manifest_sha256": ra.object_digest(self.manifest), "response_sha256": ra.object_digest(self.raw),
            "reviewer_id": "synthetic-source-reviewer", "plan_source_coverage": "pass", "source_coverage_evidence": "Synthetic fixture scope only",
            "source_fidelity": "pass", "questions": [],
            "depth_fit": {"mode": "orientation", "status": "pass", "reason": "Synthetic one-finding task",
                          "reader_quote": self.raw[0]["findings"][0], "source_quote": "five of twelve apps"},
            "answers": [{"answer_id": "A1", "surface_id": "main", "status": "pass",
                         "reader_quote": self.raw[0]["findings"][0], "rationale": "Synthetic actual replay", "judgment": self.judgment}]}

    def outcome(self):
        return reader_outcomes.summarize(self.manifest, self.raw, self.evaluation)

    def test_reader_use_required_before_drafting(self):
        del self.plan["answers"][0]["reader_use"]
        ra.save(self.plan_path, self.plan)
        with self.assertRaisesRegex(ValueError, "reader_use"):
            ra.lock_plan(self.plan_path, self.source, require_depth=True)
        self.assertFalse(self.lock_path.exists())

    def test_supported_direct_finding_needs_no_invented_bridge(self):
        self.prepare()
        self.assertEqual(ra.load(self.lock_path)["judgment_quality_version"], 1)
        self.assertEqual(ra.validate_answers(self.manifest, self.raw, self.evaluation), [])
        self.assertEqual(self.outcome()["judgment_quality"]["status"], "pass")

    def test_missing_judgment_blocks_verification(self):
        self.prepare()
        del self.evaluation["answers"][0]["judgment"]
        self.assertIn("actual task-value review", "\n".join(ra.validate_answers(self.manifest, self.raw, self.evaluation)))
        self.assertEqual(ra.outcome_record(self.manifest, self.raw, self.evaluation)["status"], "unmeasured")

    def test_exact_candidate_and_source_quotes_required(self):
        self.prepare()
        for field in ("candidate_quote", "source_quote"):
            original = self.judgment[field]
            self.judgment[field] = "Invented text not in the bound inputs"
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, field):
                self.outcome()
            self.judgment[field] = original

    def test_inferred_claim_requires_bridge(self):
        self.prepare()
        self.judgment["inference"] = True
        with self.assertRaisesRegex(ValueError, "inferential|inferred claim"):
            self.outcome()
        self.judgment["bridge"] = "Synthetic bridge explaining how the configuration definition fixes the included states"
        self.assertEqual(self.outcome()["judgment_quality"]["status"], "pass")

    def test_vague_question_cannot_be_hidden_by_answer_pass(self):
        self.plan["answers"][0]["question"] = "What differences exist?"
        self.prepare()
        self.judgment.update(question_fit="fail", repair="Replace the topic question with the specific coverage question")
        with self.assertRaisesRegex(ValueError, "cannot coexist"):
            self.outcome()
        self.evaluation["answers"][0]["status"] = "unassessed"
        result = self.outcome()
        self.assertEqual(result["judgment_quality"]["status"], "revision_required")
        self.assertEqual(result["questions"]["unassessed"], 1)

    def test_method_substitute_returns_actionable_repair(self):
        self.artifact.write_text("Mature products differ. Analyze install categories separately.")
        self.prepare()
        self.evaluation["answers"][0]["status"] = "fail"
        self.judgment.update(form="method_note", candidate_quote=self.artifact.read_text(), answer_fit="fail",
                             rationale="The requested count is replaced by advice to analyze", repair="State the supplied five-of-twelve observation")
        result = self.outcome()
        self.assertEqual(result["judgment_quality"]["problems"][0]["checks"], ["answer_fit"])
        self.assertIn("five-of-twelve", "\n".join(ra.validate_answers(self.manifest, self.raw, self.evaluation)))

    def test_configuration_does_not_establish_revenue_loss(self):
        self.artifact.write_text("Missing coverage lost 20% of revenue.")
        self.prepare()
        self.evaluation["answers"][0]["status"] = "fail"
        self.judgment.update(form="finding", candidate_quote=self.artifact.read_text(), inference=True,
                             bridge="A configuration count does not measure revenue loss", support_fit="fail",
                             rationale="Revenue loss is not observed by the source", repair="Remove the revenue-loss claim; retain the configuration finding")
        self.assertEqual(self.outcome()["judgment_quality"]["problems"][0]["checks"], ["support_fit"])

    def test_real_instruction_task_can_use_instruction(self):
        self.plan["answers"][0].update(question="What must be checked before enabling?", reader_use="Perform the prerequisite callback check",
                                      expected_information="Check the callback before enabling")
        self.prepare()
        self.judgment.update(form="instruction", candidate_quote="Check the callback before enabling.", source_quote="Check the callback before enabling.")
        self.assertEqual(ra.validate_answers(self.manifest, self.raw, self.evaluation), [])

    def test_disclosed_unknown_is_a_usable_answer(self):
        self.plan["answers"][0].update(question="Is the release date known?", reader_use="Avoid planning around an unconfirmed date",
                                      expected_information="The date is unknown", source_status="unknown")
        self.prepare()
        self.judgment.update(form="unknown", candidate_quote="Release date is unknown.", source_quote="Release date is unknown.")
        self.assertEqual(ra.validate_answers(self.manifest, self.raw, self.evaluation), [])

    def test_evidence_recomputation_rejects_quality_tampering(self):
        import test_runtime_contract
        import reader_review
        fixture = test_runtime_contract.RuntimeContractTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        fixture.init_contract()
        artifact = fixture.base / "report.html"
        artifact.write_text("<html><body>Observed changes in the pilot only.</body></html>")
        aggregate_path = fixture.complete_reader_review(artifact)
        aggregate = ra.load(aggregate_path)
        self.assertEqual(aggregate["reader_outcomes"]["judgment_quality"]["status"], "pass")
        aggregate["reader_outcomes"]["judgment_quality"]["records"] = []
        ra.save(aggregate_path, aggregate)
        errors, _ = reader_review.validate_aggregate_for_artifact(aggregate_path, ra.load(fixture.contract), artifact)
        self.assertIn("outcomes differ", "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
