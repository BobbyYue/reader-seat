#!/usr/bin/env python3
"""Validate the modular contract for Reader's Seat."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config" / "skill-contract.json"
MODULE_PROFILES_PATH = ROOT / "config" / "module-profiles.json"
RUNTIME_RULES_PATH = ROOT / "config" / "runtime-rules.json"
AGENT_ADAPTERS_PATH = ROOT / "config" / "agent-adapters.json"


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def load_json(path: Path, errors: list[str]) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"missing file: {path.relative_to(ROOT)}", errors)
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path.relative_to(ROOT)}: {exc}", errors)
    return None


def check_skill_md(contract: dict, errors: list[str]) -> None:
    path = ROOT / "SKILL.md"
    if not path.exists():
        fail("missing SKILL.md", errors)
        return

    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        fail("SKILL.md has invalid YAML frontmatter boundaries", errors)
        return

    frontmatter = match.group(1)
    keys = re.findall(r"^([A-Za-z0-9_-]+):", frontmatter, re.MULTILINE)
    if keys != ["name", "description"]:
        fail(f"SKILL.md frontmatter must contain only name and description; got {keys}", errors)
    if f"name: {contract['name']}" not in frontmatter:
        fail("SKILL.md name does not match contract", errors)
    if "TODO" in text:
        fail("SKILL.md still contains TODO", errors)
    runtime = contract.get("runtime_loading", {})
    max_lines = runtime.get("entrypoint_max_lines", 150)
    max_bytes = runtime.get("entrypoint_max_bytes", 16384)
    if len(text.splitlines()) > max_lines:
        fail(f"SKILL.md exceeds the {max_lines}-line entrypoint budget", errors)
    if len(text.encode("utf-8")) > max_bytes:
        fail(f"SKILL.md exceeds the {max_bytes}-byte entrypoint budget", errors)

    for gate in contract.get("mandatory_execution_gates", []):
        if gate not in text:
            fail(f"SKILL.md does not operationalize execution gate: {gate}", errors)

    required_entrypoint_terms = [
        "## Non-Negotiable Invariants",
        "## Runtime Sequence",
        "## Output Behavior",
        "## Operational Sources",
        "source truth and scope",
        "dominant language",
        "self-contained HTML",
        "resolved-task-contract.md",
        "module-manifest.json",
        "config/module-profiles.json",
        "config/runtime-rules.json",
        "scripts/runtime_contract.py",
        "scripts/reader_review.py",
        "check-action",
        "present-draft",
        "verify",
        "references/skill-maintenance.md",
    ]
    for term in required_entrypoint_terms:
        if term not in text:
            fail(f"SKILL.md missing required entrypoint invariant: {term}", errors)

    for link in re.findall(r"\]\(([^)]+)\)", text):
        if "://" in link or link.startswith("#"):
            continue
        target = ROOT / link.split("#", 1)[0]
        if not target.exists():
            fail(f"broken SKILL.md link: {link}", errors)


def check_reference_links(errors: list[str]) -> None:
    for path in sorted((ROOT / "references").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for link in re.findall(r"\]\(([^)]+)\)", text):
            if "://" in link or link.startswith("#") or link.startswith("mailto:"):
                continue
            relative = link.split("#", 1)[0]
            target = path.parent / relative
            if not target.exists():
                fail(f"broken reference link in {path.name}: {link}", errors)


def check_contract(contract: dict, errors: list[str]) -> None:
    if contract.get("schema_version") != 3:
        fail("skill contract schema_version must be 3", errors)
    if not re.fullmatch(r"\d+\.\d+\.\d+", contract.get("skill_version", "")):
        fail("skill_version must use semantic versioning", errors)

    routes = contract.get("primary_routes", [])
    route_ids = [route.get("id") for route in routes]
    if len(route_ids) != len(set(route_ids)):
        fail("primary route IDs must be unique", errors)
    if len(routes) != 6:
        fail(f"expected 6 primary routes, found {len(routes)}", errors)

    required_headings = contract.get("scenario_required_headings", [])
    module_paths = [route.get("reference") for route in routes]
    module_paths += contract.get("shared_modules", [])
    module_paths += [module.get("reference") for module in contract.get("conditional_modules", [])]
    module_paths += contract.get("eval_files", [])

    for relative in module_paths:
        if not relative:
            fail("contract contains an empty module path", errors)
            continue
        if not (ROOT / relative).exists():
            fail(f"contract references missing file: {relative}", errors)

    for route in routes:
        relative = route.get("reference")
        path = ROOT / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for heading in required_headings:
            if heading not in text:
                fail(f"{relative} missing heading: {heading}", errors)

    standards = contract.get("output_standards", [])
    if len(standards) != 8 or len(standards) != len(set(standards)):
        fail("output_standards must contain 8 unique items", errors)

    expected_gates = ["G1-task", "G2-source", "G3-route", "G4-build", "G5-signals", "G6-verify"]
    if contract.get("mandatory_execution_gates") != expected_gates:
        fail("mandatory_execution_gates must define the six ordered execution gates", errors)

    if contract.get("signal_decisions") != ["confirmed", "dismissed", "unresolved"]:
        fail("signal_decisions must define confirmed, dismissed, and unresolved", errors)

    expected_actions = ["none", "local-edit", "section-rebuild", "full-restructure", "surface-to-user"]
    if contract.get("signal_actions") != expected_actions:
        fail("signal_actions do not match the standardized action set", errors)

    expected_visible_structure_states = ["content-bearing", "navigation-only", "decorative"]
    if contract.get("visible_structure_states") != expected_visible_structure_states:
        fail("visible_structure_states do not match the information-bearing structure contract", errors)

    expected_language_selection_rules = [
        "explicit-user-language-override",
        "source-dominant-language-default",
        "prompt-language-does-not-trigger-translation",
        "mixed-source-language-resolution",
        "preserve-precision-critical-original-forms",
    ]
    if contract.get("language_selection_rules") != expected_language_selection_rules:
        fail("language_selection_rules do not match the source-language contract", errors)

    expected_output_format_rules = [
        "explicit-user-format-override",
        "existing-target-format-preservation",
        "chat-only-output-signal",
        "self-contained-html-default",
        "portable-html-presentation-baseline",
        "native-format-capability-preservation",
    ]
    if contract.get("output_format_rules") != expected_output_format_rules:
        fail("output_format_rules do not match the default-HTML contract", errors)

    expected_visual_states = ["verified", "contextualized", "synthetic", "rejected"]
    if contract.get("visual_claim_states") != expected_visual_states:
        fail("visual_claim_states do not match the visual evidence protocol", errors)

    expected_visual_fallback = [
        "verified-source-visual",
        "non-person-conceptual-visual",
        "no-visual",
    ]
    if contract.get("visual_fallback_order") != expected_visual_fallback:
        fail("visual_fallback_order does not match the visual evidence protocol", errors)

    expected_visual_communication_rules = [
        "reader-job-required",
        "prose-alternative-comparison",
        "deletion-test",
        "least-complex-faithful-form",
        "source-backed-encoding",
        "honest-geometry-and-scale",
        "functional-color-semantics",
        "no-color-only-meaning",
        "adjacent-context-and-source",
        "responsive-render-verification",
    ]
    if contract.get("visual_communication_rules") != expected_visual_communication_rules:
        fail("visual_communication_rules do not match the visual communication contract", errors)

    expected_natural_structure_rules = [
        "progressive-disclosure-is-a-relationship",
        "content-specific-headings",
        "visuals-only-when-useful",
        "no-method-labels-by-default",
        "avoid-mechanical-symmetry",
        "visible-structure-classification",
        "heading-proposition-map",
        "heading-only-readback",
        "concrete-object-action-result-expression",
    ]
    if contract.get("natural_structure_rules") != expected_natural_structure_rules:
        fail("natural_structure_rules do not match the anti-template contract", errors)

    expected_title_design_rules = [
        "concrete-anchor",
        "one-core-relationship",
        "evidence-calibrated-verb",
        "natural-not-formulaic",
        "no-deceptive-clickbait",
        "three-angle-candidate-generation",
        "information-value-selection",
        "verified-result-over-generic-hook",
        "subtitle-adds-distinct-information",
        "opening-fulfills-title-promise",
    ]
    if contract.get("title_design_rules") != expected_title_design_rules:
        fail("title_design_rules do not match the title design contract", errors)

    output_path = ROOT / "references" / "output-standards.md"
    if output_path.exists():
        output_text = output_path.read_text(encoding="utf-8")
        required_structure_terms = [
            "### Visible Structure Must Carry Information",
            "### Make Value Expressions Concrete",
            "content-bearing",
            "navigation-only",
            "decorative",
            "heading proposition map",
            "Heading-only readback",
            "dominant language of the primary source document",
            "The language in which the user writes the request is not, by itself",
            "Do not translate or switch languages merely because the prompt",
            "specific object -> reader-relevant action or change -> observable result",
        ]
        for term in required_structure_terms:
            if term not in output_text:
                fail(f"references/output-standards.md missing required structure rule: {term}", errors)
    else:
        fail("missing references/output-standards.md", errors)

    signal_path = ROOT / "references" / "signal-processing.md"
    if signal_path.exists():
        signal_text = signal_path.read_text(encoding="utf-8")
        required_signal_headings = [
            "## Signal Register",
            "## Mandatory Decision Flow",
            "## Signal Families And Context Tests",
            "## Hard Failure Override",
            "## Action Selection Rules",
            "## Verification Record",
        ]
        for heading in required_signal_headings:
            if heading not in signal_text:
                fail(f"references/signal-processing.md missing heading: {heading}", errors)
        required_signal_terms = [
            "Information-empty scaffolding",
            "the reader learns only that content is supposedly important",
            "heading-only readback",
        ]
        for term in required_signal_terms:
            if term not in signal_text:
                fail(f"references/signal-processing.md missing required structure signal: {term}", errors)

    visual_path = ROOT / "references" / "visual-evidence.md"
    if visual_path.exists():
        visual_text = visual_path.read_text(encoding="utf-8")
        required_visual_headings = [
            "## Visual Claim Inventory",
            "## Source Hierarchy",
            "## Mandatory Decision Flow",
            "## Real-Person And Real-Event Hard Gate",
            "## Generated And Conceptual Visuals",
            "## Captions And Attribution",
            "## Final Verification",
        ]
        for heading in required_visual_headings:
            if heading not in visual_text:
                fail(f"references/visual-evidence.md missing heading: {heading}", errors)

        required_visual_terms = [
            "Search-result previews",
            "does not by itself verify",
            "Do not generate a realistic likeness",
            "visible nearby label",
        ]
        for term in required_visual_terms:
            if term not in visual_text:
                fail(f"references/visual-evidence.md missing required rule: {term}", errors)
    else:
        fail("missing references/visual-evidence.md", errors)

    visual_decision_path = ROOT / "references" / "visual-decision.md"
    if visual_decision_path.exists():
        visual_decision_text = visual_decision_path.read_text(encoding="utf-8")
        required_visual_decision_headings = [
            "## Valid Reader Jobs",
            "## Mandatory Decision",
            "## Decision States",
            "## Exit Check",
        ]
        for heading in required_visual_decision_headings:
            if heading not in visual_decision_text:
                fail(f"references/visual-decision.md missing heading: {heading}", errors)
        required_visual_decision_terms = [
            "the reader reaches the correct judgment with less effort",
            "Apply the deletion test",
            "no-visual",
            "retain-visual",
            "asset-visual",
            "A retained visual may not be",
        ]
        for term in required_visual_decision_terms:
            if term not in visual_decision_text:
                fail(f"references/visual-decision.md missing required rule: {term}", errors)
    else:
        fail("missing references/visual-decision.md", errors)

    visual_communication_path = ROOT / "references" / "visual-communication.md"
    if visual_communication_path.exists():
        visual_communication_text = visual_communication_path.read_text(encoding="utf-8")
        required_visual_communication_headings = [
            "## Form Selection",
            "## Visual Specification",
            "## Chart Integrity",
            "## Color Encoding",
            "## Layout And Non-Chart Elements",
            "## Scenario Adaptation",
            "## Rule Levels",
            "## Final Verification",
            "## Industry Basis",
        ]
        for heading in required_visual_communication_headings:
            if heading not in visual_communication_text:
                fail(f"references/visual-communication.md missing heading: {heading}", errors)

        required_visual_communication_terms = [
            "visual-decision.md",
            "Start quantitative bar axes at zero",
            "Recompute and verify every derived annotation",
            "Do not use 3D",
            "Do not use a second axis unless",
            "Color must carry a defined role",
            "Red versus green alone is insufficient",
            "A heading plus one sentence is not enough to justify a card",
            "Hard failures",
            "Review signals",
        ]
        for term in required_visual_communication_terms:
            if term not in visual_communication_text:
                fail(f"references/visual-communication.md missing required rule: {term}", errors)
    else:
        fail("missing references/visual-communication.md", errors)

    title_path = ROOT / "references" / "title-design.md"
    if title_path.exists():
        title_text = title_path.read_text(encoding="utf-8")
        required_title_headings = [
            "## Core Construction",
            "## Candidate Selection",
            "## Mandatory Decision Flow",
            "## Scenario Guidance",
            "## Evidence And Tone Boundaries",
            "## Prohibited Outputs",
            "## Title And Subtitle",
            "## Preserve Or Rewrite",
            "## Final Verification",
        ]
        for heading in required_title_headings:
            if heading not in title_text:
                fail(f"references/title-design.md missing heading: {heading}", errors)

        required_title_terms = [
            "concrete anchor",
            "strongest source-supported relationship",
            "not a fixed sentence template",
            "opening must promptly fulfill",
            "Deceptive or clickbait titles are a hard failure",
            "title-to-body check",
            "Generate at least three internal candidates",
            "Information value",
            "lower-information rhetorical hook",
        ]
        for term in required_title_terms:
            if term not in title_text:
                fail(f"references/title-design.md missing required rule: {term}", errors)
    else:
        fail("missing references/title-design.md", errors)


def check_runtime_portability(contract: dict, errors: list[str]) -> None:
    profiles = load_json(MODULE_PROFILES_PATH, errors)
    if not isinstance(profiles, dict):
        return
    runtime_rules = load_json(RUNTIME_RULES_PATH, errors)
    if not isinstance(runtime_rules, dict):
        return

    modules = profiles.get("modules")
    if not isinstance(modules, dict) or not modules:
        fail("module profiles must define a non-empty modules object", errors)
        return

    module_ids = set(modules)
    load_order = profiles.get("load_order", [])
    if len(load_order) != len(set(load_order)) or set(load_order) != module_ids:
        fail("module profile load_order must contain every module exactly once", errors)

    if runtime_rules.get("schema_version") != 1:
        fail("runtime-rules.json must use schema_version 1", errors)
    execution_gates = runtime_rules.get("execution_gates")
    if not isinstance(execution_gates, list):
        fail("runtime-rules.json must define execution gates", errors)
        execution_gates = []
    gate_ids = [item.get("id") for item in execution_gates if isinstance(item, dict)]
    if gate_ids != contract.get("mandatory_execution_gates"):
        fail("runtime execution gates do not match the skill contract", errors)
    for item in execution_gates:
        if not isinstance(item, dict) or not all(
            isinstance(item.get(key), str) and item[key].strip()
            for key in ("id", "required_record", "exit_condition")
        ):
            fail("runtime execution gate lacks a record or exit condition", errors)
    core_rules = runtime_rules.get("core")
    module_rules = runtime_rules.get("modules")
    if not isinstance(core_rules, list) or not core_rules:
        fail("runtime-rules.json must define non-empty core rules", errors)
        core_rules = []
    if not isinstance(module_rules, dict):
        fail("runtime-rules.json must define module rule groups", errors)
        module_rules = {}
    rule_ids: list[str] = []

    def check_rule_group(label: str, items: object) -> None:
        if not isinstance(items, list) or not items:
            fail(f"runtime rule group {label} must be non-empty", errors)
            return
        for item in items:
            if not isinstance(item, dict):
                fail(f"runtime rule group {label} contains a non-object", errors)
                continue
            rule_id = item.get("id")
            instruction = item.get("instruction")
            if not isinstance(rule_id, str) or not rule_id.strip():
                fail(f"runtime rule group {label} contains an invalid id", errors)
            else:
                rule_ids.append(rule_id)
            if not isinstance(instruction, str) or len(instruction.strip()) < 20:
                fail(f"runtime rule {rule_id!r} lacks an actionable instruction", errors)
            if not isinstance(item.get("allow_not_applicable", False), bool):
                fail(f"runtime rule {rule_id!r} has invalid applicability metadata", errors)

    check_rule_group("core", core_rules)
    scenario_module_ids = set(profiles.get("scenario_modules", {}).values())
    for module_id in sorted(module_ids - scenario_module_ids):
        check_rule_group(module_id, module_rules.get(module_id))
    unknown_rule_groups = set(module_rules) - (module_ids - scenario_module_ids)
    if unknown_rule_groups:
        fail(f"runtime rules contain unknown or scenario groups: {sorted(unknown_rule_groups)}", errors)
    if len(rule_ids) != len(set(rule_ids)):
        fail("runtime rule ids must be globally unique", errors)
    inventory = contract.get("runtime_rule_inventory", {})
    actual_inventory = {
        "core": [item.get("id") for item in core_rules if isinstance(item, dict)],
        "modules": {
            module_id: [item.get("id") for item in module_rules[module_id] if isinstance(item, dict)]
            for module_id in sorted(module_rules)
            if isinstance(module_rules[module_id], list)
        },
    }
    if inventory.get("core") != actual_inventory["core"] or inventory.get("modules") != actual_inventory["modules"]:
        fail("runtime rule catalog differs from the versioned contract inventory", errors)

    for module_id, definition in modules.items():
        if not isinstance(definition, dict):
            fail(f"module profile {module_id} must be an object", errors)
            continue
        relative = definition.get("path")
        if not relative or not (ROOT / relative).is_file():
            fail(f"module profile references missing file: {module_id} -> {relative}", errors)
        if not definition.get("purpose"):
            fail(f"module profile {module_id} has no purpose", errors)

    def check_module_ids(label: str, values: object) -> None:
        if not isinstance(values, list):
            fail(f"module profile {label} must be an array", errors)
            return
        unknown = set(values) - module_ids
        if unknown:
            fail(f"module profile {label} contains unknown modules: {sorted(unknown)}", errors)

    check_module_ids("always_modules", profiles.get("always_modules"))
    check_module_ids("artifact_modules", profiles.get("artifact_modules"))
    for label, mapping in (
        ("operation_modules", profiles.get("operation_modules", {})),
        ("risk_modules", profiles.get("risk_modules", {})),
        ("feature_modules", profiles.get("feature_modules", {})),
    ):
        if not isinstance(mapping, dict):
            fail(f"module profile {label} must be an object", errors)
            continue
        for key, values in mapping.items():
            check_module_ids(f"{label}.{key}", values)

    routes = {route["id"]: route["reference"] for route in contract.get("primary_routes", [])}
    scenario_modules = profiles.get("scenario_modules", {})
    if set(scenario_modules) != set(routes):
        fail("module profile scenarios must match all six contract routes", errors)
    else:
        for scenario, module_id in scenario_modules.items():
            definition = modules.get(module_id, {})
            if definition.get("path") != routes[scenario]:
                fail(f"module profile route path mismatch for {scenario}", errors)

    always_paths = {
        modules[module_id]["path"]
        for module_id in profiles.get("always_modules", [])
        if module_id in modules
    }
    if always_paths != set(contract.get("shared_modules", [])):
        fail("module profile always_modules must match contract shared_modules", errors)

    conditional_paths = {
        module.get("reference") for module in contract.get("conditional_modules", [])
    }
    profile_paths = {definition.get("path") for definition in modules.values()}
    if not conditional_paths.issubset(profile_paths):
        fail("conditional contract modules are not all resolvable by module profiles", errors)

    if profiles.get("artifact_modules") != ["format-decision", "visual-decision", "reader-validation"]:
        fail("artifact modules must load format, visual decision, and reader validation", errors)
    features = profiles.get("feature_modules", {})
    if features.get("html-output") != ["html-output"]:
        fail("html-output must load only as a selected-format feature", errors)
    if features.get("visual-retained") != ["visual-decision", "visual-communication"]:
        fail("visual-retained must preserve decision and implementation modules", errors)
    if features.get("visual-asset") != [
        "visual-decision",
        "visual-communication",
        "visual-evidence",
    ]:
        fail("visual-asset must preserve decision, implementation, and evidence modules", errors)
    if features.get("maintenance") != ["skill-maintenance"]:
        fail("skill maintenance must load only the maintenance module", errors)

    runtime = contract.get("runtime_loading", {})
    if runtime.get("profile") != "config/module-profiles.json":
        fail("runtime loading contract does not name module-profiles.json", errors)
    if runtime.get("resolver") != "scripts/resolve_modules.py":
        fail("runtime loading contract does not name resolve_modules.py", errors)
    if runtime.get("rules") != "config/runtime-rules.json":
        fail("runtime loading contract does not name runtime-rules.json", errors)
    if runtime.get("capability_reduction_allowed") is not False:
        fail("runtime loading contract must forbid capability reduction", errors)
    if runtime.get("active_scenario_contract_extracted_from_canonical_module") is not True:
        fail("runtime loading contract must require canonical active-scenario extraction", errors)
    for key in (
        "task_bundle_generated_at_init",
        "module_manifest_generated_at_init",
        "selected_rule_review_required",
        "source_hashes_verified_before_delivery",
    ):
        if runtime.get(key) is not True:
            fail(f"runtime loading contract must enable {key}", errors)
    if runtime.get("format_decision_module") != "references/format-decision.md":
        fail("runtime loading contract must name format-decision.md", errors)
    if runtime.get("html_implementation_loaded_only_when_selected") is not True:
        fail("runtime loading contract must conditionally load HTML implementation", errors)

    required_capabilities = {
        "six-scenario-routing",
        "create-rewrite-diagnose-compare",
        "source-dominant-language-selection",
        "explicit-format-override-and-html-default",
        "meaning-preserving-revision",
        "evidence-and-certainty-calibration",
        "information-bearing-title-design",
        "visual-need-decision",
        "chart-diagram-table-color-and-layout-integrity",
        "visual-provenance-and-synthetic-disclosure",
        "self-contained-html-rendering",
        "native-non-html-format-preservation",
        "signal-based-diagnosis",
        "hard-gate-and-reader-outcome-evaluation",
        "fail-closed-runtime-contract",
        "four-way-independent-reader-validation",
        "vendor-neutral-command-adapters",
        "task-specific-runtime-bundle",
        "versioned-runtime-rule-inventory",
        "artifact-bound-semantic-review",
        "source-result-revalidated-reader-aggregate",
        "high-risk-pre-action-independent-judge",
    }
    if set(contract.get("retained_capabilities", [])) != required_capabilities:
        fail("retained_capabilities does not preserve the complete runtime capability set", errors)

    resolver = ROOT / "scripts" / "resolve_modules.py"
    resolver_cases = [
        (
            ["--scenario", "business", "--operation", "create", "--artifact", "--output-format", "native", "--visual", "none"],
            {"format-decision", "visual-decision", "reader-validation", "scenario-business"},
            {"html-output", "visual-communication", "visual-evidence"},
        ),
        (
            ["--scenario", "analysis", "--operation", "rewrite", "--artifact", "--output-format", "html", "--visual", "retained"],
            {"diagnosis-and-revision", "format-decision", "html-output", "visual-decision", "reader-validation", "visual-communication", "scenario-analysis"},
            {"visual-evidence"},
        ),
        (
            ["--scenario", "news", "--operation", "create", "--artifact", "--visual", "asset"],
            {"visual-decision", "reader-validation", "visual-communication", "visual-evidence", "scenario-news"},
            set(),
        ),
        (
            ["--scenario", "technical", "--operation", "compare", "--chat-output", "--risk", "high"],
            {"diagnosis-and-revision", "evaluation", "scenario-technical"},
            {"html-output"},
        ),
        (
            [
                "--scenario", "analysis", "--operation", "compare", "--artifact",
                "--risk", "high", "--output-format", "html", "--title",
                "--visual", "asset", "--evaluate", "--portability", "--maintenance",
            ],
            {
                "scenario-analysis", "diagnosis-and-revision", "evaluation",
                "html-output", "visual-evidence", "agent-portability", "skill-maintenance",
            },
            set(),
        ),
    ]
    for arguments, required_ids, forbidden_ids in resolver_cases:
        completed = subprocess.run(
            [sys.executable, str(resolver), *arguments, "--emit", "json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            fail(f"module resolver smoke test failed: {completed.stderr.strip()}", errors)
            continue
        try:
            result = json.loads(completed.stdout)
            resolved_ids = {module["id"] for module in result["modules"]}
            active_contract = result["active_scenario_contract"]
            runtime_contract = result["runtime_enforcement"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            fail(f"module resolver returned invalid JSON: {exc}", errors)
            continue
        for field in (
            "source",
            "reader_task",
            "required_content",
            "recommended_relationship",
            "evidence_requirements",
            "common_failures",
            "acceptance_questions",
        ):
            if not isinstance(active_contract.get(field), str) or not active_contract[field].strip():
                fail(f"module resolver active scenario contract missing {field}", errors)
        if runtime_contract != {
            "required": True,
            "contract_script": "scripts/runtime_contract.py",
            "reader_review_script": "scripts/reader_review.py",
            "reader_review_required_for_artifacts": bool(result["task_profile"]["finished_artifact"]),
            "verification_receipt_required": True,
            "task_bundle_required": True,
            "module_manifest_required": True,
        }:
            fail("module resolver does not preserve runtime enforcement", errors)
        if result.get("schema_version") != 2:
            fail("module resolver must use schema_version 2", errors)
        required_rule_ids = result.get("required_rule_ids")
        if not isinstance(required_rule_ids, list) or not required_rule_ids:
            fail("module resolver did not emit required runtime rules", errors)
        elif len(required_rule_ids) != len(set(required_rule_ids)):
            fail("module resolver emitted duplicate runtime rule ids", errors)
        manifest = result.get("module_manifest", {})
        if manifest.get("required_rule_ids") != required_rule_ids:
            fail("module manifest does not preserve the selected runtime rules", errors)
        if manifest.get("runtime_rule_applicability") != result.get("runtime_rule_applicability"):
            fail("module manifest does not preserve runtime rule applicability", errors)
        if manifest.get("required_execution_gate_ids") != contract.get("mandatory_execution_gates"):
            fail("module manifest does not preserve all execution gates", errors)
        if manifest.get("execution_gates") != execution_gates:
            fail("module manifest does not preserve execution gate records and exit conditions", errors)
        if not result.get("task_profile", {}).get("reader_profile"):
            fail("module resolver task profile has no target reader", errors)
        if manifest.get("bundle_characters", 0) <= 0:
            fail("module resolver did not measure the task bundle", errors)
        bundle_size = manifest.get("bundle_bytes", 0)
        max_bundle_size = runtime.get("task_bundle_max_bytes", 24576)
        if bundle_size > max_bundle_size:
            fail(
                f"resolved task bundle exceeds the {max_bundle_size}-byte budget: {bundle_size}",
                errors,
            )
        combined_size = len((ROOT / "SKILL.md").read_bytes()) + bundle_size
        max_combined_size = runtime.get("combined_entrypoint_and_bundle_max_bytes", 40960)
        if combined_size > max_combined_size:
            fail(
                f"entrypoint plus task bundle exceeds the {max_combined_size}-byte budget: {combined_size}",
                errors,
            )
        if "runtime-enforcement" not in resolved_ids:
            fail("module resolver omitted runtime-enforcement", errors)
        missing = required_ids - resolved_ids
        forbidden = forbidden_ids & resolved_ids
        if missing:
            fail(f"module resolver omitted required modules: {sorted(missing)}", errors)
        if forbidden:
            fail(f"module resolver loaded unnecessary modules: {sorted(forbidden)}", errors)

    adapters = load_json(AGENT_ADAPTERS_PATH, errors)
    if isinstance(adapters, dict):
        protocol = adapters.get("protocol", {})
        if not isinstance(protocol, dict):
            fail("agent adapters must define a protocol object", errors)
        else:
            for required in (
                "runtime_init",
                "semantic_review_binding",
                "reader_review_orchestration",
                "reader_review_delivery_gate",
                "reader_review_incomplete_draft_gate",
                "external_action_preflight",
                "delivery_precondition",
            ):
                if not str(protocol.get(required, "")).strip():
                    fail(f"agent adapter protocol missing enforcement term: {required}", errors)
        adapter_map = adapters.get("adapters", {})
        required_adapters = {"codex", "command-stdin", "command-files", "manual"}
        if not isinstance(adapter_map, dict) or set(adapter_map) < required_adapters:
            fail("agent adapters must preserve codex, generic command, and manual modes", errors)
        else:
            codex = adapter_map["codex"]
            command = codex.get("command", [])
            if codex.get("mode") != "command" or not isinstance(command, list):
                fail("codex adapter must use an argv command array", errors)
            else:
                joined = " ".join(str(part) for part in command)
                for required in ("{model}", "{output_file}", "--ephemeral", "read-only"):
                    if required not in joined:
                        fail(f"codex adapter missing isolation or output term: {required}", errors)
                for forbidden in ("bash -c", "bash -lc", "sh -c", "dangerously-bypass"):
                    if forbidden in joined:
                        fail(f"codex adapter contains unsafe shell or sandbox term: {forbidden}", errors)
            if adapter_map["manual"].get("mode") != "manual":
                fail("manual adapter must use manual mode", errors)
            for adapter_id in ("command-stdin", "command-files"):
                generic = adapter_map[adapter_id]
                if generic.get("mode") != "command" or not generic.get("command_env"):
                    fail(f"{adapter_id} must use an environment-supplied argv array", errors)

    portability_path = ROOT / "references" / "agent-portability.md"
    if portability_path.is_file():
        portability_text = portability_path.read_text(encoding="utf-8")
        for heading in (
            "## One Canonical Source",
            "## Adapter Contract",
            "## Deterministic Module Resolution",
            "## Evaluation Protocol",
            "## Acceptance",
        ):
            if heading not in portability_text:
                fail(f"references/agent-portability.md missing heading: {heading}", errors)
        for term in (
            "runtime_contract.py init",
            "runtime_contract.py bind-review",
            "runtime_contract.py check-action",
            "runtime_contract.py verify",
            "reader_review.py prepare",
            "reader_review.py aggregate",
            "exactly four fresh subagents",
            "stop after round 3",
            "runtime_contract.py present-draft",
            "review-incomplete-draft",
            "status=pass",
            "advisory-only",
            "machine-checked return precondition",
        ):
            if term not in portability_text:
                fail(f"references/agent-portability.md missing enforcement term: {term}", errors)
    else:
        fail("missing references/agent-portability.md", errors)

    runner = ROOT / "scripts" / "run_evals.py"
    completed = subprocess.run(
        [sys.executable, str(runner), "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if (
        completed.returncode != 0
        or "prepare" not in completed.stdout
        or "grade" not in completed.stdout
        or "matrix" not in completed.stdout
    ):
        fail("cross-agent evaluation runner help smoke test failed", errors)


def check_format_decision(errors: list[str]) -> None:
    path = ROOT / "references" / "format-decision.md"
    if not path.is_file():
        fail("missing references/format-decision.md", errors)
        return
    text = path.read_text(encoding="utf-8")
    for heading in (
        "## Output Format Decision",
        "## Portable Presentation Baseline",
        "## Exit Check",
    ):
        if heading not in text:
            fail(f"references/format-decision.md missing heading: {heading}", errors)
    for term in (
        "Otherwise, create a self-contained HTML document",
        "Preserve the principles, not the HTML implementation",
        "no HTML marker, local",
        "Load [html-output.md](html-output.md) only for HTML",
    ):
        if term not in text:
            fail(f"references/format-decision.md missing required rule: {term}", errors)


def check_runtime_enforcement(contract: dict, errors: list[str]) -> None:
    runtime = contract.get("runtime_enforcement")
    if not isinstance(runtime, dict):
        fail("contract missing runtime_enforcement", errors)
        return

    expected_true = (
        "required_for_every_task",
        "external_action_guard_required",
        "action_preflight_receipt_required",
        "reader_validation_required_for_finished_artifacts",
        "reader_validation_context_isolation_required",
        "reader_validation_parallel_required",
            "reader_validation_all_dimensions_must_pass",
            "reader_validation_rerun_all_after_change",
            "reader_validation_incomplete_draft_user_notice_required",
            "reader_validation_incomplete_draft_external_actions_blocked",
        "semantic_review_required",
        "runtime_rule_review_required",
        "runtime_rule_inventory_required",
        "nonwaivable_rule_enforcement_required",
        "execution_gate_review_required",
        "semantic_review_artifact_binding_required",
        "semantic_review_binding_receipt_required",
        "reader_review_aggregate_revalidates_source_results",
        "independent_judge_required_for_high_risk",
        "high_risk_action_preflight_judge_required",
        "module_manifest_full_execution_gate_contract_required",
        "verification_receipt_required",
        "fail_closed_on_missing_or_failed_receipt",
        "host_wrapper_required_for_absolute_enforcement",
    )
    for key in expected_true:
        if runtime.get(key) is not True:
            fail(f"runtime_enforcement must set {key}=true", errors)

    expected_lock = {
        "output-language",
        "output-format",
        "publication-target",
        "external-action",
        "publication-authorization",
    }
    if set(runtime.get("decision_lock", [])) != expected_lock:
        fail("runtime_enforcement decision_lock is incomplete", errors)
    if "publication-authorization-and-target-fidelity" not in contract.get("hard_gates", []):
        fail("hard_gates must include publication authorization and target fidelity", errors)
    if "independent-reader-validation" not in contract.get("hard_gates", []):
        fail("hard_gates must include independent reader validation", errors)
    if runtime.get("reader_validation_max_rounds") != 3:
        fail("runtime_enforcement must limit reader validation to three rounds", errors)
    if runtime.get("reader_validation_round_three_behavior") != "review-incomplete-draft-needs-user-decision":
        fail("runtime_enforcement must preserve the third-round user-decision draft behavior", errors)

    script_relative = runtime.get("contract_script")
    script = ROOT / str(script_relative)
    if script_relative != "scripts/runtime_contract.py" or not script.is_file():
        fail("runtime_enforcement does not reference scripts/runtime_contract.py", errors)
    else:
        completed = subprocess.run(
            [sys.executable, "-B", str(script), "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if (
            completed.returncode != 0
            or "present-draft" not in completed.stdout
            or "bind-review" not in completed.stdout
        ):
            fail(f"runtime_contract.py --help failed: {completed.stderr.strip()}", errors)
        action_help = subprocess.run(
            [sys.executable, "-B", str(script), "check-action", "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if action_help.returncode != 0 or "--judge-result" not in action_help.stdout:
            fail("runtime_contract.py check-action must require a high-risk judge input", errors)
        runtime_source = script.read_text(encoding="utf-8")
        for term in (
            "semantic_binding_receipt_path",
            "validate_semantic_binding_receipt",
            "independent_judge_sha256",
        ):
            if term not in runtime_source:
                fail(f"runtime_contract.py missing enforcement term: {term}", errors)
        init_help = subprocess.run(
            [sys.executable, "-B", str(script), "init", "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if (
            init_help.returncode != 0
            or "--task-bundle" not in init_help.stdout
            or "--module-manifest" not in init_help.stdout
        ):
            fail("runtime_contract.py init does not expose task-bundle controls", errors)

    tests_relative = runtime.get("unit_tests")
    if tests_relative != "tests/test_runtime_contract.py" or not (ROOT / str(tests_relative)).is_file():
        fail("runtime_enforcement does not reference its unit tests", errors)
    resolver_tests = runtime.get("module_resolver_unit_tests")
    if resolver_tests != "tests/test_module_resolver.py" or not (ROOT / str(resolver_tests)).is_file():
        fail("runtime_enforcement does not reference module resolver unit tests", errors)

    reader_script_relative = runtime.get("reader_review_script")
    reader_script = ROOT / str(reader_script_relative)
    if reader_script_relative != "scripts/reader_review.py" or not reader_script.is_file():
        fail("runtime_enforcement does not reference scripts/reader_review.py", errors)
    else:
        completed = subprocess.run(
            [sys.executable, "-B", str(reader_script), "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0 or "prepare" not in completed.stdout or "aggregate" not in completed.stdout:
            fail("reader_review.py help smoke test failed", errors)
        reader_source = reader_script.read_text(encoding="utf-8")
        for term in ("validate_result(result, manifest, packet)", "original_all_pass", "original_issues"):
            if term not in reader_source:
                fail(f"reader_review.py missing source-result revalidation term: {term}", errors)

    reader_schema_relative = runtime.get("reader_review_schema")
    reader_schema = ROOT / str(reader_schema_relative)
    if reader_schema_relative != "config/reader-review-result.schema.json" or not reader_schema.is_file():
        fail("runtime_enforcement does not reference the reader review result schema", errors)
    else:
        schema = load_json(reader_schema, errors)
        dimensions = schema.get("properties", {}).get("dimension", {}).get("enum", []) if isinstance(schema, dict) else []
        if dimensions != ["no-context", "readability", "source-reliability", "structure-visual"]:
            fail("reader review result schema does not preserve the four dimensions", errors)

    reference = ROOT / "references" / "runtime-enforcement.md"
    if not reference.is_file():
        fail("missing references/runtime-enforcement.md", errors)
    else:
        text = reference.read_text(encoding="utf-8")
        for term in (
            "Decision derivation",
            "Immutable lock",
            "Action authorization",
            "Deliverable verification",
            "runtime_contract.py init",
            "runtime_contract.py bind-review",
            "runtime_contract.py check-action",
            "runtime_contract.py verify",
            "status=pass",
            "cannot provide an absolute execution guarantee",
        ):
            if term not in text:
                fail(f"runtime-enforcement.md missing required term: {term}", errors)

    reader_reference = ROOT / "references" / "reader-validation.md"
    if not reader_reference.is_file():
        fail("missing references/reader-validation.md", errors)
    else:
        reader_text = reader_reference.read_text(encoding="utf-8")
        for term in (
            "exactly four fresh",
            "no-context",
            "readability",
            "source-reliability",
            "structure-visual",
            "parallel batch",
            "round 3",
            "needs-user-decision",
            "review-incomplete-draft",
            "runtime_contract.py present-draft",
            "reader_review.py prepare",
            "reader_review.py aggregate",
            "--reader-review-aggregate",
            "four original result",
        ):
            if term not in reader_text:
                fail(f"reader-validation.md missing required term: {term}", errors)


def check_html_output(contract: dict, errors: list[str]) -> None:
    html_contract = contract.get("html_output")
    if not isinstance(html_contract, dict):
        fail("contract missing html_output module", errors)
        return

    if html_contract.get("external_skill_dependency") is not False:
        fail("html_output must declare external_skill_dependency false", errors)

    paths = [
        html_contract.get("reference"),
        *html_contract.get("scaffold_scripts", []),
        html_contract.get("validator"),
        html_contract.get("template"),
        *html_contract.get("bundled_fonts", []),
        *html_contract.get("third_party_notices", []),
        *html_contract.get("optional_runtimes", []),
    ]
    for relative in paths:
        if not relative:
            fail("html_output contains an empty resource path", errors)
            continue
        path = ROOT / relative
        if not path.is_file():
            fail(f"html_output references missing file: {relative}", errors)
        elif path.stat().st_size == 0:
            fail(f"html_output resource is empty: {relative}", errors)

    conditional = {
        module.get("id"): module.get("reference")
        for module in contract.get("conditional_modules", [])
    }
    if conditional.get("html-output") != html_contract.get("reference"):
        fail("conditional_modules does not route self-contained HTML to html-output", errors)

    reference_path = ROOT / str(html_contract.get("reference", ""))
    if reference_path.is_file():
        reference_text = reference_path.read_text(encoding="utf-8")
        required_headings = [
            "## Output Contract",
            "## Plan Before Building",
            "## Scaffold",
            "## Visual System",
            "## Citations And Sources",
            "## Charts And Diagrams",
            "## Responsive, Accessible, And Print-Safe Output",
            "## Verification",
            "## Acceptance Questions",
        ]
        for heading in required_headings:
            if heading not in reference_text:
                fail(f"references/html-output.md missing heading: {heading}", errors)
        required_terms = [
            "no dependency on a separately",
            "format-decision.md",
            "<!-- Generated by Reader's Seat -->",
            "390px",
            "validate_html_output.py",
            "body scroll width does not exceed the viewport",
        ]
        for term in required_terms:
            if term not in reference_text:
                fail(f"references/html-output.md missing required rule: {term}", errors)

    template_path = ROOT / str(html_contract.get("template", ""))
    if template_path.is_file():
        template_text = template_path.read_text(encoding="utf-8")
        if not template_text.startswith("<!-- Generated by Reader's Seat -->\n<!DOCTYPE html>"):
            fail("HTML template has an invalid line-1 marker or doctype", errors)
        for term in (
            '<meta name="viewport"',
            '<html lang="{{LANG}}">',
            "@media (max-width:",
            "@media print",
            ".table-wrap",
            "./_shared/fonts/WorkSans-Regular.ttf",
        ):
            if term not in template_text:
                fail(f"HTML template missing required structure: {term}", errors)

    for relative in html_contract.get("scaffold_scripts", []):
        path = ROOT / relative
        if not path.is_file():
            continue
        script_text = path.read_text(encoding="utf-8")
        if "new-html-report" in path.name and "LANG" not in script_text.upper():
            fail(f"{relative} does not require the locked output language", errors)
        for forbidden in (
            "/skills/html-report/",
            "html-report/canvas-fonts",
            "html-report/assets/js",
        ):
            if forbidden in script_text:
                fail(f"{relative} depends on external html-report asset: {forbidden}", errors)

    notices_path = ROOT / "assets" / "html" / "THIRD_PARTY_NOTICES.md"
    if notices_path.is_file():
        notices_text = notices_path.read_text(encoding="utf-8")
        for project in ("Work Sans", "Red Hat Mono", "Apache ECharts", "Mermaid"):
            if project not in notices_text:
                fail(f"third-party notices missing project: {project}", errors)


def check_evals(contract: dict, errors: list[str]) -> None:
    trigger_data = load_json(ROOT / "evals" / "trigger-cases.json", errors)
    behavior_data = load_json(ROOT / "evals" / "behavior-cases.json", errors)
    cross_agent_data = load_json(ROOT / "evals" / "cross-agent-cases.json", errors)
    judge_schema = load_json(ROOT / "evals" / "judge-output.schema.json", errors)
    if not all(
        isinstance(value, dict)
        for value in (trigger_data, behavior_data, cross_agent_data, judge_schema)
    ):
        return

    all_cases = trigger_data.get("should_trigger", []) + trigger_data.get("should_not_trigger", [])
    behavior_cases = behavior_data.get("cases", [])
    cross_agent_cases = cross_agent_data.get("cases", [])
    ids = [case.get("id") for case in all_cases + behavior_cases + cross_agent_cases]
    if None in ids or len(ids) != len(set(ids)):
        fail("eval case IDs must be present and unique", errors)

    route_ids = {route["id"] for route in contract.get("primary_routes", [])}
    covered = {case.get("scenario") for case in behavior_cases}
    missing = route_ids - covered
    if missing:
        fail(f"behavior cases do not cover routes: {sorted(missing)}", errors)

    behavior_ids = {case.get("id") for case in behavior_cases}
    required_behavior_ids = set(contract.get("required_behavior_case_ids", []))
    missing_behavior_ids = required_behavior_ids - behavior_ids
    if missing_behavior_ids:
        fail(f"missing required behavior cases: {sorted(missing_behavior_ids)}", errors)

    for case in behavior_cases:
        for field in ("id", "scenario", "operation", "prompt", "must_preserve", "expected_behaviors", "forbidden_behaviors"):
            if field not in case or case[field] in (None, "", []):
                fail(f"behavior case {case.get('id', '<unknown>')} missing {field}", errors)

    if len(cross_agent_cases) != 12:
        fail(f"cross-agent suite must contain 12 frozen cases, found {len(cross_agent_cases)}", errors)
    route_counts = {route_id: 0 for route_id in route_ids}
    required_cross_fields = (
        "id",
        "scenario",
        "operation",
        "artifact",
        "risk",
        "title",
        "visual",
        "request",
        "source_material",
        "immutable_facts",
        "required_behaviors",
        "forbidden_behaviors",
        "hard_checks",
    )
    for case in cross_agent_cases:
        case_id = case.get("id", "<unknown>")
        for field in required_cross_fields:
            if field not in case or case[field] in (None, "", []):
                if field not in {"artifact", "title"}:
                    fail(f"cross-agent case {case_id} missing {field}", errors)
        scenario = case.get("scenario")
        if scenario not in route_counts:
            fail(f"cross-agent case {case_id} has invalid scenario: {scenario}", errors)
        else:
            route_counts[scenario] += 1
        if case.get("operation") not in {"create", "rewrite", "diagnose", "compare"}:
            fail(f"cross-agent case {case_id} has invalid operation", errors)
        if case.get("risk") not in {"standard", "high"}:
            fail(f"cross-agent case {case_id} has invalid risk", errors)
        if case.get("visual") not in {"none", "decision", "retained", "asset"}:
            fail(f"cross-agent case {case_id} has invalid visual state", errors)
        hard_checks = case.get("hard_checks")
        if not isinstance(hard_checks, dict) or not hard_checks.get("must_contain"):
            fail(f"cross-agent case {case_id} needs deterministic must_contain checks", errors)
        if isinstance(hard_checks, dict) and not hard_checks.get("must_not_contain"):
            fail(f"cross-agent case {case_id} needs deterministic must_not_contain checks", errors)
        if isinstance(hard_checks, dict):
            for alternatives in hard_checks.get("must_contain_any", []):
                if not isinstance(alternatives, list) or not alternatives:
                    fail(f"cross-agent case {case_id} has an invalid must_contain_any group", errors)
    if any(count != 2 for count in route_counts.values()):
        fail(f"cross-agent suite must contain two cases per route: {route_counts}", errors)

    rubric_path = ROOT / "evals" / "judge-rubric.md"
    if rubric_path.is_file():
        rubric_text = rubric_path.read_text(encoding="utf-8")
        for heading in ("## Hard Gates", "## Reader Outcome"):
            if heading not in rubric_text:
                fail(f"judge rubric missing heading: {heading}", errors)
    else:
        fail("missing evals/judge-rubric.md", errors)

    schema_required = set(judge_schema.get("required", []))
    if schema_required != {"verdict", "hard_gates", "hard_failures", "reader_outcome", "summary"}:
        fail("judge output schema does not require the complete result contract", errors)

    evaluation = contract.get("cross_agent_evaluation", {})
    required_evaluation_paths = {
        "adapters": "config/agent-adapters.json",
        "runner": "scripts/run_evals.py",
        "cases": "evals/cross-agent-cases.json",
        "rubric": "evals/judge-rubric.md",
        "judge_schema": "evals/judge-output.schema.json",
    }
    for key, expected in required_evaluation_paths.items():
        if evaluation.get(key) != expected:
            fail(f"cross-agent evaluation contract has invalid {key}", errors)
    if evaluation.get("minimum_repetitions_for_stability_claim") != 3:
        fail("cross-agent stability claim must require three repetitions", errors)
    if evaluation.get("minimum_distinct_agents_for_cross_agent_claim") != 2:
        fail("cross-agent stability claim must require two distinct agents", errors)
    if evaluation.get("minimum_automated_judge_repetitions_for_stability_claim") != 2:
        fail("cross-agent stability claim must require two automated judge repetitions", errors)
    if evaluation.get("requires_semantic_judge") is not True:
        fail("cross-agent stability claim must require a semantic judge", errors)
    if evaluation.get("report_worst_run") is not True:
        fail("cross-agent evaluation must report the worst run", errors)


def main() -> int:
    errors: list[str] = []
    contract = load_json(CONTRACT_PATH, errors)
    if not isinstance(contract, dict):
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    check_skill_md(contract, errors)
    check_reference_links(errors)
    check_contract(contract, errors)
    check_runtime_portability(contract, errors)
    check_format_decision(errors)
    check_runtime_enforcement(contract, errors)
    check_html_output(contract, errors)
    check_evals(contract, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"FAIL: {len(errors)} issue(s)")
        return 1

    print(
        "PASS: static skill contract valid | "
        f"{contract['name']} {contract['skill_version']} | "
        f"{len(contract['primary_routes'])} routes | "
        f"{len(contract['output_standards'])} output standards | "
        "self-contained HTML"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
