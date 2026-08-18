#!/usr/bin/env python3
"""Create and verify a fail-closed Reader's Seat runtime contract."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
HTML_VALIDATOR = ROOT / "scripts" / "validate_html_output.py"

SCENARIOS = ("news", "technical", "product", "business", "analysis", "procedure")
OPERATIONS = ("create", "rewrite", "diagnose", "compare")
FORMATS = ("none", "chat", "html", "feishu", "lark", "word", "markdown", "plain-text", "slides", "other")
PUBLICATION_TARGETS = ("none", "feishu", "lark", "other")
EXTERNAL_ACTIONS = ("none", "publish", "overwrite", "replace")
VISUAL_STATES = ("none", "decision", "retained", "asset")
RISK_LEVELS = ("standard", "high")

BASE_SEMANTIC_GATES = (
    "critical-proposition-fidelity",
    "critical-evidence-coverage",
    "critical-number-and-definition-accuracy",
    "certainty-calibration",
    "information-empty-visible-structure",
    "scope-and-responsibility-fidelity",
    "action-boundary",
    "scenario-task-completeness",
)
TITLE_GATE = "title-content-fidelity"
VISUAL_GATES = (
    "visual-identity-and-provenance",
    "synthetic-visual-disclosure",
    "visual-purpose-and-form-fit",
    "visual-encoding-integrity",
    "visual-color-accessibility",
)


def fail(message: str, *, code: int = 2) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(code)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"missing file: {path}")
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"expected a JSON object in {path}")
    return value


def language_root(value: str) -> str:
    return value.strip().lower().split("-", 1)[0]


def validate_language_tag(value: str, field: str, *, allow_special: bool = False) -> str:
    normalized = value.strip().lower()
    if allow_special and normalized in {"mixed", "unknown"}:
        return normalized
    if not re.fullmatch(r"[a-z]{2,3}(?:-[a-z0-9]{2,8})*", normalized):
        fail(f"{field} must be a BCP-47-like language tag, got {value!r}")
    return normalized


def source_language(args: argparse.Namespace) -> tuple[str, dict | None]:
    declared = args.source_language.strip().lower()
    snapshot: dict | None = None
    if args.source_file:
        path = args.source_file.resolve()
        if not path.is_file():
            fail(f"source snapshot does not exist: {path}")
        actual_format = "html" if path.suffix.lower() in {".html", ".htm"} else "plain-text"
        visible_text, _ = extract_visible_text(path, actual_format)
        detected = dominant_language(visible_text)
        source = detected["detected"]
        if source in {"mixed", "unknown"} and declared == "none":
            fail(
                f"source snapshot language is {source}; provide --source-language and "
                "a documented selected-language decision"
            )
        if declared != "none":
            declared = validate_language_tag(declared, "source language", allow_special=True)
            if source not in {"mixed", "unknown"} and language_root(declared) != source:
                fail(
                    f"declared source language {declared} conflicts with snapshot language {source}"
                )
            if source in {"mixed", "unknown"}:
                source = declared
        snapshot = {
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "detected_language": detected,
        }
        return source, snapshot

    if declared == "none":
        fail("use --source-file when source prose is available, or provide --source-language")
    return validate_language_tag(declared, "source language", allow_special=True), snapshot


def derive_language(args: argparse.Namespace) -> tuple[str, str, str, dict | None]:
    source, snapshot = source_language(args)
    override = args.language_override.strip().lower()
    selected = args.selected_language.strip().lower()

    if override != "none":
        override = validate_language_tag(override, "language override")
        if selected != "none" and language_root(validate_language_tag(selected, "selected language")) != language_root(override):
            fail("selected language conflicts with the explicit language override")
        return override, "explicit-user-language-override", source, snapshot

    if source not in {"mixed", "unknown"}:
        if selected != "none" and language_root(validate_language_tag(selected, "selected language")) != language_root(source):
            fail("selected language conflicts with the source-dominant default")
        return source, "source-dominant-language-default", source, snapshot

    if selected == "none":
        fail("mixed or unknown source language requires --selected-language")
    if not args.language_reason.strip():
        fail("mixed or unknown source language requires --language-reason")
    return (
        validate_language_tag(selected, "selected language"),
        "documented-mixed-source-decision",
        source,
        snapshot,
    )


def derive_format(args: argparse.Namespace) -> tuple[str, str]:
    explicit = args.explicit_format
    existing = args.existing_format
    if args.channel == "chat":
        if explicit not in {"none", "chat"} or existing != "none":
            fail("chat channel conflicts with an artifact format signal")
        return "chat", "chat-only-request"
    if explicit == "chat":
        fail("artifact channel cannot use explicit chat format")
    if explicit != "none":
        return explicit, "explicit-user-format"
    if existing != "none":
        if existing == "chat":
            fail("an existing editable artifact cannot use chat format")
        return existing, "existing-target-format"
    return "html", "self-contained-html-default"


def semantic_gates(*, title: bool, visual: str) -> list[str]:
    gates = list(BASE_SEMANTIC_GATES)
    if title:
        gates.append(TITLE_GATE)
    if visual in {"retained", "asset"}:
        gates.extend(VISUAL_GATES)
    return gates


def lock_payload(contract: dict) -> dict:
    return {
        "task": contract["task"],
        "decisions": contract["decisions"],
        "required_semantic_gates": contract["required_semantic_gates"],
    }


def payload_hash(payload: dict) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def verify_contract_integrity(contract: dict) -> None:
    required = {"schema_version", "contract_id", "status", "task", "decisions", "required_semantic_gates", "lock_sha256"}
    missing = required - set(contract)
    if missing:
        fail(f"runtime contract is missing fields: {sorted(missing)}")
    if contract["schema_version"] != 1:
        fail(f"unsupported runtime contract schema: {contract['schema_version']}")
    actual = payload_hash(lock_payload(contract))
    if actual != contract["lock_sha256"]:
        fail("runtime contract decisions changed after they were locked")
    snapshot = contract["decisions"].get("source_snapshot")
    if snapshot:
        path = Path(snapshot.get("path", ""))
        if not path.is_file():
            fail("locked source snapshot is missing")
        current = hashlib.sha256(path.read_bytes()).hexdigest()
        if current != snapshot.get("sha256"):
            fail("source snapshot changed after task decisions were locked")


def command_init(args: argparse.Namespace) -> None:
    contract_path = args.contract.resolve()
    review_path = args.review.resolve()
    if contract_path.exists() or review_path.exists():
        fail("contract and review paths must not already exist")

    output_language, language_source, detected_source_language, source_snapshot = derive_language(args)
    output_format, format_source = derive_format(args)

    if args.publication_target != "none":
        expected_format = "feishu" if args.publication_target in {"feishu", "lark"} else "other"
        if output_format not in {expected_format, args.publication_target}:
            fail("publication target conflicts with the selected output format")
        if not args.external_action_authorized:
            fail("external action requires --external-action-authorized")
        if not args.authorization_evidence.strip():
            fail("external action requires --authorization-evidence")
        if args.external_action == "none":
            fail("external target requires --external-action")
    elif args.external_action_authorized or args.authorization_evidence.strip() or args.external_action != "none":
        fail("external action or authorization was supplied without an external target")

    contract_id = hashlib.sha256(f"{utc_now()}:{contract_path}".encode("utf-8")).hexdigest()[:16]
    contract = {
        "schema_version": 1,
        "contract_id": contract_id,
        "status": "locked",
        "created_at": utc_now(),
        "task": {
            "operation": args.operation,
            "scenario": args.scenario,
            "channel": args.channel,
            "risk": args.risk,
            "title_required": args.title,
            "visual_state": args.visual,
        },
        "decisions": {
            "source_language": detected_source_language,
            "source_snapshot": source_snapshot,
            "explicit_language_override": None if args.language_override == "none" else args.language_override.lower(),
            "output_language": output_language,
            "language_decision_source": language_source,
            "explicit_format": None if args.explicit_format == "none" else args.explicit_format,
            "existing_format": None if args.existing_format == "none" else args.existing_format,
            "output_format": output_format,
            "format_decision_source": format_source,
            "publication_target": args.publication_target,
            "external_action": args.external_action,
            "external_action_authorized": bool(args.external_action_authorized),
            "authorization_evidence": args.authorization_evidence.strip() or None,
        },
        "required_semantic_gates": semantic_gates(title=args.title, visual=args.visual),
    }
    contract["lock_sha256"] = payload_hash(lock_payload(contract))

    review = {
        "schema_version": 1,
        "contract_id": contract_id,
        "checks": {
            gate: {"status": "pending", "evidence": ""}
            for gate in contract["required_semantic_gates"]
        },
    }
    write_json(contract_path, contract)
    write_json(review_path, review)
    print(json.dumps({
        "status": "locked",
        "contract": str(contract_path),
        "review": str(review_path),
        "output_language": output_language,
        "output_format": output_format,
        "publication_target": args.publication_target,
    }, ensure_ascii=False))


def command_check_action(args: argparse.Namespace) -> None:
    contract = read_json(args.contract.resolve())
    verify_contract_integrity(contract)
    decisions = contract["decisions"]
    if decisions["publication_target"] == "none":
        fail("external mutation is not part of the locked task")
    if args.action != decisions.get("external_action"):
        fail("external action differs from the locked action")
    if args.target != decisions["publication_target"]:
        fail("external target differs from the locked target")
    if not decisions["external_action_authorized"] or not decisions["authorization_evidence"]:
        fail("external action lacks explicit authorization evidence")
    receipt = {
        "schema_version": 1,
        "contract_id": contract["contract_id"],
        "checked_at": utc_now(),
        "status": "pass",
        "action": args.action,
        "target": args.target,
        "authorization_evidence_sha256": hashlib.sha256(
            decisions["authorization_evidence"].encode("utf-8")
        ).hexdigest(),
    }
    write_json(args.receipt.resolve(), receipt)
    print(f"PASS: {args.action} action is allowed for {args.target} | receipt={args.receipt.resolve()}")


def validate_action_receipt(path: Path | None, contract: dict) -> tuple[list[str], dict | None]:
    decisions = contract["decisions"]
    expected_target = decisions["publication_target"]
    expected_action = decisions["external_action"]
    if expected_target == "none":
        if path is not None:
            return ["action receipt was supplied for a task with no external action"], None
        return [], None
    if path is None:
        return ["external delivery is missing the required action preflight receipt"], None
    result = read_json(path.resolve())
    failures: list[str] = []
    if result.get("schema_version") != 1:
        failures.append("action receipt has an unsupported schema")
    if result.get("contract_id") != contract["contract_id"]:
        failures.append("action receipt belongs to a different contract")
    if result.get("status") != "pass":
        failures.append("action receipt status is not pass")
    if result.get("action") != expected_action:
        failures.append("action receipt does not match the locked external action")
    if result.get("target") != expected_target:
        failures.append("action receipt does not match the locked external target")
    evidence = decisions.get("authorization_evidence") or ""
    expected_evidence_hash = hashlib.sha256(evidence.encode("utf-8")).hexdigest()
    if result.get("authorization_evidence_sha256") != expected_evidence_hash:
        failures.append("action receipt does not match the locked authorization evidence")
    return failures, result


class VisibleTextParser(HTMLParser):
    HIDDEN = {"script", "style", "noscript", "svg"}
    EXCLUDED = {"code", "pre"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.parts: list[str] = []
        self.html_lang: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        self.stack.append(lowered)
        if lowered == "html":
            self.html_lang = dict(attrs).get("lang")

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == lowered:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if any(tag in self.HIDDEN or tag in self.EXCLUDED for tag in self.stack):
            return
        self.parts.append(data)


def extract_visible_text(path: Path, actual_format: str) -> tuple[str, str | None]:
    text = path.read_text(encoding="utf-8")
    if actual_format != "html":
        return text, None
    parser = VisibleTextParser()
    parser.feed(text)
    return " ".join(parser.parts), parser.html_lang


def dominant_language(text: str) -> dict:
    without_urls = re.sub(r"https?://\S+", " ", text)
    cjk = len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", without_urls))
    latin = len(re.findall(r"[A-Za-z]", without_urls))
    total = cjk + latin
    if total < 80:
        detected = "unknown"
    else:
        cjk_share = cjk / total
        if cjk_share >= 0.25:
            detected = "zh"
        elif cjk_share <= 0.10:
            detected = "en"
        else:
            detected = "mixed"
    return {"detected": detected, "cjk_chars": cjk, "latin_chars": latin}


def validate_review(review: dict, contract: dict) -> list[str]:
    failures: list[str] = []
    if review.get("schema_version") != 1:
        failures.append("unsupported semantic review schema")
    if review.get("contract_id") != contract["contract_id"]:
        failures.append("semantic review belongs to a different contract")
    checks = review.get("checks")
    if not isinstance(checks, dict):
        return [*failures, "semantic review has no checks object"]
    required = set(contract["required_semantic_gates"])
    if set(checks) != required:
        failures.append("semantic review gates do not exactly match the contract")
    for gate in sorted(required):
        item = checks.get(gate)
        if not isinstance(item, dict):
            failures.append(f"missing semantic gate: {gate}")
            continue
        status = item.get("status")
        evidence = str(item.get("evidence", "")).strip()
        if status != "pass":
            failures.append(f"semantic gate is not pass: {gate} ({status})")
        normalized = re.sub(r"\s+", " ", evidence.casefold()).strip(" .")
        if len(evidence) < 20:
            failures.append(f"semantic gate lacks concrete evidence: {gate}")
        if normalized in {
            "checked",
            "looks good",
            "followed the skill",
            "verified",
            "已检查",
            "没有问题",
            "符合要求",
        }:
            failures.append(f"semantic gate uses generic evidence: {gate}")
    return failures


def validate_judge_result(path: Path | None, contract: dict) -> tuple[list[str], dict | None]:
    required = contract["task"]["risk"] == "high"
    if path is None:
        return (["high-risk task is missing an independent judge result"] if required else []), None
    result = read_json(path.resolve())
    failures: list[str] = []
    if result.get("schema_version") != 1:
        failures.append("independent judge result has an unsupported schema")
    if result.get("contract_id") != contract["contract_id"]:
        failures.append("independent judge result belongs to a different contract")
    if result.get("verdict") != "pass":
        failures.append("independent judge verdict is not pass")
    hard_gates = result.get("hard_gates")
    if not isinstance(hard_gates, dict):
        failures.append("independent judge result has no hard_gates object")
    else:
        required_gates = set(contract["required_semantic_gates"])
        missing = required_gates - set(hard_gates)
        if missing:
            failures.append(f"independent judge omitted gates: {sorted(missing)}")
        for gate in sorted(required_gates & set(hard_gates)):
            if hard_gates[gate] != "pass":
                failures.append(f"independent judge gate is not pass: {gate}")
    return failures, result


def expected_extension(output_format: str) -> set[str]:
    return {
        "html": {".html", ".htm"},
        "markdown": {".md", ".markdown"},
        "plain-text": {".txt"},
        "word": {".docx"},
        "slides": {".pptx"},
        "chat": {".txt", ".md"},
        "feishu": {".txt", ".md", ".html"},
        "lark": {".txt", ".md", ".html"},
        "other": set(),
    }.get(output_format, set())


def command_verify(args: argparse.Namespace) -> None:
    contract_path = args.contract.resolve()
    contract = read_json(contract_path)
    verify_contract_integrity(contract)
    review = read_json(args.review.resolve())
    artifact = args.artifact.resolve()
    failures = validate_review(review, contract)
    judge_failures, judge_result = validate_judge_result(args.judge_result, contract)
    failures.extend(judge_failures)
    action_failures, action_receipt = validate_action_receipt(args.action_receipt, contract)
    failures.extend(action_failures)
    checks: list[dict] = []

    content_snapshot = (
        artifact
        if args.actual_format == "html"
        else (args.content_snapshot.resolve() if args.content_snapshot else artifact)
    )
    if not artifact.is_file():
        failures.append(f"artifact does not exist: {artifact}")
        visible_text = ""
        html_lang = None
    else:
        selected_format = contract["decisions"]["output_format"]
        if args.actual_format != selected_format:
            failures.append(f"actual format {args.actual_format} differs from locked format {selected_format}")
        extensions = expected_extension(selected_format)
        if extensions and artifact.suffix.lower() not in extensions:
            failures.append(f"artifact extension {artifact.suffix} does not match {selected_format}")
        if args.actual_format in {"word", "slides"} and not args.content_snapshot:
            failures.append(f"{args.actual_format} verification requires --content-snapshot")
            visible_text, html_lang = "", None
        elif not content_snapshot.is_file():
            failures.append(f"content snapshot does not exist: {content_snapshot}")
            visible_text, html_lang = "", None
        else:
            snapshot_format = (
                "html" if content_snapshot.suffix.lower() in {".html", ".htm"} else "plain-text"
            )
            visible_text, html_lang = extract_visible_text(
                content_snapshot,
                "html" if args.actual_format == "html" else snapshot_format,
            )

        expected_language = language_root(contract["decisions"]["output_language"])
        detected = dominant_language(visible_text)
        checks.append({"id": "output-language-fidelity", "expected": expected_language, **detected})
        if expected_language in {"en", "zh"} and detected["detected"] != expected_language:
            failures.append(
                f"visible text language is {detected['detected']}, expected {expected_language} "
                f"(CJK={detected['cjk_chars']}, Latin={detected['latin_chars']})"
            )
        if args.actual_format == "html":
            if not html_lang or language_root(html_lang) != expected_language:
                failures.append(f"HTML lang {html_lang!r} does not match expected language {expected_language}")
            validator = subprocess.run(
                [sys.executable, str(HTML_VALIDATOR), str(artifact), "--expected-language", expected_language],
                capture_output=True,
                text=True,
                check=False,
            )
            checks.append({
                "id": "html-structural-validation",
                "status": "pass" if validator.returncode == 0 else "fail",
                "detail": (validator.stdout + validator.stderr).strip(),
            })
            if validator.returncode != 0:
                failures.append("HTML structural validation failed")

    expected_target = contract["decisions"]["publication_target"]
    expected_action = contract["decisions"]["external_action"]
    if args.actual_publication_target != expected_target:
        failures.append(
            f"actual publication target {args.actual_publication_target} differs from locked target {expected_target}"
        )
    if args.actual_external_action != expected_action:
        failures.append(
            f"actual external action {args.actual_external_action} differs from locked action {expected_action}"
        )
    if args.actual_publication_target != "none" and not contract["decisions"]["external_action_authorized"]:
        failures.append("artifact was published without locked authorization")

    receipt = {
        "schema_version": 1,
        "contract_id": contract["contract_id"],
        "verified_at": utc_now(),
        "artifact": str(artifact),
        "content_snapshot": str(content_snapshot),
        "actual_format": args.actual_format,
        "actual_publication_target": args.actual_publication_target,
        "actual_external_action": args.actual_external_action,
        "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest() if artifact.is_file() else None,
        "content_snapshot_sha256": (
            hashlib.sha256(content_snapshot.read_bytes()).hexdigest()
            if content_snapshot.is_file() else None
        ),
        "status": "fail" if failures else "pass",
        "failures": failures,
        "checks": checks,
        "independent_judge": None if judge_result is None else {
            "verdict": judge_result.get("verdict"),
            "source": str(args.judge_result.resolve()),
        },
        "action_preflight": None if action_receipt is None else {
            "action": action_receipt.get("action"),
            "target": action_receipt.get("target"),
            "source": str(args.action_receipt.resolve()),
        },
    }
    write_json(args.receipt.resolve(), receipt)
    if failures:
        for message in failures:
            print(f"FAIL: {message}", file=sys.stderr)
        raise SystemExit(1)
    print(f"PASS: runtime contract verified | receipt={args.receipt.resolve()}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="derive and lock task decisions before drafting")
    init.add_argument("--contract", type=Path, required=True)
    init.add_argument("--review", type=Path, required=True)
    init.add_argument("--scenario", choices=SCENARIOS, required=True)
    init.add_argument("--operation", choices=OPERATIONS, required=True)
    init.add_argument("--channel", choices=("chat", "artifact"), required=True)
    init.add_argument("--risk", choices=RISK_LEVELS, default="standard")
    init.add_argument("--source-file", type=Path)
    init.add_argument("--source-language", default="none")
    init.add_argument("--language-override", default="none")
    init.add_argument("--selected-language", default="none")
    init.add_argument("--language-reason", default="")
    init.add_argument("--explicit-format", choices=FORMATS, default="none")
    init.add_argument("--existing-format", choices=FORMATS, default="none")
    init.add_argument("--publication-target", choices=PUBLICATION_TARGETS, default="none")
    init.add_argument("--external-action", choices=EXTERNAL_ACTIONS, default="none")
    init.add_argument("--external-action-authorized", action="store_true")
    init.add_argument("--authorization-evidence", default="")
    init.add_argument("--title", action="store_true")
    init.add_argument("--visual", choices=VISUAL_STATES, default="none")
    init.set_defaults(func=command_init)

    action = subparsers.add_parser("check-action", help="fail closed before an external side effect")
    action.add_argument("--contract", type=Path, required=True)
    action.add_argument("--action", choices=EXTERNAL_ACTIONS[1:], required=True)
    action.add_argument("--target", choices=PUBLICATION_TARGETS[1:], required=True)
    action.add_argument("--receipt", type=Path, required=True)
    action.set_defaults(func=command_check_action)

    verify = subparsers.add_parser("verify", help="compare the actual deliverable with locked decisions")
    verify.add_argument("--contract", type=Path, required=True)
    verify.add_argument("--review", type=Path, required=True)
    verify.add_argument("--artifact", type=Path, required=True)
    verify.add_argument("--content-snapshot", type=Path)
    verify.add_argument("--actual-format", choices=FORMATS[1:], required=True)
    verify.add_argument("--actual-publication-target", choices=PUBLICATION_TARGETS, default="none")
    verify.add_argument("--actual-external-action", choices=EXTERNAL_ACTIONS, default="none")
    verify.add_argument("--action-receipt", type=Path)
    verify.add_argument("--receipt", type=Path, required=True)
    verify.add_argument("--judge-result", type=Path)
    verify.set_defaults(func=command_verify)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
