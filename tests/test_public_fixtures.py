"""Keep the public evaluation corpus independent of private working examples."""
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PublicFixtureTests(unittest.TestCase):
    def test_required_answers_uses_fictional_workflow_case(self):
        cases = json.loads((ROOT / "evals/cross-agent-cases.json").read_text())["cases"]
        matches = [case for case in cases if case["id"] == "xagent-required-answers-workflow-features"]
        self.assertEqual(len(matches), 1)
        case = matches[0]
        self.assertIn("完全虚构", case["request"])
        self.assertIn("虚构测试数据", case["source_material"])
        self.assertIn("同一文档流程", case["source_material"])
        self.assertEqual(
            case["hard_checks"]["must_contain"],
            ["资料完整度", "检查清单完成率", "自动校验覆盖率", "84%", "52%", "20"],
        )
        self.assertIn("分组观察", case["immutable_facts"])

    def test_previously_sanitized_case_is_not_reintroduced(self):
        cases = json.loads((ROOT / "evals/cross-agent-cases.json").read_text())["cases"]
        self.assertNotIn("xagent-required-answers-ad-features", {case["id"] for case in cases})


if __name__ == "__main__":
    unittest.main()
