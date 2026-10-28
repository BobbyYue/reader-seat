#!/usr/bin/env python3
"""Version-bound writing stages and review signals; no model or network calls.

This controls registered evidence and checked exports, not unrestricted host
behavior, generation chronology, independent identity, or semantic truth.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
from html.parser import HTMLParser
import json
import math
import os
from pathlib import Path
import re
import statistics
import sys
import context_value
import defensive_expression
import direct_expression
import source_attribution
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

CONFIG = Path(__file__).resolve().parents[1] / "config" / "writing-quality.json"


class LifecycleError(ValueError):
    pass


def need(value, message):
    if not value:
        raise LifecycleError(message)


def nonempty(value, label):
    need(isinstance(value, str) and bool(value.strip()), label + " must contain text")
    return value


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())


def load_json(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    need(isinstance(value, dict), "Expected a JSON object")
    return value


def text(path):
    value = Path(path).read_text(encoding="utf-8")
    return nonempty(value, "Text file")


def stamp():
    return datetime.now(timezone.utc).isoformat()


def ref(path):
    p = Path(path).resolve()
    need(p.is_file(), "Evidence file is missing")
    return {"path": str(p), "sha256": sha(p.read_bytes())}


def verify_ref(value):
    need(ref(value["path"]) == value, "Evidence changed since registration")


def compact(value):
    return "".join(unicodedata.normalize("NFC", value).split())


def needs_layout(plan, artifact_path):
    return plan["format"] in {"html", "feishu", "word", "slides", "pdf"} or Path(artifact_path).suffix.lower() in {".html", ".htm", ".docx", ".pptx", ".pdf"}


class Surface(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "head"}:
            self.hidden += 1
        if not self.hidden and tag in {"p", "div", "li", "tr", "td", "th", "br", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "head"}:
            self.hidden = max(0, self.hidden - 1)
        if not self.hidden and tag in {"p", "div", "li", "tr", "td", "th", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def visible(path):
    raw = text(path)
    if Path(path).suffix.lower() in {".html", ".htm", ".xml"}:
        parser = Surface()
        parser.feed(raw)
        raw = "".join(parser.parts)
    return unicodedata.normalize("NFC", raw)


def artifact_text(path):
    suffix = Path(path).suffix.lower()
    if suffix in {".html", ".htm", ".xml", ".txt", ".md", ".markdown"}:
        return visible(path)
    if suffix in {".docx", ".pptx"}:
        with zipfile.ZipFile(path) as archive:
            names = (["word/document.xml"] if suffix == ".docx" else
                     sorted((n for n in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                            key=lambda n: int(re.search(r"slide(\d+)\.xml", n).group(1))))
            parts = []
            for name in names:
                root = ET.fromstring(archive.read(name))
                for paragraph in root.iter():
                    if paragraph.tag.rsplit("}", 1)[-1] == "p":
                        parts.append("".join(n.text or "" for n in paragraph.iter() if n.tag.rsplit("}", 1)[-1] == "t"))
            return unicodedata.normalize("NFC", "\n".join(parts))
    raise LifecycleError("Unsupported delivery type: no verified text extraction adapter")


def write_json(path, value, exclusive=False):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if exclusive:
        with p.open("x", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
        p.chmod(0o600)
        return
    fd, name = tempfile.mkstemp(prefix=".lifecycle-", dir=p.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, p)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def seal(state):
    return digest({k: v for k, v in state.items() if k != "state_digest"})


def implementation():
    return {"engine": sha(Path(__file__).read_bytes()), "config": ref(CONFIG),
            "defensive_expression": sha(Path(defensive_expression.__file__).read_bytes()),
            "direct_expression": sha(Path(direct_expression.__file__).read_bytes())}


@contextmanager
def session(run, mutate=False):
    p = Path(run)
    need(p.is_dir() and not p.is_symlink(), "Lifecycle run is missing")
    statefile = p / "lifecycle.json"
    need(statefile.is_file() and not statefile.is_symlink(), "Lifecycle record is missing")
    fd = os.open(p / ".lifecycle-lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_json(statefile)
        need(state.get("version") == 1 and state.get("state_digest") == seal(state), "Lifecycle state integrity failed")
        need(state["implementation"] == implementation(), "Lifecycle implementation changed; migrate explicitly")
        for value in [state["plan_ref"], *state["sources"], *state["evidence"]]:
            verify_ref(value)
        for item in state["units"]:
            need(sha(item["text"].encode()) == item["text_sha256"], "Unit snapshot changed")
        previous = ""
        for number, item in enumerate(state["events"], 1):
            need(item["sequence"] == number and item["previous"] == previous, "Event sequence changed")
            need(item["digest"] == digest({k: v for k, v in item.items() if k != "digest"}), "Event digest changed")
            previous = item["digest"]
        yield state
        if mutate:
            state["state_digest"] = seal(state)
            write_json(statefile, state)


def event(state, operation, data):
    item = {"sequence": len(state["events"]) + 1, "at": stamp(), "operation": operation,
            "previous": state["events"][-1]["digest"] if state["events"] else "", "data": data}
    item["digest"] = digest(item)
    state["events"].append(item)


def validate_plan(plan, profile, sources):
    for key in ("task", "genre", "domain", "purpose", "language", "format"):
        nonempty(plan.get(key), key)
    reader = plan.get("reader", {})
    for key in ("knowledge", "need"):
        nonempty(reader.get(key), "reader." + key)
    authority = plan.get("authority", {})
    need(authority.get("status") in {"confirmed", "provisional"}, "Declare requirement authority")
    for key in ("basis", "reference"):
        nonempty(authority.get(key), "authority." + key)
    material = plan.get("material", {})
    need(material.get("mode") in {"source-grounded", "fiction", "nonfiction"}, "Declare material mode")
    if profile == "functional":
        need(material["mode"] != "fiction" and sources, "Functional writing requires captured source or user-request material")
        answers = plan.get("required_answers")
        need(isinstance(answers, list) and answers, "Plan required answers before drafting")
        ids = set()
        for a in answers:
            for key in ("id", "question", "expected", "source_location"):
                nonempty(a.get(key), "answer." + key)
            need(a["id"] not in ids, "Duplicate answer id")
            ids.add(a["id"])
        errors = direct_expression.plan_errors(plan.get('expression_plan'), answers)
        need(not errors, '; '.join(errors))
    else:
        nonempty(plan.get("literary_intent"), "literary_intent")
        need(isinstance(plan.get("constraints"), list), "Record literary constraints, even if empty")
    route = plan.get("reading_path")
    need(isinstance(route, list) and route, "Plan a reading path")
    ids = set()
    for unit in route:
        for key in ("id", "purpose"):
            nonempty(unit.get(key), "unit." + key)
        need(unit["id"] not in ids, "Duplicate reading unit")
        ids.add(unit["id"])
    for gap in material.get("gaps", []):
        nonempty(gap.get("reason"), "gap.reason")
        need(type(gap.get("critical")) is bool, "Gap critical must be boolean")
        need(gap.get("handling") in {"unresolved", "draft-only", "narrowed"}, "Unknown gap handling")
    for field in plan.get("time_fields", []):
        nonempty(field.get("expected"), "time expected value")
        nonempty(field.get("label"), "time field label")


def init_run(run, plan_path, profile, source_paths=()):
    config = load_json(CONFIG)
    need(profile in config["profiles"], "Unknown writing profile")
    plan = load_json(plan_path)
    sources = [ref(p) for p in source_paths]
    validate_plan(plan, profile, sources)
    p = Path(run)
    p.mkdir(parents=True, mode=0o700, exist_ok=False)
    state = {"version": 1, "profile": profile, "plan": plan, "plan_ref": ref(plan_path), "sources": sources,
             "implementation": implementation(),
             "units": [], "candidates": [], "rounds": [],
             "evidence": [ref(p) for p in plan.get("wordlists", {}).values()] +
                         [ref(i["source_path"]) for i in plan.get("evidence_items", []) if i.get("source_path")], "events": []}
    packet = p / "task-packet.json"
    write_json(packet, {"profile": config["profiles"][profile], "task": plan,
        "defensive_expression": {"before": "Identify real reader questions and necessary limits in the existing plan.",
            "during": "Unit checkpoints compute candidates; use existing observations for contextual choices.",
            "after": "Existing context review must resolve excess/pending items and compute C/D/R on the current surface."},
        "stage_order": ["init before drafting", "unit after a complete unit", "measure and candidate before review", "review-start before independent calls", "review-finish after all returns", "checked skill delivery"],
        "stop": "Count early and final independent batches together, at most three. Present the current draft with unresolved impact after exhaustion."}, exclusive=True)
    state["evidence"].append(ref(packet))
    event(state, "prewrite", {"plan_sha256": digest(plan), "authority": plan["authority"]["status"]})
    state["state_digest"] = seal(state)
    write_json(p / "lifecycle.json", state, exclusive=True)
    return {"status": "ready-to-draft", "profile": profile, "authority": plan["authority"]["status"], "task_packet": str(packet.resolve())}


def record_unit(run, text_path, record_path):
    value, record = visible(text_path), load_json(record_path)
    with session(run, True) as state:
        need(not state["rounds"] or state["rounds"][-1].get("verdict") is not None, "Finish the active review batch before changing text")
        need(record.get("unit_id") in {u["id"] for u in state["plan"]["reading_path"]}, "Unit not in prewrite reading path")
        nonempty(record.get("summary"), "unit summary")
        observations = record.get("observations")
        need(isinstance(observations, list) and observations, "Record an actual unit observation")
        for observation in observations:
            quote = nonempty(observation.get("quote"), "unit quote")
            need(quote in value, "Unit quote not in registered text")
            nonempty(observation.get("reason"), "unit observation reason")
        if state['profile'] == 'functional':
            errors = direct_expression.validate(record.get('expression_review'), value, 'during')
            need(not errors, '; '.join(errors))
        item = {"unit_id": record["unit_id"], "text": value, "text_sha256": sha(value.encode()), "record": record}
        item["defensive_expression"] = defensive_expression.measurement(value)
        state["units"].append(item)
        state["evidence"].append(ref(record_path))
        event(state, "during", {"unit_id": item["unit_id"], "text_sha256": item["text_sha256"]})
    return {"status": "unit-recorded", "unit_id": record["unit_id"],
            "defensive_expression": item["defensive_expression"]}


def p90(values):
    return sorted(values)[math.ceil(.9 * len(values)) - 1] if values else None


def measure_geometry(path, text_sha256):
    raw = load_json(path)
    need(raw.get("text_sha256") == text_sha256, "Geometry belongs to another text version")
    nonempty(raw.get("target"), "geometry target")
    nonempty(raw.get("capture_method"), "geometry capture method")
    need(raw.get("state") in {"default", "expanded"}, "Measure each expand state separately")
    viewport, total = raw.get("viewport_height"), raw.get("content_height")
    need(isinstance(viewport, (int, float)) and viewport > 0 and isinstance(total, (int, float)) and total > 0, "Geometry dimensions must come from an actual page")
    lines = raw.get("lines")
    need(isinstance(lines, list) and lines, "Actual rendered lines are missing")
    need(isinstance(raw.get("unmeasured_content"), list), "Declare unmeasured image or unloaded content")
    ids, screens, blocks, counts, ratios, gaps = set(), Counter(), Counter(), [], [], []
    for line in lines:
        need(line.get("id") not in ids and line.get("id") is not None, "Duplicate rendered line")
        ids.add(line["id"])
        count = len(compact(line.get("text", "")))
        y, height, font, line_height = (line.get(k) for k in ("y", "height", "font_size", "line_height"))
        need(all(isinstance(n, (int, float)) for n in (y, height, font, line_height)) and y >= 0 and min(height, font, line_height) > 0, "Invalid actual line geometry")
        need(y + height / 2 <= total, "Line outside measured content")
        nonempty(line.get("block_id"), "geometry block id")
        if count:
            screens[int((y + height / 2) // viewport)] += count
            blocks[line["block_id"]] += 1
            counts.append(count)
            ratios.append(line_height / font)
            if "paragraph_gap" in line:
                need(isinstance(line["paragraph_gap"], (int, float)) and line["paragraph_gap"] >= 0, "Invalid paragraph gap")
                gaps.append(line["paragraph_gap"] / line_height)
    screen_values = [screens[i] for i in range(math.ceil(total / viewport))]
    return {"state": raw["state"], "target": raw["target"], "geometry": ref(path),
        "per_screen_characters": screen_values, "first_screen_characters": screen_values[0],
        "median_screen_characters": statistics.median(screen_values), "maximum_screen_characters": max(screen_values),
        "densest_screens": sorted(screens, key=lambda s: screens[s], reverse=True)[:3],
        "maximum_block_lines": max(blocks.values(), default=0), "block_line_counts": dict(blocks),
        "total_screens": total / viewport, "last_screen_is_partial": total % viewport != 0,
        "line_characters_median": statistics.median(counts) if counts else None, "line_characters_max": max(counts, default=None),
        "line_spacing_ratio_median": statistics.median(ratios) if ratios else None,
        "paragraph_spacing_ratio_median": statistics.median(gaps) if gaps else None,
        "unmeasured_content": raw["unmeasured_content"],
        "boundary": "Recomputes supplied actual line geometry; does not authenticate its capture or measure fatigue."}


def measure_data(state, value, geometry_path=None):
    config, plan = load_json(CONFIG), state["plan"]
    chars = [c for c in value if not c.isspace()]
    paragraphs = [p.strip() for p in value.splitlines() if p.strip()]
    english = plan["language"].lower().startswith("en")
    sentences = ([s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", value) if s.strip()] if english else
                 [s.strip() for s in re.findall(r'''[^。！？!?\n]+(?:[。！？!?]+[”’」』"']*)?''', value) if s.strip()])
    sentences = [s for s in sentences if any(not c.isspace() and not unicodedata.category(c).startswith(("P", "S")) for c in s)]
    lengths = ([len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", s)) for s in sentences] if english else
               [sum(not c.isspace() and not unicodedata.category(c).startswith("P") for c in s) for s in sentences])
    length_p90, length_max = p90(lengths), max(lengths, default=None)
    words = re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)*", value)
    result = {m: {"measurement_status": "not-measured", "data": {}, "signals": []} for m in config["metrics"]}
    lex = result["vocabulary"]
    lex["data"] = {"characters": len(chars), "english_word_occurrences": len(words), "segmented_chinese_words": None}
    lex["unmeasured_reason"] = "No Chinese word tokenizer or universal reader vocabulary is assumed."
    for kind, filename in plan.get("wordlists", {}).items():
        need(kind in {"zh_char", "en_word"}, "Supported wordlists: zh_char and en_word; Chinese word segmentation requires a separate measured record")
        allowed = {line.strip() for line in text(filename).splitlines() if line.strip()}
        items = [c for c in chars if "\u4e00" <= c <= "\u9fff"] if kind == "zh_char" else [w.lower() for w in words]
        outside = [(i, w) for i, w in enumerate(items) if w not in allowed]
        lex["measurement_status"] = "partial"
        lex["data"][kind] = {"wordlist": ref(filename), "denominator": len(items), "outside_occurrences": len(outside),
                              "outside_unique": sorted({w for _, w in outside}),
                              "ratio": len(outside) / len(items) if items else None}
        lex["signals"] += [{"quote": w, "kind": "outside-list"} for w in sorted({w for _, w in outside})]
    terms = plan.get("terms", [])
    used = [t for t in terms if t["term"] in value]
    explained = [t for t in used if t.get("definition") and t["definition"] in value]
    result["terms"] = {"measurement_status": "measured", "data": {"applicable": len(used), "explicitly_explained": len(explained),
                         "ratio": len(explained) / len(used) if used else None},
                       "signals": [{"quote": t["term"], "kind": "missing-declared-explanation"} for t in used if t not in explained]}
    result["sentence_length"] = {"measurement_status": "partial", "data": {"method": "en-punctuation-whitespace-words-v1" if english else "zh-punctuation-line-characters-v1", "boundary": "Deterministic boundary heuristic; not a syntax parser. Review abbreviations or mixed-language segmentation separately.", "unit": "words" if english else "non-punctuation-characters", "count": len(lengths), "mean": statistics.mean(lengths) if lengths else None, "median": statistics.median(lengths) if lengths else None, "p90": length_p90, "max": length_max},
       "signals": [{"quote": s, "kind": "long-or-upper-decile"} for s, n in zip(sentences, lengths)
                   if (not english and n > config["signals"]["zh_sentence_review_start"]) or n > (length_p90 or n) or (english and n == length_max)]}
    plens = [len(compact(p)) for p in paragraphs]
    ranked = sorted(zip(paragraphs, plens), key=lambda x: x[1], reverse=True)[:3]
    result["paragraphs"] = {"measurement_status": "partial", "data": {"method": "explicit nonempty lines; soft-wraps are not inferred", "count": len(paragraphs), "median": statistics.median(plens) if plens else None, "p90": p90(plens), "max": max(plens, default=None)},
                            "signals": [{"quote": p, "kind": "longest-block"} for p, _ in ranked]}
    hits = []
    for term in config["signals"]["literal_attention_terms"]:
        for match in re.finditer(re.escape(term), value):
            hits.append((match.start(), match.end(), term))
    spans = []
    for start, end, term in sorted(hits, key=lambda x: (-(x[1]-x[0]), x[0])):
        if not any(start < b and end > a for a, b, _ in spans):
            spans.append((start, end, term))
    result["verbosity"] = {"measurement_status": "measured", "data": {"occurrences": len(spans), "unique_terms": len({t for _, _, t in spans}), "per_1000_characters": len(spans) * 1000 / len(chars) if chars else None},
                           "signals": [{"quote": t, "start": a, "end": b, "kind": "literal-attention-term"} for a, b, t in sorted(spans)]}
    evidence_items = plan.get("evidence_items", [])
    bound = 0
    evidence_signals = []
    for item in evidence_items:
        quote = item.get("source_quote", "")
        source = item.get("source_path")
        matched = bool(source and quote and quote in text(source))
        bound += bool(matched)
        if not matched:
            evidence_signals.append({"quote": item.get("output_quote", ""), "kind": "unbound-declared-evidence"})
    result["evidence"] = {"measurement_status": "partial", "data": {"declared_items": len(evidence_items), "source_quote_matches": bound, "coverage": bound / len(evidence_items) if evidence_items else None,
                          "boundary": "Matching confirms a declared quote exists, not that it supports the claim or that the inventory is complete."}, "signals": evidence_signals}
    grammar_signals = []
    for left, right in [("（", "）"), ("(", ")"), ("[", "]")]:
        if value.count(left) != value.count(right):
            grammar_signals.append({"quote": left if left in value else right, "kind": "delimiter-count-mismatch"})
    stack, pairs = [], {"）": "（", ")": "(", "]": "["}
    for char in value:
        if char in pairs.values():
            stack.append(char)
        elif char in pairs:
            if not stack or stack.pop() != pairs[char]:
                grammar_signals.append({"quote": char, "kind": "delimiter-order-mismatch"})
    result["grammar"] = {"measurement_status": "partial", "data": {"scope": "declared delimiter counts only; grammar requires contextual review"}, "signals": grammar_signals}
    fields = plan.get("time_fields", [])
    time_signals, parsed, invalid_dates, contradictions = [], {}, 0, 0
    for field in fields:
        actual = field.get("observed", field["expected"] if field["expected"] in value else "")
        if not actual or actual not in value:
            time_signals.append({"quote": field["label"], "kind": "declared-time-or-status-not-present"})
            continue
        if actual != field["expected"]:
            contradictions += 1
            time_signals.append({"quote": actual, "kind": "declared-time-or-status-conflict"})
        if field.get("kind") in {"date", "datetime"}:
            try:
                parsed[field["label"]] = datetime.fromisoformat(actual.replace("Z", "+00:00"))
            except ValueError:
                invalid_dates += 1
                time_signals.append({"quote": actual, "kind": "iso-date-parse-failure"})
    order_failures = 0
    for relation in plan.get("time_order", []):
        before, after = parsed.get(relation["before"]), parsed.get(relation["after"])
        if before is None or after is None:
            time_signals.append({"quote": relation["before"], "kind": "time-order-unchecked"})
        else:
            try:
                if before > after:
                    order_failures += 1
                    time_signals.append({"quote": relation["before"], "kind": "declared-time-order-conflict"})
            except TypeError:
                time_signals.append({"quote": relation["before"], "kind": "time-zone-basis-missing"})
    result["time"] = {"measurement_status": "partial", "data": {"declared_fields": len(fields), "parsed_dates": len(parsed), "date_parse_failures": invalid_dates, "field_conflicts": contradictions, "order_conflicts": order_failures,
                          "boundary": "Only declared fields and order relations; relative dates, tense, narrative time and real-world completion need contextual/source review."}, "signals": time_signals}
    result["reading_burden"]["unmeasured_reason"] = "Requires actual target-page geometry and declared viewport; text length is not screen count."
    if geometry_path:
        result["reading_burden"] = {"measurement_status": "measured", "data": measure_geometry(geometry_path, sha(value.encode())), "signals": []}
    answers = plan.get("required_answers", []) if state["profile"] == "functional" else []
    positions = [{"id": a["id"], "position": value.find(a.get("output_quote", a["expected"]))} for a in answers]
    opening = plan.get("opening_text")
    if opening is not None:
        need(isinstance(opening, str) and value.startswith(opening), "Declared opening must be the actual visible text prefix")
    covered_opening = sum(p["position"] >= 0 and p["position"] + len(a.get("output_quote", a["expected"])) <= len(opening) for p, a in zip(positions, answers)) if opening is not None else None
    counts = Counter(sentences)
    duplicate_count = sum(n-1 for n in counts.values())
    result["reading_efficiency"] = {"measurement_status": "partial", "data": {"answer_positions": positions, "required_answer_denominator": len(answers), "opening_explicit_matches": covered_opening,
                       "opening_coverage": covered_opening / len(answers) if covered_opening is not None and answers else None,
                       "opening_boundary": "Literal placement in a declared opening, not semantic correctness or 30-second comprehension", "sentences": len(sentences), "exact_duplicate_sentences": duplicate_count,
                       "exact_duplicate_ratio": duplicate_count / len(sentences) if sentences else None, "human_30_second_comprehension": "not-tested"},
                       "signals": [{"quote": s, "kind": "exact-repetition"} for s, n in counts.items() if n > 1]}
    result["defensive_expression"] = defensive_expression.measurement(value)
    for metric, entry in result.items():
        for i, signal in enumerate(entry["signals"], 1):
            signal["id"] = metric + ":" + str(i)
    return {"version": 1, "profile": state["profile"], "text_sha256": sha(value.encode()), "plan_sha256": digest(plan),
            "metrics": result, "geometry": ref(geometry_path) if geometry_path else None,
            "boundary": "Signals locate candidates; they do not automatically fail prose, rewrite it, or measure human effects."}


def measure(run, text_path, output, geometry_path=None):
    value = visible(text_path)
    with session(run) as state:
        import writing_execution
        report = writing_execution.measured_once(run, state, value, geometry_path)
    write_json(output, report, exclusive=True)
    write_json(str(output) + ".assessment.json", {"text_sha256": report["text_sha256"],
        "report_sha256": ref(output)["sha256"], "observations": [], "dispositions": [], "not_applicable": {}, "issues": []}, exclusive=True)
    return report


def register_candidate(run, artifact_path, text_path, report_path, record_path):
    artifact_ref, value = ref(artifact_path), visible(text_path)
    report, record = load_json(report_path), load_json(record_path)
    with session(run, True) as state:
        need(state["units"], "Write-in-progress checkpoint is missing")
        need(not state["rounds"] or state["rounds"][-1].get("verdict") is not None, "Complete all reviewers before revision")
        need(len(state["rounds"]) < load_json(CONFIG)["max_review_rounds"], "Review limit reached; present current draft and ask for direction")
        geometry = report.get("geometry")
        if geometry:
            verify_ref(geometry)
            state["evidence"].append(geometry)
        import writing_execution
        need(report == writing_execution.measured_once(run, state, value, geometry["path"] if geometry else None), "Metric report is stale or edited")
        need(record.get("text_sha256") == report["text_sha256"] and record.get("report_sha256") == ref(report_path)["sha256"],
             "Contextual assessment is not bound to this text and measurement report")
        latest = {u["unit_id"]: u for u in state["units"]}
        full, spans = compact(value), []
        for unit in state["plan"]["reading_path"]:
            need(unit["id"] in latest, "Planned unit has no write-in-progress checkpoint")
            needle = compact(latest[unit["id"]]["text"])
            possible = [m.start() for m in re.finditer(re.escape(needle), full)]
            available = [p for p in possible if not any(p < b and p+len(needle) > a for a, b in spans)]
            need(available, "Unit changed after checkpoint; inspect the affected unit")
            spans.append((available[0], available[0]+len(needle)))
        cursor = 0
        for start, end in sorted(spans):
            need(start == cursor, "Candidate contains text outside the current complete-unit checkpoints")
            cursor = end
        need(cursor == len(full), "Candidate appended text after its complete-unit checkpoint")
        need(compact(artifact_text(artifact_path)) == full, "Candidate text does not match delivery artifact")
        observations = record.get("observations", [])
        covered = set()
        for item in observations:
            need(isinstance(item.get("metrics"), list) and item["metrics"], "Observation must name applicable metrics")
            need(set(item["metrics"]) <= set(report["metrics"]), "Unknown metric in observation")
            need(nonempty(item.get("quote"), "assessment quote") in value, "Assessment quote missing from candidate")
            nonempty(item.get("reason"), "assessment reason")
            covered.update(item["metrics"])
        exemptions = record.get("not_applicable", {})
        for key, reason in exemptions.items():
            need(key in report["metrics"], "Unknown metric exemption")
            nonempty(reason, "not-applicable reason")
            need((key == "terms" and not state["plan"].get("terms")) or
                 (key == "evidence" and state["profile"] == "literary" and state["plan"]["material"]["mode"] == "fiction" and not state["plan"].get("evidence_items")),
                 "This core standard needs a contextual observation, not a blanket exemption")
        need(covered | set(exemptions) == set(report["metrics"]), "Some standards have no contextual assessment or explicit applicability decision")
        dispositions = {d["signal_id"]: d for d in record.get("dispositions", [])}
        need(len(dispositions) == len(record.get("dispositions", [])), "Duplicate signal dispositions")
        signals = [s for m in report["metrics"].values() for s in m["signals"]]
        need(set(dispositions) == {s["id"] for s in signals}, "Every detected candidate needs a disposition")
        for item in dispositions.values():
            need(item.get("decision") in {"retain", "pending"}, "Measure repaired text again; do not claim a remaining signal was removed")
            nonempty(item.get("reason"), "signal handling reason")
        layout = record.get("layout", {})
        if needs_layout(state["plan"], artifact_path):
            need(layout.get("status") in {"inspected", "unmeasured"}, "Record target layout coverage")
            nonempty(layout.get("reason"), "layout reason")
            if layout["status"] == "inspected":
                for key in ("target", "viewport", "findings"):
                    nonempty(layout.get(key), "layout." + key)
                need(layout.get("evidence_files"), "Actual layout evidence is missing")
                state["evidence"].extend(ref(p) for p in layout["evidence_files"])
        state["evidence"].extend([ref(report_path), ref(record_path)])
        item = {"artifact": artifact_ref, "text": value, "text_sha256": sha(value.encode()), "report": ref(report_path),
                "record": ref(record_path), "pending": [d for d in dispositions.values() if d["decision"] == "pending"],
                "layout": layout, "unresolved": record.get("issues", [])}
        for issue in item["unresolved"]:
            nonempty(issue.get("impact"), "issue impact")
            need(type(issue.get("blocking")) is bool, "Issue blocking must be boolean")
        state["candidates"].append(item)
        event(state, "candidate", {"artifact_sha256": artifact_ref["sha256"], "text_sha256": item["text_sha256"]})
    return {"status": "candidate-registered", "artifact_sha256": artifact_ref["sha256"]}


def start_review(run, artifact_path, stage="after"):
    with session(run, True) as state:
        need(stage in {"during", "after"}, "Review stage must be during or after")
        need(state["candidates"], "Stabilize a candidate before independent review")
        candidate = state["candidates"][-1]
        need(ref(artifact_path) == candidate["artifact"], "Review candidate changed")
        need(not state["rounds"] or state["rounds"][-1].get("verdict") is not None, "Previous parallel batch is incomplete")
        need(len(state["rounds"]) < load_json(CONFIG)["max_review_rounds"], "Three review rounds exhausted")
        item = {"round": len(state["rounds"])+1, "stage": stage, "artifact_sha256": candidate["artifact"]["sha256"], "verdict": None}
        if state.get("execution"):
            import writing_execution
            writing_execution.reserve_batch(run, item["round"], item["artifact_sha256"])
        if state["profile"] == "literary":
            directory = Path(run).resolve() / ("review-" + str(item["round"]))
            directory.mkdir(mode=0o700)
            common = {"artifact_sha256": candidate["artifact"]["sha256"], "text": candidate["text"]}
            packets = {
                "professional": {**common, "role": "professional", "material_mode": state["plan"]["material"]["mode"],
                    "source_attribution_template": source_attribution.template(candidate['text'], '\n'.join(text(s['path']) for s in state['sources']), 'source', 'literary'),
                    "source_attribution_guidance": 'Return source_attribution from the supplied sources. Apply the attribution rules in context_review_guidance; fictional voices are not external testimony.',
                    "context_review_template": context_value.template(candidate['text'], 'literary'),
                    "context_review_guidance": context_value.GUIDANCE + " Return the completed template as context_review. Preserve characterization, narrator knowledge, rhythm and intentional repetition; no functional-report template.",
                    "constraints": state["plan"]["constraints"], "literary_intent": state["plan"]["literary_intent"],
                    "sources": [{"sha256": source["sha256"], "text": text(source["path"])} for source in state["sources"]],
                    "task": "Read the candidate first. Then use supplied sources and constraints to review internal coherence, language, voice and scene relations using exact text. Separate errors from supported artistic choices."},
                "reader": {**common, "role": "reader", "known_context": state["plan"]["reader"]["knowledge"],
                    "attribution_template": source_attribution.template(candidate['text'], profile='literary'),
                    "attribution_guidance": source_attribution.GUIDANCE + ' Return the completed template as attribution_replay using only this text.',
                    "task": "Read only this text. Retell what you understand, memorable details, uncertainties and textual reasons. Do not guess an author's intended answer or invent human timing."}}
            item["packets"] = {}
            for role, packet in packets.items():
                path = directory / (role + ".json")
                write_json(path, packet, exclusive=True)
                item["packets"][role] = ref(path)
                state["evidence"].append(ref(path))
        state["rounds"].append(item)
        event(state, "review-start", item.copy())
    return {"status": "review-started", "round": item["round"], "packets": item.get("packets", {})}


def finish_review(run, result_path, verdict, issues=None, reviewer_records=None):
    need(verdict in {"pass", "fail"}, "Unknown review verdict")
    with session(run, True) as state:
        need(state["rounds"] and state["rounds"][-1]["verdict"] is None, "No active review batch")
        item = state["rounds"][-1]
        candidate = state["candidates"][-1]
        verify_ref(candidate["artifact"])
        need(item["artifact_sha256"] == candidate["artifact"]["sha256"], "Review version changed")
        result_ref = ref(result_path)
        raw = load_json(result_path)
        issues = issues if issues is not None else raw.get("issues", raw.get("blocking_issues", []))
        if state["profile"] == "literary":
            records = reviewer_records if reviewer_records is not None else raw.get("reviewer_records")
            need(isinstance(records, list) and len(records) == 2, "Require independent professional and reader records")
            need({r.get("role") for r in records} == {"professional", "reader"}, "Missing literary reviewer role")
            contexts = [nonempty(r.get("context_id"), "review context") for r in records]
            need(len(set(contexts)) == len(contexts) and all(c not in {r.get("context_id") for old in state["rounds"][:-1] for r in old.get("reviewer_records", [])} for c in contexts), "Reuse of a review context is not independent")
            need(state["plan"].get("author_context_id") not in contexts, "Author context cannot serve as an independent reviewer")
            for r in records:
                need(r.get("packet_sha256") == item["packets"][r["role"]]["sha256"], "Reviewer did not bind the isolated input packet")
                nonempty(r.get("summary"), "independent review summary")
                need(r.get("verdict") in {"pass", "fail"}, "Unknown reviewer verdict")
                evidence = r.get("evidence")
                need(isinstance(evidence, list) and evidence, "Independent replay needs actual text evidence")
                for e in evidence:
                    need(nonempty(e.get("quote"), "review quote") in candidate["text"], "Review quote is not in current candidate")
                    nonempty(e.get("reason"), "review evidence reason")
            need(verdict == ("pass" if all(r["verdict"] == "pass" for r in records) and not issues else "fail"), "Literary aggregate disagrees with raw reviewers")
            item["reviewer_records"] = records
        else:
            native_verdict = raw.get("verdict", raw.get("status"))
            need(native_verdict is not None, "Original native review result must contain status or verdict")
            if verdict == "pass":
                need(str(native_verdict).lower() in {"pass", "passed", "verified"} and not issues, "Cannot promote a failed native result")
        if verdict == "fail":
            need(isinstance(issues, list) and issues, "Non-pass requires unresolved reader impact")
        item.update(verdict=verdict, result=result_ref, issues=issues or [])
        state["evidence"].append(result_ref)
        event(state, "review-finish", {"round": item["round"], "verdict": verdict, "result_sha256": result_ref["sha256"]})
    return {"status": "review-recorded", "round": item["round"], "verdict": verdict}


def verify_delivery(run_path, artifact_path, expected_profile, *, review_evidence=None, draft=False):
    with session(run_path) as state:
        need(state["profile"] == expected_profile, "Writing profile does not match this skill")
        need(state["candidates"] and state["units"], "Lifecycle stages are incomplete")
        candidate = state["candidates"][-1]
        need(ref(artifact_path) == candidate["artifact"], "Delivery changed after candidate registration")
        need(state["rounds"] and state["rounds"][-1]["verdict"] is not None, "Independent review batch is incomplete")
        current = state["rounds"][-1]
        need(current["artifact_sha256"] == candidate["artifact"]["sha256"], "Review belongs to an older draft")
        if review_evidence is not None:
            need(current["result"] in [ref(p) for p in review_evidence], "Native final review differs from registered lifecycle review")
        issues = list(current["issues"])
        if draft:
            need(len(state["rounds"]) == load_json(CONFIG)["max_review_rounds"] and current["verdict"] == "fail" and issues, "Draft fallback requires three completed non-pass rounds")
            status = "review-incomplete-draft"
        else:
            need(current["verdict"] == "pass", "Independent review has not passed")
            need(state["plan"]["authority"]["status"] == "confirmed", "Provisional requirements cannot support complete acceptance")
            need(not any(g["critical"] and g["handling"] != "narrowed" for g in state["plan"]["material"].get("gaps", [])), "Critical source gap remains")
            need(not candidate["pending"] and not any(i["blocking"] for i in candidate["unresolved"]), "Candidate issues remain unresolved")
            if needs_layout(state["plan"], artifact_path):
                need(candidate["layout"].get("status") == "inspected", "Actual target layout has not been inspected")
            status = "pass"
        return {"status": status, "artifact_sha256": candidate["artifact"]["sha256"], "profile": expected_profile,
                "rounds": len(state["rounds"]), "issues": issues,
                "evidence_paths": [str(Path(run_path).resolve() / "lifecycle.json"), state["plan_ref"]["path"],
                                   *[p["path"] for p in state["sources"] + state["evidence"]]],
                "user_notice_required": draft, "user_question_required": draft, "external_action_authorized": False,
                "boundary": "Validates registered stages, versions, measurements and records; does not prove host enforcement, reviewer identity or human/literary quality."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("run"); init.add_argument("--plan", required=True)
    init.add_argument("--profile", choices=("functional", "literary"), required=True)
    init.add_argument("--source", action="append", default=[])
    for command in ("unit", "measure", "candidate", "review-start", "review-finish", "check", "inspect"):
        p = sub.add_parser(command); p.add_argument("run")
        if command == "unit":
            p.add_argument("--text", required=True); p.add_argument("--record", required=True)
        elif command == "measure":
            p.add_argument("--text", required=True); p.add_argument("--output", required=True)
            p.add_argument("--geometry")
        elif command == "candidate":
            for name in ("artifact", "text", "report", "record"):
                p.add_argument("--"+name, required=True)
        elif command == "review-start":
            p.add_argument("--artifact", required=True); p.add_argument("--stage", choices=("during", "after"), default="after")
        elif command == "review-finish":
            p.add_argument("--result", required=True); p.add_argument("--verdict", choices=("pass", "fail"), required=True)
        elif command == "check":
            p.add_argument("--artifact", required=True); p.add_argument("--profile", choices=("functional", "literary"), required=True)
            p.add_argument("--draft", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "init": result = init_run(args.run, args.plan, args.profile, args.source)
        elif args.command == "unit": result = record_unit(args.run, args.text, args.record)
        elif args.command == "measure":
            r = measure(args.run, args.text, args.output, args.geometry)
            result = {"status": "measured", "report": str(Path(args.output).resolve()),
                      "assessment_template": str(Path(str(args.output)+".assessment.json").resolve()), "text_sha256": r["text_sha256"]}
        elif args.command == "candidate": result = register_candidate(args.run, args.artifact, args.text, args.report, args.record)
        elif args.command == "review-start": result = start_review(args.run, args.artifact, args.stage)
        elif args.command == "review-finish": result = finish_review(args.run, args.result, args.verdict)
        elif args.command == "check": result = verify_delivery(args.run, args.artifact, args.profile, draft=args.draft)
        else:
            with session(args.run) as state:
                result = {"profile": state["profile"], "events": state["events"], "units": len(state["units"]), "rounds": len(state["rounds"])}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
