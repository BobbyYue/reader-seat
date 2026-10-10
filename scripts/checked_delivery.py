"""Pack the exact checked bytes; this is not a host permission or semantic judge."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
from pathlib import Path


class DeliveryBlocked(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshots(paths):
    """Watch declared inputs and hash-bound evidence references, never source URLs."""
    pending = [(Path(p).resolve(), None) for p in paths if p]
    result = {}
    while pending:
        path, expected = pending.pop()
        if str(path) in result:
            continue
        raw = path.read_bytes()
        result[str(path)] = digest(raw)
        if path.suffix != ".json":
            continue
        try:
            value = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            continue

        def collect(item):
            if isinstance(item, list):
                for child in item:
                    collect(child)
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
                for child in item.values():
                    collect(child)
        collect(value)
    return result


def pack(artifact, inputs, verify):
    artifact = Path(artifact).resolve()
    watched = [artifact, *inputs]
    before = snapshots(watched)
    payload = artifact.read_bytes()
    if digest(payload) != before[str(artifact)]:
        raise DeliveryBlocked("Candidate changed before verification")
    result = verify()
    if not isinstance(result, dict) or result.get("status") not in {"pass", "review-incomplete-draft"}:
        raise DeliveryBlocked("No final check result; prepared, built and schema-only states cannot deliver")
    if result.get("artifact_sha256") != digest(payload):
        raise DeliveryBlocked("Verification result is not bound to the returned bytes")
    if any(before.get(path) != value for path, value in result.get("verified_inputs", {}).items()):
        raise DeliveryBlocked("Verifier consumed a different input snapshot")
    after = snapshots(watched)
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
