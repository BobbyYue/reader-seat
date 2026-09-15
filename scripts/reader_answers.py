#!/usr/bin/env python3
"""Source-locked reader questions and actually isolated reading surfaces.

This module validates evidence bindings and completeness, not semantic truth.
Reader responses remain blind; a separate source reviewer evaluates them.
The same version is vendored in Reader's Seat and 3080 Brief for portability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path

CONTRACT_VERSION = "reader-answers-1"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def object_digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def plan_errors(plan):
    errors = []
    if not isinstance(plan, dict):
        return ["reader plan must be an object"]
    if plan.get("version") != CONTRACT_VERSION:
        errors.append("reader plan version is not reader-answers-1")
    reader = plan.get("reader", {})
    if not isinstance(reader, dict):
        return ["reader must be an object"]
    for field in ("profile", "known_context", "decision"):
        if not isinstance(reader.get(field), str) or not reader[field].strip():
            errors.append(f"reader.{field} must state the real audience and task")
    surfaces = plan.get("surfaces", [])
    if not isinstance(surfaces, list) or not surfaces:
        return errors + ["reader plan requires at least one reading surface"]
    ids = set()
    for surface in surfaces:
        if not isinstance(surface, dict):
            return ["each reading surface must be an object"]
        sid = surface.get("id")
        if not isinstance(sid, str) or not sid.strip():
            return ["surface IDs must be non-empty strings"]
        if sid in ids:
            errors.append("surface IDs must be present and unique")
        ids.add(sid)
        mode = surface.get("mode")
        if not isinstance(mode, str):
            return [f"{sid}: mode must be a string"]
        if mode not in {"headings", "blocks", "between", "opening", "full"}:
            errors.append(f"{sid}: invalid reading mode")
        if mode == "full" and not str(surface.get("reason", "")).strip():
            errors.append(f"{sid}: full reading requires a task-specific reason")
        if mode == "blocks" and not surface.get("block_ids"):
            errors.append(f"{sid}: blocks mode requires exact native block IDs")
        if mode == "blocks":
            block_ids = surface.get("block_ids")
            if (not isinstance(block_ids, list) or
                    any(not isinstance(v, str) or not v.strip() for v in block_ids)):
                return [f"{sid}: block_ids must be an array of non-empty strings"]
            if len(block_ids) != len(set(block_ids)):
                errors.append(f"{sid}: block_ids must be unique")
        if mode == "between" and not all(surface.get(k) for k in ("start", "end")):
            errors.append(f"{sid}: between mode requires unique start/end anchors")
    answers = plan.get("answers", [])
    if not isinstance(answers, list) or not answers:
        return errors + ["reader plan requires source-backed minimum answers"]
    answer_ids = set()
    for answer in answers:
        if not isinstance(answer, dict):
            return ["each required answer must be an object"]
        aid = answer.get("id")
        if not isinstance(aid, str) or not aid.strip():
            return ["answer IDs must be non-empty strings"]
        if aid in answer_ids:
            errors.append("answer IDs must be present and unique")
        answer_ids.add(aid)
        for field in ("question", "expected_information", "source_location"):
            if not isinstance(answer.get(field), str) or not answer[field].strip():
                errors.append(f"{aid}: missing {field}")
        if not isinstance(answer.get("source_status"), str) or answer.get("source_status") not in {"supported", "unknown"}:
            errors.append(f"{aid}: source_status must preserve supported or unknown")
        required = answer.get("required_on", [])
        if not isinstance(required, list) or any(not isinstance(v, str) for v in required):
            return [f"{aid}: required_on must be an array of surface IDs"]
        if not isinstance(required, list) or not required or set(required) - ids:
            errors.append(f"{aid}: required_on must name existing surfaces")
    for sid in ids:
        if not any(sid in a.get("required_on", []) for a in answers):
            errors.append(f"{sid}: surface has no reader-required answers")
    return errors


class SurfaceParser(HTMLParser):
    def __init__(self, mode, block_ids=()):
        super().__init__(convert_charrefs=True)
        self.mode, self.ids = mode, set(block_ids)
        self.stack, self.parts, self.found = [], [], set()
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        hidden = tag in {"script", "style", "template"} or "hidden" in attrs
        selected = ((self.mode == "headings" and re.fullmatch(r"h[1-6]", tag)) or
                    (self.mode == "blocks" and attrs.get("id") in self.ids))
        if selected:
            if self.mode == "blocks" and attrs.get("id") in self.found:
                raise ValueError("requested native block ID is duplicated")
            self.found.add(attrs.get("id"))
            self.parts.append("\n")
        void = tag in {"br", "img", "hr", "input", "meta", "link", "source", "wbr"}
        if not void:
            self.stack.append((tag, bool(selected), hidden))
        if tag == "br" and any(item[1] for item in self.stack):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                if any(item[1] for item in self.stack[i:]):
                    self.parts.append("\n")
                del self.stack[i:]
                break

    def handle_data(self, text):
        if any(item[1] for item in self.stack) and not any(item[2] for item in self.stack):
            self.parts.append(text)


def rich_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(str(v.get("text", "")) for v in value if isinstance(v, dict))
    raise ValueError("opening must contain visible strings or rich-text spans")


def extract_surface(text, surface):
    mode = surface["mode"]
    if mode == "full":
        result = text
    elif mode == "opening":
        brief = json.loads(text)
        lines = brief["opening"]["lines"]
        if not isinstance(lines, list) or not lines:
            raise ValueError("opening.lines must be a non-empty array")
        result = "\n".join(rich_text(line) for line in lines)
    elif mode == "between":
        start, end = surface["start"], surface["end"]
        if text.count(start) != 1 or text.count(end) != 1:
            raise ValueError("reading surface anchors must each match once")
        first, last = text.index(start), text.index(end)
        if last <= first:
            raise ValueError("reading surface anchors are reversed")
        result = text[first:last]
    elif re.search(r"<[A-Za-z][^>]*>", text) and mode in {"headings", "blocks"} and not (
            mode == "headings" and re.search(r"^#{1,6}\s+", text, re.MULTILINE)):
        parser = SurfaceParser(mode, surface.get("block_ids", []))
        parser.feed(text)
        if mode == "blocks" and parser.ids - parser.found:
            raise ValueError("requested native blocks are missing")
        result = "\n".join(line.strip() for line in "".join(parser.parts).splitlines() if line.strip())
    elif mode == "headings":
        # Ignore fenced code; an example heading is not a visible document heading.
        lines, fenced = [], False
        for line in text.splitlines():
            if re.match(r"^\s*(```|~~~)", line):
                fenced = not fenced
            elif not fenced and re.match(r"^#{1,6}\s+", line):
                heading = re.sub(r"^#{1,6}\s+", "", line).strip()
                lines.append(re.sub(r"</?[A-Za-z][^>]*>", "", heading))
        result = "\n".join(lines)
    else:
        raise ValueError("unsupported surface format; supply a real UTF-8 content snapshot")
    if not result.strip():
        raise ValueError("selected reading surface is empty")
    return result.strip() + "\n"


def lock_plan(plan_path, source_path):
    plan = load(plan_path)
    errors = plan_errors(plan)
    if errors:
        raise ValueError("; ".join(errors))
    return {"version": CONTRACT_VERSION, "plan": {"path": str(Path(plan_path).resolve()),
            "sha256": digest(plan_path)}, "source": {"path": str(Path(source_path).resolve()),
            "sha256": digest(source_path)}}


def open_lock(lock_path):
    lock = load(lock_path)
    if lock.get("version") != CONTRACT_VERSION:
        raise ValueError("unsupported reader-plan lock")
    for name in ("plan", "source"):
        item = lock[name]
        if digest(item["path"]) != item["sha256"]:
            raise ValueError(f"locked {name} changed; relock and rerun affected checks")
    plan = load(lock["plan"]["path"])
    errors = plan_errors(plan)
    if errors:
        raise ValueError("; ".join(errors))
    return lock, plan


def prepare(lock_path, artifact_path, output_dir, content_snapshot=None):
    lock, plan = open_lock(lock_path)
    artifact = Path(artifact_path)
    snapshot = Path(content_snapshot) if content_snapshot else artifact
    text = snapshot.read_text(encoding="utf-8")
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise ValueError("surface output directory must be empty")
    output.mkdir(parents=True, exist_ok=True)
    surfaces = []
    for surface in plan["surfaces"]:
        body = extract_surface(text, surface)
        filename = hashlib.sha256(surface["id"].encode()).hexdigest()[:16]
        path = output / f"surface-{filename}.txt"
        path.write_text(body, encoding="utf-8")
        # No artifact/source/plan path, answer checklist or expected response reaches a blind reader.
        packet = {"version": CONTRACT_VERSION, "surface_id": surface["id"],
                  "reader": plan["reader"], "surface": {"path": str(path.resolve()), "sha256": digest(path)},
                  "instructions": "Read only the supplied surface. Independently restate concrete findings and remaining decision-relevant questions. Do not infer from unseen body text or grade yourself.",
                  "response_fields": ["surface_id", "surface_sha256", "reader_id", "findings", "remaining_questions"]}
        packet_path = output / f"packet-{filename}.json"
        save(packet_path, packet)
        surfaces.append({"id": surface["id"], "path": str(path.resolve()), "sha256": digest(path),
                         "packet_path": str(packet_path.resolve()), "packet_sha256": digest(packet_path)})
    manifest = {"version": CONTRACT_VERSION, "lock_path": str(Path(lock_path).resolve()),
                "lock_sha256": digest(lock_path), "artifact": {"path": str(artifact.resolve()), "sha256": digest(artifact)},
                "snapshot": {"path": str(snapshot.resolve()), "sha256": digest(snapshot)}, "surfaces": surfaces}
    save(output / "surface-manifest.json", manifest)
    return manifest


def verify_manifest(manifest):
    if manifest.get("version") != CONTRACT_VERSION:
        raise ValueError("unsupported reading surface manifest")
    if digest(manifest["lock_path"]) != manifest["lock_sha256"]:
        raise ValueError("reader-plan lock changed")
    lock, plan = open_lock(manifest["lock_path"])
    for name in ("artifact", "snapshot"):
        item = manifest[name]
        if digest(item["path"]) != item["sha256"]:
            raise ValueError(f"{name} changed after surface extraction")
    text = Path(manifest["snapshot"]["path"]).read_text(encoding="utf-8")
    mapping = {s["id"]: s for s in manifest["surfaces"]}
    if set(mapping) != {s["id"] for s in plan["surfaces"]}:
        raise ValueError("reading surfaces differ from locked plan")
    for surface in plan["surfaces"]:
        entry = mapping[surface["id"]]
        if digest(entry["path"]) != entry["sha256"] or digest(entry["packet_path"]) != entry["packet_sha256"]:
            raise ValueError("blind surface or packet changed")
        if Path(entry["path"]).read_text(encoding="utf-8") != extract_surface(text, surface):
            raise ValueError("blind surface is not the requested artifact extraction")
        packet = load(entry["packet_path"])
        if set(packet) != {"version", "surface_id", "reader", "surface", "instructions", "response_fields"}:
            raise ValueError("blind packet contains unexpected context or missing fields")
        if (packet.get("version") != CONTRACT_VERSION or packet.get("surface_id") != surface["id"] or
                packet.get("reader") != plan["reader"] or
                packet.get("surface") != {"path": entry["path"], "sha256": entry["sha256"]} or
                packet.get("instructions") != "Read only the supplied surface. Independently restate concrete findings and remaining decision-relevant questions. Do not infer from unseen body text or grade yourself." or
                packet.get("response_fields") != ["surface_id", "surface_sha256", "reader_id", "findings", "remaining_questions"]):
            raise ValueError("blind packet differs from its locked reading surface")
    return plan


def validate_answers(manifest, responses, evaluation):
    errors = []
    if not isinstance(manifest, dict):
        return ["reading manifest must be an object"]
    if not isinstance(evaluation, dict) or not isinstance(responses, list):
        return ["responses must be an array and evaluation an object"]
    if any(not isinstance(r, dict) for r in responses):
        return ["each blind response must be an object"]
    if any(not isinstance(evaluation.get(k, []), list) or
           any(not isinstance(v, dict) for v in evaluation.get(k, [])) for k in ("answers", "questions")):
        return ["answer and question evaluations must be arrays of objects"]
    def present_text(value):
        return isinstance(value, str) and bool(value.strip())
    for field in ("reviewer_id", "source_coverage_evidence", "plan_source_coverage", "source_fidelity"):
        if not present_text(evaluation.get(field)):
            if field == "reviewer_id":
                return ["answer evaluator reviewer_id identity is required as a non-empty string"]
            return [f"evaluation.{field} must be a non-empty string"]
    for response in responses:
        if any(not present_text(response.get(field)) for field in ("surface_id", "reader_id", "surface_sha256")):
            return ["blind response IDs and surface hash must be non-empty strings"]
    for check in evaluation.get("answers", []):
        if any(not present_text(check.get(field)) for field in ("answer_id", "surface_id", "reader_quote", "rationale", "status")):
            return ["answer evaluation fields must be non-empty strings"]
    for question in evaluation.get("questions", []):
        if (any(not present_text(question.get(field)) for field in ("surface_id", "classification", "rationale")) or
                type(question.get("index")) is not int or question["index"] < 0):
            return ["question fields require non-empty strings and a nonnegative integer index"]
    try:
        plan = verify_manifest(manifest)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        return [str(exc)]
    if evaluation.get("manifest_sha256") != object_digest(manifest):
        errors.append("answer evaluation is stale or from another manifest")
    if evaluation.get("response_sha256") != object_digest(responses):
        errors.append("answer evaluation is not bound to the raw blind responses")
    if evaluation.get("plan_source_coverage") != "pass" or not evaluation.get("source_coverage_evidence"):
        errors.append("source reviewer must confirm plan covers the user's decision-critical source information")
    if evaluation.get("source_fidelity") != "pass":
        errors.append("source fidelity must pass independently of answer coverage")
    judge = evaluation.get("reviewer_id")
    by_surface = {}
    for response in responses:
        sid = response.get("surface_id")
        if sid in by_surface:
            errors.append("duplicate blind surface response")
        by_surface[sid] = response
        if not response.get("reader_id") or response.get("reader_id") == judge:
            errors.append("source evaluator must differ from blind reader")
        if (not isinstance(response.get("findings"), list) or not response["findings"] or
                any(not isinstance(v, str) or not v.strip() for v in response["findings"])):
            errors.append(f"{sid}: findings must record the reader's actual understanding")
        if (not isinstance(response.get("remaining_questions"), list) or
                any(not isinstance(v, str) or not v.strip() for v in response["remaining_questions"])):
            errors.append(f"{sid}: missing remaining questions")
    if errors:
        return errors
    if not judge:
        errors.append("answer evaluator identity is required")
    if set(by_surface) != {s["id"] for s in manifest["surfaces"]}:
        errors.append("all locked reading surfaces need a blind response")
    for surface in manifest["surfaces"]:
        if by_surface.get(surface["id"], {}).get("surface_sha256") != surface["sha256"]:
            errors.append(f"{surface['id']}: blind response is not bound to the supplied surface")
    expected = {(a["id"], sid) for a in plan["answers"] for sid in a["required_on"]}
    checks = evaluation.get("answers", [])
    actual = [(c.get("answer_id"), c.get("surface_id")) for c in checks]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        errors.append("evaluation must cover every required answer on every assigned surface exactly once")
    for check in checks:
        sid = check.get("surface_id")
        quote = check.get("reader_quote", "")
        raw = "\n".join(str(v) for v in by_surface.get(sid, {}).get("findings", []))
        if check.get("status") != "pass":
            errors.append(f"{check.get('answer_id')}: required answer is missing or misunderstood")
        if not quote or quote not in raw:
            errors.append("answer match must quote the actual blind findings, not the author's expected answer")
        if not check.get("rationale"):
            errors.append("semantic answer match requires source-grounded rationale")
    expected_questions = {(sid, i) for sid, response in by_surface.items()
                          for i in range(len(response.get("remaining_questions", [])))}
    questions = evaluation.get("questions", [])
    actual_questions = [(q.get("surface_id"), q.get("index")) for q in questions]
    if len(actual_questions) != len(set(actual_questions)) or set(actual_questions) != expected_questions:
        errors.append("every reader follow-up question must be classified")
    for question in questions:
        classification = question.get("classification")
        if classification not in {"missing_required_answer", "source_unknown", "detail"} or not question.get("rationale"):
            errors.append("question requires a source-based classification and rationale")
        if classification == "missing_required_answer":
            errors.append("known decision-required answer was omitted from the reading surface")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    lock = sub.add_parser("lock")
    lock.add_argument("--plan", required=True)
    lock.add_argument("--source", required=True)
    lock.add_argument("--output", required=True)
    prepare_p = sub.add_parser("prepare")
    prepare_p.add_argument("--lock", required=True)
    prepare_p.add_argument("--artifact", required=True)
    prepare_p.add_argument("--content-snapshot")
    prepare_p.add_argument("--output-dir", required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--responses", required=True)
    verify.add_argument("--evaluation", required=True)
    verify.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        if args.command == "lock":
            if Path(args.output).exists():
                raise ValueError("plan lock already exists; do not overwrite evidence")
            save(args.output, lock_plan(args.plan, args.source))
        elif args.command == "prepare":
            prepare(args.lock, args.artifact, args.output_dir, args.content_snapshot)
        else:
            manifest, responses, evaluation = load(args.manifest), load(args.responses), load(args.evaluation)
            errors = validate_answers(manifest, responses, evaluation)
            save(args.output, {"version": CONTRACT_VERSION, "status": "pass" if not errors else "fail",
                 "manifest_path": str(Path(args.manifest).resolve()), "manifest_sha256": digest(args.manifest),
                 "responses_path": str(Path(args.responses).resolve()), "responses_sha256": digest(args.responses),
                 "evaluation_path": str(Path(args.evaluation).resolve()), "evaluation_sha256": digest(args.evaluation),
                 "errors": errors})
            if errors:
                raise ValueError("; ".join(errors))
        print("PASS: " + args.command)
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print("FAIL: " + str(exc))
        return 1


def validate_receipt(path, artifact_path=None):
    try:
        receipt = load(path)
        for name in ("manifest", "responses", "evaluation"):
            if digest(receipt[name + "_path"]) != receipt[name + "_sha256"]:
                return [f"reader-answer {name} evidence changed"]
        manifest = load(receipt["manifest_path"])
        if artifact_path and manifest["artifact"]["sha256"] != digest(artifact_path):
            return ["reader-answer receipt belongs to a different artifact"]
        errors = validate_answers(manifest, load(receipt["responses_path"]), load(receipt["evaluation_path"]))
        if receipt.get("status") != "pass":
            errors.append("reader-answer receipt did not pass")
        return errors
    except (ValueError, KeyError, TypeError, OSError) as exc:
        return [str(exc)]


if __name__ == "__main__":
    raise SystemExit(main())
