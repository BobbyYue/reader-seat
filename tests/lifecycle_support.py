"""Synthetic lifecycle records for wiring tests, never writing-quality evidence."""
from pathlib import Path

import writing_lifecycle as lifecycle
from lifecycle_guard import init_native_run, native_plan
from lifecycle_fixture import prepare_flow
from execution_fixture import init_fixture, seed_fixture
from expression_fixture import structural_expression, structural_expression_plan


def make_run(root, artifact, result, *, rounds=1, verdict="pass", profile="functional", format="html",
             until="complete", layout_status=None, contract_path=None, plan_changes=None, source_paths=None):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    if until == "complete" and layout_status is None and contract_path is None:
        return prepare_flow(lifecycle, root, artifact, native_result=result, profile=profile,
                            rounds=rounds, verdict=verdict)["run"]
    seed = None
    if contract_path is not None and until == "complete":
        seed_dir = root / "shared-seed"
        seed_dir.mkdir()
        seed = prepare_flow(lifecycle, seed_dir, artifact, native_result=result, rounds=rounds, verdict=verdict)
    text = lifecycle.visible(artifact)
    source = root / "source.txt"
    source.write_text(text, encoding="utf-8")
    plan = root / "plan.json"
    lifecycle.write_json(plan, {
        "task": "Structural delivery wiring fixture, not a quality outcome",
        "genre": "report", "domain": "synthetic", "purpose": "Test exact evidence bindings",
        "language": "en", "format": format,
        "reader": {"knowledge": "No project context", "need": "Inspect the fixture"},
        "authority": {"status": "confirmed", "basis": "Synthetic test request", "reference": "Unit test"},
        "material": {"mode": "source-grounded", "gaps": []},
        "required_answers": [{"id": "A1", "question": "What is the statement?", "expected": text[:40],
                              "source_location": "Synthetic source.txt"}],
        "expression_plan": structural_expression_plan(),
        "literary_intent": "Synthetic fixture", "constraints": [],
        "reading_path": [{"id": "body", "purpose": "Inspect the fixture statement"}],
    })
    run = root / "run"
    if contract_path is not None:
        if plan_changes is not None or source_paths is not None:
            changed, native_sources = native_plan(contract_path)
            changed.update(plan_changes or {})
            lifecycle.write_json(run.with_name(run.name + ".plan.json"), changed)
            lifecycle.init_run(run, run.with_name(run.name + ".plan.json"), profile,
                               source_paths if source_paths is not None else [item["path"] for item in native_sources])
        else:
            init_native_run(run, contract_path)
        active_plan = lifecycle.load_json(run.with_name(run.name + ".plan.json"))
    else:
        lifecycle.init_run(run, plan, profile, [source])
        active_plan = lifecycle.load_json(plan)
    init_fixture(run)
    if until == "init":
        return run
    unit = root / "unit.json"
    lifecycle.write_json(unit, {"unit_id": active_plan["reading_path"][0]["id"], "summary": "Structural checkpoint only",
                               "expression_review": structural_expression(text, "during"),
                               "observations": [{"quote": text[:40], "reason": "Fixture text exists, not a semantic judgment"}]})
    lifecycle.record_unit(run, artifact, unit)
    if until == "unit":
        return run
    report_path = root / "metrics.json"
    report = lifecycle.measure(run, artifact, report_path)
    layout = root / "layout-STRUCTURAL-FIXTURE.txt"
    layout.write_text("Structural attachment only, not actual target rendering.", encoding="utf-8")
    record = root / "candidate.json"
    lifecycle.write_json(record, {
        "text_sha256": report["text_sha256"],
        "report_sha256": lifecycle.ref(report_path)["sha256"],
        "observations": (lifecycle.load_json(seed["record"])["observations"] if seed else
                         [{"metrics": list(report["metrics"]), "quote": text[:40],
                           "reason": "Structural assessment fixture only; not measured reader benefit"}]),
        "dispositions": [{"signal_id": signal["id"], "decision": "retain", "reason": "Retained for structural test coverage only"}
                         for metric in report["metrics"].values() for signal in metric["signals"]],
        "layout": {"status": layout_status or "inspected", "reason": "Synthetic layout record only",
                   "target": "Structural fixture", "viewport": "Fixture viewport", "findings": "Not live render evidence",
                   "evidence_files": [str(layout)]},
        "issues": [],
    })
    lifecycle.register_candidate(run, artifact, artifact, report_path, record)
    if until == "candidate":
        return run
    for _ in range(rounds):
        lifecycle.start_review(run, artifact)
        if until == "review-start":
            return run
        lifecycle.finish_review(run, result, verdict)
        seed_fixture(run, result)
    return run
