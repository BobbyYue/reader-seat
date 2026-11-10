"""Compute reader outcomes from bound reviews, not from word counts or taste."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

VERSION = 1
CLASSES = {"missing_required_answer", "source_unknown", "detail"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def summarize(manifest, responses, evaluation):
    import reader_answers as ra

    plan = ra.verify_manifest(manifest)
    require(isinstance(responses, list) and isinstance(evaluation, dict), "Reader outcomes need actual response and evaluation records")
    require(evaluation.get("manifest_sha256") == ra.object_digest(manifest), "Reader outcome manifest changed")
    require(evaluation.get("response_sha256") == ra.object_digest(responses), "Reader outcomes are not bound to raw answers")
    judge = evaluation.get("reviewer_id")
    require(nonempty(judge), "Reader outcome evaluator identity is missing")
    by_surface = {}
    surfaces = {s["id"]: s for s in manifest["surfaces"]}
    for response in responses:
        sid = response.get("surface_id")
        require(sid in surfaces and sid not in by_surface, "Duplicate or unknown reader outcome surface")
        require(response.get("surface_sha256") == surfaces[sid]["sha256"], "Reader outcome surface changed")
        require(nonempty(response.get("reader_id")) and response["reader_id"] != judge, "Reader outcome needs an independent reader")
        require(isinstance(response.get("findings"), list) and response["findings"] and all(nonempty(x) for x in response["findings"]), "Reader findings must preserve actual words")
        require(isinstance(response.get("remaining_questions"), list) and all(nonempty(x) for x in response["remaining_questions"]), "Record raw remaining questions, including an empty array")
        by_surface[sid] = response
    require(set(by_surface) == set(surfaces), "All reading surfaces need raw responses")
    expected = {(a["id"], sid) for a in plan["answers"] for sid in a["required_on"]}
    checks = evaluation.get("answers")
    require(isinstance(checks, list) and len(checks) == len(expected), "Reader outcomes must retain every required answer")
    indexed = {}
    for check in checks:
        key = (check.get("answer_id"), check.get("surface_id"))
        require(key in expected and key not in indexed, "Duplicate or unknown answer outcome")
        require(check.get("status") in {"pass", "fail", "unassessed"}, "Answer outcome requires pass, fail or unassessed")
        require(nonempty(check.get("rationale")), "Explain each answer outcome")
        quote = check.get("reader_quote")
        raw = "\n".join(by_surface[key[1]]["findings"])
        require(nonempty(quote) and quote in raw, "Answer outcomes must quote actual blind findings")
        indexed[key] = check
    states = {}
    for answer in plan["answers"]:
        statuses = [indexed[(answer["id"], sid)]["status"] for sid in answer["required_on"]]
        states[answer["id"]] = "fail" if "fail" in statuses else "unassessed" if "unassessed" in statuses else "pass"
    correct = sum(x == "pass" for x in states.values())
    pending = sum(x == "unassessed" for x in states.values())
    question_slots = {(sid, i) for sid, r in by_surface.items() for i in range(len(r["remaining_questions"]))}
    reviews = evaluation.get("questions")
    require(isinstance(reviews, list) and len(reviews) == len(question_slots), "Classify every raw follow-up exactly once")
    seen, groups, exact_groups, records = set(), {}, {}, []
    answer_map = {a["id"]: a for a in plan["answers"]}
    for item in reviews:
        key = (item.get("surface_id"), item.get("index"))
        require(type(key[1]) is int and key in question_slots and key not in seen, "Unknown or duplicate raw follow-up index")
        seen.add(key)
        group, kind = item.get("group_id"), item.get("classification")
        require(nonempty(group) and kind in CLASSES and nonempty(item.get("rationale")), "Each follow-up needs a deduplication group, classification and reason")
        related = item.get("answer_ids")
        require(isinstance(related, list) and all(isinstance(a, str) for a in related)
                and len(related) == len(set(related)) and set(related) <= set(answer_map), "Follow-up answer_ids must reference the locked plan")
        require(all(key[0] in answer_map[a]["required_on"] for a in related), "Follow-up refers to an answer outside this reading surface")
        if kind == "source_unknown":
            require(related and all(answer_map[a]["source_status"] == "unknown" for a in related), "A known required answer cannot be relabeled source_unknown")
            disclosure = item.get("disclosure_quote")
            visible = Path(surfaces[key[0]]["path"]).read_text(encoding="utf-8")
            require(nonempty(disclosure) and disclosure in visible, "Source-unknown follow-up needs the actual visible uncertainty disclosure")
        if kind == "detail":
            require(all(states[a] == "pass" for a in related), "An unresolved required answer cannot be relabeled optional detail")
        if kind == "missing_required_answer" and related:
            require(any(states[a] == "fail" for a in related), "A mapped missing answer needs a failed required answer, not only passed or pending answers")
        raw_question = by_surface[key[0]]["remaining_questions"][key[1]]
        normalized = re.sub(r"\s+", "", raw_question).casefold()
        signature = (kind, tuple(sorted(related)))
        require(group not in groups or groups[group] == signature, "One follow-up group cannot mix classifications or required answers")
        require(normalized not in exact_groups or exact_groups[normalized] == group, "An identical follow-up cannot be counted as different problems")
        groups[group], exact_groups[normalized] = signature, group
        records.append({"surface_id": key[0], "index": key[1], "question": raw_question,
                        "group_id": group, "classification": kind, "answer_ids": related,
                        "rationale": item["rationale"], "disclosure_quote": item.get("disclosure_quote"),
                        "action": "revise" if kind == "missing_required_answer" else "preserve"})
    counts = {kind: sum(signature[0] == kind for signature in groups.values()) for kind in sorted(CLASSES)}
    basis = {"reader": plan["reader"], "source_sha256": ra.load(manifest["lock_path"])["source"]["sha256"],
             "depth": plan.get("depth", {}).get("mode"),
             "surfaces": [{"id": s["id"], "mode": s["mode"]} for s in plan["surfaces"]],
             "answers": [{**{k: a.get(k) for k in ("id", "kind", "question", "expected_information", "source_status", "required_on")},
                          **({"reader_use": a["reader_use"]} if "reader_use" in a else {})} for a in plan["answers"]]}
    lock = ra.load(manifest["lock_path"])
    quality = {}
    if lock.get("judgment_quality_version") == 1:
        import judgment_quality
        quality["judgment_quality"] = judgment_quality.summarize(manifest, plan, evaluation, lock)
    return {"version": VERSION, "status": "partial" if pending else "measured", "reader_type": "ai", "artifact_sha256": manifest["artifact"]["sha256"],
            **quality,
            "basis_sha256": ra.object_digest(basis), "basis": basis,
            "source_fidelity": evaluation.get("source_fidelity", "unassessed"),
            "plan_source_coverage": evaluation.get("plan_source_coverage", "unassessed"),
            "reader_ids": sorted({r["reader_id"] for r in responses}), "evaluator_id": judge,
            "evidence": {"manifest_sha256": ra.object_digest(manifest), "responses_sha256": ra.object_digest(responses), "evaluation_sha256": ra.object_digest(evaluation)},
            "questions": {"total": len(states), "correct": correct, "incorrect": len(states) - correct - pending,
                          "unassessed": pending, "correct_rate": correct / len(states) if states else None,
                          "complete": pending == 0, "states": states},
            "followups": {"raw_count": len(records), "group_count": len(groups), "avoidable_count": counts["missing_required_answer"],
                          "source_unknown_count": counts["source_unknown"], "detail_count": counts["detail"], "records": records},
            "comparison": {"status": "not_measured", "reason": "No comparable baseline was supplied; no improvement or human reading gain was measured."},
            "boundary": "Code recomputes counts from source-review judgments; it does not establish semantic truth, real reader identity or human understanding. Required explanations and useful transitions need not add a new fact in every sentence."}


def from_receipt(path):
    import reader_answers as ra

    receipt = ra.load(path)
    for name in ("manifest", "responses", "evaluation"):
        require(ra.digest(receipt[name + "_path"]) == receipt[name + "_sha256"], "Reader outcome receipt evidence changed: " + name)
    result = summarize(ra.load(receipt["manifest_path"]), ra.load(receipt["responses_path"]), ra.load(receipt["evaluation_path"]))
    require(receipt.get("reader_outcomes") == result, "Stored reader outcomes differ from bound raw reviews")
    return result


def compare(baseline, candidate):
    import reader_answers as ra
    require(baseline.get("version") == VERSION and candidate.get("version") == VERSION, "Comparison needs versioned reader outcomes")
    require(all(item["basis_sha256"] == ra.object_digest(item["basis"]) for item in (baseline, candidate)), "Comparison basis hash is invalid")
    require(baseline["basis_sha256"] == candidate["basis_sha256"] and baseline["basis"] == candidate["basis"], "Reader, source, questions, judging criteria or reading scope changed")
    require(baseline["reader_type"] == candidate["reader_type"] == "ai", "Do not mix AI and human reading results")
    require(not set(baseline["reader_ids"]) & set(candidate["reader_ids"]), "Version comparison needs fresh independent reading contexts")
    require(baseline["artifact_sha256"] != candidate["artifact_sha256"], "Identical artifacts do not establish a version improvement")
    require(baseline["questions"]["complete"] and candidate["questions"]["complete"], "Pending answers cannot establish a complete comparison")
    return {"version": VERSION, "status": "measured", "reader_type": "ai", "basis_sha256": baseline["basis_sha256"],
            "baseline_artifact_sha256": baseline["artifact_sha256"], "candidate_artifact_sha256": candidate["artifact_sha256"],
            "correct_rate_change": candidate["questions"]["correct_rate"] - baseline["questions"]["correct_rate"],
            "avoidable_followup_change": candidate["followups"]["avoidable_count"] - baseline["followups"]["avoidable_count"],
            "regressed_answer_ids": [key for key, value in baseline["questions"]["states"].items()
                                     if value == "pass" and candidate["questions"]["states"][key] != "pass"],
            "source_fidelity": {"baseline": baseline["source_fidelity"], "candidate": candidate["source_fidelity"]},
            "boundary": "One same-task AI version comparison, not a human learning experiment or a statistically established improvement. Check regressions and source fidelity separately."}


def main():
    import reader_answers as ra

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("compare")
    command.add_argument("--baseline-receipt", required=True)
    command.add_argument("--candidate-receipt", required=True)
    command.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        output = Path(args.output)
        require(not output.exists(), "Preserve previous comparison records")
        result = compare(from_receipt(args.baseline_receipt), from_receipt(args.candidate_receipt))
        result["receipts"] = [{"path": str(Path(p).resolve()), "sha256": ra.digest(p)} for p in (args.baseline_receipt, args.candidate_receipt)]
        ra.save(output, result)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print("FAIL: " + str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
