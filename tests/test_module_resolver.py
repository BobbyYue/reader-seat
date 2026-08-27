from __future__ import annotations

import argparse
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import resolve_modules  # noqa: E402
import run_evals  # noqa: E402


class ModuleResolverTests(unittest.TestCase):
    def test_legacy_caller_can_omit_new_optional_flags(self) -> None:
        namespace = argparse.Namespace(
            scenario="news",
            operation="rewrite",
            artifact=False,
            chat_output=True,
            risk="standard",
            output_format="html",
            title=True,
            visual="none",
        )
        result = resolve_modules.resolve(namespace, resolve_modules.load_profiles())
        self.assertFalse(result["task_profile"]["explicit_evaluation"])
        self.assertFalse(result["task_profile"]["portability"])
        self.assertFalse(result["task_profile"]["maintenance"])

    def test_maximal_bundle_stays_within_runtime_budget(self) -> None:
        namespace = argparse.Namespace(
            scenario="analysis",
            operation="compare",
            artifact=True,
            chat_output=False,
            risk="high",
            output_format="html",
            title=True,
            visual="asset",
            evaluate=True,
            portability=True,
            maintenance=True,
        )
        result = resolve_modules.resolve(namespace, resolve_modules.load_profiles())
        bundle = resolve_modules.render_bundle(result)
        contract = json.loads((ROOT / "config" / "skill-contract.json").read_text(encoding="utf-8"))
        self.assertLessEqual(
            len(bundle.encode("utf-8")),
            contract["runtime_loading"]["task_bundle_max_bytes"],
        )

    def test_finished_artifact_requires_reading_path_layout_rules(self) -> None:
        namespace = argparse.Namespace(
            scenario="business",
            operation="create",
            artifact=True,
            chat_output=False,
            risk="standard",
            output_format="html",
            title=True,
            visual="none",
            evaluate=False,
            portability=False,
            maintenance=False,
        )
        result = resolve_modules.resolve(namespace, resolve_modules.load_profiles())
        module_ids = {item["id"] for item in result["modules"]}
        self.assertIn("reading-path-layout", module_ids)
        layout_rule_ids = {
            "layout-plan-before-build",
            "layout-opening-hierarchy",
            "layout-one-reader-job-per-section",
            "layout-claim-evidence-adjacency",
            "layout-density-rhythm",
            "layout-spacing-hierarchy",
            "layout-native-render-verification",
        }
        self.assertTrue(layout_rule_ids <= set(result["required_rule_ids"]))
        self.assertTrue(
            all(result["runtime_rule_applicability"][rule_id] is False for rule_id in layout_rule_ids)
        )

    def test_execution_efficiency_is_mandatory(self) -> None:
        namespace = argparse.Namespace(
            scenario="business",
            operation="create",
            artifact=True,
            chat_output=False,
            risk="standard",
            output_format="html",
            title=True,
            visual="none",
            evaluate=False,
            portability=False,
            maintenance=False,
        )
        result = resolve_modules.resolve(namespace, resolve_modules.load_profiles())
        self.assertIn("execution-efficiency", {item["id"] for item in result["modules"]})
        expected = {
            "efficiency-readiness-before-build",
            "efficiency-batch-independent-artifacts",
            "efficiency-change-impact-rerun",
            "efficiency-merge-review-fixes",
        }
        self.assertTrue(expected <= set(result["required_rule_ids"]))

    def test_chat_output_does_not_load_artifact_layout_module(self) -> None:
        namespace = argparse.Namespace(
            scenario="business",
            operation="create",
            artifact=False,
            chat_output=True,
            risk="standard",
            output_format="chat",
            title=False,
            visual="none",
            evaluate=False,
            portability=False,
            maintenance=False,
        )
        result = resolve_modules.resolve(namespace, resolve_modules.load_profiles())
        self.assertNotIn("reading-path-layout", {item["id"] for item in result["modules"]})

    def test_evaluation_harness_uses_task_bundle_not_full_references(self) -> None:
        cases = json.loads(
            (ROOT / "evals" / "cross-agent-cases.json").read_text(encoding="utf-8")
        )["cases"]
        case = next(item for item in cases if item["id"] == "xagent-news-source-language")
        prompt = run_evals.build_producer_prompt(case, run_evals.module_plan(case))
        self.assertIn("GENERATED TASK CONTRACT", prompt)
        self.assertIn("`title-no-clickbait`", prompt)
        self.assertNotIn("Read every listed file", prompt)
        self.assertNotIn("references/scenario-technical.md", prompt)

    def test_readability_extensions_reuse_existing_runtime_rules(self) -> None:
        rules = resolve_modules.load_runtime_rules()
        modules = rules["modules"]
        self.assertEqual(len(modules["output-standards"]), 9)
        self.assertEqual(len(modules["signal-processing"]), 5)
        self.assertEqual(len(modules["html-output"]), 9)

        by_id = {
            item["id"]: item["instruction"]
            for group in modules.values()
            for item in group
        }
        self.assertIn("accessible, findable", by_id["reader-perspective"])
        self.assertIn("paragraph topic drift", by_id["signals-are-not-errors"])
        self.assertIn("start near 16px", by_id["html-accessible-print-layout"])
        self.assertIn("not rewrite triggers", by_id["signals-are-not-errors"])

    def test_deleted_mandatory_rule_is_rejected(self) -> None:
        rules = copy.deepcopy(resolve_modules.load_runtime_rules())
        rules["core"] = [item for item in rules["core"] if item["id"] != "no-invention"]
        namespace = argparse.Namespace(
            scenario="business",
            operation="rewrite",
            artifact=False,
            chat_output=True,
            risk="standard",
            output_format="html",
            title=False,
            visual="none",
        )
        with self.assertRaisesRegex(SystemExit, "versioned skill contract inventory"):
            resolve_modules.resolve(namespace, resolve_modules.load_profiles(), rules)

    def test_html_language_check_uses_visible_text_not_css(self) -> None:
        case = {
            "id": "html-language-check",
            "scenario": "technical",
            "operation": "create",
            "artifact": True,
            "output_format": "html",
            "source_material": "这是一份中文技术说明，正文应保持中文。" * 5,
            "hard_checks": {"must_contain": ["技术说明"]},
        }
        html = (
            "<!doctype html><html><head><style>"
            + ".layout { background: white; display: grid; }" * 80
            + "</style></head><body><h1>技术说明</h1><p>"
            + "采集、校验和发布三个阶段均有明确边界。" * 8
            + "</p></body></html>"
        )
        result = run_evals.deterministic_grade(case, html)
        self.assertEqual(result["verdict"], "pass", result["failures"])


if __name__ == "__main__":
    unittest.main()
