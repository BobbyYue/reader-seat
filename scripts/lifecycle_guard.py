"""Bind the shared functional lifecycle to the original reader-review aggregate."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def native_plan(contract_path):
    """Project the existing locked task; do not maintain a second answer list."""
    import reader_answers
    import direct_expression
    contract_path = Path(contract_path).resolve()
    task = reader_answers.load(contract_path)
    decisions = task["decisions"]
    reader = decisions["reader_validation"]
    lock = reader["answer_lock"]
    for name in ("plan", "source"):
        item = lock[name]
        if reader_answers.digest(item["path"]) != item["sha256"]:
            raise ValueError("native reader-answer plan or source changed")
    original = reader_answers.load(lock["plan"]["path"])
    errors = reader_answers.plan_errors(original, require_depth=lock.get("requires_depth", False))
    if errors:
        raise ValueError("native reader-answer plan is invalid: " + "; ".join(errors))
    errors = direct_expression.plan_errors(original.get('expression_plan'), original['answers'])
    if errors:
        raise ValueError('; '.join(errors))
    sources = [reader["source_bundle"]]
    if decisions.get("source_snapshot"):
        sources.append(decisions["source_snapshot"])
    sources = list({item["path"]: item for item in sources}.values())
    binding = {"contract_path": str(contract_path), "contract_id": task["contract_id"],
               "task": task["task"], "decisions": decisions, "answer_plan": lock["plan"]}
    answers = [{"id": answer["id"], "question": answer["question"],
                "expected": answer["expected_information"], "source_location": answer["source_location"],
                "source_status": answer["source_status"]} for answer in original["answers"]]
    plan = {"task": task["contract_id"], "genre": task["task"]["scenario"],
            "domain": "Internet-industry work document", "purpose": original["reader"]["decision"],
            "language": decisions["output_language"], "format": decisions["output_format"],
            "reader": {"knowledge": original["reader"]["known_context"],
                       "need": original["reader"]["decision"], "profile": original["reader"]["profile"]},
            "authority": {"status": "confirmed", "basis": "Existing locked native task and reader-answer plan",
                          "reference": str(contract_path)},
            "material": {"mode": "source-grounded", "gaps": []}, "required_answers": answers,
            "reading_path": [{"id": surface["id"], "purpose": surface.get("reason") or original["reader"]["decision"]}
                             for surface in original["surfaces"]],
            "expression_plan": original['expression_plan'], "native_binding": binding}
    return plan, sources


def init_native_run(run_path, contract_path):
    import writing_lifecycle as lifecycle
    plan, sources = native_plan(contract_path)
    run = Path(run_path).absolute()
    plan_path = run.with_name(run.name + ".plan.json")
    lifecycle.write_json(plan_path, plan, exclusive=True)
    return lifecycle.init_run(run, plan_path, "functional", [item["path"] for item in sources])


def validate_native_binding(run_path, contract_path):
    expected, sources = native_plan(contract_path)
    state = json.loads((Path(run_path) / "lifecycle.json").read_text(encoding="utf-8"))
    plan = state["plan"]
    for key in ("native_binding", "task", "genre", "purpose", "language", "format", "reader", "required_answers", "expression_plan"):
        if plan.get(key) != expected[key]:
            raise ValueError("lifecycle differs from locked native task: " + key)
    if plan.get("material", {}).get("mode") != "source-grounded":
        raise ValueError("functional lifecycle cannot change the native source/fiction boundary")
    for source in sources:
        identity = {key: source[key] for key in ("path", "sha256")}
        if identity not in state["sources"]:
            raise ValueError("lifecycle source differs from the native locked source")
    return [Path(contract_path).resolve(), Path(expected["native_binding"]["answer_plan"]["path"]),
            *[Path(source["path"]) for source in sources]]


def verify_preview(run_path, artifact_path, contract_path):
    """Readiness for an authorized preview write, never final acceptance."""
    import writing_lifecycle as lifecycle
    if run_path is None:
        raise ValueError("preview requires --lifecycle-run")
    run, artifact = Path(run_path).absolute(), Path(artifact_path).resolve()
    with lifecycle.session(run) as state:
        lifecycle.need(state["profile"] == "functional", "Writing profile does not match this skill")
        lifecycle.need(state["units"] and state["candidates"], "Preview requires prewrite, unit and candidate stages")
        current = state["candidates"][-1]
        lifecycle.need(lifecycle.ref(artifact) == current["artifact"], "Preview candidate changed")
        checkpoint = max(event["sequence"] for event in state["events"] if event["operation"] == "during")
        candidate = max(event["sequence"] for event in state["events"] if event["operation"] == "candidate")
        lifecycle.need(checkpoint < candidate, "Preview checkpoints changed; register the complete candidate again")
        paths = [run / "lifecycle.json", Path(state["plan_ref"]["path"]),
                 *[Path(item["path"]) for item in state["sources"] + state["evidence"]]]
    paths.extend(validate_native_binding(run, contract_path))
    import writing_execution
    writing_execution.inspect_candidate(run, artifact)
    engine = Path(lifecycle.__file__).resolve()
    paths.extend([engine, engine.parents[1] / "config" / "writing-quality.json"])
    paths = sorted({str(path.resolve()) for path in paths})
    return {"status": "preview-only", "artifact_sha256": lifecycle.ref(artifact)["sha256"],
            "run_path": str(run), "evidence_paths": paths,
            "verified_inputs": {path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in paths},
            "publishable": False, "verified_finished_artifact": False}


def verify_lifecycle(run_path, artifact_path, aggregate_path, *, draft=False, contract_path=None):
    if run_path is None:
        raise ValueError("finished delivery requires --lifecycle-run")
    run = Path(run_path).absolute()
    state = run / "lifecycle.json"
    if not run.is_dir() or not state.is_file():
        raise ValueError("lifecycle run is missing lifecycle.json")
    if aggregate_path is None or not Path(aggregate_path).is_file():
        raise ValueError("lifecycle requires the original reader-review aggregate")
    try:
        import writing_lifecycle as lifecycle
    except ImportError as exc:
        raise ValueError("shared writing lifecycle verifier is unavailable") from exc
    artifact = Path(artifact_path).resolve()
    result = lifecycle.verify_delivery(run, artifact, "functional",
                             review_evidence=[Path(aggregate_path).resolve()], draft=draft)
    native_paths = [] if contract_path is None else validate_native_binding(run, contract_path)
    import writing_execution
    captured = writing_execution.verify_reviews(run, [Path(aggregate_path).resolve()])
    expected = "review-incomplete-draft" if draft else "pass"
    if not isinstance(result, dict) or result.get("status") != expected:
        raise ValueError("lifecycle did not authorize this delivery state")
    if result.get("artifact_sha256") != hashlib.sha256(artifact.read_bytes()).hexdigest():
        raise ValueError("lifecycle is bound to another artifact version")
    evidence = result.get("evidence_paths")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("lifecycle did not return its evidence paths")
    engine = Path(lifecycle.__file__).resolve()
    paths = [artifact, state, Path(aggregate_path).resolve(), engine,
             engine.parents[1] / "config" / "writing-quality.json", *map(Path, evidence), *native_paths,
             *map(Path, captured.get("evidence_paths", []))]
    if any(not path.is_absolute() or not path.is_file() for path in paths):
        raise ValueError("lifecycle evidence is missing or not absolute")
    paths = sorted({str(path.resolve()) for path in paths})
    verified = {path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in paths}
    verified[str(artifact)] = result["artifact_sha256"]
    return {**result, "run_path": str(run), "evidence_paths": paths, "verified_inputs": verified}
