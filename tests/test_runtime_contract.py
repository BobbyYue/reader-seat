from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "scripts" / "runtime_contract.py"
READER_REVIEW = ROOT / "scripts" / "reader_review.py"
SCAFFOLD = ROOT / "scripts" / "new-html-report.sh"
HTML_VALIDATOR = ROOT / "scripts" / "validate_html_output.py"


class RuntimeContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.contract = self.base / "contract.json"
        self.review = self.base / "review.json"
        self.receipt = self.base / "receipt.json"
        self.action_receipt = self.base / "action-receipt.json"
        self.source_bundle = self.base / "source-bundle.txt"
        self.source_bundle.write_text(
            "This source bundle records the substantive evidence, definitions, scope, and "
            "source metadata required to review the finished artifact reliably. " * 4,
            encoding="utf-8",
        )
        self.review_counter = 0

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_cli(self, *args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        arguments = list(args)
        if arguments and arguments[0] == "init" and "--channel" in arguments:
            channel = arguments[arguments.index("--channel") + 1]
            if channel == "artifact":
                if "--reader-profile" not in arguments:
                    arguments.extend(["--reader-profile", "A target reader without project history"])
                if "--source-bundle" not in arguments:
                    arguments.extend(["--source-bundle", str(self.source_bundle)])
        completed = subprocess.run(
            [sys.executable, "-B", str(RUNTIME), *arguments],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            expected,
            msg=f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )
        return completed

    def run_reader_cli(self, *args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            [sys.executable, "-B", str(READER_REVIEW), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            expected,
            msg=f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )
        return completed

    def complete_reader_review(
        self,
        artifact: Path,
        *,
        round_number: int = 1,
        previous_aggregate: Path | None = None,
        failing_dimension: str | None = None,
        reuse_session: bool = False,
        parent_context_received: bool = False,
        expected: int = 0,
    ) -> Path:
        self.review_counter += 1
        review_dir = self.base / f"reader-round-{round_number}-{self.review_counter}"
        render = self.base / f"render-{round_number}-{self.review_counter}.png"
        render.write_bytes(b"reader-seat-render-evidence")
        prepare_args = [
            "prepare",
            "--contract", str(self.contract),
            "--artifact", str(artifact),
            "--render-evidence", str(render),
            "--round", str(round_number),
            "--output-dir", str(review_dir),
        ]
        if previous_aggregate:
            prepare_args.extend(["--previous-aggregate", str(previous_aggregate)])
        self.run_reader_cli(*prepare_args)

        result_paths: list[Path] = []
        for packet_path in sorted(review_dir.glob("*-packet.json")):
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            dimension = packet["dimension"]
            status = "fail" if dimension == failing_dimension else "pass"
            checks = {
                check_id: {
                    "status": "fail" if status == "fail" and index == 0 else "pass",
                    "evidence": f"{dimension} {check_id} was inspected against this exact artifact and reader task.",
                }
                for index, check_id in enumerate(packet["required_checks"])
            }
            issues = []
            if status == "fail":
                issues.append({
                    "severity": "major",
                    "location": "Opening section",
                    "observed_problem": "The main conclusion is not recoverable without hidden context.",
                    "reader_consequence": "The target reader may make the wrong decision.",
                    "required_fix": "State the supported conclusion and its scope directly.",
                })
            result = {
                "schema_version": 1,
                "contract_id": packet["contract_id"],
                "batch_id": packet["batch_id"],
                "round": packet["round"],
                "dimension": dimension,
                "artifact_sha256": packet["artifact"]["sha256"],
                "packet_sha256": packet["packet_sha256"],
                "reviewer": {
                    "agent_id": f"agent-{dimension}-{self.review_counter}",
                    "session_id": (
                        f"session-shared-{self.review_counter}"
                        if reuse_session else f"session-{dimension}-{self.review_counter}"
                    ),
                    "context_isolation": "fresh-subagent",
                    "parent_context_received": parent_context_received,
                    "invocation_mode": "parallel-batch",
                },
                "status": status,
                "summary": f"Independent {dimension} review completed against the current artifact version.",
                "checks": checks,
                "issues": issues,
            }
            if dimension == "no-context":
                result["reader_understanding"] = {
                    "object": "The documented workflow",
                    "main_conclusion": "The workflow should preserve relevant evidence and context.",
                    "evidence": "The report explains the supporting mechanisms and constraints.",
                    "meaning": "Readers can choose the bounded recommended action.",
                    "action": "Follow the stated recommendation and retain the evidence boundary.",
                }
            result_path = review_dir / f"{dimension}-result.json"
            result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            result_paths.append(result_path)

        aggregate = review_dir / "aggregate.json"
        aggregate_args = [
            "aggregate",
            "--contract", str(self.contract),
            "--manifest", str(review_dir / "round-manifest.json"),
        ]
        for path in result_paths:
            aggregate_args.extend(["--result", str(path)])
        aggregate_args.extend(["--output", str(aggregate)])
        self.run_reader_cli(*aggregate_args, expected=expected)
        return aggregate

    def init_contract(self, *extra: str) -> dict:
        self.run_cli(
            "init",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--scenario", "news",
            "--operation", "create",
            "--channel", "artifact",
            "--source-language", "en",
            *extra,
        )
        return json.loads(self.contract.read_text(encoding="utf-8"))

    def complete_review(self, artifact: Path, content_snapshot: Path | None = None) -> None:
        bind_args = [
            "bind-review",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--artifact", str(artifact),
        ]
        if content_snapshot is not None:
            bind_args.extend(["--content-snapshot", str(content_snapshot)])
        self.run_cli(*bind_args)
        review = json.loads(self.review.read_text(encoding="utf-8"))
        for gate_name, gate in review["checks"].items():
            gate["status"] = "pass"
            gate["evidence"] = f"{gate_name}: report body checked against the frozen source and stated scope."
        for rule_id, rule in review["runtime_rules"].items():
            rule["status"] = "pass"
            rule["evidence"] = f"{rule_id}: applied to the exact artifact and rechecked before verification."
        for gate_id, gate in review["execution_gates"].items():
            gate["status"] = "pass"
            gate["evidence"] = f"{gate_id}: required record and exit condition confirmed for this artifact."
        self.review.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")

    def write_html(self, *, language: str, body: str) -> Path:
        path = self.base / "report.html"
        path.write_text(
            "<!-- Generated by Reader's Seat -->\n"
            "<!doctype html>\n"
            f'<html lang="{language}"><head><meta name="viewport" content="width=device-width">'
            "<title>Report</title></head><body><main><h1>Report</h1>"
            f"<p>{body}</p></main></body></html>\n",
            encoding="utf-8",
        )
        return path

    def test_source_language_and_default_html_are_locked(self) -> None:
        contract = self.init_contract()
        self.assertEqual(contract["decisions"]["output_language"], "en")
        self.assertEqual(contract["decisions"]["language_decision_source"], "source-dominant-language-default")
        self.assertEqual(contract["decisions"]["output_format"], "html")
        self.assertEqual(contract["decisions"]["format_decision_source"], "self-contained-html-default")

    def test_concrete_value_expression_gate_is_mandatory(self) -> None:
        contract = self.init_contract()
        self.assertIn("concrete-value-expression", contract["required_semantic_gates"])
        review = json.loads(self.review.read_text(encoding="utf-8"))
        self.assertEqual(review["checks"]["concrete-value-expression"]["status"], "pending")
        self.assertEqual(review["execution_gates"]["G1-task"]["status"], "pending")
        self.assertIsNone(review["artifact_binding"])

    def test_init_generates_minimum_complete_task_bundle(self) -> None:
        contract = self.init_contract()
        context = contract["runtime_context"]
        bundle = Path(context["task_bundle"]["path"])
        manifest = json.loads(
            Path(context["module_manifest"]["path"]).read_text(encoding="utf-8")
        )
        bundle_text = bundle.read_text(encoding="utf-8")
        self.assertIn("## Active Scenario: news", bundle_text)
        self.assertIn("Target reader:", bundle_text)
        self.assertIn("### G1-task", bundle_text)
        self.assertIn("### G6-verify", bundle_text)
        self.assertIn("`html-render-verification`", bundle_text)
        self.assertNotIn("scenario-technical.md", bundle_text)
        self.assertEqual(manifest["contract_id"], contract["contract_id"])
        self.assertEqual(
            manifest["required_rule_ids"],
            contract["required_runtime_rule_ids"],
        )
        self.assertEqual(
            manifest["required_execution_gate_ids"],
            contract["required_execution_gate_ids"],
        )
        self.assertEqual(
            [gate["id"] for gate in manifest["execution_gates"]],
            contract["required_execution_gate_ids"],
        )
        for gate in manifest["execution_gates"]:
            self.assertTrue(gate["required_record"])
            self.assertTrue(gate["exit_condition"])
        self.assertLess(manifest["bundle_characters"], 30000)

    def test_pending_runtime_rule_blocks_delivery(self) -> None:
        self.init_contract()
        artifact = self.write_html(
            language="en",
            body="This is a sufficiently long English report with a clear supported conclusion. " * 5,
        )
        self.complete_review(artifact)
        review = json.loads(self.review.read_text(encoding="utf-8"))
        first_rule = next(iter(review["runtime_rules"].values()))
        first_rule["status"] = "pending"
        first_rule["evidence"] = ""
        self.review.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
        reader_aggregate = self.complete_reader_review(artifact)
        self.run_cli(
            "verify",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--artifact", str(artifact),
            "--actual-format", "html",
            "--reader-review-aggregate", str(reader_aggregate),
            "--receipt", str(self.receipt),
            expected=1,
        )

    def test_core_runtime_rule_cannot_be_marked_not_applicable(self) -> None:
        self.init_contract()
        artifact = self.write_html(
            language="en",
            body="This report contains enough English text for a complete artifact review. " * 6,
        )
        self.complete_review(artifact)
        review = json.loads(self.review.read_text(encoding="utf-8"))
        review["runtime_rules"]["no-invention"] = {
            "status": "not-applicable",
            "evidence": "The reviewer attempted to waive this core rule for the complete artifact.",
        }
        self.review.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
        reader_aggregate = self.complete_reader_review(artifact)
        self.run_cli(
            "verify",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--artifact", str(artifact),
            "--actual-format", "html",
            "--reader-review-aggregate", str(reader_aggregate),
            "--receipt", str(self.receipt),
            expected=1,
        )
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertTrue(any("cannot be marked not-applicable: no-invention" in item for item in receipt["failures"]))

    def test_changed_task_bundle_blocks_delivery(self) -> None:
        contract = self.init_contract()
        bundle = Path(contract["runtime_context"]["task_bundle"]["path"])
        bundle.write_text(bundle.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
        artifact = self.write_html(
            language="en",
            body="This is a sufficiently long English report with a clear supported conclusion. " * 5,
        )
        self.run_cli(
            "verify",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--artifact", str(artifact),
            "--actual-format", "html",
            "--receipt", str(self.receipt),
            expected=2,
        )

    def test_source_snapshot_derives_language_and_hash(self) -> None:
        source = self.base / "source.txt"
        source.write_text(
            "This official article explains model pricing, prompt caching, context management, "
            "and practical ways to reduce unnecessary token use in long coding sessions. " * 4,
            encoding="utf-8",
        )
        self.run_cli(
            "init",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--scenario", "news",
            "--operation", "create",
            "--channel", "artifact",
            "--source-file", str(source),
        )
        contract = json.loads(self.contract.read_text(encoding="utf-8"))
        self.assertEqual(contract["decisions"]["source_language"], "en")
        self.assertEqual(contract["decisions"]["output_language"], "en")
        self.assertEqual(len(contract["decisions"]["source_snapshot"]["sha256"]), 64)

    def test_declared_language_cannot_override_snapshot(self) -> None:
        source = self.base / "source.txt"
        source.write_text(
            "This is an English source article with enough substantive prose for deterministic "
            "language detection and a stable output-language decision. " * 4,
            encoding="utf-8",
        )
        self.run_cli(
            "init",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--scenario", "news",
            "--operation", "create",
            "--channel", "artifact",
            "--source-file", str(source),
            "--source-language", "zh",
            expected=2,
        )

    def test_source_snapshot_cannot_change_after_lock(self) -> None:
        source = self.base / "source.txt"
        source.write_text(
            "This source is frozen before drafting so later evidence checks use the same text. " * 5,
            encoding="utf-8",
        )
        self.run_cli(
            "init",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--scenario", "news",
            "--operation", "create",
            "--channel", "artifact",
            "--source-file", str(source),
        )
        source.write_text("The source changed after the decision lock. " * 5, encoding="utf-8")
        self.run_cli(
            "check-action",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--action", "publish",
            "--target", "feishu",
            "--receipt", str(self.action_receipt),
            expected=2,
        )

    def test_explicit_language_override_wins(self) -> None:
        contract = self.init_contract("--language-override", "zh-CN")
        self.assertEqual(contract["decisions"]["output_language"], "zh-cn")
        self.assertEqual(contract["decisions"]["language_decision_source"], "explicit-user-language-override")

    def test_conflicting_selected_language_is_rejected(self) -> None:
        self.run_cli(
            "init",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--scenario", "news",
            "--operation", "create",
            "--channel", "artifact",
            "--source-language", "en",
            "--selected-language", "zh",
            expected=2,
        )

    def test_feishu_publication_requires_explicit_authorization(self) -> None:
        self.run_cli(
            "init",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--scenario", "business",
            "--operation", "create",
            "--channel", "artifact",
            "--source-language", "zh",
            "--explicit-format", "feishu",
            "--publication-target", "feishu",
            expected=2,
        )

    def test_publish_action_uses_locked_target_and_evidence(self) -> None:
        self.run_cli(
            "init",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--scenario", "business",
            "--operation", "create",
            "--channel", "artifact",
            "--source-language", "zh",
            "--explicit-format", "feishu",
            "--publication-target", "feishu",
            "--external-action", "publish",
            "--external-action-authorized",
            "--authorization-evidence", "User requested a new Feishu document",
        )
        artifact = self.base / "publish-export.md"
        artifact.write_text("A reviewed English publication artifact with sufficient visible content. " * 5, encoding="utf-8")
        self.complete_review(artifact)
        reader_aggregate = self.complete_reader_review(artifact)
        self.run_cli(
            "check-action",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--action", "publish",
            "--target", "feishu",
            "--artifact", str(artifact),
            "--reader-review-aggregate", str(reader_aggregate),
            "--receipt", str(self.action_receipt),
        )
        action_receipt = json.loads(self.action_receipt.read_text(encoding="utf-8"))
        self.assertEqual(action_receipt["status"], "pass")
        self.assertEqual(action_receipt["action"], "publish")

    def test_external_action_cannot_change_after_authorization(self) -> None:
        self.run_cli(
            "init",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--scenario", "business",
            "--operation", "rewrite",
            "--channel", "artifact",
            "--source-language", "zh",
            "--existing-format", "feishu",
            "--publication-target", "feishu",
            "--external-action", "overwrite",
            "--external-action-authorized",
            "--authorization-evidence", "User requested overwriting the named Feishu document",
        )
        self.run_cli(
            "check-action",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--action", "publish",
            "--target", "feishu",
            "--receipt", str(self.action_receipt),
            expected=2,
        )
        artifact = self.base / "overwrite-export.md"
        artifact.write_text("A reviewed English overwrite artifact with sufficient visible content. " * 5, encoding="utf-8")
        self.complete_review(artifact)
        reader_aggregate = self.complete_reader_review(artifact)
        self.run_cli(
            "check-action",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--action", "overwrite",
            "--target", "feishu",
            "--artifact", str(artifact),
            "--reader-review-aggregate", str(reader_aggregate),
            "--receipt", str(self.action_receipt),
        )

    def test_external_delivery_requires_matching_action_receipt(self) -> None:
        self.run_cli(
            "init",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--scenario", "business",
            "--operation", "create",
            "--channel", "artifact",
            "--source-language", "en",
            "--explicit-format", "feishu",
            "--publication-target", "feishu",
            "--external-action", "publish",
            "--external-action-authorized",
            "--authorization-evidence", "User requested a new Feishu document",
        )
        artifact = self.base / "feishu-export.md"
        artifact.write_text(
            "This published report contains enough English text to verify its language, "
            "format, target, and preflight action against the locked task decisions. " * 4,
            encoding="utf-8",
        )
        self.complete_review(artifact)
        reader_aggregate = self.complete_reader_review(artifact)
        self.run_cli(
            "verify",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--artifact", str(artifact),
            "--actual-format", "feishu",
            "--actual-publication-target", "feishu",
            "--actual-external-action", "publish",
            "--reader-review-aggregate", str(reader_aggregate),
            "--receipt", str(self.receipt),
            expected=1,
        )
        self.run_cli(
            "check-action",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--action", "publish",
            "--target", "feishu",
            "--artifact", str(artifact),
            "--reader-review-aggregate", str(reader_aggregate),
            "--receipt", str(self.action_receipt),
        )
        self.run_cli(
            "verify",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--artifact", str(artifact),
            "--actual-format", "feishu",
            "--actual-publication-target", "feishu",
            "--actual-external-action", "publish",
            "--action-receipt", str(self.action_receipt),
            "--reader-review-aggregate", str(reader_aggregate),
            "--receipt", str(self.receipt),
        )

    def test_english_artifact_passes_only_with_complete_review(self) -> None:
        self.init_contract()
        artifact = self.write_html(
            language="en",
            body=(
                "This report explains how prompt caching, model choice, output token pricing, "
                "and session boundaries affect the cost of a Claude Code workflow. The main "
                "recommendation is to preserve relevant context while removing unrelated history."
            ),
        )
        self.complete_review(artifact)
        reader_aggregate = self.complete_reader_review(artifact)
        self.run_cli(
            "verify",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--artifact", str(artifact),
            "--actual-format", "html",
            "--reader-review-aggregate", str(reader_aggregate),
            "--receipt", str(self.receipt),
        )
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "pass")

    def test_chinese_translation_of_english_source_is_blocked(self) -> None:
        self.init_contract()
        artifact = self.write_html(
            language="zh-CN",
            body=(
                "这份报告解释提示词缓存、模型选择、输出计费和会话边界如何影响工作成本。"
                "核心建议是保留真正相关的上下文，同时清理与当前任务无关的历史信息。"
                "这样可以降低不必要的输入消耗，并让模型更专注于当前需要解决的问题。"
            ),
        )
        self.complete_review(artifact)
        self.run_cli(
            "verify",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--artifact", str(artifact),
            "--actual-format", "html",
            "--receipt", str(self.receipt),
            expected=1,
        )
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "fail")
        self.assertTrue(any("visible text language" in item for item in receipt["failures"]))

    def test_format_drift_is_blocked(self) -> None:
        self.init_contract()
        artifact = self.base / "feishu-export.md"
        artifact.write_text("A sufficiently long English report body " * 12, encoding="utf-8")
        self.complete_review(artifact)
        self.run_cli(
            "verify",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--artifact", str(artifact),
            "--actual-format", "feishu",
            "--actual-publication-target", "feishu",
            "--receipt", str(self.receipt),
            expected=1,
        )

    def test_binary_native_format_uses_extracted_content_snapshot(self) -> None:
        self.init_contract("--explicit-format", "word")
        artifact = self.base / "report.docx"
        artifact.write_bytes(b"PK\x03\x04placeholder-docx-package")
        snapshot = self.base / "report.txt"
        snapshot.write_text(
            "This Word report contains enough extracted English prose to verify the locked "
            "language while the binary package is checked separately by its native document tool. " * 3,
            encoding="utf-8",
        )
        self.complete_review(artifact, snapshot)
        reader_aggregate = self.complete_reader_review(artifact)
        self.run_cli(
            "verify",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--artifact", str(artifact),
            "--content-snapshot", str(snapshot),
            "--actual-format", "word",
            "--reader-review-aggregate", str(reader_aggregate),
            "--receipt", str(self.receipt),
        )

    def test_pending_semantic_gate_blocks_delivery(self) -> None:
        self.init_contract()
        artifact = self.write_html(
            language="en",
            body="This is a sufficiently long English report body with clear factual content. " * 5,
        )
        reader_aggregate = self.complete_reader_review(artifact)
        self.run_cli(
            "verify",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--artifact", str(artifact),
            "--actual-format", "html",
            "--receipt", str(self.receipt),
            expected=1,
        )

    def test_high_risk_task_requires_independent_judge(self) -> None:
        contract = self.init_contract("--risk", "high")
        artifact = self.write_html(
            language="en",
            body="This high-risk report contains enough English prose for deterministic checks. " * 5,
        )
        self.complete_review(artifact)
        self.run_cli(
            "verify",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--artifact", str(artifact),
            "--actual-format", "html",
            "--receipt", str(self.receipt),
            expected=1,
        )
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertIn("high-risk task is missing an independent judge result", receipt["failures"])
        self.assertEqual(contract["task"]["risk"], "high")

    def test_high_risk_task_accepts_complete_independent_judge(self) -> None:
        contract = self.init_contract("--risk", "high")
        judge = self.base / "judge.json"
        judge.write_text(
            json.dumps({
                "schema_version": 1,
                "contract_id": contract["contract_id"],
                "verdict": "pass",
                "hard_gates": {gate: "pass" for gate in contract["required_semantic_gates"]},
            }, indent=2) + "\n",
            encoding="utf-8",
        )
        artifact = self.write_html(
            language="en",
            body="This independently reviewed report contains enough English prose to verify. " * 5,
        )
        self.complete_review(artifact)
        reader_aggregate = self.complete_reader_review(artifact)
        self.run_cli(
            "verify",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--artifact", str(artifact),
            "--actual-format", "html",
            "--judge-result", str(judge),
            "--reader-review-aggregate", str(reader_aggregate),
            "--receipt", str(self.receipt),
        )

    def test_high_risk_external_action_requires_judge_before_side_effect(self) -> None:
        self.run_cli(
            "init",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--scenario", "business",
            "--operation", "create",
            "--channel", "artifact",
            "--risk", "high",
            "--source-language", "en",
            "--explicit-format", "feishu",
            "--publication-target", "feishu",
            "--external-action", "publish",
            "--external-action-authorized",
            "--authorization-evidence", "User explicitly requested this high-risk publication",
        )
        contract = json.loads(self.contract.read_text(encoding="utf-8"))
        artifact = self.base / "high-risk-export.md"
        artifact.write_text(
            "This high-risk publication has enough English content for all required checks. " * 6,
            encoding="utf-8",
        )
        self.complete_review(artifact)
        reader_aggregate = self.complete_reader_review(artifact)
        self.run_cli(
            "check-action",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--action", "publish",
            "--target", "feishu",
            "--artifact", str(artifact),
            "--reader-review-aggregate", str(reader_aggregate),
            "--receipt", str(self.action_receipt),
            expected=2,
        )
        self.assertFalse(self.action_receipt.exists())

        judge = self.base / "high-risk-judge.json"
        judge.write_text(
            json.dumps({
                "schema_version": 1,
                "contract_id": contract["contract_id"],
                "verdict": "pass",
                "hard_gates": {gate: "pass" for gate in contract["required_semantic_gates"]},
            }, indent=2) + "\n",
            encoding="utf-8",
        )
        self.run_cli(
            "check-action",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--action", "publish",
            "--target", "feishu",
            "--artifact", str(artifact),
            "--reader-review-aggregate", str(reader_aggregate),
            "--judge-result", str(judge),
            "--receipt", str(self.action_receipt),
        )
        action_receipt = json.loads(self.action_receipt.read_text(encoding="utf-8"))
        self.assertEqual(
            action_receipt["independent_judge_sha256"],
            hashlib.sha256(judge.read_bytes()).hexdigest(),
        )

    def test_missing_reader_review_blocks_finished_artifact(self) -> None:
        self.init_contract()
        artifact = self.write_html(
            language="en",
            body="This finished report has enough English content but no independent reader review. " * 5,
        )
        self.complete_review(artifact)
        self.run_cli(
            "verify",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--artifact", str(artifact),
            "--actual-format", "html",
            "--receipt", str(self.receipt),
            expected=1,
        )
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertIn(
            "finished artifact is missing the required reader review aggregate",
            receipt["failures"],
        )

    def test_reader_review_is_invalid_after_artifact_changes(self) -> None:
        self.init_contract()
        artifact = self.write_html(
            language="en",
            body="This report is reviewed before a later unreviewed content change. " * 6,
        )
        self.complete_review(artifact)
        aggregate = self.complete_reader_review(artifact)
        artifact.write_text(
            artifact.read_text(encoding="utf-8").replace(
                "</main>", "<p>This paragraph was added after review.</p></main>"
            ),
            encoding="utf-8",
        )
        self.run_cli(
            "verify",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--artifact", str(artifact),
            "--actual-format", "html",
            "--reader-review-aggregate", str(aggregate),
            "--receipt", str(self.receipt),
            expected=1,
        )
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertIn("artifact changed after independent reader review", receipt["failures"])

    def test_semantic_review_is_invalid_after_artifact_changes_with_fresh_reader_review(self) -> None:
        self.init_contract()
        artifact = self.write_html(
            language="en",
            body="This report has an artifact-bound semantic review before later revision. " * 6,
        )
        self.complete_review(artifact)
        artifact.write_text(
            artifact.read_text(encoding="utf-8").replace(
                "</main>", "<p>This revised paragraph creates a new artifact hash.</p></main>"
            ),
            encoding="utf-8",
        )
        fresh_reader_aggregate = self.complete_reader_review(artifact)
        self.run_cli(
            "verify",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--artifact", str(artifact),
            "--actual-format", "html",
            "--reader-review-aggregate", str(fresh_reader_aggregate),
            "--receipt", str(self.receipt),
            expected=1,
        )
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertIn(
            "semantic review is missing or bound to a different artifact version",
            receipt["failures"],
        )

    def test_semantic_review_binding_cannot_be_retargeted_by_editing_review(self) -> None:
        self.init_contract()
        artifact = self.write_html(
            language="en",
            body="This report has a semantic review locked to one exact artifact version. " * 6,
        )
        self.complete_review(artifact)
        artifact.write_text(
            artifact.read_text(encoding="utf-8").replace(
                "</main>", "<p>This is a different artifact version.</p></main>"
            ),
            encoding="utf-8",
        )
        review = json.loads(self.review.read_text(encoding="utf-8"))
        review["artifact_binding"]["artifact"]["sha256"] = hashlib.sha256(
            artifact.read_bytes()
        ).hexdigest()
        self.review.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
        fresh_reader_aggregate = self.complete_reader_review(artifact)
        self.run_cli(
            "verify",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--artifact", str(artifact),
            "--actual-format", "html",
            "--reader-review-aggregate", str(fresh_reader_aggregate),
            "--receipt", str(self.receipt),
            expected=1,
        )
        failures = json.loads(self.receipt.read_text(encoding="utf-8"))["failures"]
        self.assertIn("runtime contract is bound to a different artifact version", failures)

    def test_failed_reader_result_cannot_be_changed_to_pass_in_aggregate(self) -> None:
        self.run_cli(
            "init",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--scenario", "business",
            "--operation", "create",
            "--channel", "artifact",
            "--source-language", "en",
            "--explicit-format", "feishu",
            "--publication-target", "feishu",
            "--external-action", "publish",
            "--external-action-authorized",
            "--authorization-evidence", "User explicitly requested publication to Feishu",
        )
        artifact = self.base / "failed-review-export.md"
        artifact.write_text(
            "This report remains readable but one independent review found a material issue. " * 6,
            encoding="utf-8",
        )
        self.complete_review(artifact)
        aggregate = self.complete_reader_review(
            artifact,
            failing_dimension="source-reliability",
            expected=1,
        )
        forged = json.loads(aggregate.read_text(encoding="utf-8"))
        forged["status"] = "pass"
        forged["issues"] = []
        forged["validation_failures"] = []
        for record in forged["reviews"]:
            record["status"] = "pass"
        aggregate.write_text(json.dumps(forged, indent=2) + "\n", encoding="utf-8")
        self.run_cli(
            "check-action",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--action", "publish",
            "--target", "feishu",
            "--artifact", str(artifact),
            "--reader-review-aggregate", str(aggregate),
            "--receipt", str(self.action_receipt),
            expected=2,
        )
        self.assertFalse(self.action_receipt.exists())

    def test_reader_review_rejects_reused_subagent_session(self) -> None:
        self.init_contract()
        artifact = self.write_html(
            language="en",
            body="This report is sent to four reviewers that incorrectly reuse one session. " * 6,
        )
        aggregate = self.complete_reader_review(
            artifact,
            reuse_session=True,
            expected=1,
        )
        result = json.loads(aggregate.read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "revision-required")
        self.assertTrue(any("session_id was reused" in item for item in result["validation_failures"]))

    def test_reader_review_rejects_parent_context(self) -> None:
        self.init_contract()
        artifact = self.write_html(
            language="en",
            body="This report is reviewed by agents that must not inherit the parent context. " * 6,
        )
        aggregate = self.complete_reader_review(
            artifact,
            parent_context_received=True,
            expected=1,
        )
        result = json.loads(aggregate.read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "revision-required")
        self.assertTrue(any("received or did not reject parent context" in item for item in result["validation_failures"]))

    def test_reader_review_third_failure_returns_draft_and_prevents_round_four(self) -> None:
        self.init_contract()
        artifact = self.write_html(
            language="en",
            body="This report intentionally retains one major reader-comprehension problem. " * 6,
        )
        round_one = self.complete_reader_review(
            artifact,
            round_number=1,
            failing_dimension="no-context",
            expected=1,
        )
        early_receipt = self.base / "early-draft-receipt.json"
        self.run_cli(
            "present-draft",
            "--contract", str(self.contract),
            "--artifact", str(artifact),
            "--reader-review-aggregate", str(round_one),
            "--receipt", str(early_receipt),
            expected=1,
        )
        self.assertEqual(
            json.loads(early_receipt.read_text(encoding="utf-8"))["status"],
            "fail",
        )
        artifact.write_text(artifact.read_text(encoding="utf-8") + "\n<!-- revision two -->\n", encoding="utf-8")
        round_two = self.complete_reader_review(
            artifact,
            round_number=2,
            previous_aggregate=round_one,
            failing_dimension="readability",
            expected=1,
        )
        artifact.write_text(artifact.read_text(encoding="utf-8") + "\n<!-- revision three -->\n", encoding="utf-8")
        round_three = self.complete_reader_review(
            artifact,
            round_number=3,
            previous_aggregate=round_two,
            failing_dimension="source-reliability",
            expected=1,
        )
        final_result = json.loads(round_three.read_text(encoding="utf-8"))
        self.assertEqual(final_result["status"], "needs-user-decision")
        self.assertTrue(final_result["max_rounds_exhausted"])

        draft_receipt = self.base / "review-incomplete-draft-receipt.json"
        self.run_cli(
            "present-draft",
            "--contract", str(self.contract),
            "--artifact", str(artifact),
            "--reader-review-aggregate", str(round_three),
            "--receipt", str(draft_receipt),
        )
        presented = json.loads(draft_receipt.read_text(encoding="utf-8"))
        self.assertEqual(presented["status"], "review-incomplete-draft")
        self.assertFalse(presented["publishable"])
        self.assertFalse(presented["verified_finished_artifact"])
        self.assertTrue(presented["user_notice_required"])
        self.assertTrue(presented["user_question_required"])
        self.assertEqual(presented["unresolved_dimensions"], ["source-reliability"])
        self.assertTrue(presented["issues"])
        self.assertIn("publish", presented["prohibited_actions"])

        self.complete_review(artifact)
        self.run_cli(
            "verify",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--artifact", str(artifact),
            "--actual-format", "html",
            "--reader-review-aggregate", str(round_three),
            "--receipt", str(self.receipt),
            expected=1,
        )
        verification = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertTrue(any("status needs-user-decision" in item for item in verification["failures"]))

        artifact.write_text(artifact.read_text(encoding="utf-8") + "\n<!-- forbidden round four -->\n", encoding="utf-8")
        self.run_reader_cli(
            "prepare",
            "--contract", str(self.contract),
            "--artifact", str(artifact),
            "--render-evidence", str(self.base / "render-3-3.png"),
            "--round", "4",
            "--previous-aggregate", str(round_three),
            "--output-dir", str(self.base / "reader-round-4"),
            expected=2,
        )

    def test_reader_review_incomplete_draft_cannot_authorize_publish(self) -> None:
        self.run_cli(
            "init",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--scenario", "business",
            "--operation", "create",
            "--channel", "artifact",
            "--source-language", "en",
            "--explicit-format", "feishu",
            "--publication-target", "feishu",
            "--external-action", "publish",
            "--external-action-authorized",
            "--authorization-evidence", "User explicitly requested publication to Feishu",
        )
        artifact = self.base / "incomplete-publish-export.md"
        artifact.write_text(
            "This current report version remains useful for review but still has one "
            "material source reliability issue that must be resolved before publication. " * 5,
            encoding="utf-8",
        )
        round_one = self.complete_reader_review(
            artifact,
            round_number=1,
            failing_dimension="source-reliability",
            expected=1,
        )
        artifact.write_text(artifact.read_text(encoding="utf-8") + "\nRevision two.\n", encoding="utf-8")
        round_two = self.complete_reader_review(
            artifact,
            round_number=2,
            previous_aggregate=round_one,
            failing_dimension="source-reliability",
            expected=1,
        )
        artifact.write_text(artifact.read_text(encoding="utf-8") + "\nRevision three.\n", encoding="utf-8")
        round_three = self.complete_reader_review(
            artifact,
            round_number=3,
            previous_aggregate=round_two,
            failing_dimension="source-reliability",
            expected=1,
        )
        draft_receipt = self.base / "publish-task-draft-receipt.json"
        self.run_cli(
            "present-draft",
            "--contract", str(self.contract),
            "--artifact", str(artifact),
            "--reader-review-aggregate", str(round_three),
            "--receipt", str(draft_receipt),
        )
        self.run_cli(
            "check-action",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--action", "publish",
            "--target", "feishu",
            "--artifact", str(artifact),
            "--reader-review-aggregate", str(round_three),
            "--receipt", str(self.action_receipt),
            expected=2,
        )
        self.assertFalse(self.action_receipt.exists())

    def test_generic_semantic_evidence_blocks_delivery(self) -> None:
        self.init_contract()
        artifact = self.write_html(
            language="en",
            body="This is a sufficiently long English report body with clear factual content. " * 5,
        )
        self.complete_review(artifact)
        review = json.loads(self.review.read_text(encoding="utf-8"))
        for gate in review["checks"].values():
            gate["status"] = "pass"
            gate["evidence"] = "已检查"
        self.review.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
        self.run_cli(
            "verify",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--artifact", str(artifact),
            "--actual-format", "html",
            "--receipt", str(self.receipt),
            expected=1,
        )

    def test_locked_decisions_cannot_be_changed_silently(self) -> None:
        contract = self.init_contract()
        contract["decisions"]["output_language"] = "zh"
        self.contract.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
        self.run_cli(
            "check-action",
            "--contract", str(self.contract),
            "--review", str(self.review),
            "--action", "publish",
            "--target", "feishu",
            "--receipt", str(self.action_receipt),
            expected=2,
        )

    def test_html_scaffold_requires_locked_language(self) -> None:
        completed = subprocess.run(
            ["bash", str(SCAFFOLD), "missing-language", str(self.base)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("--lang", completed.stderr)

    def test_html_scaffold_writes_locked_language(self) -> None:
        completed = subprocess.run(
            ["bash", str(SCAFFOLD), "language-report", str(self.base), "--lang", "zh-CN"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        html = self.base / "language-report" / "language-report.html"
        self.assertIn('<html lang="zh-CN">', html.read_text(encoding="utf-8"))
        validation = subprocess.run(
            [
                sys.executable,
                "-B",
                str(HTML_VALIDATOR),
                str(html),
                "--scaffold",
                "--expected-language",
                "zh-CN",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)


if __name__ == "__main__":
    unittest.main()
