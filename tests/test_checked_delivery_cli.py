"""End-to-end delivery wiring with existing structural fixtures, not real reviewers."""
import base64
import json
import subprocess
import sys
import unittest
from pathlib import Path

import test_runtime_contract as fixtures

ROOT = Path(__file__).resolve().parents[1]


class CheckedDeliveryCLITests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.RuntimeContractTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.fixture.init_contract()
        self.artifact = self.fixture.write_html(language="en", body="This fixture reports only the inspected period; later data is unknown. " * 4)
        self.fixture.complete_review(self.artifact)
        self.aggregate = self.fixture.complete_reader_review(self.artifact)
        self.args = ["verify", "--contract", str(self.fixture.contract), "--review", str(self.fixture.review),
                     "--artifact", str(self.artifact), "--actual-format", "html",
                     "--reader-review-aggregate", str(self.aggregate)]

    def run_delivery(self, args=None):
        return subprocess.run([sys.executable, "-B", str(ROOT / "scripts/deliver.py"),
                               *(self.args if args is None else args)], capture_output=True, text=True)

    def test_real_runtime_verifier_returns_exact_candidate(self):
        result = self.run_delivery()
        self.assertEqual(result.returncode, 0, result.stderr)
        envelope = json.loads(result.stdout)
        self.assertEqual(envelope["delivery_state"], "checked")
        self.assertEqual(base64.b64decode(envelope["payload"]), self.artifact.read_bytes())
        self.assertFalse(envelope["external_action_authorized"])

    def test_init_or_bare_receipt_is_not_delivery(self):
        self.assertNotEqual(self.run_delivery(["init"]).returncode, 0)
        self.assertNotEqual(self.run_delivery([*self.args, "--receipt", str(self.fixture.receipt)]).returncode, 0)

    def test_missing_review_blocks(self):
        self.aggregate.unlink()
        result = self.run_delivery()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_changed_candidate_cannot_reuse_pass(self):
        self.artifact.write_text(self.artifact.read_text() + "<p>A different unsupported claim.</p>")
        result = self.run_delivery()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_pending_semantic_check_cannot_deliver(self):
        review = json.loads(self.fixture.review.read_text())
        next(iter(review["checks"].values()))["status"] = "pending"
        self.fixture.review.write_text(json.dumps(review))
        self.assertNotEqual(self.run_delivery().returncode, 0)

    def test_third_round_fallback_is_draft_not_checked(self):
        previous = None
        for round_number in range(1, 4):
            self.artifact.write_text(self.artifact.read_text() + f"\n<!-- repair {round_number} -->\n")
            previous = self.fixture.complete_reader_review(self.artifact, round_number=round_number,
                previous_aggregate=previous, failing_dimension="no-context", expected=1)
        args = ["present-draft", "--contract", str(self.fixture.contract), "--artifact", str(self.artifact),
                "--reader-review-aggregate", str(previous)]
        result = self.run_delivery(args)
        self.assertEqual(result.returncode, 0, result.stderr)
        envelope = json.loads(result.stdout)
        self.assertEqual(envelope["delivery_state"], "draft")
        self.assertTrue(envelope["issues"])
        self.assertTrue(envelope["user_question_required"])
        self.assertFalse(envelope["external_action_authorized"])
        self.assertEqual(base64.b64decode(envelope["payload"]), self.artifact.read_bytes())


if __name__ == "__main__":
    unittest.main()
