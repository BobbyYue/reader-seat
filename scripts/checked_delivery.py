"""Pack the exact checked bytes; this is not a host permission or semantic judge."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sys
from pathlib import Path


class DeliveryBlocked(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshots(paths, *, inactive_fields=None, opaque_paths=()):
    """Watch declared inputs and hash-bound evidence references, never source URLs."""
    pending = [(Path(p).resolve(), None) for p in paths if p]
    opaque = {str(Path(p).resolve()) for p in opaque_paths if p}
    result = {}
    while pending:
        path, expected = pending.pop()
        if str(path) in result:
            if expected is not None and result[str(path)] != expected:
                raise DeliveryBlocked("Conflicting or stale evidence reference")
            continue
        raw = path.read_bytes()
        result[str(path)] = digest(raw)
        if expected is not None and (not re.fullmatch(r"[0-9a-f]{64}", expected) or result[str(path)] != expected):
            raise DeliveryBlocked("Evidence does not match its declared hash")
        if str(path) in opaque or path.suffix != ".json":
            continue
        try:
            value = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            continue

        excluded = (inactive_fields or {}).get(str(path), ())

        def collect(item, location=()):
            if location in excluded:
                return
            if isinstance(item, list):
                for index, child in enumerate(item):
                    collect(child, (*location, index))
            elif isinstance(item, dict):
                candidate = item.get("path")
                if isinstance(candidate, str) and isinstance(item.get("sha256"), str):
                    reference = Path(candidate)
                    if not reference.is_absolute():
                        root = Path(__file__).resolve().parents[1]
                        reference = (root / reference).resolve()
                        if not reference.is_relative_to(root):
                            raise DeliveryBlocked("Relative evidence escapes the skill package")
                    pending.append((reference.resolve(), item["sha256"]))
                for key, candidate in item.items():
                    if key.endswith("_path") and isinstance(candidate, str) and isinstance(item.get(key[:-5] + "_sha256"), str):
                        reference = Path(candidate)
                        if not reference.is_absolute():
                            raise DeliveryBlocked("Task evidence paths must be absolute")
                        pending.append((reference.resolve(), item[key[:-5] + "_sha256"]))
                for key, child in item.items():
                    collect(child, (*location, key))
        collect(value)
    return result


def pack(artifact, inputs, verify, *, inactive_fields=None, opaque_paths=()):
    artifact = Path(artifact).resolve()
    watched = [artifact, *inputs]
    opaque = [artifact, *opaque_paths]
    before = snapshots(watched, inactive_fields=inactive_fields, opaque_paths=opaque)
    payload = artifact.read_bytes()
    if digest(payload) != before[str(artifact)]:
        raise DeliveryBlocked("Candidate changed before verification")
    result = verify()
    if not isinstance(result, dict) or result.get("status") not in {"pass", "review-incomplete-draft"}:
        raise DeliveryBlocked("No final check result; prepared, built and schema-only states cannot deliver")
    if result.get("artifact_sha256") != digest(payload):
        raise DeliveryBlocked("Verification result is not bound to the returned bytes")
    if result.get("review_method") not in ("independent", "scoped-revalidation", "self-check"):
        raise DeliveryBlocked("Final verification must identify its review method")
    consumed = result.get("verified_inputs")
    if (not isinstance(consumed, dict) or consumed.get(str(artifact)) != digest(payload)
            or any(not isinstance(p, str) or not isinstance(h, str) or not re.fullmatch(r"[0-9a-f]{64}", h)
                   for p, h in consumed.items())):
        raise DeliveryBlocked("Verifier must bind the actual consumed artifact and inputs")
    if result.get("verification_scope") == "semantic-and-format-only":
        raise DeliveryBlocked("Local semantic verification is not finished delivery")
    if any(before.get(path) != value for path, value in result.get("verified_inputs", {}).items()):
        raise DeliveryBlocked("Verifier consumed a different input snapshot")
    after = snapshots(watched, inactive_fields=inactive_fields, opaque_paths=opaque)
    if before != after:
        raise DeliveryBlocked("Candidate or evidence changed during verification")
    is_draft = result["status"] == "review-incomplete-draft"
    if is_draft and not result.get("issues"):
        raise DeliveryBlocked("Incomplete drafts must identify unresolved issues")
    context = digest(json.dumps(before, sort_keys=True).encode())
    return {
        "schema_version": 1,
        "delivery_state": "draft" if is_draft else "checked",
        "verification_scope": "local-candidate-only",
        "review_method": result.get("review_method", "not-attested"),
        "external_action_authorized": False,
        "artifact": {"path": str(artifact), "sha256": digest(payload), "bytes": len(payload)},
        "checked_inputs_sha256": context,
        "verified_inputs": consumed,
        "payload_encoding": "base64",
        "payload": base64.b64encode(payload).decode("ascii"),
        "issues": result.get("issues", []),
        "user_notice_required": is_draft,
        "user_question_required": is_draft,
    }


def emit(envelope, output=None):
    content = json.dumps(envelope, ensure_ascii=False) + "\n"
    if output is None:
        sys.stdout.write(content)
        return
    # Never overwrite an input, an earlier checked result, or a symlink target.
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(content)


def blocked():
    # Do not expose source text, model output, or path-bearing exception messages.
    sys.stderr.write('Delivery blocked: verification failed or inputs changed. Inspect the existing checks; no payload was released.\n')
    return 1
