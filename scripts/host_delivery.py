"""Portable host-side consumer for the package's actual checked-delivery CLI.

Call from trusted host code before preview/copy/replace. This module does not
intercept unrelated application paths or authenticate an arbitrary OS user.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import math
import re
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "reader-seat"
METHODS = {
    "reader-seat": {"checked": {"independent"}, "draft": {"independent"}},
    "3080-brief": {"checked": {"independent", "scoped-revalidation"},
                   "self-checked": {"self-check"}, "draft": {"independent", "scoped-revalidation"}},
    "hit-send": {"checked": {"self-check"}},
}


class HostDeliveryBlocked(ValueError):
    pass


def require(value, message):
    if not value:
        raise HostDeliveryBlocked(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON fields")
        result[key] = value
    return result


def fingerprint(paths):
    return {str(Path(p).absolute()): (str(Path(p).resolve()), digest(Path(p).read_bytes())) for p in paths}


def validate_envelope(raw, artifact, expected_bytes, accepted_state, expected_context):
    """Validate fresh CLI output, never treat model-supplied JSON as evidence."""
    try:
        result = json.loads(raw, object_pairs_hook=unique_object)
        require(isinstance(result, dict) and type(result.get("schema_version")) is int
                and result["schema_version"] == 1, "Invalid delivery schema")
        require(result.get("delivery_state") == accepted_state, "Unexpected delivery state")
        require(result.get("review_method") in METHODS[SKILL_NAME][accepted_state], "Review method does not fit this workflow")
        require(result.get("external_action_authorized") is False, "Content acceptance is not publication permission")
        require(result.get("verification_scope") == "local-candidate-only", "Unrecognized verification scope")
        info = result["artifact"]
        require(isinstance(info, dict) and isinstance(info.get("path"), str)
                and Path(info["path"]).resolve() == artifact, "Delivery targets a different artifact")
        require(type(info.get("bytes")) is int and info["bytes"] == len(expected_bytes), "Incorrect artifact size")
        require(result.get("payload_encoding") == "base64" and isinstance(result.get("payload"), str), "Missing payload")
        payload = base64.b64decode(result["payload"], validate=True)
        require(payload == expected_bytes and digest(payload) == info.get("sha256"), "Checked payload changed")
        require(isinstance(result.get("checked_inputs_sha256"), str)
                and re.fullmatch(r"[0-9a-f]{64}", result["checked_inputs_sha256"]), "Missing input binding")
        consumed = result.get("verified_inputs")
        require(isinstance(consumed, dict) and all(isinstance(p, str) and isinstance(h, str)
                and re.fullmatch(r"[0-9a-f]{64}", h) for p, h in consumed.items()), "Missing consumed inputs")
        require(consumed.get(str(artifact)) == digest(expected_bytes)
                and all(consumed.get(p) == h for p, h in expected_context.items()),
                "Current host context was not consumed by verification")
        require(isinstance(result.get("issues"), list), "Missing issue list")
        draft = accepted_state == "draft"
        require(result.get("user_notice_required") is draft and result.get("user_question_required") is draft,
                "Draft notices or final-state flags are inconsistent")
        if draft:
            require(bool(result["issues"]), "Draft must disclose unresolved issues")
        return result
    except (KeyError, TypeError, json.JSONDecodeError, UnicodeError, binascii.Error) as exc:
        raise HostDeliveryBlocked("Malformed checked output") from exc


def run(arguments, *, expected_artifact, context_files, accepted_state="checked", timeout=120):
    """Reverify using this installed package; consume no caller-provided receipt.

    The host chooses state and current context, not the producing model. Fresh
    validation is required on every action that exposes a newly changed result.
    Source files remain ephemeral; nothing is logged or retained by this helper.
    """
    require(accepted_state in METHODS[SKILL_NAME], "Unsupported delivery state")
    require(isinstance(arguments, (list, tuple)) and arguments
            and all(isinstance(a, str) and a and "\x00" not in a for a in arguments), "Use an argument array")
    require(not any(a.startswith("--") and len(a.split("=", 1)[0]) > 2
                    and "--output".startswith(a.split("=", 1)[0]) for a in arguments), "Host owns the output channel")
    require(type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0, "Use a bounded positive timeout")
    require(isinstance(context_files, (list, tuple)) and all(isinstance(p, (str, Path)) for p in context_files),
            "Host must supply a context-file list")
    context = [Path(p).absolute() for p in context_files]
    require(bool(context), "Host must supply its current request/context files")
    original_path = Path(expected_artifact).absolute()
    artifact = original_path.resolve()
    scripts = sorted((ROOT / "scripts").glob("*.py"))
    configs = sorted((ROOT / "config").glob("*.json")) if (ROOT / "config").exists() else []
    watched = [original_path, *context, *scripts, *configs, ROOT / "SKILL.md"]
    try:
        before = fingerprint(watched)
        expected = artifact.read_bytes()
        require(digest(expected) == before[str(original_path)][1], "Artifact changed before validation")
        completed = subprocess.run([sys.executable, "-E", "-S", "-B", str(ROOT / "scripts/deliver.py"), *arguments],
                                   cwd=ROOT, capture_output=True, timeout=timeout, check=False)
        require(completed.returncode == 0, "Checked delivery did not complete; no result was released")
        require(before == fingerprint(watched), "Request, artifact or validation code changed during delivery")
        expected_context = {before[str(p)][0]: before[str(p)][1] for p in context}
        return validate_envelope(completed.stdout, artifact, expected, accepted_state, expected_context)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HostDeliveryBlocked("Checked delivery unavailable; preserve the original and retry safely") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-artifact", required=True, type=Path)
    parser.add_argument("--context", action="append", required=True, type=Path)
    parser.add_argument("--accepted-state", default="checked", choices=("checked", "draft", "self-checked"))
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    arguments = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
    try:
        result = run(arguments, expected_artifact=args.expected_artifact, context_files=args.context,
                     accepted_state=args.accepted_state, timeout=args.timeout)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, TypeError):
        print("Host delivery blocked. No checked content was released.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
