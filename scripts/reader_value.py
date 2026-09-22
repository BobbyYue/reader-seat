"""Validate artifact-bound editorial evidence; semantic judgments stay with reviewers.

Distributed with each skill so none needs another skill installed.
"""
from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

VERSION = 2
EMPTY_ATTESTATIONS = {"pass", "passed", "ok", "yes", "checked", "none", "n/a", "true", "false", "通过", "正常", "无", "已检查"}
CRAFT_GUIDANCE = {
    "concrete_detail": "Quote the highest-risk or representative passage. Restate the actual event, operation, finding or question the reader learns; do not require invented details, stories or numbers when evidence is thin.",
    "progression": "Quote a passage with its transition where needed. Explain how it advances or supports understanding, rather than restating praise. A necessary example, bridge, emotion or short acknowledgement can suffice without a new fact; no fixed paragraph template.",
    "reading_flow": "Quote a sentence in context. Explain whether subject, conditions and emphasis can be followed without rereading; retain the writer's register. Change only an actual obstacle or explicit style mismatch, never a sentence-length ratio, punctuation quota or forced casual voice.",
}
GUIDANCE = {
    "expression": "Identify a concrete proposition or real contrast. Keep useful contrasts; revise empty framing only when it delays or distorts understanding. No banned phrase list.",
    "selection": "Explain what misunderstanding would result from removing the quoted passage. Keep decisive caveats and helpful transitions/examples; remove boilerplate, defer lookup detail. Do not request additions merely for completeness.",
    "presentation": "Inspect the supplied rendering. Locate the main point, reading order and dense region; explain whether layout exposes a relationship or merely repackages prose. Do not prescribe a diagram or identical section template.",
    "meaning": "Compare the source and final text: facts, request/refusal, urgency, ownership, numbers and uncertainty must survive. Natural wording must not weaken or invent a request.",
    "unit_roles": "Explain the different reader jobs of the takeaway, picture and question table. Useful repetition is allowed; copying the same explanation three times is not. Preserve P0 and weighted coverage, never hide claims to lower the denominator.",
}
GUIDANCE["expression"] += " Complete all craft_checks with an anchored quote, pass/fail and concrete reason. Review the whole candidate, record representative or problematic spans; a clear short message may reuse one span. " + " ".join(f"{key}: {value}" for key, value in CRAFT_GUIDANCE.items())
GUIDANCE["meaning"] += " Explain detail_support: match vivid or specific details to the supplied source; retain unknowns and label permitted illustrative examples. Never trade a factual boundary for a story or hide the conclusion as literary suspense."


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.stack = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        hidden = (any(hidden for _, hidden in self.stack) or tag in {"head", "script", "style", "template"}
                  or "hidden" in attrs or attrs.get("aria-hidden") == "true"
                  or bool(re.search(r"(?:display\s*:\s*none|visibility\s*:\s*hidden)", attrs.get("style", ""), re.I)))
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append((tag, hidden))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if not any(hidden for _, hidden in self.stack):
            self.parts.append(data)


def normalize(text):
    return re.sub(r"\s+", "", text)


def substantive(value):
    return (isinstance(value, str) and any(c.isalnum() for c in value)
            and value.strip().casefold() not in EMPTY_ATTESTATIONS)


