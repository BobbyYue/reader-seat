#!/usr/bin/env python3
"""Validate a narrowly authorized native text patch; never perform remote writes.

Snapshot JSON: {document_id: str, revision: str|int, blocks: [
  {block_id: str, text: str, ...native fields preserved verbatim...}]}
Object key order/JSON whitespace are irrelevant; array order and value types are
not. The candidate must equal the baseline except for the declared block.text
replacements. Its revision is still the baseline revision before the write.

The reader-answer manifest must bind the candidate JSON as its artifact and use
the exact candidate_xml() result as its snapshot: UTF-8, LF, no declaration,
<document id="XML-escaped document_id">, then one <block id="XML-escaped
block_id">XML-escaped text</block> per block in existing order, then </document>.
Every line ends with LF. Both quotes are escaped; CR is &#13;, and attribute LF
and TAB are &#10; and &#9;. No trimming, HTML rendering, or text substitution.

prepare requires no screenshot. Its prewrite-approved receipt is NOT completion.
After the separately executed authorized write, verify requires a new readback
revision, matching native blocks, a PNG/JPEG, and an inspection JSON:
  {readback_sha256, render_sha256,
   inspector: {id: "actual inspector", method: "native-render-inspection"},
   verdict: "pass", checks: {
     readability: {verdict: "pass", evidence: "specific observed conclusion"},
     overflow: {verdict: "pass", evidence: "specific observed conclusion"},
     claim_evidence_adjacency: {verdict: "pass", evidence: "specific conclusion"}}}
The inspection must describe the actual native rendering for this readback.
Hashes and image structure are checked; a local validator cannot independently
prove capture provenance or the truth of a human/agent inspection. Unit-test
images and inspection records are structural fixtures, never live Feishu proof.

CLI:
  prepare --baseline B --live-baseline L --candidate C --changes D
          --authorization A --answer-receipt R --output P
  verify --prewrite P --readback N --render I --inspection V --output F
Receipts are created exclusively; existing evidence is never overwritten.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import struct
import zlib
from pathlib import Path
from xml.sax.saxutils import escape

import reader_answers


VERSION = "native-text-patch-1"
INPUT_NAMES = ("baseline", "live_baseline", "candidate", "changes",
               "authorization", "answer_receipt")
CHECK_NAMES = ("readability", "overflow", "claim_evidence_adjacency")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_constant(value):
    raise ValueError(f"non-finite JSON number: {value}")


def load(path):
    return json.loads(Path(path).read_bytes().decode("utf-8"),
                      object_pairs_hook=_unique_object,
                      parse_constant=_reject_constant)


def reference(path):
    return {"path": str(Path(path).resolve()), "sha256": digest(path)}


def check_reference(item, name):
    if (not isinstance(item, dict) or set(item) != {"path", "sha256"}
            or not isinstance(item["path"], str)
            or not Path(item["path"]).is_absolute()
            or digest(item["path"]) != item["sha256"]):
        raise ValueError(f"{name} evidence changed or has an invalid binding")


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")
    return value


def _xml(value, attribute=False):
    if any(not (c in "\t\n\r" or 0x20 <= ord(c) <= 0xD7FF
                or 0xE000 <= ord(c) <= 0xFFFD
                or 0x10000 <= ord(c) <= 0x10FFFF) for c in value):
        raise ValueError("native IDs/text contain a character XML 1.0 cannot represent")
    value = escape(value, {'"': "&quot;", "'": "&apos;"}).replace("\r", "&#13;")
    return value.replace("\n", "&#10;").replace("\t", "&#9;") if attribute else value


def snapshot(value, name):
    if not isinstance(value, dict):
        raise ValueError(f"{name} snapshot must be an object")
    _text(value.get("document_id"), f"{name}.document_id")
    revision = value.get("revision")
    if not ((type(revision) is int and revision >= 0)
            or (isinstance(revision, str) and revision.strip())):
        raise ValueError(f"{name}.revision must be a nonempty string or nonnegative integer")
    blocks = value.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        raise ValueError(f"{name}.blocks must be a nonempty array")
    seen = set()
    for block in blocks:
        if not isinstance(block, dict):
            raise ValueError(f"{name} blocks must be objects")
        bid = _text(block.get("block_id"), f"{name}.block_id")
        if bid in seen:
            raise ValueError(f"{name} block IDs must be unique")
        seen.add(bid)
        if not isinstance(block.get("text"), str):
            raise ValueError(f"{name} block.text must be a string")
    return value


def candidate_xml(candidate):
    """Return the sole accepted readable snapshot; see module protocol above."""
    candidate = snapshot(candidate, "candidate")
    lines = ['<document id="' + _xml(candidate["document_id"], True) + '">']
    lines.extend('<block id="' + _xml(block["block_id"], True) + '">'
                 + _xml(block["text"]) + '</block>' for block in candidate["blocks"])
    return "\n".join(lines + ["</document>", ""])


def _validate_changes(baseline, candidate, changes):
    if not isinstance(changes, list) or not changes:
        raise ValueError("changes must be a nonempty array")
    expected = copy.deepcopy(baseline)
    blocks = {block["block_id"]: block for block in expected["blocks"]}
    seen = set()
    for change in changes:
        if not isinstance(change, dict) or set(change) != {"block_id", "before", "after"}:
            raise ValueError("each change must contain exactly block_id, before, and after")
        bid = _text(change["block_id"], "change.block_id")
        if bid in seen or bid not in blocks:
            raise ValueError("change block IDs must be unique and exist in the baseline")
        seen.add(bid)
        if not isinstance(change["before"], str) or not isinstance(change["after"], str):
            raise ValueError("change before/after must be strings")
        if change["before"] != blocks[bid]["text"]:
            raise ValueError(f"{bid}: before text does not equal the baseline")
        if change["before"] == change["after"]:
            raise ValueError(f"{bid}: change must actually replace text")
        blocks[bid]["text"] = change["after"]
    if canonical(candidate) != canonical(expected):
        raise ValueError("candidate differs beyond the declared block.text replacements")
    return [block["block_id"] for block in baseline["blocks"] if block["block_id"] in seen]


def _validate_authorization(authorization, document_id, block_ids):
    if not isinstance(authorization, dict):
        raise ValueError("explicit authorization must be an object")
    if (authorization.get("document_id") != document_id
            or authorization.get("action") != "replace-text"
            or authorization.get("risk") != "standard"):
        raise ValueError("authorization must name this document, replace-text, and standard risk")
    _text(authorization.get("user_instruction"), "authorization.user_instruction")
    authorized = authorization.get("block_ids")
    if (not isinstance(authorized, list)
            or any(not isinstance(bid, str) for bid in authorized)
            or len(authorized) != len(set(authorized))
            or set(authorized) != set(block_ids)):
        raise ValueError("authorization.block_ids must exactly match the changed blocks")


def _validate_answer_receipt(answer_path, candidate_path, candidate):
    errors = reader_answers.validate_receipt(answer_path, candidate_path)
    if errors:
        raise ValueError("reader answers failed: " + "; ".join(errors))
    answer = load(answer_path)
    manifest = load(answer["manifest_path"])
    _, plan = reader_answers.open_lock(manifest["lock_path"])
    declared_blocks = {bid for surface in plan["surfaces"] if surface["mode"] == "blocks"
                       for bid in surface["block_ids"]}
    if not declared_blocks:
        raise ValueError("native text patch must test explicit block reading surfaces")
    surface = Path(manifest["snapshot"]["path"]).read_bytes().decode("utf-8")
    if surface != candidate_xml(candidate):
        raise ValueError("reader snapshot is not the exact candidate block XML")


def prepare(baseline, live_baseline, candidate, changes, authorization, answer_receipt):
    """Return prewrite evidence only. This never writes to the native document."""
    paths = dict(zip(INPUT_NAMES, (baseline, live_baseline, candidate, changes,
                                  authorization, answer_receipt)))
    inputs = {name: reference(path) for name, path in paths.items()}
    if inputs["baseline"]["sha256"] != inputs["live_baseline"]["sha256"]:
        raise ValueError("live baseline changed; fetch again and rebuild the patch")
    old = snapshot(load(baseline), "baseline")
    new = snapshot(load(candidate), "candidate")
    block_ids = _validate_changes(old, new, load(changes))
    _validate_authorization(load(authorization), old["document_id"], block_ids)
    _validate_answer_receipt(answer_receipt, candidate, new)
    manifest = load(load(answer_receipt)["manifest_path"])
    _, plan = reader_answers.open_lock(manifest["lock_path"])
    tested = {bid for surface in plan["surfaces"] if surface["mode"] == "blocks" for bid in surface["block_ids"]}
    if set(block_ids) - tested:
        raise ValueError("reader surface omits a changed block")
    for name, item in inputs.items():
        check_reference(item, name)
    return {"version": VERSION, "status": "prewrite-approved", "complete": False,
            "native_render_pending": True, "external_write_performed": False,
            "document_id": old["document_id"], "baseline_revision": old["revision"],
            "block_ids": block_ids, "inputs": inputs,
            "candidate_xml_sha256": hashlib.sha256(candidate_xml(new).encode("utf-8")).hexdigest()}


def _image_format(path):
    """Check PNG chunks/CRC or JPEG marker structure; not visual/native provenance."""
    data = Path(path).read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        offset, tags = 8, []
        while offset + 12 <= len(data):
            size = struct.unpack(">I", data[offset:offset + 4])[0]
            tag = data[offset + 4:offset + 8]
            end = offset + 8 + size
            if end + 4 > len(data):
                raise ValueError("render PNG has a truncated chunk")
            body = data[offset + 8:end]
            crc = struct.unpack(">I", data[end:end + 4])[0]
            if zlib.crc32(tag + body) & 0xFFFFFFFF != crc:
                raise ValueError("render PNG checksum is invalid")
            if not tags:
                if tag != b"IHDR" or size != 13 or not all(struct.unpack(">II", body[:8])):
                    raise ValueError("render PNG needs valid image dimensions")
            tags.append(tag)
            offset = end + 4
            if tag == b"IEND":
                if size or offset != len(data) or b"IDAT" not in tags:
                    raise ValueError("render PNG structure is invalid")
                return "png"
        raise ValueError("render PNG is incomplete")
    if data.startswith(b"\xff\xd8\xff") and data.endswith(b"\xff\xd9"):
        offset, has_frame = 2, False
        frames = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
        while offset < len(data) - 2:
            if data[offset] != 0xFF:
                break
            while offset < len(data) and data[offset] == 0xFF:
                offset += 1
            if offset >= len(data):
                break
            marker = data[offset]
            offset += 1
            if offset + 2 > len(data):
                break
            size = int.from_bytes(data[offset:offset + 2], "big")
            if size < 2 or offset + size > len(data):
                break
            if marker in frames:
                if size < 8 or not all(struct.unpack(">HH", data[offset + 3:offset + 7])):
                    break
                has_frame = True
            if marker == 0xDA and has_frame and offset + size < len(data) - 2:
                return "jpeg"
            offset += size
        raise ValueError("render JPEG is missing valid frame/scan structure")
    raise ValueError("render must be a real PNG or JPEG, not a placeholder or renamed file")


def _validate_inspection(inspection, readback_sha, render_sha):
    if not isinstance(inspection, dict):
        raise ValueError("inspection must be an object")
    if (inspection.get("readback_sha256") != readback_sha
            or inspection.get("render_sha256") != render_sha):
        raise ValueError("inspection is stale or bound to a different readback/render")
    inspector = inspection.get("inspector")
    if not isinstance(inspector, dict) or inspector.get("method") != "native-render-inspection":
        raise ValueError("inspection must identify an actual native-render inspector")
    _text(inspector.get("id"), "inspection.inspector.id")
    if inspection.get("verdict") != "pass":
        raise ValueError("native-render inspection did not pass")
    checks = inspection.get("checks")
    if not isinstance(checks, dict):
        raise ValueError("native-render inspection must include concrete checks")
    for name in CHECK_NAMES:
        check = checks.get(name)
        if not isinstance(check, dict) or check.get("verdict") != "pass":
            raise ValueError(f"native-render {name} must pass")
        evidence = _text(check.get("evidence"), f"inspection.{name}.evidence")
        if evidence.strip().lower() in {"pass", "passed", "ok", "yes", "checked", "none", "n/a", "通过", "正常", "无"}:
            raise ValueError(f"native-render {name} needs a specific observed conclusion")


def verify(prewrite, readback, render, inspection):
    """Recheck original evidence and native results before returning completion."""
    originals = {name: reference(path) for name, path in
                 (("prewrite", prewrite), ("readback", readback),
                  ("render", render), ("inspection", inspection))}
    receipt = load(prewrite)
    if (not isinstance(receipt, dict) or receipt.get("version") != VERSION
            or receipt.get("status") != "prewrite-approved"
            or receipt.get("complete") is not False
            or receipt.get("native_render_pending") is not True):
        raise ValueError("verify requires a valid prewrite-approved receipt; prewrite is not completion")
    inputs = receipt.get("inputs")
    if not isinstance(inputs, dict) or set(inputs) != set(INPUT_NAMES):
        raise ValueError("prewrite receipt must bind every original input")
    for name, item in inputs.items():
        check_reference(item, name)
    rebuilt = prepare(**{name: inputs[name]["path"] for name in INPUT_NAMES})
    if canonical(receipt) != canonical(rebuilt):
        raise ValueError("prewrite receipt no longer matches its original evidence")
    candidate = snapshot(load(inputs["candidate"]["path"]), "candidate")
    actual = snapshot(load(readback), "readback")
    if actual["document_id"] != candidate["document_id"]:
        raise ValueError("readback belongs to another document")
    if canonical(actual["blocks"]) != canonical(candidate["blocks"]):
        raise ValueError("readback blocks differ from the approved candidate")
    if canonical(actual["revision"]) == canonical(candidate["revision"]):
        raise ValueError("readback revision must change after the native write")
    image_format = _image_format(render)
    _validate_inspection(load(inspection), originals["readback"]["sha256"], originals["render"]["sha256"])
    for name, item in originals.items():
        check_reference(item, name)
    for name, item in inputs.items():
        check_reference(item, name)
    _validate_answer_receipt(inputs["answer_receipt"]["path"], inputs["candidate"]["path"], candidate)
    return {"version": VERSION, "status": "verified", "complete": True,
            "native_render_pending": False, "document_id": actual["document_id"],
            "baseline_revision": candidate["revision"], "readback_revision": actual["revision"],
            "block_ids": rebuilt["block_ids"], "inputs": inputs,
            "evidence": originals, "render_format": image_format,
            "validation_scope": "local evidence bindings and native-inspector attestation; no external write performed"}


def save_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    preparing = commands.add_parser("prepare", help="authorize only the declared patch; native render remains pending")
    for name in INPUT_NAMES:
        preparing.add_argument("--" + name.replace("_", "-"), required=True)
    preparing.add_argument("--output", required=True)
    verifying = commands.add_parser("verify", help="complete only after exact readback and native render inspection")
    for name in ("prewrite", "readback", "render", "inspection", "output"):
        verifying.add_argument("--" + name, required=True)
    args = vars(parser.parse_args())
    command, output = args.pop("command"), args.pop("output")
    try:
        receipt = prepare(**args) if command == "prepare" else verify(**args)
        save_new(output, receipt)
        print(receipt["status"] + (": native render and readback still required; not complete" if command == "prepare" else ": post-write evidence verified"))
        return 0
    except (ValueError, KeyError, TypeError, OSError, UnicodeError) as exc:
        print("FAIL: " + str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
