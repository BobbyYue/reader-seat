"""Validate scan-review evidence, not eye movements or human comprehension."""
from __future__ import annotations

import hashlib
import re

VERSION = 1
PROFILES = {"document", "brief", "message"}
KINDS = {"title", "heading", "lead", "emphasis", "visual-label", "table-label", "message"}
CHECKS = {"orientation", "conditions", "detail"}
EMPTY = {"pass", "passed", "ok", "yes", "checked", "none", "n/a", "通过", "正常", "无", "已检查", "可以", "没问题"}
GUIDANCE = (
    "Complete scan_reading in this same expression review. Before full reading, collect the actual "
    "title/headings/leads/emphasis or message opening as cues and restate what they communicate. "
    "Then compare against the whole text and locked reader-answer plan: important answers are findable, "
    "decisive conditions travel with their claims, and necessary explanation remains reachable. "
    "For each decisive condition record location cue/body/missing. Cue needs quote and cue_index; body "
    "needs its real quote and a null index; missing needs expected_condition and its source/task basis, "
    "not an invented candidate quote. Body/missing stays a completed negative judgment. When no "
    "condition is needed explain why for this task. Document: overview and section path; brief: TLDR, "
    "main visual and question table; message: supplied intent/update/ask, no invented action or headings. "
    "A clear short message may reuse the same quote for cue and detail. Native visual review separately "
    "checks that these cues really stand out and conditions remain readable in the actual window. "
    "Mark fail for buried answers, misleading emphasis, missing conditions or thin explanation; merge "
    "fixes with the existing paragraph task. No new reviewer, score, F-shaped layout, word limit or "
    "universal 30-second threshold. This is editorial simulation, never a human timing or eye-tracking result."
)


def _hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _norm(text):
    return re.sub(r"\s+", "", text)


def _useful(value):
    return isinstance(value, str) and any(c.isalnum() for c in value) and value.strip().casefold() not in EMPTY


def _quote(value, text):
    return isinstance(value, str) and bool(_norm(value)) and _norm(value) in _norm(text)


def template(text, profile):
    if not isinstance(profile, str) or profile not in PROFILES:
        raise ValueError("unknown scan-reading profile")
    return {"version": VERSION, "profile": profile, "text_sha256": _hash(text),
            "evidence_kind": "editorial-simulation", "cues": [], "takeaway": "",
            "conditions": [], "no_conditions_reason": "", "detail_quote": "",
            "checks": {key: {"status": "pending", "reason": ""} for key in sorted(CHECKS)}}


def validate(record, text, profile):
    prefix = "scan_reading"
    if not isinstance(record, dict):
        return [prefix + " review is required"]
    errors = []
    if type(record.get("version")) is not int or record["version"] != VERSION:
        errors.append(prefix + " version is stale")
    if not isinstance(profile, str) or profile not in PROFILES or record.get("profile") != profile:
        errors.append(prefix + " profile does not match this skill")
    if record.get("text_sha256") != _hash(text):
        errors.append(prefix + " text binding is stale")
    if record.get("evidence_kind") != "editorial-simulation":
        errors.append(prefix + " must not impersonate human or eye-tracking evidence")
    cues = record.get("cues")
    if not isinstance(cues, list) or not cues:
        errors.append(prefix + " needs quoted scanning cues")
        cues = []
    valid_cues = []
    for index, cue in enumerate(cues):
        if (not isinstance(cue, dict) or not isinstance(cue.get("kind"), str)
                or cue["kind"] not in KINDS or not _quote(cue.get("quote"), text)):
            errors.append(f"{prefix}.cues[{index}] must quote the reviewed text and name its role")
            valid_cues.append("")
        else:
            valid_cues.append(cue["quote"])
    if not _useful(record.get("takeaway")):
        errors.append(prefix + " needs the reader's first-pass takeaway")
    conditions = record.get("conditions")
    if not isinstance(conditions, list):
        errors.append(prefix + " conditions must be a list")
        conditions = []
    if not conditions and not _useful(record.get("no_conditions_reason")):
        errors.append(prefix + " must explain why no decisive condition is needed")
    for index, item in enumerate(conditions):
        if not isinstance(item, dict):
            errors.append(f"{prefix}.conditions[{index}] must be an object")
            continue
        cue_index = item.get("cue_index")
        quote = item.get("quote")
        location = item.get("location", "cue")
        if not isinstance(location, str):
            errors.append(f"{prefix}.conditions[{index}] invalid location")
            continue
        if location in {"body", "missing"}:
            if cue_index is not None:
                errors.append(f"{prefix}.conditions[{index}] buried/missing condition must use null cue_index")
            if location == "body" and not _quote(quote, text):
                errors.append(f"{prefix}.conditions[{index}] body quote not found in current text")
            if location == "missing" and (not _useful(item.get("expected_condition")) or not _useful(item.get("basis"))):
                errors.append(f"{prefix}.conditions[{index}] missing condition needs its expectation and basis")
            errors.append(f"{prefix}.candidate_failed: decisive condition is {location}")
            condition_check = record.get("checks", {})
            if isinstance(condition_check, dict):
                condition_check = condition_check.get("conditions", {})
            if not isinstance(condition_check, dict) or condition_check.get("status") != "fail":
                errors.append(prefix + ".conditions inconsistent_judgment: located failure requires fail")
            continue
        if location != "cue":
            errors.append(f"{prefix}.conditions[{index}] invalid location")
            continue
        if not _quote(quote, text):
            errors.append(f"{prefix}.conditions[{index}] quote not found in current text")
        if (type(cue_index) is not int or not 0 <= cue_index < len(valid_cues)
                or not _quote(quote, valid_cues[cue_index])):
            errors.append(f"{prefix}.conditions[{index}] is missing from the selected scanning cue")
    if not _quote(record.get("detail_quote"), text):
        errors.append(prefix + " must locate necessary detail in the current text")
    checks = record.get("checks")
    if not isinstance(checks, dict) or set(checks) != CHECKS:
        errors.append(prefix + " needs orientation, conditions and detail judgments")
    else:
        for key, check in checks.items():
            if not isinstance(check, dict):
                errors.append(f"{prefix}.{key} invalid_record")
                continue
            status = check.get("status")
            if status == "fail":
                errors.append(f"{prefix}.{key} candidate_failed")
            elif status == "pending":
                errors.append(f"{prefix}.{key} review_incomplete")
            elif status != "pass":
                errors.append(f"{prefix}.{key} invalid_status")
            if not _useful(check.get("reason")):
                errors.append(f"{prefix}.{key} missing_specific_reason")
    return errors