def read_text(path):
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".html", ".htm", ".svg"}:
        styles = re.findall(r"<style\b[^>]*>([\s\S]*?)</style>", raw, re.I)
        # A string parser cannot resolve CSS cascade/media state. Use text from
        # the existing browser-render pass rather than accepting hidden anchors.
        if (re.search(r'<link\b[^>]*\brel\s*=\s*[\"\']?stylesheet', raw, re.I)
                or any(re.search(r"display\s*:\s*none|visibility\s*:\s*(?:hidden|collapse)|opacity\s*:\s*0(?:\D|$)|\bclip(?:-path)?\s*:", css, re.I) for css in styles)):
            raise ValueError("CSS-controlled visibility requires a bound rendered-text content snapshot")
        parser = VisibleText()
        parser.feed(raw)
        return " ".join(parser.parts)
    if path.suffix.lower() == ".json":
        payload = json.loads(raw)
        if (isinstance(payload, dict) and isinstance(payload.get("blocks"), list)
                and all(isinstance(b, dict) and "text" in b for b in payload["blocks"])):
            return "\n".join(str(block.get("text", "")) for block in payload["blocks"] if isinstance(block, dict))
        def values(value):
            if isinstance(value, str):
                yield value
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                yield str(value)
            elif isinstance(value, list):
                for item in value:
                    yield from values(item)
            elif isinstance(value, dict):
                for key, item in value.items():
                    if key not in {"id", "metadata", "owner", "artifact_binding", "sha256"} and not key.endswith("_id"):
                        yield from values(item)
        return "\n".join(values(payload))
    if path.suffix.lower() == ".xml":
        return " ".join(ET.fromstring(raw).itertext())
    return raw


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(review, axes, binding, text, *, source="", renders=()):
    """Check coverage, anchors and freshness, not whether prose is 'human'."""
    if not isinstance(review, dict):
        return ["missing reader_value review"]
    errors = []
    if type(review.get("version")) is not int or review.get("version") != VERSION or review.get("artifact_binding") != binding:
        errors.append("reader_value version or artifact binding is stale")
    checks = review.get("checks")
    if not isinstance(checks, dict) or set(checks) != set(axes):
        return errors + ["reader_value checks must match the assigned axes"]
    for axis in axes:
        item = checks[axis]
        prefix = f"reader_value.{axis}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for key in ("location", "reader_effect", "protected_meaning"):
            if not substantive(item.get(key)):
                errors.append(f"{prefix} missing {key}")
        quote = item.get("quote", "")
        if not isinstance(quote, str) or not normalize(quote) or normalize(quote) not in normalize(text):
            errors.append(f"{prefix} quote not found in reviewed text")
        if not isinstance(item.get("status"), str) or item.get("status") not in {"pass", "fail"}:
            errors.append(f"{prefix} requires pass/fail")
        if not isinstance(item.get("action"), str) or item.get("action") not in {"keep", "revise", "remove", "defer"}:
            errors.append(f"{prefix} requires a content disposition")
        if item.get("status") != "pass" or item.get("action") != "keep":
            errors.append(f"{prefix} retains an unresolved reader problem")
        if axis == "expression":
            probes = item.get("craft_checks")
            if not isinstance(probes, dict) or set(probes) != set(CRAFT_GUIDANCE):
                errors.append(f"{prefix} requires concrete_detail, progression and reading_flow evidence")
            else:
                for name, probe in probes.items():
                    label = f"{prefix}.craft_checks.{name}"
                    if not isinstance(probe, dict):
                        errors.append(f"{label} must be an object")
                        continue
                    evidence = probe.get("quote", "")
                    if not isinstance(evidence, str) or not normalize(evidence) or normalize(evidence) not in normalize(text):
                        errors.append(f"{label} quote not found in reviewed text")
                    if not substantive(probe.get("reason")):
                        errors.append(f"{label} requires a concrete reader-effect reason")
                    if probe.get("status") != "pass":
                        errors.append(f"{label} missing or unresolved; no extra style-only review round")
        if axis == "selection" and not substantive(item.get("removal_effect")):
            errors.append(f"{prefix} must explain the consequence of removing this passage")
        if axis == "meaning":
            if not substantive(item.get("detail_support")):
                errors.append(f"{prefix} must explain source support for specificity")
            quote = item.get("source_quote", "")
            if not isinstance(quote, str) or not normalize(quote) or normalize(quote) not in normalize(source):
                errors.append(f"{prefix} source quote not found")
        if axis == "presentation":
            allowed = {str(Path(p).resolve()) for p in renders}
            render = item.get("render_path")
            if not isinstance(render, str) or str(Path(render).resolve()) not in allowed:
                errors.append(f"{prefix} must reference supplied render evidence")
            if not substantive(item.get("observation")):
                errors.append(f"{prefix} missing visible reading-order observation")
        if axis == "unit_roles":
            roles = item.get("roles")
            if not isinstance(roles, dict) or set(roles) != {"takeaway", "picture", "questions"}:
                errors.append(f"{prefix} must explain all three mandatory units")
            elif any(not substantive(v) for v in roles.values()):
                errors.append(f"{prefix} unit reader jobs cannot be empty")
    return errors


def template(axes, binding):
    checks = {}
    for axis in axes:
        item = {"status": "fail", "action": "revise", "location": "", "quote": "",
                "reader_effect": "", "protected_meaning": ""}
        if axis == "expression":
            item["craft_checks"] = {name: {"status": "fail", "quote": "", "reason": ""} for name in CRAFT_GUIDANCE}
        if axis == "selection":
            item["removal_effect"] = ""
        if axis == "meaning":
            item["source_quote"] = ""
            item["detail_support"] = ""
        if axis == "presentation":
            item.update(render_path="", observation="")
        if axis == "unit_roles":
            item["roles"] = {"takeaway": "", "picture": "", "questions": ""}
        checks[axis] = item
    return {"version": VERSION, "artifact_binding": binding, "checks": checks}
