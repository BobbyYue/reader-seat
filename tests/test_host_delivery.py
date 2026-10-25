"""Host-consumer protocol tests. Synthetic returns do not certify any platform."""
import base64
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import host_delivery as host


class HostDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.artifact = self.root / "candidate.txt"
        self.artifact.write_bytes(b"SYNTHETIC checked text")
        self.context = self.root / "request.txt"
        self.context.write_bytes(b"SYNTHETIC request")
        self.raw = self.artifact.read_bytes()
        self.envelope = {"schema_version": 1, "delivery_state": "checked",
            "review_method": "self-check" if host.SKILL_NAME == "hit-send" else "independent",
            "external_action_authorized": False, "verification_scope": "local-candidate-only",
            "artifact": {"path": str(self.artifact), "bytes": len(self.raw), "sha256": host.digest(self.raw)},
            "payload_encoding": "base64", "payload": base64.b64encode(self.raw).decode(),
            "checked_inputs_sha256": "a" * 64,
            "verified_inputs": {str(self.artifact.resolve()): host.digest(self.raw),
                                str(self.context.resolve()): host.digest(self.context.read_bytes())},
            "issues": [], "user_notice_required": False, "user_question_required": False}

    def invoke(self, **kwargs):
        return host.run(["synthetic-argument"], expected_artifact=self.artifact, context_files=[self.context], **kwargs)

    def completion(self, value=None, code=0):
        return subprocess.CompletedProcess([], code, json.dumps(value or self.envelope).encode(), b"")

    def test_runs_package_verifier_without_shell_and_returns_unchanged_envelope(self):
        with patch.object(host.subprocess, "run", return_value=self.completion()) as process:
            result = self.invoke()
        command = process.call_args.args[0]
        self.assertEqual(command[:5], [sys.executable, "-E", "-S", "-B", str(ROOT / "scripts/deliver.py")])
        self.assertNotIn("shell", process.call_args.kwargs)
        self.assertEqual(result, self.envelope)

    def test_failed_process_cannot_release_even_a_well_formed_envelope(self):
        with patch.object(host.subprocess, "run", return_value=self.completion(code=1)), self.assertRaises(ValueError):
            self.invoke()

    def test_missing_or_malformed_payload_is_rejected(self):
        for raw in (b"", b"PASS", b'{}', b'{}\n{}', b'{"schema_version":1,"schema_version":1}'):
            with self.subTest(raw=raw), patch.object(host.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, raw, b"")), self.assertRaises(ValueError):
                self.invoke()

    def test_artifact_context_and_symlink_changes_block_before_display(self):
        for target in (self.artifact, self.context):
            original = target.read_bytes()
            def changed(*args, **kwargs):
                target.write_bytes(original + b" changed")
                return self.completion()
            with patch.object(host.subprocess, "run", side_effect=changed), self.assertRaises(ValueError):
                self.invoke()
            target.write_bytes(original)
        alias = self.root / "context-alias.txt"
        alias.symlink_to(self.context)
        second = self.root / "different-context.txt"
        second.write_bytes(self.context.read_bytes())
        def retarget(*args, **kwargs):
            alias.unlink(); alias.symlink_to(second)
            return self.completion()
        with patch.object(host.subprocess, "run", side_effect=retarget), self.assertRaises(ValueError):
            host.run(["synthetic"], expected_artifact=self.artifact, context_files=[alias])

    def test_state_method_permission_and_payload_tampering_are_rejected(self):
        changes = [{"delivery_state": "prepared"}, {"review_method": "not-attested"},
                   {"external_action_authorized": True}, {"schema_version": True},
                   {"payload": base64.b64encode(b"Changed text").decode()}, {"payload": "not base64"},
                   {"user_notice_required": True}, {"verification_scope": "semantic-and-format-only"},
                   {"verified_inputs": {}}, {"checked_inputs_sha256": "z" * 64}]
        for change in changes:
            with self.subTest(change=change), patch.object(host.subprocess, "run", return_value=self.completion({**self.envelope, **change})), self.assertRaises(ValueError):
                self.invoke()

    def test_draft_needs_host_choice_issues_and_notice(self):
        if host.SKILL_NAME == "hit-send":
            with self.assertRaises(ValueError):
                self.invoke(accepted_state="draft")
            return
        draft = {**self.envelope, "delivery_state": "draft", "issues": ["SYNTHETIC unresolved issue"],
                 "user_notice_required": True, "user_question_required": True}
        with patch.object(host.subprocess, "run", return_value=self.completion(draft)):
            with self.assertRaises(ValueError):
                self.invoke()
            self.assertEqual(self.invoke(accepted_state="draft")["delivery_state"], "draft")

    def test_output_redirection_and_unbounded_timeout_are_rejected(self):
        for arguments in (["--output", "ignored"], ["--output=ignored"], ["--out", "ignored"],
                          ["--out=ignored"], ["--o", "ignored"], "shell command", []):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                host.run(arguments, expected_artifact=self.artifact, context_files=[self.context])
        for timeout in (0, -1, float("inf"), float("nan"), True):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                self.invoke(timeout=timeout)

    def test_timeout_does_not_release_text(self):
        with patch.object(host.subprocess, "run", side_effect=subprocess.TimeoutExpired("synthetic", 1)), self.assertRaises(ValueError):
            self.invoke()

    def test_real_package_entrypoint_rejects_missing_evidence(self):
        with self.assertRaises(host.HostDeliveryBlocked):
            self.invoke()


