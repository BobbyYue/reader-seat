#!/usr/bin/env python3
"""Resolve the minimum complete Reader's Seat module set for one task."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PROFILE_PATH = ROOT / "config" / "module-profiles.json"


def load_profiles() -> dict:
    try:
        data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"error: cannot load {PROFILE_PATH}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("modules"), dict):
        raise SystemExit("error: module profile has an invalid structure")
    return data


def add_unique(items: list[str], values: list[str]) -> None:
    for value in values:
        if value not in items:
            items.append(value)


def extract_section(text: str, heading: str) -> str:
    pattern = re.compile(
        rf"^{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        raise SystemExit(f"error: scenario module is missing {heading}")
    return match.group("body").strip()


def resolve(args: argparse.Namespace, profiles: dict) -> dict:
    selected: list[str] = []
    reasons: dict[str, list[str]] = {}

    def include(module_ids: list[str], reason: str) -> None:
        add_unique(selected, module_ids)
        for module_id in module_ids:
            reasons.setdefault(module_id, [])
            if reason not in reasons[module_id]:
                reasons[module_id].append(reason)

    include(profiles["always_modules"], "required for every task")
    include(
        [profiles["scenario_modules"][args.scenario]],
        f"primary scenario: {args.scenario}",
    )
    include(
        profiles["operation_modules"][args.operation],
        f"operation: {args.operation}",
    )

    if args.artifact:
        include(profiles["artifact_modules"], "finished artifact")
        if args.output_format == "html":
            include(profiles["feature_modules"]["html-output"], "selected output format: html")

    include(profiles["risk_modules"][args.risk], f"risk level: {args.risk}")

    if args.title:
        include(profiles["feature_modules"]["title"], "title or subtitle required")

    if args.visual == "decision":
        include(profiles["feature_modules"]["visual-decision"], "visual decision requested")
    elif args.visual == "retained":
        include(profiles["feature_modules"]["visual-retained"], "material visual retained or reviewed")
    elif args.visual == "asset":
        include(profiles["feature_modules"]["visual-asset"], "visual asset carries provenance claims")

    if args.evaluate:
        include(profiles["feature_modules"]["explicit-evaluation"], "explicit evaluation")
    if args.portability:
        include(profiles["feature_modules"]["portability"], "cross-agent packaging or evaluation")

    order = {module_id: index for index, module_id in enumerate(profiles["load_order"])}
    selected.sort(key=lambda module_id: order[module_id])

    resolved = []
    for module_id in selected:
        definition = profiles["modules"].get(module_id)
        if not isinstance(definition, dict):
            raise SystemExit(f"error: unknown module in profile: {module_id}")
        relative = definition.get("path")
        path = ROOT / str(relative)
        if not path.is_file():
            raise SystemExit(f"error: resolved module is missing: {relative}")
        resolved.append(
            {
                "id": module_id,
                "path": relative,
                "purpose": definition.get("purpose", ""),
                "reasons": reasons[module_id],
            }
        )

    scenario_module_id = profiles["scenario_modules"][args.scenario]
    scenario_path = ROOT / profiles["modules"][scenario_module_id]["path"]
    scenario_text = scenario_path.read_text(encoding="utf-8")
    active_scenario_contract = {
        "source": str(scenario_path.relative_to(ROOT)),
        "required_content": extract_section(scenario_text, "## Required Content"),
        "evidence_requirements": extract_section(scenario_text, "## Evidence Requirements"),
        "acceptance_questions": extract_section(scenario_text, "## Acceptance Questions"),
    }

    return {
        "schema_version": 1,
        "skill": "reader-seat",
        "runtime_enforcement": {
            "required": True,
            "contract_script": "scripts/runtime_contract.py",
            "verification_receipt_required": True,
        },
        "task_profile": {
            "scenario": args.scenario,
            "operation": args.operation,
            "finished_artifact": args.artifact,
            "output_format": args.output_format if args.artifact else "chat",
            "risk": args.risk,
            "title": args.title,
            "visual": args.visual,
            "explicit_evaluation": args.evaluate,
            "portability": args.portability,
        },
        "canonical_entry": profiles["canonical_entry"],
        "modules": resolved,
        "active_scenario_contract": active_scenario_contract,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve a deterministic Reader's Seat module load plan."
    )
    parser.add_argument(
        "--scenario",
        required=True,
        choices=("news", "technical", "product", "business", "analysis", "procedure"),
    )
    parser.add_argument(
        "--operation",
        default="create",
        choices=("create", "rewrite", "diagnose", "compare"),
    )
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument("--artifact", action="store_true", help="the task produces or edits a finished artifact")
    output.add_argument("--chat-output", action="store_true", help="the task returns only conversational text")
    parser.add_argument("--risk", default="standard", choices=("standard", "high"))
    parser.add_argument(
        "--output-format",
        default="html",
        choices=(
            "html",
            "native",
            "feishu",
            "lark",
            "word",
            "markdown",
            "plain-text",
            "slides",
            "other",
        ),
        help="selected finished-artifact format; native remains a generic non-HTML alias",
    )
    parser.add_argument("--title", action="store_true")
    parser.add_argument(
        "--visual",
        default="none",
        choices=("none", "decision", "retained", "asset"),
        help="none, decision only, retained visual implementation, or provenance-bearing asset",
    )
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--portability", action="store_true")
    parser.add_argument("--emit", default="paths", choices=("paths", "json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profiles = load_profiles()
    result = resolve(args, profiles)
    if args.emit == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["canonical_entry"])
        for module in result["modules"]:
            print(module["path"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
