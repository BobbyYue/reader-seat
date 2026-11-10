"""Validate bound task-value judgments within the existing source review."""
from pathlib import Path

VERSION = 1
STATES = {"pass", "fail", "unassessed"}
FORMS = {"finding", "fact", "explanation", "instruction", "unknown", "method_note", "topic_label"}
CONTRACT = {
    "where": "Each existing answers[] item includes judgment; reuse this source review and the actual blind reader_quote, never add a reviewer.",
    "fields": "judgment={question_fit,answer_fit,support_fit:pass|fail|unassessed,form:finding|fact|explanation|instruction|unknown|method_note|topic_label,inference:boolean,candidate_quote,source_quote,bridge,rationale,repair}",
    "criteria": "question_fit: frozen question and reader_use resolve a specific reader need, not merely enumerate topics. answer_fit: actual surface and blind replay supply the needed answer. A request for a finding is not satisfied by saying distinctions should be made or analysis is needed. Instructions and method notes are valid when that is the task. support_fit: evidence supports the stated claim; explain the inferential bridge when inference=true, without turning configuration into observed behavior, causality or measured business loss.",
    "evidence": "candidate_quote must occur on this actual reading surface; source_quote in the locked source. Reuse exact compact excerpts. bridge may be empty for direct facts, instructions and disclosed unknowns. rationale explains the contextual judgment; repair required for a failure or unassessed check. Non-pass cannot coexist with answer status=pass. No universal number/action/visual or conclusion-heading requirement; no forced visible template.",
}


def text(value):
    return isinstance(value, str) and bool(value.strip())


def plan_errors(plan):
    return [f"{a['id']}: reader_use must say what this answer lets the reader know, judge or do"
            for a in plan["answers"] if not text(a.get("reader_use"))]


def summarize(manifest, plan, evaluation, lock):
    def need(condition, message):
        if not condition:
            raise ValueError("judgment quality: " + message)

    source = Path(lock["source"]["path"]).read_text(encoding="utf-8")
    surfaces = {s["id"]: Path(s["path"]).read_text(encoding="utf-8") for s in manifest["surfaces"]}
    answers = {a["id"]: a for a in plan["answers"]}
    records = []
    for check in evaluation["answers"]:
        review = check.get("judgment")
        need(isinstance(review, dict), "each answer needs its actual task-value review")
        for key in ("question_fit", "answer_fit", "support_fit"):
            need(review.get(key) in STATES, "record " + key + " as pass, fail or unassessed")
        need(review.get("form") in FORMS and type(review.get("inference")) is bool, "declare actual answer form and inference")
        need(text(review.get("rationale")), "give a contextual rationale, not only a status")
        for key, actual in (("candidate_quote", surfaces[check["surface_id"]]), ("source_quote", source)):
            need(text(review.get(key)) and review[key] in actual, key + " must quote bound actual text")
        need(isinstance(review.get("bridge"), str), "record bridge, using an empty string for direct information")
        if review["inference"]:
            need(text(review["bridge"]), "an inferred claim needs its evidence-to-claim bridge")
        pending = [k for k in ("question_fit", "answer_fit", "support_fit") if review[k] != "pass"]
        need(not pending or check["status"] != "pass", "failed or pending task-value judgment cannot coexist with a passed answer")
        need(isinstance(review.get("repair"), str) and (not pending or text(review["repair"])), "non-pass needs a concrete repair")
        records.append({"answer_id": check["answer_id"], "surface_id": check["surface_id"],
                        "reader_use": answers[check["answer_id"]]["reader_use"], **review})
    problems = [{"answer_id": r["answer_id"], "surface_id": r["surface_id"],
                 "checks": [k for k in ("question_fit", "answer_fit", "support_fit") if r[k] != "pass"],
                 "reason": r["rationale"], "repair": r["repair"]}
                for r in records if any(r[k] != "pass" for k in ("question_fit", "answer_fit", "support_fit"))]
    return {"version": VERSION, "status": "revision_required" if problems else "pass",
            "problems": problems, "records": records,
            "boundary": "Code verifies coverage, text bindings and declared consistency; question usefulness, reasoning validity and understanding remain semantic review judgments."}
