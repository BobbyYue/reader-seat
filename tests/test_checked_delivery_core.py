"""Fault injection into the real envelope boundary, not a semantic-quality test."""
import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import checked_delivery as delivery


class CheckedDeliveryCoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.artifact = self.root / "candidate.txt"
        self.artifact.write_bytes(b"Only yesterday's data was inspected.\n")
        self.source = self.root / "source.txt"
        self.source.write_bytes(self.artifact.read_bytes())

    def tearDown(self):
        self.tmp.cleanup()

    def result(self, **extra):
        digest = delivery.digest(self.artifact.read_bytes())
        return {"status": "pass", "review_method": "independent", "artifact_sha256": digest,
                "verified_inputs": {str(self.artifact.resolve()): digest}, **extra}

    def test_nonfinal_success_states_never_release_payload(self):
        for status in ("PENDING", "prepared", "built", "ready", "PASS_SCHEMA_ONLY", "fail", None):
            with self.subTest(status=status), self.assertRaises(delivery.DeliveryBlocked):
                delivery.pack(self.artifact, [self.source], lambda: {"status": status})

    def test_exact_bytes_are_returned_without_rewriting(self):
        value = delivery.pack(self.artifact, [self.source], self.result)
        self.assertEqual(base64.b64decode(value["payload"]), self.artifact.read_bytes())
        self.assertFalse(value["external_action_authorized"])
        self.assertEqual(value["verification_scope"], "local-candidate-only")

    def test_candidate_or_source_changed_during_check_blocks(self):
        for changed in (self.artifact, self.source):
            def mutate():
                changed.write_bytes(changed.read_bytes() + b" changed")
                return self.result()
            with self.subTest(changed=changed.name), self.assertRaises(delivery.DeliveryBlocked):
                delivery.pack(self.artifact, [self.source], mutate)

    def test_nested_bound_review_changed_during_check_blocks(self):
        review = self.root / "review.json"
        review.write_text('{"status":"pass"}')
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps({"review": {"path": str(review), "sha256": delivery.digest(review.read_bytes())}}))
        def mutate():
            review.write_text('{"status":"fail"}')
            return self.result()
        with self.assertRaises(delivery.DeliveryBlocked):
            delivery.pack(self.artifact, [manifest], mutate)

    def test_draft_is_not_checked_or_publishable(self):
        value = delivery.pack(self.artifact, [], lambda: self.result(
            status="review-incomplete-draft", issues=[{"reader_impact": "Scope remains unclear"}]))
        self.assertEqual(value["delivery_state"], "draft")
        self.assertTrue(value["user_notice_required"])
        self.assertTrue(value["user_question_required"])
        self.assertFalse(value["external_action_authorized"])
        with self.assertRaises(delivery.DeliveryBlocked):
            delivery.pack(self.artifact, [], lambda: self.result(status="review-incomplete-draft", issues=[]))

    def test_pass_for_other_bytes_does_not_release_this_candidate(self):
        with self.assertRaises(delivery.DeliveryBlocked):
            delivery.pack(self.artifact, [], lambda: self.result(artifact_sha256="0" * 64))

    def test_existing_output_and_symlink_are_not_overwritten(self):
        output = self.root / "out.json"
        output.symlink_to(self.artifact)
        before = self.artifact.read_bytes()
        with self.assertRaises(FileExistsError):
            delivery.emit({"status": "pass"}, output)
        self.assertEqual(before, self.artifact.read_bytes())

    def test_exception_emits_no_payload(self):
        def broken():
            raise OSError("Unavailable verifier")
        with self.assertRaises(OSError):
            delivery.pack(self.artifact, [], broken)


if __name__ == "__main__":
    unittest.main()
