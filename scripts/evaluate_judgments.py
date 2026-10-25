"""Measure reviewer errors against a frozen reference set; never certify quality."""
import argparse
import hashlib
import json
from pathlib import Path

LABELS = {"keep", "revise", "abstain"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def evaluate(dataset, results, dataset_sha256):
    if not isinstance(dataset, dict) or not isinstance(results, dict):
        raise ValueError("Expected dataset and results objects")
    if results.get("dataset_sha256") != dataset_sha256:
        raise ValueError("Results belong to a different frozen dataset")
    if dataset.get("label_origin") not in {"synthetic", "human-reviewed"} or not dataset.get("label_reference"):
        raise ValueError("State how the reference labels were obtained")
    cases, expected = dataset.get("cases"), dataset.get("expected_runs")
    if not isinstance(cases, list) or not cases or not isinstance(expected, list) or not expected:
        raise ValueError("Freeze cases and expected runs before evaluation")
    by_case = {}
    for case in cases:
        if (not isinstance(case, dict) or not isinstance(case.get("id"), str) or not case["id"]
                or case["id"] in by_case or case.get("expected") not in {"keep", "revise"}
                or not isinstance(case.get("category"), str) or not case["category"]):
            raise ValueError("Invalid or duplicate reference case")
        by_case[case["id"]] = case
    plans = {}
    for run in expected:
        if (not isinstance(run, dict) or not all(isinstance(run.get(k), str) and run[k] for k in ("id", "host", "model"))
                or run["id"] in plans):
            raise ValueError("Invalid or duplicate expected run")
        plans[run["id"]] = run
    records = results.get("records")
    if not isinstance(records, list):
        raise ValueError("Missing actual result records")
    seen, rows = set(), []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Result must be an object")
        pair = (record.get("run_id"), record.get("case_id"))
        if any(not isinstance(x, str) for x in pair) or pair in seen or pair[0] not in plans or pair[1] not in by_case:
            raise ValueError("Unknown, missing or duplicate run/case")
        if record.get("status") not in {"completed", "error"}:
            raise ValueError("Record completed or failed attempts explicitly")
        if record["status"] == "completed" and record.get("prediction") not in LABELS:
            raise ValueError("A completed prediction needs keep/revise/abstain")
        if not isinstance(record.get("evidence_ref"), str) or not record["evidence_ref"]:
            raise ValueError("Reference the original result or failure record")
        seen.add(pair)
        rows.append({**record, "expected": by_case[pair[1]]["expected"], "category": by_case[pair[1]]["category"]})
    planned = {(run, case) for run in plans for case in by_case}
    missing = sorted(planned - seen)

    def metrics(group, total):
        complete = [r for r in group if r["status"] == "completed"]
        decided = [r for r in complete if r["prediction"] != "abstain"]
        correct = sum(r["prediction"] == r["expected"] for r in decided)
        unsafe = sum(r["expected"] == "revise" and r.get("prediction") == "keep" and r["status"] == "completed" for r in group)
        unnecessary = sum(r["expected"] == "keep" and r.get("prediction") == "revise" and r["status"] == "completed" for r in group)
        rate = lambda n, d: n / d if d else None
        return {"planned": total, "recorded": len(group), "completed": len(complete), "decided": len(decided),
                "abstained": len(complete) - len(decided), "errors": len(group) - len(complete),
                "correct": correct, "missed_problem": unsafe, "unnecessary_revision": unnecessary,
                "decision_coverage": rate(len(decided), total), "accuracy_on_decided": rate(correct, len(decided)),
                "correct_over_planned": rate(correct, total)}
    per_run = {run: metrics([r for r in rows if r["run_id"] == run], len(by_case)) for run in plans}
    by_category = {category: metrics([r for r in rows if r["category"] == category],
                    len(plans) * sum(c["category"] == category for c in cases)) for category in sorted({c["category"] for c in cases})}
    unstable = [case for case in by_case if len({r["prediction"] for r in rows
                    if r["case_id"] == case and r["status"] == "completed"}) > 1]
    return {"status": "incomplete" if missing else "measured", "dataset_sha256": dataset_sha256,
            "label_origin": dataset["label_origin"], "label_reference": dataset["label_reference"],
            "total": metrics(rows, len(planned)), "by_run": per_run, "by_category": by_category,
            "worst_run_correct_over_planned": min(v["correct_over_planned"] for v in per_run.values()),
            "missing": missing, "disagreement_case_ids": unstable,
            "quality_certified": False, "host_integration_certified": False,
            "limits": "Arithmetic only. Label provenance and real host execution require independent verification; no deployment threshold is implied."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = evaluate(json.loads(args.dataset.read_text()), json.loads(args.results.read_text()), sha(args.dataset))
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
    print(json.dumps({"status": report["status"], "quality_certified": False}))
    return 1 if report["missing"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
