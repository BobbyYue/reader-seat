#!/usr/bin/env python3
"""Resolve and package the minimum complete Reader's Seat runtime context."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PROFILE_PATH = ROOT / "config" / "module-profiles.json"
RULES_PATH = ROOT / "config" / "runtime-rules.json"
CONTRACT_PATH = ROOT / "config" / "skill-contract.json"


def load_json(path: Path, label: str) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"error: cannot load {label} {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"error: {label} must contain a JSON object")
    return data


def load_profiles() -> dict:
    data = load_json(PROFILE_PATH, "module profile")
    if not isinstance(data.get("modules"), dict):
        raise SystemExit("error: module profile has an invalid modules object")
    return data


def load_runtime_rules() -> dict:
    data = load_json(RULES_PATH, "runtime rules")
    if data.get("schema_version") != 1:
        raise SystemExit("error: runtime rules use an unsupported schema")
    if (
        not isinstance(data.get("execution_gates"), list)
        or not isinstance(data.get("core"), list)
        or not isinstance(data.get("modules"), dict)
    ):
        raise SystemExit("error: runtime rules require execution_gates, core, and modules collections")
    validate_runtime_rule_inventory(data)
    return data


def validate_runtime_rule_inventory(data: dict) -> None:
    contract = load_json(CONTRACT_PATH, "skill contract")
    inventory = contract.get("runtime_rule_inventory")
    if not isinstance(inventory, dict):
        raise SystemExit("error: skill contract has no runtime rule inventory")
    actual_core = [item.get("id") for item in data["core"] if isinstance(item, dict)]
    actual_modules = {
        module_id: [item.get("id") for item in items if isinstance(item, dict)]
        for module_id, items in data["modules"].items()
        if isinstance(items, list)
    }
    if actual_core != inventory.get("core") or actual_modules != inventory.get("modules"):
        raise SystemExit("error: runtime rule catalog differs from the versioned skill contract inventory")
    gate_ids = [item.get("id") for item in data["execution_gates"] if isinstance(item, dict)]
    if gate_ids != contract.get("mandatory_execution_gates"):
        raise SystemExit("error: execution gates differ from the skill contract")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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


def validate_rules(items: object, label: str) -> list[dict[str, str]]:
    if not isinstance(items, list) or not items:
        raise SystemExit(f"error: {label} has no runtime rules")
    result: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            raise SystemExit(f"error: {label} contains a non-object runtime rule")
        rule_id = item.get("id")
        instruction = item.get("instruction")
        if not isinstance(rule_id, str) or not rule_id.strip():
            raise SystemExit(f"error: {label} contains a runtime rule without an id")
        if not isinstance(instruction, str) or not instruction.strip():
            raise SystemExit(f"error: runtime rule {rule_id} has no instruction")
        allow_not_applicable = item.get("allow_not_applicable", False)
        if not isinstance(allow_not_applicable, bool):
            raise SystemExit(f"error: runtime rule {rule_id} has invalid applicability metadata")
        result.append(
            {
                "id": rule_id,
                "instruction": instruction.strip(),
                "allow_not_applicable": allow_not_applicable,
            }
        )
    return result


def validate_execution_gates(items: object) -> list[dict[str, str]]:
    if not isinstance(items, list) or not items:
        raise SystemExit("error: runtime rules have no execution gates")
    result = []
    for item in items:
        if not isinstance(item, dict):
            raise SystemExit("error: execution gate must be an object")
        gate_id = item.get("id")
        required_record = item.get("required_record")
        exit_condition = item.get("exit_condition")
        if not all(isinstance(value, str) and value.strip() for value in (gate_id, required_record, exit_condition)):
            raise SystemExit("error: execution gate requires id, required_record, and exit_condition")
        result.append(
            {
                "id": gate_id,
                "required_record": required_record.strip(),
                "exit_condition": exit_condition.strip(),
            }
        )
    return result


def resolve(
    args: argparse.Namespace,
    profiles: dict,
    runtime_rules: dict | None = None,
) -> dict:
    rules = runtime_rules or load_runtime_rules()
    validate_runtime_rule_inventory(rules)
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

    evaluate = bool(getattr(args, "evaluate", False))
    portability = bool(getattr(args, "portability", False))
    maintenance = bool(getattr(args, "maintenance", False))
    if evaluate:
        include(profiles["feature_modules"]["explicit-evaluation"], "explicit evaluation")
    if portability:
        include(profiles["feature_modules"]["portability"], "cross-agent packaging or evaluation")
    if maintenance:
        include(profiles["feature_modules"]["maintenance"], "skill maintenance or structural change")

    order = {module_id: index for index, module_id in enumerate(profiles["load_order"])}
    selected.sort(key=lambda module_id: order[module_id])

    resolved = []
    module_rule_groups = []
    scenario_module_ids = set(profiles["scenario_modules"].values())
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
                "sha256": file_hash(path),
                "purpose": definition.get("purpose", ""),
                "reasons": reasons[module_id],
                "default_load": "task-bundle",
            }
        )
        if module_id not in scenario_module_ids:
            module_rule_groups.append(
                {
                    "module_id": module_id,
                    "source": str(RULES_PATH.relative_to(ROOT)),
                    "rules": validate_rules(rules["modules"].get(module_id), module_id),
                }
            )

    execution_gates = validate_execution_gates(rules["execution_gates"])
    core_rules = validate_rules(rules["core"], "core")
    scenario_module_id = profiles["scenario_modules"][args.scenario]
    scenario_path = ROOT / profiles["modules"][scenario_module_id]["path"]
    scenario_text = scenario_path.read_text(encoding="utf-8")
    active_scenario_contract = {
        "source": str(scenario_path.relative_to(ROOT)),
        "sha256": file_hash(scenario_path),
        "reader_task": extract_section(scenario_text, "## Reader Task"),
        "required_content": extract_section(scenario_text, "## Required Content"),
        "recommended_relationship": extract_section(scenario_text, "## Recommended Relationship"),
        "evidence_requirements": extract_section(scenario_text, "## Evidence Requirements"),
        "common_failures": extract_section(scenario_text, "## Common Failures"),
        "acceptance_questions": extract_section(scenario_text, "## Acceptance Questions"),
    }
    required_rule_ids = [rule["id"] for rule in core_rules]
    for group in module_rule_groups:
        required_rule_ids.extend(rule["id"] for rule in group["rules"])
    if len(required_rule_ids) != len(set(required_rule_ids)):
        raise SystemExit("error: selected runtime rules contain duplicate ids")

    return {
        "schema_version": 2,
        "skill": "reader-seat",
        "runtime_enforcement": {
            "required": True,
            "contract_script": "scripts/runtime_contract.py",
            "reader_review_script": "scripts/reader_review.py",
            "reader_review_required_for_artifacts": bool(args.artifact),
            "verification_receipt_required": True,
            "task_bundle_required": True,
            "module_manifest_required": True,
        },
        "task_profile": {
            "scenario": args.scenario,
            "operation": args.operation,
            "finished_artifact": args.artifact,
            "output_format": args.output_format if args.artifact else "chat",
            "risk": args.risk,
            "title": args.title,
            "visual": args.visual,
            "explicit_evaluation": evaluate,
            "portability": portability,
            "maintenance": maintenance,
            "reader_profile": getattr(args, "reader_profile", "") or "General reader with no assumed hidden context",
        },
        "canonical_entry": profiles["canonical_entry"],
        "canonical_entry_sha256": file_hash(ROOT / profiles["canonical_entry"]),
        "routing_source": str(PROFILE_PATH.relative_to(ROOT)),
        "routing_source_sha256": file_hash(PROFILE_PATH),
        "rules_source": str(RULES_PATH.relative_to(ROOT)),
        "rules_source_sha256": file_hash(RULES_PATH),
        "modules": resolved,
        "core_rules": core_rules,
        "module_rule_groups": module_rule_groups,
        "required_rule_ids": required_rule_ids,
        "runtime_rule_applicability": {
            rule["id"]: rule["allow_not_applicable"]
            for rule in core_rules
        }
        | {
            rule["id"]: rule["allow_not_applicable"]
            for group in module_rule_groups
            for rule in group["rules"]
        },
        "execution_gates": execution_gates,
        "required_execution_gate_ids": [gate["id"] for gate in execution_gates],
        "active_scenario_contract": active_scenario_contract,
    }


def render_bundle(
    result: dict,
    *,
    contract_id: str = "unlocked-preview",
    output_language: str | None = None,
) -> str:
    profile = result["task_profile"]
    lines = [
        "# Reader's Seat Task Contract",
        "",
        f"Contract: `{contract_id}`",
        "",
        "This generated packet is the default instruction context for this task. Its rules are mandatory. Read a full reference only when troubleshooting, maintaining the skill, or when this packet explicitly lacks the procedure needed for the task.",
        "",
        "## Locked Task",
        "",
        f"- Scenario: `{profile['scenario']}`",
        f"- Operation: `{profile['operation']}`",
        f"- Channel: `{'artifact' if profile['finished_artifact'] else 'chat'}`",
        f"- Output format: `{profile['output_format']}`",
        f"- Output language: `{output_language or 'set by runtime contract'}`",
        f"- Risk: `{profile['risk']}`",
        f"- Title required: `{str(profile['title']).lower()}`",
        f"- Visual state: `{profile['visual']}`",
        f"- Target reader: {profile['reader_profile']}",
        "",
        "## Non-Negotiable Rules",
        "",
    ]
    lines.extend(
        f"- `{rule['id']}`{' [conditional]' if rule['allow_not_applicable'] else ''}: {rule['instruction']}"
        for rule in result["core_rules"]
    )
    for group in result["module_rule_groups"]:
        lines.extend(["", f"## {group['module_id']}", ""])
        lines.extend(
            f"- `{rule['id']}`{' [conditional]' if rule['allow_not_applicable'] else ''}: {rule['instruction']}"
            for rule in group["rules"]
        )

    lines.extend(["", "## Execution Gates", ""])
    for gate in result["execution_gates"]:
        lines.extend(
            [
                f"### {gate['id']}",
                "",
                f"- Required record: {gate['required_record']}",
                f"- Exit condition: {gate['exit_condition']}",
                "",
            ]
        )

    scenario = result["active_scenario_contract"]
    lines.extend(
        [
            "",
            f"## Active Scenario: {profile['scenario']}",
            "",
            "### Reader Task",
            "",
            scenario["reader_task"],
            "",
            "### Required Content",
            "",
            scenario["required_content"],
            "",
            "### Recommended Relationship",
            "",
            scenario["recommended_relationship"],
            "",
            "### Evidence Requirements",
            "",
            scenario["evidence_requirements"],
            "",
            "### Common Failures",
            "",
            scenario["common_failures"],
            "",
            "### Acceptance Questions",
            "",
            scenario["acceptance_questions"],
            "",
            "## Source Modules",
            "",
            "The manifest binds this packet to the following canonical modules. They are detailed references, not default context:",
            "",
        ]
    )
    lines.extend(
        f"- `{module['path']}` ({module['purpose']})"
        for module in result["modules"]
    )
    lines.extend(
        [
            "",
            "## Completion Record",
            "",
            "Complete every listed runtime rule in the generated semantic review with concrete evidence. A rule may be `not-applicable` only with a task-specific reason. Complete the selected scenario acceptance questions and all required semantic gates before verification.",
            "",
        ]
    )
    return "\n".join(lines)


def build_manifest(result: dict, bundle: str, *, contract_id: str) -> dict:
    return {
        "schema_version": 1,
        "contract_id": contract_id,
        "task_profile": result["task_profile"],
        "bundle_sha256": text_hash(bundle),
        "bundle_characters": len(bundle),
        "bundle_bytes": len(bundle.encode("utf-8")),
        "canonical_entry": {
            "path": result["canonical_entry"],
            "sha256": result["canonical_entry_sha256"],
        },
        "routing_source": {
            "path": result["routing_source"],
            "sha256": result["routing_source_sha256"],
        },
        "rules_source": {
            "path": result["rules_source"],
            "sha256": result["rules_source_sha256"],
        },
        "modules": [
            {"id": module["id"], "path": module["path"], "sha256": module["sha256"]}
            for module in result["modules"]
        ],
        "required_rule_ids": result["required_rule_ids"],
        "runtime_rule_applicability": result["runtime_rule_applicability"],
        "execution_gates": result["execution_gates"],
        "required_execution_gate_ids": result["required_execution_gate_ids"],
        "scenario_contract": {
            "source": result["active_scenario_contract"]["source"],
            "sha256": result["active_scenario_contract"]["sha256"],
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve a deterministic Reader's Seat task contract."
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
    parser.add_argument("--maintenance", action="store_true")
    parser.add_argument("--contract-id", default="unlocked-preview")
    parser.add_argument("--output-language")
    parser.add_argument("--reader-profile", default="")
    parser.add_argument("--bundle-out", type=Path)
    parser.add_argument("--manifest-out", type=Path)
    parser.add_argument("--emit", default="paths", choices=("paths", "json", "bundle"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = resolve(args, load_profiles(), load_runtime_rules())
    bundle = render_bundle(
        result,
        contract_id=args.contract_id,
        output_language=args.output_language,
    )
    manifest = build_manifest(result, bundle, contract_id=args.contract_id)
    if args.bundle_out:
        args.bundle_out.parent.mkdir(parents=True, exist_ok=True)
        args.bundle_out.write_text(bundle, encoding="utf-8")
    if args.manifest_out:
        args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_out.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if args.emit == "json":
        output = dict(result)
        output["module_manifest"] = manifest
        print(json.dumps(output, ensure_ascii=False, indent=2))
    elif args.emit == "bundle":
        print(bundle)
    else:
        print(result["canonical_entry"])
        for module in result["modules"]:
            print(module["path"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