class NativeHostIntegrationTests(unittest.TestCase):
    def test_renamed_package_keeps_independent_review_and_evidence_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            relocated = Path(tmp) / "arbitrary-checkout-name"
            shutil.copytree(ROOT, relocated, ignore=shutil.ignore_patterns(".git", "__pycache__", "node_modules"))
            # Generate fresh evidence in the relocated installation; an old
            # installation's implementation-bound review must not be reused.
            result = subprocess.run([sys.executable, "-E", "-S", "-B", "-m", "unittest",
                "test_host_delivery.NativeHostIntegrationTests.test_real_native_verification_is_required_for_release", "-q"],
                cwd=relocated / "tests", capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_real_native_verification_is_required_for_release(self):
        import test_checked_delivery_cli as fixtures
        case = fixtures.CheckedDeliveryCLITests()
        case.setUp()
        if host.SKILL_NAME == "hit-send":
            self.addCleanup(case.tearDown)
            artifact, contexts = case.response, [case.source]
            arguments = [str(case.response), "--source", str(case.source), "--review", str(case.review)]
            fail_path = case.review
        elif host.SKILL_NAME == "reader-seat":
            self.addCleanup(case.doCleanups)
            artifact, contexts, arguments = case.artifact, [case.fixture.source_bundle], case.args
            fail_path = case.aggregate
        else:
            self.addCleanup(case.doCleanups)
            artifact, contexts, arguments = case.artifact, [case.fixture.source_path], case.args
            fail_path = case.reviews[0]
        result = host.run(arguments, expected_artifact=artifact, context_files=contexts)
        self.assertEqual(base64.b64decode(result["payload"]), artifact.read_bytes())
        self.assertEqual(result["review_method"], "independent")
        with self.assertRaises(host.HostDeliveryBlocked):
            host.run(arguments, expected_artifact=artifact, context_files=contexts, accepted_state="self-checked")
        with tempfile.TemporaryDirectory() as tmp:
            wrong_context = Path(tmp) / "new-request.txt"
            wrong_context.write_text("SYNTHETIC new request unrelated to the checked one")
            with self.assertRaises(host.HostDeliveryBlocked):
                host.run(arguments, expected_artifact=artifact, context_files=[wrong_context])
            for index, flag in enumerate(("--out", "--out=", "--o", "--output")):
                output = Path(tmp) / (str(index) + ".json")
                redirect = [flag + str(output)] if flag.endswith("=") else [flag, str(output)]
                with self.assertRaises(host.HostDeliveryBlocked):
                    host.run([*arguments, *redirect], expected_artifact=artifact, context_files=contexts)
                self.assertFalse(output.exists())
        fail_path.unlink()
        with self.assertRaises(host.HostDeliveryBlocked):
            host.run(arguments, expected_artifact=artifact, context_files=contexts)


if __name__ == "__main__":
    unittest.main()
