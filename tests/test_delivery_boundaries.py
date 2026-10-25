"""Synthetic regressions for stale references and unbound acceptance records."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import checked_delivery as delivery


class DeliveryBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.artifact = self.root / "artifact.txt"
        self.artifact.write_text("SYNTHETIC content")
        self.sha = delivery.digest(self.artifact.read_bytes())

    def manifest(self, items):
        path = self.root / "evidence.json"
        path.write_text(json.dumps(items))
        return path

    def test_wrong_hash_cannot_be_ignored(self):
        manifest = self.manifest({"path": str(self.artifact), "sha256": "0" * 64})
        with self.assertRaises(delivery.DeliveryBlocked):
            delivery.snapshots([manifest])

    def test_source_json_is_opaque_but_still_hash_bound(self):
        source = self.root / "source.json"
        source.write_text(json.dumps({"path": str(self.root / "not-uploaded.txt"), "sha256": "0" * 64}))
        source_sha = delivery.digest(source.read_bytes())
        evidence = self.manifest({"path": str(source), "sha256": source_sha})
        self.assertEqual(delivery.snapshots([evidence], opaque_paths=[source])[str(source)], source_sha)
        source.write_text('{"message": "changed"}')
        with self.assertRaises(delivery.DeliveryBlocked):
            delivery.snapshots([evidence], opaque_paths=[source])

    def test_conflicting_reference_is_rejected_in_both_orders(self):
        good = {"path": str(self.artifact), "sha256": self.sha}
        bad = {"path": str(self.artifact), "sha256": "0" * 64}
        for records in ([good, bad], [bad, good]):
            with self.subTest(records=records), self.assertRaises(delivery.DeliveryBlocked):
                delivery.snapshots([self.manifest(records)])

    def test_matching_duplicate_reference_is_safe(self):
        good = {"path": str(self.artifact), "sha256": self.sha}
        self.assertEqual(delivery.snapshots([self.manifest([good, good])])[str(self.artifact)], self.sha)

    def test_inactive_history_is_scoped_and_whole_record_stays_watched(self):
        old = {"path": str(self.artifact), "sha256": "0" * 64}
        manifest = self.manifest({"old": old})
        inactive = {str(manifest): {("old",)}}
        before = delivery.snapshots([manifest, self.artifact], inactive_fields=inactive)
        self.assertIn(str(manifest), before)
        self.manifest({"old": {**old, "note": "history changed"}})
        self.assertNotEqual(before, delivery.snapshots([manifest, self.artifact], inactive_fields=inactive))
        self.manifest({"old": old, "current": old})
        with self.assertRaises(delivery.DeliveryBlocked):
            delivery.snapshots([manifest], inactive_fields=inactive)
        with self.assertRaises(delivery.DeliveryBlocked):
            delivery.snapshots([manifest])

    def test_path_suffix_reference_is_checked(self):
        manifest = self.manifest({"source_path": str(self.artifact), "source_sha256": "0" * 64})
        with self.assertRaises(delivery.DeliveryBlocked):
            delivery.snapshots([manifest])

    def test_previsited_direct_file_does_not_hide_conflicting_nested_reference(self):
        manifest = self.manifest({"path": str(self.artifact), "sha256": "0" * 64})
        with self.assertRaises(delivery.DeliveryBlocked):
            delivery.snapshots([manifest, self.artifact])

    def test_missing_method_and_consumed_input_binding_cannot_be_accepted(self):
        complete = {"status": "pass", "artifact_sha256": self.sha, "review_method": "independent",
                    "verified_inputs": {str(self.artifact): self.sha}}
        for key in ("review_method", "verified_inputs"):
            result = dict(complete)
            del result[key]
            with self.subTest(key=key), self.assertRaises(delivery.DeliveryBlocked):
                delivery.pack(self.artifact, [], lambda: result)
        for inputs in ({}, [], None, {str(self.artifact): "0" * 64}):
            with self.subTest(inputs=inputs), self.assertRaises(delivery.DeliveryBlocked):
                delivery.pack(self.artifact, [], lambda: {**complete, "verified_inputs": inputs})


if __name__ == "__main__":
    unittest.main()
