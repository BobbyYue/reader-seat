#!/usr/bin/env python3
"""Prepare and aggregate fail-closed independent reader review rounds."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path


DIMENSIONS = (
    "no-context",
    "readability",
    "source-reliability",
    "structure-visual",
)
MAX_ROUNDS = 3
VISUAL_FORMATS = {"html", "feishu", "lark", "word", "slides"}
REQUIRED_CHECKS = {
    "no-context": (
        "object-understood",
        "main-conclusion-understood",
        "evidence-understood",
        "scope-and-meaning-understood",
        "action-understood",
        "critical-ambiguity-absent",
    ),
    "readability": (
        "audience-fit-language",
        "terminology-explained-when-needed",
        "references-unambiguous",
        "reasoning-continuity",
        "repetition-and-filler-controlled",
        "natural-professional-expression",
    ),
    "source-reliability": (
        "material-claims-traceable",
        "source-authority-and-recency-calibrated",
        "facts-inferences-and-advice-separated",
        "numbers-definitions-and-scope-preserved",
        "certainty-matches-evidence",
        "visual-provenance-supported",
    ),
    "structure-visual": (
        "reading-path-clear",
        "headings-carry-information",
        "layout-has-no-obstruction",
        "tables-and-visuals-readable",
        "visual-encoding-not-misleading",
        "responsive-and-accessible-presentation",
    ),
}
SEVERITIES = {"blocker", "major", "minor"}
REVIEW_STATUSES = {"pass", "fail", "blocked"}


class ReaderReviewError(ValueError):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def object_hash(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReaderReviewError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ReaderReviewError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReaderReviewError(f"expected a JSON object in {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fail(message: str, *, code: int = 2) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(code)


def reader_config(contract: dict) -> dict:
    decisions = contract.get("decisions")
    if not isinstance(decisions, dict):
        raise ReaderReviewError("runtime contract has no decisions object")
    config = decisions.get("reader_validation")
    if not isinstance(config, dict):
        raise ReaderReviewError("runtime contract has no reader_validation decision")
    if config.get("required") is not True:
        raise ReaderReviewError("reader validation is not required for this task")
    if tuple(config.get("dimensions", [])) != DIMENSIONS:
        raise ReaderReviewError("runtime contract reader dimensions do not match the canonical set")
    if config.get("max_rounds") != MAX_ROUNDS:
        raise ReaderReviewError("runtime contract reader review round limit is not canonical")
    return config


def validate_previous_aggregate(path: Path, contract: dict, round_number: int, artifact_sha256: str) -> None:
    previous = read_json(path)
    if previous.get("schema_version") != 1:
        raise ReaderReviewError("previous reader review aggregate has an unsupported schema")
    if previous.get("contract_id") != contract.get("contract_id"):
        raise ReaderReviewError("previous reader review aggregate belongs to a different contract")
    if previous.get("round") != round_number - 1:
        raise ReaderReviewError("previous reader review aggregate is not from the immediately preceding round")
    if previous.get("status") not in {"revision-required", "needs-user-decision"}:
        raise ReaderReviewError("a new review round requires a failed preceding aggregate")
    if previous.get("max_rounds_exhausted") is True:
        raise ReaderReviewError("the three-round reader review limit is already exhausted")
    if previous.get("artifact_sha256") == artifact_sha256:
        raise ReaderReviewError("a new review round requires a modified artifact")


def command_prepare(args: argparse.Namespace) -> None:
    try:
        contract = read_json(args.contract.resolve())
        config = reader_config(contract)
    except ReaderReviewError as exc:
        fail(str(exc))

    artifact = args.artifact.resolve()
    source_bundle_info = config.get("source_bundle")
    if not isinstance(source_bundle_info, dict):
        fail("runtime contract has no locked reader-review source bundle")
    source_bundle = Path(str(source_bundle_info.get("path", "")))
    if not artifact.is_file():
        fail(f"artifact does not exist: {artifact}")
    if not source_bundle.is_file():
        fail(f"source bundle does not exist: {source_bundle}")
    if file_hash(source_bundle) != source_bundle_info.get("sha256"):
        fail("locked reader-review source bundle changed before review")
    if args.round < 1 or args.round > MAX_ROUNDS:
        fail(f"reader review round must be between 1 and {MAX_ROUNDS}")

    artifact_sha256 = file_hash(artifact)
    if args.round == 1 and args.previous_aggregate:
        fail("round 1 must not use a previous aggregate")
    if args.round > 1:
        if not args.previous_aggregate:
            fail("rounds 2 and 3 require --previous-aggregate")
        try:
            validate_previous_aggregate(
                args.previous_aggregate.resolve(), contract, args.round, artifact_sha256
            )
        except ReaderReviewError as exc:
            fail(str(exc))

    render_paths = [path.resolve() for path in args.render_evidence]
    for path in render_paths:
        if not path.is_file():
            fail(f"render evidence does not exist: {path}")
    output_format = contract.get("decisions", {}).get("output_format")
    if output_format in VISUAL_FORMATS and not render_paths:
        fail(f"{output_format} reader review requires at least one --render-evidence file")

    output_dir = args.output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        fail(f"reader review output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    batch_id = hashlib.sha256(
        f"{contract.get('contract_id')}:{args.round}:{artifact_sha256}:{utc_now()}".encode("utf-8")
    ).hexdigest()[:16]
    source = {"path": str(source_bundle), "sha256": file_hash(source_bundle)}
    renders = [{"path": str(path), "sha256": file_hash(path)} for path in render_paths]
    packets: list[dict] = []

    for dimension in DIMENSIONS:
        packet = {
            "schema_version": 1,
            "contract_id": contract.get("contract_id"),
            "batch_id": batch_id,
            "round": args.round,
            "invocation_mode": "parallel-batch",
            "dimension": dimension,
            "artifact": {"path": str(artifact), "sha256": artifact_sha256},
            "reader_profile": config.get("reader_profile"),
            "required_checks": list(REQUIRED_CHECKS[dimension]),
            "context_policy": {
                "fresh_subagent_required": True,
                "parent_context_forbidden": True,
                "other_review_results_forbidden": True,
            },
            "source_bundle": source if dimension == "source-reliability" else None,
            "render_evidence": renders if dimension == "structure-visual" else [],
        }
        packet["packet_sha256"] = object_hash(packet)
        packet_path = output_dir / f"{dimension}-packet.json"
        write_json(packet_path, packet)
        packets.append({
            "dimension": dimension,
            "path": str(packet_path),
            "sha256": file_hash(packet_path),
            "packet_sha256": packet["packet_sha256"],
        })

    manifest = {
        "schema_version": 1,
        "contract_id": contract.get("contract_id"),
        "batch_id": batch_id,
        "round": args.round,
        "created_at": utc_now(),
        "artifact_sha256": artifact_sha256,
        "source_bundle_sha256": source["sha256"],
        "render_evidence": renders,
        "parallel_required": True,
        "all_must_pass": True,
        "max_rounds": MAX_ROUNDS,
        "packets": packets,
    }
    manifest_path = output_dir / "round-manifest.json"
    write_json(manifest_path, manifest)
    print(f"PASS: reader review round prepared | manifest={manifest_path}")


def validate_result(result: dict, manifest: dict, packet: dict) -> list[str]:
    failures: list[str] = []
    dimension = packet["dimension"]
    expected = {
        "schema_version": 1,
        "contract_id": manifest["contract_id"],
        "batch_id": manifest["batch_id"],
        "round": manifest["round"],
        "dimension": dimension,
        "artifact_sha256": manifest["artifact_sha256"],
        "packet_sha256": packet["packet_sha256"],
    }
    for field, value in expected.items():
        if result.get(field) != value:
            failures.append(f"{dimension} result has wrong {field}")

    reviewer = result.get("reviewer")
    if not isinstance(reviewer, dict):
        failures.append(f"{dimension} result has no reviewer identity")
    else:
        if not str(reviewer.get("agent_id", "")).strip():
            failures.append(f"{dimension} reviewer has no agent_id")
        if not str(reviewer.get("session_id", "")).strip():
            failures.append(f"{dimension} reviewer has no session_id")
        if reviewer.get("context_isolation") != "fresh-subagent":
            failures.append(f"{dimension} reviewer did not declare fresh-subagent isolation")
        if reviewer.get("parent_context_received") is not False:
            failures.append(f"{dimension} reviewer received or did not reject parent context")
        if reviewer.get("invocation_mode") != "parallel-batch":
            failures.append(f"{dimension} reviewer was not launched in the parallel batch")

    status = result.get("status")
    if status not in REVIEW_STATUSES:
        failures.append(f"{dimension} result has invalid status: {status}")
    summary = str(result.get("summary", "")).strip()
    if len(summary) < 20:
        failures.append(f"{dimension} result lacks a concrete summary")

    checks = result.get("checks")
    required_checks = set(REQUIRED_CHECKS[dimension])
    if not isinstance(checks, dict) or set(checks) != required_checks:
        failures.append(f"{dimension} result does not contain the exact required checks")
        checks = {} if not isinstance(checks, dict) else checks
    for check_id in sorted(required_checks & set(checks)):
        item = checks[check_id]
        if not isinstance(item, dict):
            failures.append(f"{dimension} check {check_id} is not an object")
            continue
        if item.get("status") not in REVIEW_STATUSES:
            failures.append(f"{dimension} check {check_id} has invalid status")
        if len(str(item.get("evidence", "")).strip()) < 20:
            failures.append(f"{dimension} check {check_id} lacks artifact-specific evidence")

    issues = result.get("issues")
    if not isinstance(issues, list):
        failures.append(f"{dimension} result has no issues array")
        issues = []
    material_issues = 0
    for index, issue in enumerate(issues):
        if not isinstance(issue, dict):
            failures.append(f"{dimension} issue {index} is not an object")
            continue
        severity = issue.get("severity")
        if severity not in SEVERITIES:
            failures.append(f"{dimension} issue {index} has invalid severity")
        if severity in {"blocker", "major"}:
            material_issues += 1
        for field in ("location", "observed_problem", "reader_consequence", "required_fix"):
            if len(str(issue.get(field, "")).strip()) < 4:
                failures.append(f"{dimension} issue {index} lacks {field}")

    if status == "pass":
        if material_issues:
            failures.append(f"{dimension} cannot pass with blocker or major issues")
        if any(item.get("status") != "pass" for item in checks.values() if isinstance(item, dict)):
            failures.append(f"{dimension} cannot pass while a required check is not pass")
    elif status in {"fail", "blocked"}:
        if not issues:
            failures.append(f"{dimension} non-pass result has no actionable issue")
        if not material_issues and not any(
            item.get("status") != "pass" for item in checks.values() if isinstance(item, dict)
        ):
            failures.append(f"{dimension} non-pass result has no material issue or failed check")

    if dimension == "no-context":
        understanding = result.get("reader_understanding")
        if not isinstance(understanding, dict):
            failures.append("no-context result has no reader_understanding object")
        else:
            for field in ("object", "main_conclusion", "evidence", "meaning", "action"):
                if len(str(understanding.get(field, "")).strip()) < 2:
                    failures.append(f"no-context reader understanding lacks {field}")
    return failures


def command_aggregate(args: argparse.Namespace) -> None:
    try:
        contract = read_json(args.contract.resolve())
        reader_config(contract)
        manifest_path = args.manifest.resolve()
        manifest = read_json(manifest_path)
    except ReaderReviewError as exc:
        fail(str(exc))

    failures: list[str] = []
    if manifest.get("schema_version") != 1:
        failures.append("reader review manifest has an unsupported schema")
    if manifest.get("contract_id") != contract.get("contract_id"):
        failures.append("reader review manifest belongs to a different contract")
    if manifest.get("parallel_required") is not True or manifest.get("all_must_pass") is not True:
        failures.append("reader review manifest does not require parallel unanimous review")
    if manifest.get("max_rounds") != MAX_ROUNDS:
        failures.append("reader review manifest has a noncanonical round limit")

    packet_entries = manifest.get("packets")
    if not isinstance(packet_entries, list):
        failures.append("reader review manifest has no packets array")
        packet_entries = []
    packet_map = {item.get("dimension"): item for item in packet_entries if isinstance(item, dict)}
    if set(packet_map) != set(DIMENSIONS):
        failures.append("reader review manifest does not contain exactly four dimensions")

    result_paths = [path.resolve() for path in args.result]
    if len(result_paths) != len(DIMENSIONS):
        failures.append("exactly four --result files are required")
    results: dict[str, tuple[dict, Path]] = {}
    agent_ids: set[str] = set()
    session_ids: set[str] = set()

    for path in result_paths:
        try:
            result = read_json(path)
        except ReaderReviewError as exc:
            failures.append(str(exc))
            continue
        dimension = result.get("dimension")
        if dimension in results:
            failures.append(f"duplicate reader review dimension: {dimension}")
            continue
        if dimension not in DIMENSIONS:
            failures.append(f"unknown reader review dimension: {dimension}")
            continue
        results[dimension] = (result, path)
        reviewer = result.get("reviewer", {})
        if isinstance(reviewer, dict):
            agent_id = str(reviewer.get("agent_id", "")).strip()
            session_id = str(reviewer.get("session_id", "")).strip()
            if agent_id in agent_ids:
                failures.append(f"reviewer agent_id was reused: {agent_id}")
            if session_id in session_ids:
                failures.append(f"reviewer session_id was reused: {session_id}")
            agent_ids.add(agent_id)
            session_ids.add(session_id)

    if set(results) != set(DIMENSIONS):
        failures.append("reader review results do not contain exactly four dimensions")

    review_records: list[dict] = []
    all_pass = True
    combined_issues: list[dict] = []
    for dimension in DIMENSIONS:
        if dimension not in results or dimension not in packet_map:
            all_pass = False
            continue
        entry = packet_map[dimension]
        packet_path = Path(str(entry.get("path", "")))
        try:
            packet = read_json(packet_path)
        except ReaderReviewError as exc:
            failures.append(str(exc))
            all_pass = False
            continue
        if file_hash(packet_path) != entry.get("sha256"):
            failures.append(f"{dimension} packet file changed after manifest creation")
        if object_hash({key: value for key, value in packet.items() if key != "packet_sha256"}) != packet.get("packet_sha256"):
            failures.append(f"{dimension} packet content hash is invalid")
        result, result_path = results[dimension]
        result_failures = validate_result(result, manifest, packet)
        failures.extend(result_failures)
        if result.get("status") != "pass" or result_failures:
            all_pass = False
        for issue in result.get("issues", []):
            if isinstance(issue, dict):
                combined_issues.append({"dimension": dimension, **issue})
        review_records.append({
            "dimension": dimension,
            "status": result.get("status"),
            "agent_id": result.get("reviewer", {}).get("agent_id"),
            "session_id": result.get("reviewer", {}).get("session_id"),
            "result_path": str(result_path),
            "result_sha256": file_hash(result_path),
        })

    round_number = manifest.get("round")
    if not isinstance(round_number, int) or not 1 <= round_number <= MAX_ROUNDS:
        failures.append("reader review manifest has an invalid round")
        round_number = MAX_ROUNDS
    status = "pass" if all_pass and not failures else (
        "needs-user-decision" if round_number >= MAX_ROUNDS else "revision-required"
    )
    aggregate = {
        "schema_version": 1,
        "contract_id": contract.get("contract_id"),
        "batch_id": manifest.get("batch_id"),
        "round": round_number,
        "aggregated_at": utc_now(),
        "artifact_sha256": manifest.get("artifact_sha256"),
        "manifest_path": str(manifest_path),
        "manifest_sha256": file_hash(manifest_path),
        "status": status,
        "all_must_pass": True,
        "dimensions": list(DIMENSIONS),
        "reviews": review_records,
        "issues": combined_issues,
        "validation_failures": failures,
        "max_rounds": MAX_ROUNDS,
        "max_rounds_exhausted": status == "needs-user-decision" and round_number >= MAX_ROUNDS,
    }
    output = args.output.resolve()
    write_json(output, aggregate)
    if status != "pass":
        for message in failures:
            print(f"FAIL: {message}", file=sys.stderr)
        print(f"FAIL: reader review requires revision | status={status} | aggregate={output}", file=sys.stderr)
        raise SystemExit(1)
    print(f"PASS: all four independent reader reviews passed | aggregate={output}")


def validate_aggregate_for_artifact(
    path: Path | None,
    contract: dict,
    artifact: Path,
    *,
    allowed_statuses: set[str] | None = None,
    require_all_pass: bool = True,
) -> tuple[list[str], dict | None]:
    decisions = contract.get("decisions", {})
    config = decisions.get("reader_validation", {})
    if not config.get("required"):
        if path is not None:
            return ["reader review aggregate was supplied for a task that does not require it"], None
        return [], None
    if path is None:
        return ["finished artifact is missing the required reader review aggregate"], None
    try:
        aggregate = read_json(path.resolve())
    except ReaderReviewError as exc:
        return [str(exc)], None
    failures: list[str] = []
    if aggregate.get("schema_version") != 1:
        failures.append("reader review aggregate has an unsupported schema")
    if aggregate.get("contract_id") != contract.get("contract_id"):
        failures.append("reader review aggregate belongs to a different contract")
    allowed = {"pass"} if allowed_statuses is None else allowed_statuses
    if aggregate.get("status") not in allowed:
        failures.append(
            f"reader review aggregate status {aggregate.get('status')} is not allowed here"
        )
    if aggregate.get("validation_failures") not in ([], None):
        failures.append("reader review aggregate retains validation failures")
    if aggregate.get("all_must_pass") is not True:
        failures.append("reader review aggregate does not require unanimous passage")
    if tuple(aggregate.get("dimensions", [])) != DIMENSIONS:
        failures.append("reader review aggregate does not contain the canonical four dimensions")
    if aggregate.get("max_rounds") != MAX_ROUNDS:
        failures.append("reader review aggregate has a noncanonical round limit")
    if not isinstance(aggregate.get("round"), int) or not 1 <= aggregate["round"] <= MAX_ROUNDS:
        failures.append("reader review aggregate has an invalid round")
    if not artifact.is_file():
        failures.append(f"artifact does not exist: {artifact}")
    elif aggregate.get("artifact_sha256") != file_hash(artifact):
        failures.append("artifact changed after independent reader review")
    manifest_path = Path(str(aggregate.get("manifest_path", "")))
    manifest: dict | None = None
    if not manifest_path.is_file():
        failures.append("reader review manifest referenced by the aggregate is missing")
    elif file_hash(manifest_path) != aggregate.get("manifest_sha256"):
        failures.append("reader review manifest changed after aggregation")
    else:
        try:
            manifest = read_json(manifest_path)
        except ReaderReviewError as exc:
            failures.append(str(exc))

    packet_map: dict[str, dict] = {}
    if manifest is not None:
        if manifest.get("schema_version") != 1:
            failures.append("reader review manifest has an unsupported schema")
        if manifest.get("contract_id") != contract.get("contract_id"):
            failures.append("reader review manifest belongs to a different contract")
        if manifest.get("batch_id") != aggregate.get("batch_id"):
            failures.append("reader review aggregate batch differs from its manifest")
        if manifest.get("round") != aggregate.get("round"):
            failures.append("reader review aggregate round differs from its manifest")
        if manifest.get("artifact_sha256") != aggregate.get("artifact_sha256"):
            failures.append("reader review aggregate artifact differs from its manifest")
        if manifest.get("parallel_required") is not True or manifest.get("all_must_pass") is not True:
            failures.append("reader review manifest does not require parallel unanimous review")
        if manifest.get("max_rounds") != MAX_ROUNDS:
            failures.append("reader review manifest has a noncanonical round limit")
        packet_entries = manifest.get("packets")
        if not isinstance(packet_entries, list):
            failures.append("reader review manifest has no packets array")
        else:
            packet_map = {
                item.get("dimension"): item for item in packet_entries if isinstance(item, dict)
            }
            if set(packet_map) != set(DIMENSIONS):
                failures.append("reader review manifest does not contain exactly four dimensions")

    reviews = aggregate.get("reviews")
    review_map: dict[str, dict] = {}
    if not isinstance(reviews, list) or len(reviews) != len(DIMENSIONS):
        failures.append("reader review aggregate does not contain four review records")
    else:
        review_map = {
            item.get("dimension"): item for item in reviews if isinstance(item, dict)
        }
        if set(review_map) != set(DIMENSIONS):
            failures.append("reader review aggregate review records do not cover all dimensions")

    original_all_pass = manifest is not None and set(packet_map) == set(DIMENSIONS)
    original_issues: list[dict] = []
    agent_ids: set[str] = set()
    session_ids: set[str] = set()
    for dimension in DIMENSIONS:
        record = review_map.get(dimension)
        packet_entry = packet_map.get(dimension)
        if not isinstance(record, dict) or not isinstance(packet_entry, dict) or manifest is None:
            original_all_pass = False
            continue

        packet_path = Path(str(packet_entry.get("path", "")))
        if not packet_path.is_file():
            failures.append(f"reader review packet is missing: {dimension}")
            original_all_pass = False
            continue
        if file_hash(packet_path) != packet_entry.get("sha256"):
            failures.append(f"reader review packet changed after manifest creation: {dimension}")
            original_all_pass = False
        try:
            packet = read_json(packet_path)
        except ReaderReviewError as exc:
            failures.append(str(exc))
            original_all_pass = False
            continue
        if object_hash({key: value for key, value in packet.items() if key != "packet_sha256"}) != packet.get("packet_sha256"):
            failures.append(f"reader review packet content hash is invalid: {dimension}")
            original_all_pass = False

        result_path = Path(str(record.get("result_path", "")))
        if not result_path.is_file():
            failures.append(f"reader review result is missing: {result_path}")
            original_all_pass = False
            continue
        if file_hash(result_path) != record.get("result_sha256"):
            failures.append(f"reader review result changed after aggregation: {dimension}")
            original_all_pass = False
        try:
            result = read_json(result_path)
        except ReaderReviewError as exc:
            failures.append(str(exc))
            original_all_pass = False
            continue
        result_failures = validate_result(result, manifest, packet)
        failures.extend(result_failures)
        if result_failures or result.get("status") != "pass":
            original_all_pass = False
        reviewer = result.get("reviewer", {})
        if isinstance(reviewer, dict):
            agent_id = str(reviewer.get("agent_id", "")).strip()
            session_id = str(reviewer.get("session_id", "")).strip()
            if agent_id in agent_ids:
                failures.append(f"reader review agent_id was reused: {agent_id}")
            if session_id in session_ids:
                failures.append(f"reader review session_id was reused: {session_id}")
            agent_ids.add(agent_id)
            session_ids.add(session_id)
            if record.get("agent_id") != agent_id or record.get("session_id") != session_id:
                failures.append(f"reader review aggregate changed reviewer identity: {dimension}")
        if record.get("status") != result.get("status"):
            failures.append(f"reader review aggregate changed the original verdict: {dimension}")
        for issue in result.get("issues", []):
            if isinstance(issue, dict):
                original_issues.append({"dimension": dimension, **issue})

    expected_status = "pass" if original_all_pass else (
        "needs-user-decision" if aggregate.get("round") == MAX_ROUNDS else "revision-required"
    )
    if aggregate.get("status") != expected_status:
        failures.append("reader review aggregate status does not match the original review results")
    if aggregate.get("issues") != original_issues:
        failures.append("reader review aggregate issues do not match the original review results")
    if require_all_pass and not original_all_pass:
        failures.append("reader review original results do not all pass")
    return failures, aggregate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="prepare four isolated review packets")
    prepare.add_argument("--contract", type=Path, required=True)
    prepare.add_argument("--artifact", type=Path, required=True)
    prepare.add_argument("--render-evidence", type=Path, action="append", default=[])
    prepare.add_argument("--round", type=int, required=True)
    prepare.add_argument("--previous-aggregate", type=Path)
    prepare.add_argument("--output-dir", type=Path, required=True)
    prepare.set_defaults(func=command_prepare)

    aggregate = subparsers.add_parser("aggregate", help="validate and combine four review results")
    aggregate.add_argument("--contract", type=Path, required=True)
    aggregate.add_argument("--manifest", type=Path, required=True)
    aggregate.add_argument("--result", type=Path, action="append", default=[])
    aggregate.add_argument("--output", type=Path, required=True)
    aggregate.set_defaults(func=command_aggregate)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
