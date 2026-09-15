"""Deterministic evidence/structure tests; fixtures do not prove semantic judgment.

The answers and source-review judgments below are deliberately hand-authored
fixtures. A passing test checks extraction, identity, binding, and completeness,
not whether a real reader understood a document or a model judged it correctly.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import reader_answers as answers


class ReaderAnswersTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="reader-answers-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.plan_path = self.base / "private-plan.json"
        self.source_path = self.base / "private-source.txt"
        self.lock_path = self.base / "plan-lock.json"
        self.artifact_path = self.base / "artifact.md"
        self.source_path.write_text(
            "PRIVATE_SOURCE_SENTINEL_71: structural source fixture only.\n",
            encoding="utf-8",
        )
        self.artifact_path.write_text(
            "# The pilot retry count rose by two\n"
            "## Eligibility remains unknown\n\n"
            "<!-- BEGIN_DETAIL -->\n"
            "Check eligibility before extending. Eligibility remains unknown.\n"
            "<!-- END_DETAIL -->\n"
            "UNSEEN_BODY_SENTINEL_93 must not reach the blind reader.\n",
            encoding="utf-8",
        )
        self.plan = {
            "version": answers.CONTRACT_VERSION,
            "reader": {
                "profile": "A fixture reader outside the project",
                "known_context": "No project history",
                "decision": "Inspect the bounded structural fixture",
            },
            "surfaces": [
                {"id": "headings", "mode": "headings"},
                {
                    "id": "detail", "mode": "between",
                    "start": "<!-- BEGIN_DETAIL -->", "end": "<!-- END_DETAIL -->",
                },
            ],
            "answers": [
                {
                    "id": "result", "question": "What changed in the fixture?",
                    "expected_information": "PRIVATE_EXPECTED_ANSWER_SENTINEL_82",
                    "source_location": "PRIVATE_SOURCE_LOCATION_SENTINEL_84",
                    "source_status": "supported", "required_on": ["headings"],
                },
                {
                    "id": "next", "question": "What should be checked next?",
                    "expected_information": "Fixture-only next step",
                    "source_location": "Fixture source, second paragraph",
                    "source_status": "supported", "required_on": ["detail"],
                },
                {
                    "id": "uncertainty", "question": "Is eligibility established?",
                    "expected_information": "The source leaves eligibility unknown",
                    "source_location": "Fixture source, missing eligibility",
                    "source_status": "unknown", "required_on": ["headings", "detail"],
                },
            ],
        }

    def prepare(self, *, snapshot=None):
        answers.save(self.plan_path, self.plan)
        answers.save(self.lock_path, answers.lock_plan(self.plan_path, self.source_path))
        self.manifest = answers.prepare(
            self.lock_path, self.artifact_path, self.base / "surfaces", snapshot
        )
        self.responses = [
            {
                "surface_id": surface["id"],
                "surface_sha256": surface["sha256"],
                "reader_id": "blind-reader-" + surface["id"],
                "findings": (
                    ["The retry count rose by two.", "Eligibility is unknown."]
                    if surface["id"] == "headings"
                    else ["Check eligibility before extending.", "Eligibility is unknown."]
                ),
                "remaining_questions": [],
            }
            for surface in self.manifest["surfaces"]
        ]
        quote_by_answer = {
            "result": "The retry count rose by two.",
            "next": "Check eligibility before extending.",
            "uncertainty": "Eligibility is unknown.",
        }
        self.evaluation = {
            "manifest_sha256": answers.object_digest(self.manifest),
            "response_sha256": answers.object_digest(self.responses),
            "reviewer_id": "source-reviewer",
            "plan_source_coverage": "pass",
            "source_coverage_evidence": "Hand-authored structural fixture only",
            "source_fidelity": "pass",
            "answers": [
                {
                    "answer_id": answer["id"], "surface_id": sid, "status": "pass",
                    "reader_quote": quote_by_answer[answer["id"]],
                    "rationale": "Hand-authored structural match; not semantic proof",
                }
                for answer in self.plan["answers"]
                for sid in answer["required_on"]
            ],
            "questions": [],
        }
        return self.manifest

    def validate(self):
        return answers.validate_answers(self.manifest, self.responses, self.evaluation)

    def rebind_responses(self):
        self.evaluation["response_sha256"] = answers.object_digest(self.responses)

    def assert_invalid(self, expected_text):
        errors = self.validate()
        self.assertTrue(errors, "Invalid structural evidence must not pass")
        self.assertIn(expected_text, "\n".join(errors))

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts" / "reader_answers.py"), *args],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )

    def write_evidence_files(self):
        paths = {}
        for name, value in (
            ("manifest", self.manifest), ("responses", self.responses),
            ("evaluation", self.evaluation),
        ):
            paths[name] = self.base / (name + ".json")
            answers.save(paths[name], value)
        return paths

    def test_structural_fixture_passes_with_every_required_pair(self):
        self.prepare()
        self.assertEqual(answers.plan_errors(self.plan), [])
        self.assertEqual(self.validate(), [])
        self.assertEqual(len(self.evaluation["answers"]), 4)

    def test_lock_binds_both_plan_and_source_bytes(self):
        for changed in ("plan", "source"):
            with self.subTest(changed=changed):
                answers.save(self.plan_path, self.plan)
                self.source_path.write_text("Fixture source\n", encoding="utf-8")
                answers.save(self.lock_path, answers.lock_plan(self.plan_path, self.source_path))
                lock, loaded_plan = answers.open_lock(self.lock_path)
                self.assertEqual(loaded_plan, self.plan)
                target = self.plan_path if changed == "plan" else self.source_path
                target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "locked " + changed + " changed"):
                    answers.open_lock(self.lock_path)
                self.assertEqual(lock[changed]["path"], str(target.resolve()))

    def test_cli_refuses_to_overwrite_existing_lock(self):
        self.prepare()
        old_bytes = self.lock_path.read_bytes()
        result = self.run_cli(
            "lock", "--plan", str(self.plan_path), "--source", str(self.source_path),
            "--output", str(self.lock_path),
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("already exists", result.stdout)
        self.assertEqual(self.lock_path.read_bytes(), old_bytes)

    def test_plan_rejects_incomplete_or_wrong_surface_assignments(self):
        mutations = {
            "version": lambda p: p.update(version="unsupported"),
            "blank audience": lambda p: p["reader"].update(profile=" "),
            "missing answers": lambda p: p.update(answers=[]),
            "duplicate answer": lambda p: p["answers"].append(copy.deepcopy(p["answers"][0])),
            "duplicate surface": lambda p: p["surfaces"].append(copy.deepcopy(p["surfaces"][0])),
            "unknown surface": lambda p: p["answers"][0].update(required_on=["unplanned"]),
            "unassigned answer": lambda p: p["answers"][0].update(required_on=[]),
            "missing source": lambda p: p["answers"][0].update(source_location=""),
            "invented certainty": lambda p: p["answers"][0].update(source_status="guessed"),
            "unjustified full": lambda p: p["surfaces"][0].update(mode="full"),
            "missing block IDs": lambda p: p["surfaces"][0].update(mode="blocks"),
            "missing anchors": lambda p: p["surfaces"][0].update(mode="between"),
            "invalid mode": lambda p: p["surfaces"][0].update(mode="summary"),
        }
        for label, mutate in mutations.items():
            with self.subTest(case=label):
                plan = copy.deepcopy(self.plan)
                mutate(plan)
                self.assertTrue(answers.plan_errors(plan))

    def test_malformed_surface_ids_and_required_on_return_errors(self):
        mutations = {
            "surface list ID": lambda p: p["surfaces"][0].update(id=["headings"]),
            "surface object ID": lambda p: p["surfaces"][0].update(id={"id": "headings"}),
            "numeric surface ID": lambda p: p["surfaces"][0].update(id=7),
            "blank surface ID": lambda p: p["surfaces"][0].update(id=" "),
            "answer list ID": lambda p: p["answers"][0].update(id=["result"]),
            "nested required_on": lambda p: p["answers"][0].update(required_on=[["headings"]]),
            "object required_on": lambda p: p["answers"][0].update(required_on={"headings": True}),
            "numeric block ID": lambda p: p["surfaces"][0].update(mode="blocks", block_ids=[7]),
            "string block IDs": lambda p: p["surfaces"][0].update(mode="blocks", block_ids="headings"),
        }
        for label, mutate in mutations.items():
            with self.subTest(case=label):
                plan = copy.deepcopy(self.plan)
                mutate(plan)
                self.assertTrue(answers.plan_errors(plan))

    def test_markdown_extracts_visible_headings_and_ignores_fences_and_body(self):
        text = (
            "# Result\nBody must stay private.\n"
            "~~~md\n## Tilde-fenced example\n~~~\n"
            "\x60\x60\x60md\n# Backtick-fenced example\n\x60\x60\x60\n"
            "## Scope\n### Next step\n"
        )
        self.assertEqual(
            answers.extract_surface(text, {"mode": "headings"}),
            "Result\nScope\nNext step\n",
        )

    def test_markdown_inline_html_does_not_hide_real_headings(self):
        self.assertEqual(
            answers.extract_surface("# Result <em>improved</em>\nBody\n## Scope\n", {"mode": "headings"}),
            "Result improved\nScope\n",
        )

    def test_html_extracts_heading_text_without_body_or_hidden_content(self):
        text = (
            "<html><head><style>PRIVATE_STYLE</style></head><body>"
            "<h1>Result <em>improved</em></h1><p>PRIVATE_BODY</p>"
            "<h2>Scope <span hidden>PRIVATE_HIDDEN</span><br>pilot only</h2>"
            "<script><h3>PRIVATE_SCRIPT</h3></script>"
            "<template><h3>PRIVATE_TEMPLATE</h3></template>"
            "<h3 hidden>PRIVATE_HIDDEN_HEADING</h3></body></html>"
        )
        self.assertEqual(
            answers.extract_surface(text, {"mode": "headings"}),
            "Result improved\nScope\npilot only\n",
        )

    def test_native_block_selection_uses_exact_ids_and_document_order(self):
        text = (
            '<section id="other">PRIVATE_OTHER</section>'
            '<section id="decision"><p>Keep the pilot.</p><p hidden>PRIVATE_HIDDEN</p></section>'
            '<div id="scope">Observed <strong>pilot</strong> only.</div>'
        )
        self.assertEqual(
            answers.extract_surface(text, {"mode": "blocks", "block_ids": ["scope", "decision"]}),
            "Keep the pilot.\nObserved pilot only.\n",
        )

    def test_native_blocks_reject_missing_duplicate_and_empty_selections(self):
        fixtures = [
            ('<div id="present">Content</div>', ["missing"]),
            ('<div id="same">First</div><div id="same">Second</div>', ["same"]),
            ('<div id="hidden" hidden>Secret</div>', ["hidden"]),
            ("Plain text cannot be selected by native block ID", ["native"]),
        ]
        for text, ids in fixtures:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    answers.extract_surface(text, {"mode": "blocks", "block_ids": ids})

    def test_opening_extracts_only_visible_lines_and_rich_text(self):
        brief = {
            "opening": {"lines": ["Observed change", [{"text": "Pilot "}, {"text": "only"}]]},
            "body": "PRIVATE_UNSEEN_BODY",
        }
        self.assertEqual(
            answers.extract_surface(json.dumps(brief), {"mode": "opening"}),
            "Observed change\nPilot only\n",
        )

    def test_opening_rejects_string_instead_of_line_array(self):
        with self.assertRaises((ValueError, TypeError)):
            answers.extract_surface(
                json.dumps({"opening": {"lines": "malformed string"}}), {"mode": "opening"}
            )

    def test_between_requires_unique_ordered_anchors(self):
        surface = {"mode": "between", "start": "[BEGIN]", "end": "[END]"}
        self.assertEqual(
            answers.extract_surface("Before[BEGIN]Read this[END]After", surface),
            "[BEGIN]Read this\n",
        )
        for text in ("No anchors", "[BEGIN]a[BEGIN]b[END]", "[END]before[BEGIN]"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    answers.extract_surface(text, surface)

    def test_blind_packet_contains_only_reader_and_extracted_surface(self):
        self.prepare()
        forbidden = [
            self.plan_path, self.source_path, self.artifact_path, self.lock_path,
            "PRIVATE_SOURCE_SENTINEL_71", "PRIVATE_EXPECTED_ANSWER_SENTINEL_82",
            "PRIVATE_SOURCE_LOCATION_SENTINEL_84", "UNSEEN_BODY_SENTINEL_93",
            "expected_information", "source_location", "required_on",
            "What changed in the fixture?",
        ]
        for surface in self.manifest["surfaces"]:
            packet = answers.load(surface["packet_path"])
            self.assertEqual(set(packet), {
                "version", "surface_id", "reader", "surface", "instructions", "response_fields"
            })
            self.assertEqual(packet["surface_id"], surface["id"])
            self.assertEqual(packet["surface"]["sha256"], answers.digest(surface["path"]))
            blind_material = (
                Path(surface["packet_path"]).read_text(encoding="utf-8")
                + Path(surface["path"]).read_text(encoding="utf-8")
            )
            for value in forbidden:
                self.assertNotIn(str(value), blind_material)

    def test_prepare_refuses_nonempty_output_directory(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "must be empty"):
            answers.prepare(self.lock_path, self.artifact_path, self.base / "surfaces")

    def test_separate_native_content_snapshot_is_extracted_and_bound(self):
        self.plan["surfaces"] = [{"id": "headings", "mode": "headings"}]
        self.plan["answers"] = [self.plan["answers"][0]]
        snapshot = self.base / "rendered-snapshot.html"
        snapshot.write_text("<h1>Native visible title</h1><p>Private body</p>", encoding="utf-8")
        self.artifact_path.write_bytes(b"Native document descriptor")
        self.prepare(snapshot=snapshot)
        self.assertEqual(
            Path(self.manifest["surfaces"][0]["path"]).read_text(encoding="utf-8"),
            "Native visible title\n",
        )
        self.assertEqual(answers.verify_manifest(self.manifest), self.plan)
        snapshot.write_text("<h1>Changed native title</h1>", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "snapshot changed"):
            answers.verify_manifest(self.manifest)

    def test_changed_artifact_surface_packet_or_lock_fails_validation(self):
        self.prepare()
        files = {
            "artifact": self.artifact_path,
            "surface": Path(self.manifest["surfaces"][0]["path"]),
            "packet": Path(self.manifest["surfaces"][0]["packet_path"]),
            "lock": self.lock_path, "source": self.source_path, "plan": self.plan_path,
        }
        for label, path in files.items():
            with self.subTest(changed=label):
                old_bytes = path.read_bytes()
                path.write_bytes(old_bytes + b"\n")
                try:
                    self.assertTrue(self.validate())
                finally:
                    path.write_bytes(old_bytes)
        self.assertEqual(self.validate(), [])

    def test_rehashed_wrong_surface_is_still_rejected(self):
        self.prepare()
        entry = self.manifest["surfaces"][0]
        Path(entry["path"]).write_text("Forged reading content\n", encoding="utf-8")
        entry["sha256"] = answers.digest(entry["path"])
        self.evaluation["manifest_sha256"] = answers.object_digest(self.manifest)
        self.assert_invalid("not the requested artifact extraction")

    def test_rehashed_packet_cannot_smuggle_source_or_answer_key(self):
        self.prepare()
        entry = self.manifest["surfaces"][0]
        packet = answers.load(entry["packet_path"])
        packet["source_path"] = str(self.source_path)
        packet["expected_answers"] = self.plan["answers"]
        answers.save(entry["packet_path"], packet)
        entry["packet_sha256"] = answers.digest(entry["packet_path"])
        self.evaluation["manifest_sha256"] = answers.object_digest(self.manifest)
        self.assertTrue(self.validate(), "A rehashed packet must retain its blind-content contract")

    def test_omitting_any_required_answer_surface_pair_fails(self):
        self.prepare()
        original = copy.deepcopy(self.evaluation["answers"])
        for index, check in enumerate(original):
            with self.subTest(answer=check["answer_id"], surface=check["surface_id"]):
                self.evaluation["answers"] = original[:index] + original[index + 1:]
                self.assert_invalid("every required answer")
        self.evaluation["answers"] = original
        self.assertEqual(self.validate(), [])

    def test_duplicate_extra_and_wrong_correspondence_fail(self):
        self.prepare()
        original = copy.deepcopy(self.evaluation["answers"])
        invalid = {
            "duplicate": original + [copy.deepcopy(original[0])],
            "extra": original + [dict(original[0], answer_id="unplanned")],
            "wrong answer": [dict(original[0], answer_id="next")] + original[1:],
            "wrong surface": [dict(original[0], surface_id="detail")] + original[1:],
        }
        for label, checks in invalid.items():
            with self.subTest(case=label):
                self.evaluation["answers"] = checks
                self.assert_invalid("every required answer")

    def test_answer_must_pass_quote_its_own_blind_findings_and_have_rationale(self):
        self.prepare()
        original = copy.deepcopy(self.evaluation["answers"][0])
        invalid = (
            {"status": "fail"},
            {"reader_quote": "PRIVATE_EXPECTED_ANSWER_SENTINEL_82"},
            {"reader_quote": "Check eligibility before extending."},
            {"rationale": ""},
        )
        for change in invalid:
            with self.subTest(change=change):
                self.evaluation["answers"][0] = dict(original, **change)
                self.assertTrue(self.validate())

    def test_stale_manifest_response_and_surface_hashes_fail(self):
        self.prepare()
        for field in ("manifest_sha256", "response_sha256"):
            with self.subTest(field=field):
                old = self.evaluation[field]
                self.evaluation[field] = "0" * 64
                self.assertTrue(self.validate())
                self.evaluation[field] = old
        self.responses[0]["surface_sha256"] = "0" * 64
        self.rebind_responses()
        self.assert_invalid("not bound to the supplied surface")

    def test_changed_raw_response_requires_new_evaluation(self):
        self.prepare()
        self.responses[0]["findings"].append("An additional observation.")
        self.assert_invalid("not bound to the raw blind responses")

    def test_missing_duplicate_or_foreign_blind_surface_response_fails(self):
        self.prepare()
        original = copy.deepcopy(self.responses)
        invalid = {
            "missing": original[:1],
            "duplicate": original + [copy.deepcopy(original[0])],
            "foreign": [dict(original[0], surface_id="unplanned")] + original[1:],
        }
        for label, responses in invalid.items():
            with self.subTest(case=label):
                self.responses = responses
                self.rebind_responses()
                self.assertTrue(self.validate())

    def test_source_reviewer_and_blind_reader_must_have_separate_identities(self):
        self.prepare()
        self.evaluation["reviewer_id"] = self.responses[0]["reader_id"]
        self.assert_invalid("must differ from blind reader")
        self.evaluation["reviewer_id"] = ""
        self.assert_invalid("reviewer_id")

    def test_source_coverage_and_fidelity_are_independent_requirements(self):
        self.prepare()
        for field, bad_value in (
            ("plan_source_coverage", "fail"),
            ("source_coverage_evidence", ""),
            ("source_fidelity", "fail"),
        ):
            with self.subTest(field=field):
                old = self.evaluation[field]
                self.evaluation[field] = bad_value
                self.assertTrue(self.validate())
                self.evaluation[field] = old

    def add_question(self, classification):
        self.responses[0]["remaining_questions"] = ["A fixture follow-up question?"]
        self.rebind_responses()
        self.evaluation["questions"] = [{
            "surface_id": "headings", "index": 0, "classification": classification,
            "rationale": "Hand-authored structural classification against the source",
        }]

    def test_source_unknown_and_optional_detail_do_not_block(self):
        self.prepare()
        self.assertEqual(self.plan["answers"][-1]["source_status"], "unknown")
        for classification in ("source_unknown", "detail"):
            with self.subTest(classification=classification):
                self.add_question(classification)
                self.assertEqual(self.validate(), [])

    def test_followup_for_missing_required_answer_blocks(self):
        self.prepare()
        self.add_question("missing_required_answer")
        self.assert_invalid("known decision-required answer was omitted")

    def test_every_followup_requires_one_valid_classification(self):
        self.prepare()
        self.add_question("detail")
        original = copy.deepcopy(self.evaluation["questions"])
        variants = (
            [], original + copy.deepcopy(original),
            [dict(original[0], index=1)],
            [dict(original[0], surface_id="detail")],
            [dict(original[0], classification="ignore")],
            [dict(original[0], rationale="")],
        )
        for questions in variants:
            with self.subTest(questions=questions):
                self.evaluation["questions"] = questions
                self.assertTrue(self.validate())

    def test_malformed_top_level_response_and_evaluation_fail_closed(self):
        self.prepare()
        for responses, evaluation in (
            ({}, self.evaluation), ([None], self.evaluation),
            (self.responses, []),
            (self.responses, dict(self.evaluation, answers="invalid")),
            (self.responses, dict(self.evaluation, questions=[None])),
        ):
            with self.subTest(responses=responses, evaluation=evaluation):
                self.assertTrue(answers.validate_answers(self.manifest, responses, evaluation))

    def test_nontext_blind_findings_cannot_be_coerced_into_passing_evidence(self):
        self.prepare()
        self.responses[0]["findings"] = [{"unexpected": "object"}]
        self.rebind_responses()
        for check in self.evaluation["answers"]:
            if check["surface_id"] == "headings":
                check["reader_quote"] = "{'unexpected': 'object'}"
        self.assertTrue(self.validate(), "Findings must contain actual reader text")

    def test_malformed_manifest_returns_errors_instead_of_accepting(self):
        self.prepare()
        for manifest in ({}, {"version": answers.CONTRACT_VERSION}, None, []):
            with self.subTest(manifest=manifest):
                self.assertTrue(answers.validate_answers(manifest, self.responses, self.evaluation))

    def test_malformed_nested_response_fields_fail_closed(self):
        self.prepare()
        original = copy.deepcopy(self.responses)
        changes = (
            {"surface_id": ["headings"]},
            {"reader_id": {"id": "reader"}},
            {"findings": [" "]},
            {"remaining_questions": [None]},
        )
        for change in changes:
            with self.subTest(change=change):
                self.responses = copy.deepcopy(original)
                self.responses[0].update(change)
                self.rebind_responses()
                if "remaining_questions" in change:
                    self.evaluation["questions"] = [{
                        "surface_id": "headings", "index": 0, "classification": "detail",
                        "rationale": "Structural fixture",
                    }]
                else:
                    self.evaluation["questions"] = []
                self.assertTrue(self.validate())

    def test_malformed_answer_check_fields_fail_closed(self):
        self.prepare()
        original = copy.deepcopy(self.evaluation["answers"][0])
        for change in (
            {"answer_id": ["result"]},
            {"surface_id": ["headings"]},
            {"reader_quote": ["The retry count rose by two."]},
            {"rationale": {"text": "not a string"}},
        ):
            with self.subTest(change=change):
                self.evaluation["answers"][0] = dict(original, **change)
                self.assertTrue(self.validate())

    def test_malformed_question_index_and_classification_fail_closed(self):
        self.prepare()
        self.add_question("detail")
        original = copy.deepcopy(self.evaluation["questions"][0])
        for change in (
            {"index": False},
            {"index": [0]},
            {"surface_id": ["headings"]},
            {"classification": ["detail"]},
            {"rationale": {"text": "not a string"}},
        ):
            with self.subTest(change=change):
                self.evaluation["questions"][0] = dict(original, **change)
                self.assertTrue(self.validate())

    def test_cli_verify_writes_receipt_and_receipt_detects_stale_evidence(self):
        self.prepare()
        paths = self.write_evidence_files()
        receipt = self.base / "answer-receipt.json"
        result = self.run_cli(
            "verify", "--manifest", str(paths["manifest"]),
            "--responses", str(paths["responses"]),
            "--evaluation", str(paths["evaluation"]), "--output", str(receipt),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(answers.load(receipt)["status"], "pass")
        self.assertEqual(answers.validate_receipt(receipt, self.artifact_path), [])
        self.responses[0]["findings"].append("Changed after receipt")
        answers.save(paths["responses"], self.responses)
        self.assertIn("responses evidence changed", "\n".join(answers.validate_receipt(receipt)))

    def test_cli_failure_creates_fail_receipt_and_returns_nonzero(self):
        self.prepare()
        self.evaluation["answers"].pop()
        paths = self.write_evidence_files()
        receipt = self.base / "failed-answer-receipt.json"
        result = self.run_cli(
            "verify", "--manifest", str(paths["manifest"]),
            "--responses", str(paths["responses"]),
            "--evaluation", str(paths["evaluation"]), "--output", str(receipt),
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(answers.load(receipt)["status"], "fail")
        self.assertTrue(answers.validate_receipt(receipt))

    def test_receipt_rejects_another_artifact(self):
        self.prepare()
        paths = self.write_evidence_files()
        receipt = self.base / "answer-receipt.json"
        result = self.run_cli(
            "verify", "--manifest", str(paths["manifest"]),
            "--responses", str(paths["responses"]),
            "--evaluation", str(paths["evaluation"]), "--output", str(receipt),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        other = self.base / "another-artifact.md"
        other.write_text("Different artifact\n", encoding="utf-8")
        self.assertIn("different artifact", "\n".join(answers.validate_receipt(receipt, other)))


if __name__ == "__main__":
    unittest.main()
