#!/usr/bin/env python3
"""Smoke-test the vendor-neutral command adapter transports."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "scripts" / "run_evals.py"
CASE_ID = "xagent-analysis-causality"


def prepare(run_dir: str, adapter: str, agent_id: str) -> None:
    subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "prepare",
            "--adapter",
            adapter,
            "--agent-id",
            agent_id,
            "--case",
            CASE_ID,
            "--repetitions",
            "1",
            "--output-dir",
            run_dir,
        ],
        check=True,
        cwd=ROOT,
    )


def execute(run_dir: str, env: dict[str, str]) -> None:
    subprocess.run(
        [sys.executable, str(RUNNER), "execute", "--run-dir", run_dir],
        check=True,
        cwd=ROOT,
        env=env,
    )
    outputs = list((Path(run_dir) / "outputs").glob("*.txt"))
    if len(outputs) != 1 or outputs[0].stat().st_size == 0:
        raise SystemExit("adapter smoke test did not produce one non-empty output")


def test_stdin_adapter() -> None:
    with tempfile.TemporaryDirectory(prefix="reader-seat-stdin-") as run_dir:
        prepare(run_dir, "command-stdin", "stdin-smoke")
        env = os.environ.copy()
        env["READER_SEAT_AGENT_COMMAND_JSON"] = json.dumps(
            [sys.executable, "-c", "import sys; print(sys.stdin.read())"]
        )
        execute(run_dir, env)


def test_file_adapter() -> None:
    with tempfile.TemporaryDirectory(prefix="reader-seat-files-") as run_dir:
        prepare(run_dir, "command-files", "files-smoke")
        copy_code = (
            "from pathlib import Path; import sys; "
            "Path(sys.argv[2]).write_text("
            "Path(sys.argv[1]).read_text(encoding='utf-8'), encoding='utf-8')"
        )
        env = os.environ.copy()
        env["READER_SEAT_AGENT_FILE_COMMAND_JSON"] = json.dumps(
            [sys.executable, "-c", copy_code, "{prompt_file}", "{output_file}"]
        )
        execute(run_dir, env)


def main() -> int:
    test_stdin_adapter()
    test_file_adapter()
    print("PASS: vendor-neutral command adapter transports")
    return 0


if __name__ == "__main__":
    sys.exit(main())
