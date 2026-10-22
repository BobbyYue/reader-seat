"""Synthetic process fixtures, not real independent reviews or quality proof."""
import json
from pathlib import Path
from execution_fixture import init_fixture, seed_fixture
from context_fixture import structural_context, structural_attribution


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return Path(path)


def prepare_flow(lifecycle, base, artifact, native_result=None, profile="functional", authority="confirmed", rounds=1, verdict="pass", plan_updates=None, layout_status="inspected"):
    root = Path(base) / ("lifecycle-fixture-" + profile)
    root.mkdir()
    value = lifecycle.visible(artifact)
    quote = next(line.strip() for line in value.splitlines() if line.strip())[:60]
    source = root / "source.txt"
    source.write_text(value, encoding="utf-8")
    plan = {
        "task": "Synthetic process fixture", "genre": "work report" if profile == "functional" else "scene",
        "domain": "synthetic testing", "purpose": "Exercise stage and version checks", "language": "zh", "format": "text",
        "reader": {"knowledge": "Only the supplied synthetic text", "need": "Read the text without author context"},
        "authority": {"status": authority, "basis": "Synthetic unit-test instruction", "reference": "fixture request, not user acceptance evidence"},
        "material": {"mode": "source-grounded" if profile == "functional" else "fiction", "gaps": []},
        "reading_path": [{"id": "unit", "purpose": "Exercise this complete synthetic unit"}],
        "required_answers": [{"id": "A1", "question": "What did the source state?", "expected": quote, "source_location": "synthetic source.txt"}],
        "literary_intent": "Preserve the concrete situation and allow supported plural interpretations", "constraints": [],
        "author_context_id": "synthetic-author"
    }
    plan.update(plan_updates or {})
    plan_path = save(root / "plan.json", plan)
    run = root / "run"
    lifecycle.init_run(run, plan_path, profile, [source])
    mode = 'self-check' if native_result and Path(native_result).exists() and json.loads(Path(native_result).read_text()).get('review_method') == 'self-check' else 'independent'
    init_fixture(run, mode=mode)
    unit = save(root / "unit.json", {"unit_id": "unit", "summary": "Synthetic unit observation; not a semantic audit",
                "observations": [{"quote": quote, "reason": "Quote identity fixture"}]})
    lifecycle.record_unit(run, artifact, unit)
    report_path = root / "report.json"
    report = lifecycle.measure(run, artifact, report_path)
    record = {"text_sha256": report["text_sha256"], "report_sha256": lifecycle.ref(report_path)["sha256"],
              "observations": [{"metrics": list(report["metrics"]), "quote": quote, "reason": "Structural fixture only; no claim of actual metric-specific editorial judgment"}],
              "dispositions": [{"signal_id": s["id"], "decision": "retain", "reason": "Synthetic signal-handling fixture"}
                  for m in report["metrics"].values() for s in m["signals"]], "not_applicable": {}, "issues": []}
    if lifecycle.needs_layout(plan, artifact):
        evidence = save(root / "layout-fixture.json", {"synthetic": True, "warning": "Test input only, not an actual rendered-page inspection"})
        record["layout"] = {"status": layout_status, "reason": "Synthetic layout-record fixture only",
            "target": "unit-test fixture", "viewport": "synthetic", "findings": "Tests record wiring, not actual layout", "evidence_files": [str(evidence)]}
    record_path = save(root / "assessment.json", record)
    lifecycle.register_candidate(run, artifact, artifact, report_path, record_path)
    result_path = Path(native_result) if native_result else root / "review.json"
    for number in range(1, rounds+1):
        started = lifecycle.start_review(run, artifact, "during" if number == 1 and rounds > 1 else "after")
        current_result = result_path if number == rounds else root / ("review-"+str(number)+".json")
        issues = [] if verdict == "pass" else [{"impact": "Synthetic unresolved reader issue", "reason": "Fixture only"}]
        if profile == "literary":
            records = [{"role": role, "context_id": "synthetic-"+role+"-"+str(number),
                        "packet_sha256": started["packets"][role]["sha256"], "verdict": verdict,
                        "summary": "Synthetic independent-context record; not an actual reviewer",
                        "evidence": [{"quote": quote, "reason": "Exact quote fixture"}], "issues": issues}
                       for role in ("professional", "reader")]
            records[0]['context_review'] = structural_context(value, 'literary')
            records[0]['source_attribution'] = structural_attribution(value, value, 'source', 'literary')
            records[1]['attribution_replay'] = structural_attribution(value, profile='literary')
            save(current_result, {"reviewer_records": records, "issues": issues})
        elif not current_result.exists():
            save(current_result, {"status": verdict, "issues": issues})
        lifecycle.finish_review(run, current_result, verdict, issues=issues)
        if mode == 'independent':
            seed_fixture(run, current_result)
    return {"run": run, "plan": plan_path, "source": source, "result": result_path, "report": report_path,
            "record": record_path, "unit": unit, "root": root}
