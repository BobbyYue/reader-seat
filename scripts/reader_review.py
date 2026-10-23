#!/usr/bin/env python3
"""Prepare and aggregate fail-closed independent reader review rounds."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
import reader_value
import source_attribution


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
        "claim-evidence-adjacent",
        "density-and-spacing-support-path",
        "layout-has-no-obstruction",
        "tables-and-visuals-readable",
        "visual-encoding-not-misleading",
        "stable-and-accessible-presentation",
    ),
}
SEVERITIES = {"blocker", "major", "minor"}
REVIEW_STATUSES = {"pass", "fail", "blocked"}


def editorial_axes(dimension, renders):
    return {
        "no-context": (),
        "readability": ("expression", "selection"),
        "source-reliability": ("meaning",),
        "structure-visual": ("presentation",) if renders else ("selection",),
    }[dimension]


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
    import reader_answers
    try:
        answer_lock = config.get("answer_lock")
        if not answer_lock:
            fail("runtime contract is missing its pre-draft reader answer plan")
        lock_path = output_dir / "answer-lock.json"
        write_json(lock_path, answer_lock)
        answer_manifest = reader_answers.prepare(lock_path, artifact, output_dir / "answers", args.content_snapshot)
        primary_surface = answer_manifest["surfaces"][0]
        _, answer_plan = reader_answers.open_lock(lock_path)
    except (ValueError, OSError) as exc:
        fail(str(exc))

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
            "artifact": ({"path": primary_surface["path"], "sha256": primary_surface["sha256"]}
                         if dimension == "no-context" else {"path": str(artifact), "sha256": artifact_sha256}),
            "reader_profile": config.get("reader_profile"),
            "required_checks": list(REQUIRED_CHECKS[dimension]),
            "reading_guidance": {
                "no-context": "In the existing main_conclusion and meaning fields, restate the lead's fact or relationship and its applicable conditions from the artifact alone. Do not demand a contrast or action for a simple fact.",
                "readability": "Check empty abstraction, template-driven structure, purposeless repetition and audience mismatch as context-dependent signals. Preserve necessary context, legitimate terminology and useful repetition. For expression issues quote the passage in observed_problem, name concrete impact in reader_consequence, and give the smallest fix plus protected meaning in required_fix. Compare corrective wording with a faithful direct version and assess repeated framing across the whole text. Accurate comprehension alone does not resolve avoidable reading effort or an explicit expression requirement. AI-like alone is not evidence; unsupported taste preferences cannot start another round. Resolve substantive wording issues in the existing batch.",
                "source-reliability": "Check leads and adjacent qualifiers against source subject, direction, scope, time and certainty. Reject invented opposites, winners, causes or requests and decision-changing conditions moved out of view. For rhetorical overstatement, quote the claim and its source boundary; require a minimal fix without invented specificity or erased uncertainty.",
                "structure-visual": "Check that headings and visuals convey the same relationship and qualifications as the supporting text; keep interpretation-changing conditions beside the claim. Check empty visual packaging by reader impact, not counts of cards, tables or repeated layouts. Locate the element, explain the reading obstacle and smallest fix; style preference alone is nonblocking and cannot start another round.",
            }[dimension],
            "context_policy": {
                "fresh_subagent_required": True,
                "parent_context_forbidden": True,
                "other_review_results_forbidden": True,
            },
            "source_bundle": source if dimension == "source-reliability" else None,
            "render_evidence": renders if dimension == "structure-visual" else [],
        }
        if dimension == "no-context":
            packet['attribution_template'] = source_attribution.template(Path(packet['artifact']['path']).read_text(encoding='utf-8'))
            packet['reading_guidance'] += ' Complete attribution_template as reader_understanding.attribution_replay from this surface only: who says what, and is a negative conclusion established? ' + source_attribution.GUIDANCE
            packet["answer_packet"] = reader_answers.load(primary_surface["packet_path"])
            packet["reading_guidance"] += " Read only this extracted surface; never open the full artifact. Include answer_responses as a one-item array using answer_packet.response_fields. Do not score against unseen expected answers."
            packet["reading_guidance"] += " Restate any reasons or relationships you actually understand; do not fill missing explanations from your own knowledge."
        elif answer_plan.get("depth"):
            packet["depth_requirement"] = answer_plan["depth"]
            packet["reading_guidance"] += " Check the planned understanding depth against the reader task. A list of accurate labels may still omit the reasons, evidence or relationships needed to understand it; preserve concise orientation when that is the actual task."
        if dimension == "source-reliability":
            packet["answer_manifest"] = str(output_dir / "answers" / "surface-manifest.json")
            packet["reading_guidance"] += " After the no-context response is frozen, independently evaluate it against the locked answer plan. Include answer_evaluation using reader_answers.py contract; do not alter or coach the raw response."
            if answer_plan.get("depth"):
                packet["reading_guidance"] += " Complete answer_evaluation.depth_fit with mode, pass/fail, task-specific reason, an exact source_quote and an exact reader_quote. Reject a shallow answer plan as well as a shallow draft; keyword coverage is not understanding. Source limitations must remain explicit, never filled with invention."
        axes = editorial_axes(dimension, packet["render_evidence"])
        if axes:
            editorial_text = args.content_snapshot.resolve() if args.content_snapshot else artifact
            packet["editorial_text"] = {"path": str(editorial_text), "sha256": file_hash(editorial_text)}
            packet["reader_value_template"] = reader_value.template(axes, artifact_sha256, reader_value.read_text(packet.get("editorial_text", packet["artifact"])["path"]), reader_value.read_text(source_bundle) if dimension == 'source-reliability' else '')
            packet["reader_value_guidance"] = {axis: reader_value.GUIDANCE[axis] for axis in axes}
            packet["reading_guidance"] += " Complete reader_value_template as reader_value in the same response. Quote the final artifact, explain reader impact and protected meaning. Every requested addition must name a concrete misunderstanding it prevents; completeness or style preference alone does not justify it. Never expose this audit in the document."
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
        "answer_manifest": {"path": str(output_dir / "answers" / "surface-manifest.json"),
                            "sha256": file_hash(output_dir / "answers" / "surface-manifest.json")},
    }
    manifest_path = output_dir / "round-manifest.json"
    write_json(manifest_path, manifest)
    if getattr(args, "lifecycle_run", None):
        import writing_execution
        writing_execution.register_packets(args.lifecycle_run,
            {p["dimension"]: p["path"] for p in packets}, manifest_path)
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
        "artifact_sha256": packet["artifact"]["sha256"],
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

    axes = editorial_axes(dimension, packet.get("render_evidence", []))
    if axes:
        try:
            source_entry = packet.get("source_bundle") or {}
            source_text = reader_value.read_text(source_entry["path"]) if source_entry else ""
            text_entry = packet.get("editorial_text", packet["artifact"])
            if file_hash(Path(text_entry["path"])) != text_entry["sha256"]:
                failures.append(f"{dimension} editorial text snapshot changed")
            failures.extend(reader_value.validate(
                result.get("reader_value"), axes, packet["artifact"]["sha256"],
                reader_value.read_text(text_entry["path"]), source=source_text,
                renders=[entry["path"] for entry in packet.get("render_evidence", [])],
            ))
        except (OSError, ValueError, KeyError) as exc:
            failures.append(f"{dimension} reader_value evidence unavailable: {exc}")

    if dimension == "no-context":
        understanding = result.get("reader_understanding")
        if not isinstance(understanding, dict):
            failures.append("no-context result has no reader_understanding object")
        else:
            failures.extend(source_attribution.validate(understanding.get('attribution_replay'), Path(packet['artifact']['path']).read_text(encoding='utf-8')))
            for field in ("object", "main_conclusion", "evidence", "meaning", "action"):
                if len(str(understanding.get(field, "")).strip()) < 2:
                    failures.append(f"no-context reader understanding lacks {field}")
    return failures


def validate_answer_evidence(manifest, contract, results):
    """Consume raw blind replay plus the existing source review, not a fifth audit."""
    import reader_answers
    try:
        entry = manifest["answer_manifest"]
        if file_hash(Path(entry["path"])) != entry["sha256"]:
            return ["reader answer manifest changed"]
        answer_manifest = reader_answers.load(entry["path"])
        plan = reader_answers.verify_manifest(answer_manifest)
        lock, _ = reader_answers.open_lock(answer_manifest["lock_path"])
        if lock != contract["decisions"]["reader_validation"].get("answer_lock"):
            return ["reader answer plan differs from the pre-draft contract"]
        if answer_manifest["artifact"]["sha256"] != manifest["artifact_sha256"]:
            return ["reader answer surface belongs to another artifact"]
        blind = results["no-context"]
        source = results["source-reliability"]
        responses = blind["answer_responses"]
        evaluation = source["answer_evaluation"]
        source_map = source['reader_value']['checks']['meaning']['source_attribution']
        failures_attribution = source_attribution.compare(source_map, blind['reader_understanding']['attribution_replay'])
        readability = results['readability']['reader_value']['checks']['selection']['context_review']['attribution_replay']
        failures_attribution.extend(source_attribution.compare(source_map, readability))
        failures = reader_answers.validate_answers(answer_manifest, responses, evaluation)
        failures.extend(failures_attribution)
        if any(r["reader_id"] != blind["reviewer"]["agent_id"] for r in responses):
            failures.append("answer response identity differs from the no-context reviewer")
        if evaluation["reviewer_id"] != source["reviewer"]["agent_id"]:
            failures.append("answer evaluator identity differs from the source reviewer")
        return failures
    except (KeyError, TypeError, ValueError, OSError) as exc:
        return [f"missing or invalid required reader answers: {exc}"]


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

    failures.extend(validate_answer_evidence(manifest, contract, {k: v[0] for k, v in results.items()}))
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

    if manifest is not None:
        raw_results = {key: read_json(Path(record["result_path"])) for key, record in review_map.items()
                       if Path(str(record.get("result_path", ""))).is_file()}
        answer_failures = validate_answer_evidence(manifest, contract, raw_results)
        failures.extend(answer_failures)
        original_all_pass = original_all_pass and not answer_failures
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
    prepare.add_argument("--content-snapshot", type=Path)
    prepare.add_argument("--render-evidence", type=Path, action="append", default=[])
    prepare.add_argument("--round", type=int, required=True)
    prepare.add_argument("--previous-aggregate", type=Path)
    prepare.add_argument("--output-dir", type=Path, required=True)
    prepare.add_argument("--lifecycle-run", type=Path, help="Register exact packets with the managed writing task")
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
