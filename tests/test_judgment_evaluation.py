"""Arithmetic on synthetic labels, not human or cross-platform validation."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from evaluate_judgments import evaluate


class JudgmentEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.dataset = {"label_origin": "synthetic", "label_reference": "Invented arithmetic fixture",
            "cases": [{"id": "valid", "category": "fidelity", "expected": "keep"},
                      {"id": "invalid", "category": "fidelity", "expected": "revise"}],
            "expected_runs": [{"id": "r1", "host": "fixture-a", "model": "synthetic"},
                              {"id": "r2", "host": "fixture-b", "model": "synthetic"}]}
        self.records = [{"run_id": run, "case_id": case, "status": "completed", "prediction": label,
                         "evidence_ref": "synthetic-output"}
                        for run in ("r1", "r2") for case, label in (("valid", "keep"), ("invalid", "revise"))]

    def run_eval(self):
        return evaluate(self.dataset, {"dataset_sha256": "a" * 64, "records": self.records}, "a" * 64)

    def test_complete_arithmetic_does_not_claim_host_or_quality_certification(self):
        report = self.run_eval()
        self.assertEqual(report["total"]["correct"], 4)
        self.assertEqual(report["total"]["correct_over_planned"], 1)
        self.assertFalse(report["quality_certified"])
        self.assertFalse(report["host_integration_certified"])

    def test_error_abstention_missing_and_wrong_predictions_stay_in_denominator(self):
        self.records[0]["prediction"] = "revise"
        self.records[1]["prediction"] = "keep"
        self.records[2]["prediction"] = "abstain"
        self.records[3].update(status="error", prediction=None)
        report = self.run_eval()
        self.assertEqual(report["total"]["unnecessary_revision"], 1)
        self.assertEqual(report["total"]["missed_problem"], 1)
        self.assertEqual(report["total"]["abstained"], 1)
        self.assertEqual(report["total"]["errors"], 1)
        self.records.pop()
        report = self.run_eval()
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["total"]["planned"], 4)

    def test_duplicate_cannot_inflate_success(self):
        self.records.append(dict(self.records[0]))
        with self.assertRaises(ValueError):
            self.run_eval()

    def test_changed_dataset_cannot_reuse_results(self):
        with self.assertRaises(ValueError):
            evaluate(self.dataset, {"dataset_sha256": "different", "records": self.records}, "a" * 64)

    def test_worst_run_and_disagreement_remain_visible(self):
        self.records[-1]["prediction"] = "keep"
        result = self.run_eval()
        self.assertEqual(result["worst_run_correct_over_planned"], 0.5)
        self.assertEqual(result["disagreement_case_ids"], ["invalid"])


if __name__ == "__main__":
    unittest.main()
