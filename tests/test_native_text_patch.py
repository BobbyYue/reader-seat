"""Local structural regression fixtures, NOT actual Feishu rendering evidence.

The synthetic PNG/JPEG and invented reader/inspection identities below test the
receipt protocol only. Passing these tests does not establish live document
write success, visual quality, screenshot provenance, or semantic reader quality.
"""
from __future__ import annotations

import copy
import json
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import native_text_patch as patch
import reader_answers


def png_fixture(rgb=b"\xff\xff\xff"):
    """Create a one-pixel structural fixture; never a native-render receipt."""
    def chunk(tag, body):
        return (struct.pack(">I", len(body)) + tag + body
                + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00" + rgb)) + chunk(b"IEND", b""))


class NativeTextPatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="native-patch-structural-fixture-")
        self.base = Path(self.temp.name)
        self.paths = {name: self.base / (name + ".json") for name in patch.INPUT_NAMES}
        self.baseline = {
            "document_id": "doc-structural-fixture",
            "revision": "42",
            "title": "结构夹具，不是线上飞书证据",
            "blocks": [
                {"block_id": "finding", "text": "Pilot revenue is higher.",
                 "style": {"bold": True, "size": 16}, "type": "paragraph"},
                {"block_id": "evidence", "text": "Pilot sample only; causality is unknown.",
                 "style": {"bold": False, "size": 12}, "type": "paragraph"}],
            "metadata": {"owner": "structural-fixture", "versioned": True},
        }
        self.candidate = copy.deepcopy(self.baseline)
        self.candidate["blocks"][0]["text"] = "Pilot revenue rose 5%; the cause is unknown."
        self.changes = [{"block_id": "finding", "before": self.baseline["blocks"][0]["text"],
                         "after": self.candidate["blocks"][0]["text"]}]
        self.authorization = {"document_id": self.baseline["document_id"], "action": "replace-text",
                              "risk": "standard", "block_ids": ["finding"],
                              "user_instruction": "Replace only the finding block text with the supplied sentence."}
        for key, value in (("baseline", self.baseline), ("live_baseline", self.baseline),
                           ("candidate", self.candidate), ("changes", self.changes),
                           ("authorization", self.authorization)):
            self.write(self.paths[key], value)
        self.make_answer_receipt()
        self.prewrite = self.base / "prewrite.json"
        self.readback = self.base / "readback.json"
        self.render = self.base / "native-STRUCTURAL-FIXTURE.png"
        self.inspection = self.base / "inspection-STRUCTURAL-FIXTURE.json"
        self.final = self.base / "verified.json"

    def tearDown(self):
        self.temp.cleanup()

    def write(self, path, value):
        Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return Path(path)

    def make_answer_receipt(self, xml=None):
        # These are intentionally invented structural reviews; no semantic pass
        # or real blind-reader run is asserted by this fixture.
        counter = len(list(self.base.glob("answers-*")))
        folder = self.base / f"answers-{counter}"
        folder.mkdir()
        source = folder / "source.txt"
        source.write_text("STRUCTURAL FIXTURE: pilot revenue rose 5%; causality is unknown.", encoding="utf-8")
        plan = self.write(folder / "plan.json", {
            "version": reader_answers.CONTRACT_VERSION,
            "reader": {"profile": "Fixture reader", "known_context": "No actual live reading",
                       "decision": "Validate the local evidence-binding protocol"},
            "surfaces": [{"id": "finding-and-evidence", "mode": "blocks", "block_ids": ["finding", "evidence"]}],
            "answers": [{"id": "A1", "question": "What changed and what remains unknown?",
                         "expected_information": "Pilot rose 5%; cause unknown.",
                         "source_location": "Structural fixture source", "source_status": "supported",
                         "required_on": ["finding-and-evidence"]}]})
        lock = self.write(folder / "lock.json", reader_answers.lock_plan(plan, source))
        snapshot = folder / "candidate.xml"
        snapshot.write_text(patch.candidate_xml(patch.load(self.paths["candidate"])) if xml is None else xml,
                            encoding="utf-8")
        surfaces = folder / "surfaces"
        manifest = reader_answers.prepare(lock, self.paths["candidate"], surfaces, snapshot)
        surface = manifest["surfaces"][0]
        finding = "STRUCTURAL FIXTURE ONLY: pilot revenue rose 5%; cause remains unknown."
        responses = self.write(folder / "responses.json", [{
            "surface_id": surface["id"], "surface_sha256": surface["sha256"],
            "reader_id": "invented-fixture-reader", "findings": [finding], "remaining_questions": []}])
        evaluation = self.write(folder / "evaluation.json", {
            "manifest_sha256": reader_answers.object_digest(manifest),
            "response_sha256": reader_answers.object_digest(patch.load(responses)),
            "reviewer_id": "invented-fixture-source-reviewer", "plan_source_coverage": "pass",
            "source_coverage_evidence": "Structural fixture only, not actual source verification.",
            "source_fidelity": "pass", "questions": [],
            "answers": [{"answer_id": "A1", "surface_id": surface["id"], "status": "pass",
                         "reader_quote": finding, "rationale": "Structural fixture only, not semantic evidence."}]})
        manifest_path = surfaces / "surface-manifest.json"
        answer = {"version": reader_answers.CONTRACT_VERSION, "status": "pass", "errors": []}
        for key, path in (("manifest", manifest_path), ("responses", responses), ("evaluation", evaluation)):
            answer[key + "_path"] = str(path)
            answer[key + "_sha256"] = patch.digest(path)
        self.write(self.paths["answer_receipt"], answer)
        self.assertEqual(reader_answers.validate_receipt(self.paths["answer_receipt"], self.paths["candidate"]), [])
        self.answer_source, self.answer_manifest = source, manifest_path

    def prepare(self):
        return patch.prepare(**self.paths)

    def ready_for_verify(self):
        receipt = self.prepare()
        self.write(self.prewrite, receipt)
        actual = copy.deepcopy(patch.load(self.paths["candidate"]))
        actual["revision"] = "43"
        self.write(self.readback, actual)
        self.render.write_bytes(png_fixture())
        self.write_inspection()
        return receipt

    def write_inspection(self):
        import reader_value
        from editorial_fixture import structural_review
        self.write(self.inspection, {
            "reader_value": structural_review(("expression", "selection", "meaning", "presentation"), patch.digest(self.readback), reader_value.read_text(self.readback), reader_value.read_text(self.paths["baseline"]), self.render),
            "readback_sha256": patch.digest(self.readback), "render_sha256": patch.digest(self.render),
            "inspector": {"id": "invented-STRUCTURAL-FIXTURE-inspector", "method": "native-render-inspection"},
            "verdict": "pass", "checks": {
                "readability": {"verdict": "pass", "evidence": "STRUCTURAL FIXTURE: finding text and causal qualifier are legible in the same block."},
                "overflow": {"verdict": "pass", "evidence": "STRUCTURAL FIXTURE: complete finding line remains inside the native block bounds."},
                "claim_evidence_adjacency": {"verdict": "pass", "evidence": "STRUCTURAL FIXTURE: pilot evidence follows the finding and preserves its causal limit."}}})

    def verify(self):
        return patch.verify(self.prewrite, self.readback, self.render, self.inspection)

    def test_editorial_review_must_quote_body_not_metadata(self):
        self.ready_for_verify()
        inspection = patch.load(self.inspection)
        inspection["reader_value"]["checks"]["expression"]["quote"] = self.baseline["document_id"]
        self.write(self.inspection, inspection)
        with self.assertRaisesRegex(ValueError, "quote not found"):
            self.verify()

    def run_cli(self, command, arguments, output, expected=0):
        args = [sys.executable, "-B", str(ROOT / "scripts" / "native_text_patch.py"), command]
        for name, path in arguments.items():
            args.extend(["--" + name.replace("_", "-"), str(path)])
        args.extend(["--output", str(output)])
        result = subprocess.run(args, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, expected, msg=result.stdout + result.stderr)
        return result

    def test_prepare_requires_no_render_and_cannot_claim_completion(self):
        self.assertFalse(self.render.exists())
        receipt = self.prepare()
        self.assertEqual(receipt["status"], "prewrite-approved")
        self.assertIs(receipt["complete"], False)
        self.assertIs(receipt["native_render_pending"], True)
        self.assertIs(receipt["external_write_performed"], False)
        self.assertEqual(set(receipt["inputs"]), set(patch.INPUT_NAMES))
        for name, item in receipt["inputs"].items():
            self.assertEqual(item["sha256"], patch.digest(self.paths[name]))

    def test_positive_prepare_and_verify_cli(self):
        self.ready_for_verify()
        self.prewrite.unlink()  # Local fixture only; CLI must create evidence exclusively.
        result = self.run_cli("prepare", self.paths, self.prewrite)
        self.assertIn("not complete", result.stdout)
        self.run_cli("verify", {"prewrite": self.prewrite, "readback": self.readback,
                                "render": self.render, "inspection": self.inspection}, self.final)
        final = patch.load(self.final)
        self.assertEqual(final["status"], "verified")
        self.assertIs(final["complete"], True)
        self.assertIs(final["native_render_pending"], False)
        self.assertEqual(final["evidence"]["prewrite"]["sha256"], patch.digest(self.prewrite))

    def test_candidate_style_change_is_rejected(self):
        self.candidate["blocks"][0]["style"]["bold"] = False
        self.write(self.paths["candidate"], self.candidate)
        with self.assertRaisesRegex(ValueError, "beyond"):
            self.prepare()

    def test_candidate_other_block_change_is_rejected(self):
        self.candidate["blocks"][1]["text"] = "An unrelated change."
        self.write(self.paths["candidate"], self.candidate)
        with self.assertRaisesRegex(ValueError, "beyond"):
            self.prepare()

    def test_candidate_document_change_is_rejected(self):
        self.candidate["document_id"] = "another-document"
        self.write(self.paths["candidate"], self.candidate)
        with self.assertRaisesRegex(ValueError, "beyond"):
            self.prepare()

    def test_candidate_order_or_metadata_change_is_rejected(self):
        for field in ("order", "metadata", "revision", "bool-as-int", "extra-field"):
            with self.subTest(field=field):
                candidate = copy.deepcopy(self.candidate)
                if field == "order":
                    candidate["blocks"].reverse()
                elif field == "metadata":
                    candidate["metadata"]["owner"] = "changed"
                elif field == "revision":
                    candidate["revision"] = "99"
                elif field == "bool-as-int":
                    candidate["blocks"][0]["style"]["bold"] = 1
                else:
                    candidate["blocks"][0]["new_field"] = "unapproved"
                self.write(self.paths["candidate"], candidate)
                with self.assertRaisesRegex(ValueError, "beyond"):
                    self.prepare()

    def test_concurrent_revision_and_even_reserialization_are_rejected(self):
        for mutation in ("revision", "format"):
            with self.subTest(mutation=mutation):
                if mutation == "revision":
                    live = copy.deepcopy(self.baseline)
                    live["revision"] = "43"
                    self.write(self.paths["live_baseline"], live)
                else:
                    self.paths["live_baseline"].write_text(json.dumps(self.baseline), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "live baseline changed"):
                    self.prepare()

    def test_missing_or_wrong_authorization_is_rejected(self):
        for value in ({}, None, {**self.authorization, "block_ids": []},
                      {**self.authorization, "block_ids": ["finding", "evidence"]},
                      {**self.authorization, "block_ids": ["finding", "finding"]},
                      {**self.authorization, "user_instruction": " "},
                      {**self.authorization, "document_id": "wrong"},
                      {**self.authorization, "action": "publish"},
                      {**self.authorization, "risk": "high"}):
            with self.subTest(authorization=value):
                self.write(self.paths["authorization"], value)
                with self.assertRaises(ValueError):
                    self.prepare()

    def test_missing_authorization_file_is_rejected(self):
        self.paths["authorization"].unlink()
        with self.assertRaises(OSError):
            self.prepare()

    def test_empty_duplicate_unknown_and_noop_changes_are_rejected(self):
        for value in ([], self.changes * 2,
                      [{**self.changes[0], "block_id": "unknown"}],
                      [{**self.changes[0], "before": "stale"}],
                      [{**self.changes[0], "after": self.changes[0]["before"]}],
                      [{**self.changes[0], "style": "overreach"}]):
            with self.subTest(changes=value):
                self.write(self.paths["changes"], value)
                with self.assertRaises(ValueError):
                    self.prepare()

    def test_valid_empty_after_text_is_a_real_replacement(self):
        self.candidate["blocks"][0]["text"] = ""
        self.changes[0]["after"] = ""
        self.write(self.paths["candidate"], self.candidate)
        self.write(self.paths["changes"], self.changes)
        self.make_answer_receipt()
        self.assertEqual(self.prepare()["status"], "prewrite-approved")

    def test_stale_answer_receipt_is_rejected(self):
        receipt = patch.load(self.paths["answer_receipt"])
        Path(receipt["responses_path"]).write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "reader answers failed"):
            self.prepare()

    def test_valid_answer_receipt_for_unrelated_snapshot_is_rejected(self):
        self.make_answer_receipt('<document id="unrelated">\n<block id="finding">Other findings</block>\n<block id="evidence">Other evidence</block>\n</document>\n')
        self.assertEqual(reader_answers.validate_receipt(self.paths["answer_receipt"], self.paths["candidate"]), [])
        with self.assertRaisesRegex(ValueError, "exact candidate block XML"):
            self.prepare()

    def test_equivalent_but_noncanonical_xml_is_rejected(self):
        self.make_answer_receipt(patch.candidate_xml(self.candidate).replace("<block", "  <block"))
        with self.assertRaisesRegex(ValueError, "exact candidate block XML"):
            self.prepare()

    def test_xml_escaping_roundtrip_and_block_order(self):
        candidate = copy.deepcopy(self.candidate)
        candidate["document_id"] = 'doc<&"\'\n\t'
        candidate["blocks"][0]["block_id"] = 'b<&"\'\n\t'
        candidate["blocks"][0]["text"] = '<visible>& "quoted" \'text\'\r\n保留'
        text = patch.candidate_xml(candidate)
        self.assertIn("&lt;visible&gt;&amp; &quot;quoted&quot; &apos;text&apos;&#13;", text)
        self.assertIn("&#10;&#9;", text)
        root = ElementTree.fromstring(text)
        self.assertEqual(root.attrib["id"], candidate["document_id"])
        self.assertEqual([b.attrib["id"] for b in root], [b["block_id"] for b in candidate["blocks"]])
        self.assertEqual(root[0].text, candidate["blocks"][0]["text"])

    def test_xml_invalid_characters_and_duplicate_blocks_are_rejected(self):
        candidate = copy.deepcopy(self.candidate)
        candidate["blocks"][0]["text"] = "invalid\x00text"
        with self.assertRaisesRegex(ValueError, "XML 1.0"):
            patch.candidate_xml(candidate)
        candidate["blocks"] = [self.candidate["blocks"][0]] * 2
        with self.assertRaisesRegex(ValueError, "unique"):
            patch.candidate_xml(candidate)

    def test_prewrite_alone_is_not_completion_and_cli_requires_postwrite_inputs(self):
        self.write(self.prewrite, self.prepare())
        self.run_cli("verify", {"prewrite": self.prewrite}, self.final, expected=2)
        self.assertFalse(self.final.exists())

    def test_missing_render_cannot_complete(self):
        self.ready_for_verify()
        self.render.unlink()
        self.run_cli("verify", {"prewrite": self.prewrite, "readback": self.readback,
                                "render": self.render, "inspection": self.inspection}, self.final, expected=1)
        self.assertFalse(self.final.exists())

    def test_missing_inspection_cannot_complete(self):
        self.ready_for_verify()
        self.inspection.unlink()
        with self.assertRaises(OSError):
            self.verify()

    def test_wrong_readback_document_blocks_style_order_revision_are_rejected(self):
        self.ready_for_verify()
        original = patch.load(self.readback)
        for field in ("document", "text", "style", "order", "revision", "missing-block"):
            with self.subTest(field=field):
                actual = copy.deepcopy(original)
                if field == "document":
                    actual["document_id"] = "wrong-document"
                elif field == "text":
                    actual["blocks"][0]["text"] = "Wrong native result"
                elif field == "style":
                    actual["blocks"][0]["style"]["size"] = 99
                elif field == "order":
                    actual["blocks"].reverse()
                elif field == "revision":
                    actual["revision"] = self.candidate["revision"]
                else:
                    actual["blocks"].pop()
                self.write(self.readback, actual)
                self.write_inspection()
                with self.assertRaises(ValueError):
                    self.verify()

    def test_verify_rechecks_every_original_input_hash(self):
        self.ready_for_verify()
        for name in patch.INPUT_NAMES:
            with self.subTest(input=name):
                path = self.paths[name]
                original = path.read_bytes()
                path.write_bytes(original + b" ")
                with self.assertRaisesRegex(ValueError, "evidence changed"):
                    self.verify()
                path.write_bytes(original)

    def test_verify_rechecks_transitive_answer_source(self):
        self.ready_for_verify()
        self.answer_source.write_text("Changed source after the write preflight.", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "reader answers failed"):
            self.verify()

    def test_verify_rechecks_answer_semantics_after_rebinding_hashes(self):
        self.ready_for_verify()
        answer = patch.load(self.paths["answer_receipt"])
        evaluation = patch.load(answer["evaluation_path"])
        evaluation["source_fidelity"] = "fail"
        self.write(answer["evaluation_path"], evaluation)
        answer["evaluation_sha256"] = patch.digest(answer["evaluation_path"])
        self.write(self.paths["answer_receipt"], answer)
        prewrite = patch.load(self.prewrite)
        prewrite["inputs"]["answer_receipt"]["sha256"] = patch.digest(self.paths["answer_receipt"])
        self.write(self.prewrite, prewrite)
        with self.assertRaisesRegex(ValueError, "source fidelity"):
            self.verify()

    def test_tampered_prewrite_cannot_be_promoted(self):
        self.ready_for_verify()
        original = patch.load(self.prewrite)
        for field, value in (("status", "verified"), ("complete", True),
                             ("native_render_pending", False), ("document_id", "wrong"),
                             ("external_write_performed", True), ("candidate_xml_sha256", "0" * 64)):
            with self.subTest(field=field):
                self.write(self.prewrite, {**original, field: value})
                with self.assertRaises(ValueError):
                    self.verify()

    def test_stale_inspection_readback_binding_is_rejected(self):
        self.ready_for_verify()
        actual = patch.load(self.readback)
        actual["revision"] = "44"
        self.write(self.readback, actual)
        with self.assertRaisesRegex(ValueError, "inspection is stale"):
            self.verify()

    def test_stale_inspection_render_binding_is_rejected(self):
        self.ready_for_verify()
        self.render.write_bytes(png_fixture(b"\x00\x00\x00"))
        with self.assertRaisesRegex(ValueError, "inspection is stale"):
            self.verify()

    def test_placeholder_truncated_and_bad_crc_images_are_rejected(self):
        self.ready_for_verify()
        corrupt = bytearray(png_fixture())
        corrupt[-1] ^= 1
        for content in (b"pretend screenshot", b"\x89PNG\r\n\x1a\n", png_fixture()[:30],
                        bytes(corrupt), b"\xff\xd8\xffnot-a-jpeg\xff\xd9"):
            with self.subTest(content=content[:20]):
                self.render.write_bytes(content)
                self.write_inspection()
                with self.assertRaisesRegex(ValueError, "render"):
                    self.verify()

    def test_jpeg_frame_scan_header_is_accepted_as_structure_only(self):
        self.ready_for_verify()
        # Synthetic JPEG marker sequence, not a decoded image or native capture.
        frame = b"\x08\x00\x01\x00\x01\x01\x01\x11\x00"
        scan = b"\x01\x01\x00\x00\x3f\x00"
        jpeg = (b"\xff\xd8\xff\xc0" + struct.pack(">H", len(frame) + 2) + frame
                + b"\xff\xda" + struct.pack(">H", len(scan) + 2) + scan + b"\x01\xff\xd9")
        self.render.write_bytes(jpeg)
        self.write_inspection()
        self.assertEqual(self.verify()["render_format"], "jpeg")

    def test_inspection_requires_identity_and_all_specific_passed_checks(self):
        self.ready_for_verify()
        original = patch.load(self.inspection)
        variants = [{**original, "inspector": {}}, {**original, "verdict": "fail"},
                    {**original, "checks": {}}]
        for name in patch.CHECK_NAMES:
            for replacement in ({"verdict": "fail", "evidence": "Actual issue observed"},
                                {"verdict": "pass", "evidence": "pass"},
                                {"verdict": "pass", "evidence": ""}):
                modified = copy.deepcopy(original)
                modified["checks"][name] = replacement
                variants.append(modified)
        for variant in variants:
            with self.subTest(inspection=variant):
                self.write(self.inspection, variant)
                with self.assertRaises(ValueError):
                    self.verify()

    def test_existing_evidence_output_is_never_overwritten(self):
        old = self.paths["baseline"].read_bytes()
        self.run_cli("prepare", self.paths, self.paths["baseline"], expected=1)
        self.assertEqual(self.paths["baseline"].read_bytes(), old)

    def test_duplicate_json_keys_fail_closed(self):
        self.paths["authorization"].write_text('{"document_id":"one","document_id":"two"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            self.prepare()


if __name__ == "__main__":
    unittest.main()
