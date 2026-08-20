#!/usr/bin/env python3
"""Prepare, execute, and grade Reader's Seat cross-agent regression cases."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import resolve_modules


ROOT = Path(__file__).resolve().parent.parent
CASES_PATH = ROOT / "evals" / "cross-agent-cases.json"
ADAPTERS_PATH = ROOT / "config" / "agent-adapters.json"
CONTRACT_PATH = ROOT / "config" / "skill-contract.json"
RUBRIC_PATH = ROOT / "evals" / "judge-rubric.md"
JUDGE_SCHEMA_PATH = ROOT / "evals" / "judge-output.schema.json"


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"error: cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"error: expected a JSON object in {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_cases(case_ids: list[str]) -> list[dict]:
    data = load_json(CASES_PATH)
    cases = data.get("cases")
    if not isinstance(cases, list):
        raise SystemExit("error: cross-agent case file has no cases array")
    by_id = {case.get("id"): case for case in cases if isinstance(case, dict)}
    if not case_ids:
        return list(by_id.values())
    missing = [case_id for case_id in case_ids if case_id not in by_id]
    if missing:
        raise SystemExit(f"error: unknown case IDs: {', '.join(missing)}")
    return [by_id[case_id] for case_id in case_ids]


def module_plan(case: dict) -> dict:
    namespace = argparse.Namespace(
        scenario=case["scenario"],
        operation=case["operation"],
        artifact=bool(case.get("artifact")),
        chat_output=not bool(case.get("artifact")),
        output_format=case.get("output_format", "html"),
        risk=case.get("risk", "standard"),
        title=bool(case.get("title")),
        visual=case.get("visual", "none"),
        evaluate=False,
        portability=False,
        maintenance=False,
        emit="json",
    )
    return resolve_modules.resolve(namespace, resolve_modules.load_profiles())


def dominant_language(text: str) -> str:
    without_urls = re.sub(r"https?://\S+", " ", text)
    cjk = len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", without_urls))
    latin = len(re.findall(r"[A-Za-z]", without_urls))
    total = cjk + latin
    if total < 40:
        return "unknown"
    share = cjk / total
    if share >= 0.25:
        return "zh"
    if share <= 0.10:
        return "en"
    return "mixed"


def locked_test_decisions(case: dict) -> dict:
    source_language = dominant_language(case["source_material"])
    if source_language in {"mixed", "unknown"}:
        raise SystemExit(f"error: case {case['id']} needs an explicit frozen output language")
    return {
        "output_language": case.get("output_language", source_language),
        "output_format": case.get("output_format", "html" if case.get("artifact") else "chat"),
        "publication_target": "none",
    }


def build_producer_prompt(case: dict, plan: dict) -> str:
    decisions = locked_test_decisions(case)
    bundle = resolve_modules.render_bundle(
        plan,
        contract_id=f"eval-{case['id']}",
        output_language=decisions["output_language"],
    )
    return f"""Use the generated Reader's Seat task contract below as the complete
default instruction context. Apply it silently; do not mention the skill, this
test, module routing, internal records, tools, or evaluation.

The evaluation harness owns runtime enforcement for this frozen, read-only test.
Do not create runtime files or call external tools. Treat these decisions as the
locked task contract; the harness will reject a candidate that drifts from them:
- output_language: {decisions['output_language']}
- output_format: {decisions['output_format']}
- publication_target: none

GENERATED TASK CONTRACT
{bundle}

Complete the user's request using only the frozen source material. Do not add a
fact, number, owner, reason, result, or certainty that the source does not
support. Return only the finished user-facing answer. Do not edit, publish, or
send anything and do not describe your process.

USER REQUEST
{case['request']}

FROZEN SOURCE MATERIAL
{case['source_material']}
"""


def build_judge_prompt(case: dict, candidate: str) -> str:
    rubric = RUBRIC_PATH.read_text(encoding="utf-8")
    schema = JUDGE_SCHEMA_PATH.read_text(encoding="utf-8")
    return f"""Act as an independent semantic judge. Evaluate the candidate
against the frozen source and request. Do not rewrite it. Use the rubric and
return exactly one JSON object that satisfies the supplied schema. Do not wrap
the JSON in Markdown.

RUBRIC
{rubric}

OUTPUT JSON SCHEMA
{schema}

SCENARIO
{case['scenario']}

USER REQUEST
{case['request']}

FROZEN SOURCE MATERIAL
{case['source_material']}

IMMUTABLE FACTS
{json.dumps(case['immutable_facts'], ensure_ascii=False)}

REQUIRED BEHAVIORS
{json.dumps(case['required_behaviors'], ensure_ascii=False)}

FORBIDDEN BEHAVIORS
{json.dumps(case['forbidden_behaviors'], ensure_ascii=False)}

CANDIDATE
{candidate}
"""


def get_adapter(adapter_id: str) -> dict:
    adapters = load_json(ADAPTERS_PATH).get("adapters", {})
    adapter = adapters.get(adapter_id) if isinstance(adapters, dict) else None
    if not isinstance(adapter, dict):
        raise SystemExit(f"error: unknown adapter: {adapter_id}")
    return adapter


def validate_adapter_parameters(adapter: dict, model: str | None) -> None:
    required = adapter.get("requires", [])
    if "model" in required and not model:
        raise SystemExit("error: the selected adapter requires --model")


def expand_command(
    adapter: dict,
    *,
    model: str | None,
    prompt_file: Path,
    output_file: Path,
) -> list[str]:
    values = {
        "model": model or "",
        "prompt_file": str(prompt_file),
        "output_file": str(output_file),
        "skill_root": str(ROOT),
        "judge_schema": str(JUDGE_SCHEMA_PATH),
    }
    command = adapter.get("command")
    if not isinstance(command, list) or not command:
        env_name = adapter.get("command_env")
        if not isinstance(env_name, str) or not env_name:
            raise SystemExit("error: command adapter has no command array or command_env")
        raw_command = os.environ.get(env_name)
        if not raw_command:
            raise SystemExit(
                f"error: command adapter requires {env_name} as a JSON argv array"
            )
        try:
            command = json.loads(raw_command)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"error: {env_name} is not valid JSON: {exc}") from exc
        if not isinstance(command, list) or not command or not all(
            isinstance(part, str) and part for part in command
        ):
            raise SystemExit(f"error: {env_name} must contain a non-empty JSON string array")
    try:
        return [str(part).format_map(values) for part in command]
    except KeyError as exc:
        raise SystemExit(f"error: unknown adapter placeholder: {exc}") from exc


def run_command_adapter(
    adapter: dict,
    *,
    model: str | None,
    prompt_file: Path,
    output_file: Path,
    log_file: Path,
) -> tuple[bool, str]:
    command = expand_command(
        adapter,
        model=model,
        prompt_file=prompt_file,
        output_file=output_file,
    )
    prompt = prompt_file.read_text(encoding="utf-8")
    timeout = int(adapter.get("timeout_seconds", 420))
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            input=prompt if adapter.get("prompt_transport") == "stdin" else None,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log_file.write_text(f"adapter execution failed: {exc}\n", encoding="utf-8")
        return False, str(exc)

    log_file.write_text(
        "COMMAND\n"
        + json.dumps(command, ensure_ascii=False)
        + "\n\nSTDOUT\n"
        + completed.stdout
        + "\n\nSTDERR\n"
        + completed.stderr,
        encoding="utf-8",
    )
    if adapter.get("result_transport") == "stdout":
        output_file.write_text(completed.stdout, encoding="utf-8")
    success = completed.returncode == 0 and output_file.is_file() and output_file.stat().st_size > 0
    return success, f"exit={completed.returncode}"


def prepare_run(args: argparse.Namespace) -> Path:
    run_dir = Path(args.output_dir).expanduser().resolve()
    if run_dir.exists() and any(run_dir.iterdir()) and not args.overwrite:
        raise SystemExit(f"error: output directory is not empty: {run_dir}; use --overwrite")
    run_dir.mkdir(parents=True, exist_ok=True)
    for name in ("prompts", "outputs", "logs", "judgments"):
        (run_dir / name).mkdir(exist_ok=True)

    adapter = get_adapter(args.adapter)
    validate_adapter_parameters(adapter, args.model)
    cases = selected_cases(args.case)
    contract = load_json(CONTRACT_PATH)
    items = []
    for case in cases:
        plan = module_plan(case)
        for repetition in range(1, args.repetitions + 1):
            stem = f"{case['id']}--r{repetition}"
            prompt_path = run_dir / "prompts" / f"{stem}.txt"
            output_path = run_dir / "outputs" / f"{stem}.txt"
            producer_prompt = build_producer_prompt(case, plan)
            prompt_path.write_text(producer_prompt, encoding="utf-8")
            items.append(
                {
                    "case_id": case["id"],
                    "repetition": repetition,
                    "prompt": str(prompt_path.relative_to(run_dir)),
                    "output": str(output_path.relative_to(run_dir)),
                    "log": str((run_dir / "logs" / f"{stem}.log").relative_to(run_dir)),
                    "module_ids": [module["id"] for module in plan["modules"]],
                    "runtime_rule_ids": plan["required_rule_ids"],
                    "prompt_bytes": len(producer_prompt.encode("utf-8")),
                    "status": "prepared",
                }
            )

    manifest = {
        "schema_version": 1,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "skill": "reader-seat",
        "skill_version": contract.get("skill_version"),
        "skill_root": str(ROOT),
        "case_file": str(CASES_PATH),
        "case_file_sha256": file_hash(CASES_PATH),
        "module_profile_sha256": file_hash(ROOT / "config" / "module-profiles.json"),
        "runtime_rules_sha256": file_hash(ROOT / "config" / "runtime-rules.json"),
        "adapter": args.adapter,
        "agent_id": args.agent_id or args.adapter,
        "agent_version": args.agent_version or "not-recorded",
        "model": args.model or "manual-not-recorded",
        "repetitions": args.repetitions,
        "items": items,
    }
    write_json(run_dir / "manifest.json", manifest)
    print(f"PREPARED: {len(items)} run item(s) in {run_dir}")
    if adapter.get("mode") == "manual":
        print("MANUAL: run each prompt file unchanged and save only the final answer at its output path")
    return run_dir


def execute_run(run_dir: Path) -> None:
    manifest_path = run_dir / "manifest.json"
    manifest = load_json(manifest_path)
    if file_hash(CASES_PATH) != manifest.get("case_file_sha256"):
        raise SystemExit("error: frozen case file changed after run preparation")
    adapter = get_adapter(str(manifest.get("adapter")))
    if adapter.get("mode") == "manual":
        print("MANUAL: no command executed; populate the prepared output files, then run grade")
        return
    validate_adapter_parameters(adapter, str(manifest.get("model")))

    completed_count = 0
    failed_count = 0
    for item in manifest.get("items", []):
        output_path = run_dir / item["output"]
        if output_path.is_file() and output_path.stat().st_size > 0:
            item["status"] = "completed"
            completed_count += 1
            continue
        success, detail = run_command_adapter(
            adapter,
            model=str(manifest.get("model")),
            prompt_file=run_dir / item["prompt"],
            output_file=output_path,
            log_file=run_dir / item["log"],
        )
        item["status"] = "completed" if success else "failed"
        item["execution_detail"] = detail
        completed_count += int(success)
        failed_count += int(not success)
        write_json(manifest_path, manifest)
        print(f"{item['status'].upper()}: {item['case_id']} repetition {item['repetition']}")

    print(f"EXECUTED: {completed_count} completed, {failed_count} failed")


def deterministic_grade(case: dict, text: str) -> dict:
    checks = case.get("hard_checks", {})
    normalize = lambda value: re.sub(r"\s+", "", str(value)).casefold()
    folded = normalize(text)
    failures: list[str] = []
    signals: list[str] = []
    decisions = locked_test_decisions(case)
    detected_language = dominant_language(text)
    if detected_language != decisions["output_language"]:
        failures.append(
            f"output language is {detected_language}, expected {decisions['output_language']}"
        )
    for literal in checks.get("must_contain", []):
        if normalize(literal) not in folded:
            failures.append(f"missing required literal: {literal}")
    for alternatives in checks.get("must_contain_any", []):
        if not isinstance(alternatives, list) or not alternatives:
            failures.append("invalid empty must_contain_any group")
        elif not any(normalize(literal) in folded for literal in alternatives):
            failures.append(f"missing required concept group: {alternatives}")
    for literal in checks.get("must_not_contain", []):
        if normalize(literal) in folded:
            failures.append(f"contains forbidden literal: {literal}")
    for pattern in checks.get("must_match", []):
        if not re.search(pattern, text, re.MULTILINE):
            failures.append(f"missing required pattern: {pattern}")
    for pattern in checks.get("must_not_match", []):
        if re.search(pattern, text, re.MULTILINE):
            failures.append(f"matches forbidden pattern: {pattern}")
    length = len(text.strip())
    minimum = checks.get("min_chars")
    maximum = checks.get("max_chars")
    if isinstance(minimum, int) and length < minimum:
        signals.append(f"output shorter than review signal: {length} < {minimum}")
    if isinstance(maximum, int) and length > maximum:
        signals.append(f"output longer than review signal: {length} > {maximum}")
    if length == 0:
        failures.append("output is empty")
    return {
        "verdict": "pass" if not failures else "fail",
        "output_chars": length,
        "failures": failures,
        "signals": signals,
    }


def parse_judgment(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError(f"judge did not return valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("judge result is not an object")
    required = {"verdict", "hard_gates", "hard_failures", "reader_outcome", "summary"}
    missing = required - set(value)
    if missing:
        raise ValueError(f"judge result missing keys: {sorted(missing)}")
    if value["verdict"] not in {"pass", "fail"}:
        raise ValueError("judge verdict must be pass or fail")
    expected_gates = {
        "fact_fidelity",
        "evidence_boundary",
        "scope_and_commitment",
        "scenario_completeness",
        "language_and_format",
        "title_and_visual_integrity",
        "action_boundary",
    }
    if set(value["hard_gates"]) != expected_gates:
        raise ValueError("judge hard_gates do not match the required set")
    if any(status not in {"pass", "fail", "not_applicable"} for status in value["hard_gates"].values()):
        raise ValueError("judge hard gate contains an invalid status")
    scores = value.get("reader_outcome")
    expected_scores = {
        "conclusion_retrieval",
        "paraphrase_accuracy",
        "evidence_traceability",
        "natural_expression",
        "actionability",
    }
    if not isinstance(scores, dict) or set(scores) != expected_scores:
        raise ValueError("judge reader outcome keys do not match the required set")
    if any(not isinstance(score, int) or not 1 <= score <= 5 for score in scores.values()):
        raise ValueError("judge reader outcome scores must be integers from 1 to 5")
    if any(status == "fail" for status in value["hard_gates"].values()) and value["verdict"] != "fail":
        raise ValueError("judge passed a candidate with a failed hard gate")
    return value


def judge_output(
    *,
    run_dir: Path,
    item: dict,
    case: dict,
    candidate: str,
    adapter_id: str,
    model: str | None,
    judge_index: int,
) -> dict:
    adapter = get_adapter(adapter_id)
    if adapter.get("mode") != "command":
        raise SystemExit("error: semantic judging requires a command adapter")
    validate_adapter_parameters(adapter, model)
    stem = f"{item['case_id']}--r{item['repetition']}--judge-{judge_index}"
    prompt_file = run_dir / "judgments" / f"{stem}.prompt.txt"
    output_file = run_dir / "judgments" / f"{stem}.json"
    log_file = run_dir / "logs" / f"{stem}.log"
    prompt_file.write_text(build_judge_prompt(case, candidate), encoding="utf-8")
    success, detail = run_command_adapter(
        adapter,
        model=model,
        prompt_file=prompt_file,
        output_file=output_file,
        log_file=log_file,
    )
    if not success:
        return {"verdict": "error", "error": f"judge execution failed: {detail}"}
    try:
        return parse_judgment(output_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"verdict": "error", "error": str(exc)}


def combine_judgments(judgments: list[dict]) -> dict:
    if not judgments:
        return {"verdict": "not_run"}
    if any(judgment.get("verdict") == "error" for judgment in judgments):
        return {
            "verdict": "error",
            "error": "at least one semantic judge run failed",
            "judge_runs": judgments,
        }

    gate_names = list(judgments[0]["hard_gates"])
    combined_gates = {}
    for gate in gate_names:
        statuses = [judgment["hard_gates"][gate] for judgment in judgments]
        if "fail" in statuses:
            combined_gates[gate] = "fail"
        elif "pass" in statuses:
            combined_gates[gate] = "pass"
        else:
            combined_gates[gate] = "not_applicable"

    score_names = list(judgments[0]["reader_outcome"])
    combined_scores = {
        score: min(judgment["reader_outcome"][score] for judgment in judgments)
        for score in score_names
    }
    failures = []
    for judgment in judgments:
        for failure in judgment.get("hard_failures", []):
            if failure not in failures:
                failures.append(failure)
    verdict = "fail" if any(judgment["verdict"] == "fail" for judgment in judgments) else "pass"
    return {
        "verdict": verdict,
        "hard_gates": combined_gates,
        "hard_failures": failures,
        "reader_outcome": combined_scores,
        "summary": f"Worst-of-{len(judgments)} semantic judge aggregation.",
        "judge_runs": judgments,
    }


def grade_run(
    run_dir: Path,
    *,
    judge_adapter: str | None,
    judge_model: str | None,
    judge_repetitions: int,
) -> dict:
    manifest = load_json(run_dir / "manifest.json")
    case_map = {case["id"]: case for case in selected_cases([])}
    results = []
    for item in manifest.get("items", []):
        case = case_map[item["case_id"]]
        output_path = run_dir / item["output"]
        if not output_path.is_file() or output_path.stat().st_size == 0:
            results.append(
                {
                    "case_id": item["case_id"],
                    "repetition": item["repetition"],
                    "deterministic": {"verdict": "fail", "failures": ["missing output file"]},
                    "semantic": {"verdict": "not_run"},
                    "overall": "fail",
                }
            )
            continue
        candidate = output_path.read_text(encoding="utf-8")
        deterministic = deterministic_grade(case, candidate)
        semantic = {"verdict": "not_run"}
        if judge_adapter:
            judgments = [
                judge_output(
                    run_dir=run_dir,
                    item=item,
                    case=case,
                    candidate=candidate,
                    adapter_id=judge_adapter,
                    model=judge_model,
                    judge_index=index,
                )
                for index in range(1, judge_repetitions + 1)
            ]
            semantic = combine_judgments(judgments)
        if deterministic["verdict"] == "fail" or semantic["verdict"] in {"fail", "error"}:
            overall = "fail"
        elif semantic["verdict"] == "pass":
            overall = "pass"
        else:
            overall = "deterministic_only"
        results.append(
            {
                "case_id": item["case_id"],
                "repetition": item["repetition"],
                "deterministic": deterministic,
                "semantic": semantic,
                "overall": overall,
            }
        )

    hard_failures = sum(result["overall"] == "fail" for result in results)
    complete_passes = sum(result["overall"] == "pass" for result in results)
    deterministic_only = sum(result["overall"] == "deterministic_only" for result in results)
    summary = {
        "schema_version": 1,
        "graded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "agent": manifest.get("agent_id", manifest.get("adapter")),
        "adapter": manifest.get("adapter"),
        "agent_version": manifest.get("agent_version"),
        "model": manifest.get("model"),
        "repetitions": manifest.get("repetitions"),
        "semantic_judge": judge_adapter or "not-run",
        "semantic_judge_model": judge_model or "not-run",
        "semantic_judge_repetitions": judge_repetitions if judge_adapter else 0,
        "status": "fail" if hard_failures else ("pass" if complete_passes == len(results) else "partial"),
        "counts": {
            "items": len(results),
            "complete_passes": complete_passes,
            "deterministic_only": deterministic_only,
            "failures": hard_failures,
        },
        "within_agent_stability_supported": bool(
            len(results) > 0
            and manifest.get("repetitions", 0) >= 3
            and complete_passes == len(results)
            and hard_failures == 0
            and judge_repetitions >= 2
        ),
        "results": results,
    }
    write_json(run_dir / "results.json", summary)

    lines = [
        "# Reader's Seat Evaluation Result",
        "",
        f"- Agent: `{summary['agent']}`",
        f"- Model: `{summary['model']}`",
        f"- Repetitions: `{summary['repetitions']}`",
        f"- Status: `{summary['status']}`",
        f"- Complete passes: `{complete_passes}/{len(results)}`",
        f"- Hard failures: `{hard_failures}`",
        f"- Within-agent stability supported: `{str(summary['within_agent_stability_supported']).lower()}`",
        "",
        "A deterministic-only result is partial evidence. One run directory cannot establish cross-agent stability.",
    ]
    (run_dir / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"GRADED: status={summary['status']} complete={complete_passes}/{len(results)} "
        f"failures={hard_failures} within_agent_stability={summary['within_agent_stability_supported']}"
    )
    return summary


def build_matrix(run_dirs: list[str], output_dir: str) -> dict:
    if len(run_dirs) < 2:
        raise SystemExit("error: matrix requires at least two run directories")
    records = []
    for value in run_dirs:
        run_dir = Path(value).expanduser().resolve()
        manifest = load_json(run_dir / "manifest.json")
        results = load_json(run_dir / "results.json")
        records.append({"run_dir": str(run_dir), "manifest": manifest, "results": results})

    agents = {
        record["manifest"].get("agent_id", record["manifest"].get("adapter"))
        for record in records
    }
    case_hashes = {record["manifest"].get("case_file_sha256") for record in records}
    profile_hashes = {record["manifest"].get("module_profile_sha256") for record in records}
    skill_versions = {record["manifest"].get("skill_version") for record in records}
    case_sets = {
        tuple(sorted({item["case_id"] for item in record["manifest"].get("items", [])}))
        for record in records
    }
    failures = []
    if len(agents) < 2:
        failures.append("fewer than two distinct agent IDs")
    if len(case_hashes) != 1 or None in case_hashes:
        failures.append("run directories do not share one frozen case-file hash")
    if len(profile_hashes) != 1 or None in profile_hashes:
        failures.append("run directories do not share one module-profile hash")
    if len(skill_versions) != 1 or None in skill_versions:
        failures.append("run directories do not share one skill version")
    if len(case_sets) != 1:
        failures.append("run directories do not cover the same case IDs")

    all_scores: list[int] = []
    run_summaries = []
    for record in records:
        manifest = record["manifest"]
        results = record["results"]
        agent = manifest.get("agent_id", manifest.get("adapter"))
        if int(manifest.get("repetitions", 0)) < 3:
            failures.append(f"{agent}: fewer than three repetitions")
        if results.get("status") != "pass":
            failures.append(f"{agent}: run status is not pass")
        if results.get("semantic_judge") in {None, "not-run"}:
            failures.append(f"{agent}: semantic judge was not run")
        if int(results.get("semantic_judge_repetitions", 0)) < 2:
            failures.append(f"{agent}: fewer than two automated semantic judge repetitions")
        for item in results.get("results", []):
            semantic = item.get("semantic", {})
            if item.get("overall") != "pass":
                failures.append(
                    f"{agent}: {item.get('case_id')} repetition {item.get('repetition')} did not pass"
                )
            scores = semantic.get("reader_outcome", {})
            if isinstance(scores, dict):
                all_scores.extend(score for score in scores.values() if isinstance(score, int))
        run_summaries.append(
            {
                "agent": agent,
                "adapter": manifest.get("adapter"),
                "agent_version": manifest.get("agent_version"),
                "model": manifest.get("model"),
                "repetitions": manifest.get("repetitions"),
                "status": results.get("status"),
                "semantic_judge": results.get("semantic_judge"),
                "semantic_judge_repetitions": results.get("semantic_judge_repetitions"),
            }
        )

    unique_failures = list(dict.fromkeys(failures))
    matrix = {
        "schema_version": 1,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "agents": sorted(str(agent) for agent in agents),
        "skill_version": next(iter(skill_versions)) if len(skill_versions) == 1 else "mixed",
        "case_file_sha256": next(iter(case_hashes)) if len(case_hashes) == 1 else "mixed",
        "module_profile_sha256": next(iter(profile_hashes)) if len(profile_hashes) == 1 else "mixed",
        "case_ids": list(next(iter(case_sets))) if len(case_sets) == 1 else [],
        "runs": run_summaries,
        "worst_reader_outcome_score": min(all_scores) if all_scores else None,
        "failures": unique_failures,
        "cross_agent_stability_supported": not unique_failures,
    }
    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    write_json(destination / "matrix-results.json", matrix)
    lines = [
        "# Reader's Seat Cross-Agent Matrix",
        "",
        f"- Agents: `{', '.join(matrix['agents'])}`",
        f"- Skill version: `{matrix['skill_version']}`",
        f"- Cases: `{len(matrix['case_ids'])}`",
        f"- Worst reader-outcome score: `{matrix['worst_reader_outcome_score']}`",
        f"- Cross-agent stability supported: `{str(matrix['cross_agent_stability_supported']).lower()}`",
    ]
    if unique_failures:
        lines.extend(["", "## Blocking Failures", "", *[f"- {item}" for item in unique_failures]])
    (destination / "matrix-results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"MATRIX: agents={len(agents)} cases={len(matrix['case_ids'])} "
        f"supported={matrix['cross_agent_stability_supported']} failures={len(unique_failures)}"
    )
    return matrix


def add_prepare_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--agent-id")
    parser.add_argument("--model")
    parser.add_argument("--agent-version")
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--overwrite", action="store_true")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Reader's Seat cross-agent evaluations.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="create frozen prompts and output slots")
    add_prepare_options(prepare)

    execute = subparsers.add_parser("execute", help="execute a prepared command-adapter run")
    execute.add_argument("--run-dir", required=True)

    grade = subparsers.add_parser("grade", help="grade outputs from a prepared run")
    grade.add_argument("--run-dir", required=True)
    grade.add_argument("--judge-adapter")
    grade.add_argument("--judge-model")
    grade.add_argument("--judge-repetitions", type=int, default=1)

    run = subparsers.add_parser("run", help="prepare, execute, and grade a command-adapter run")
    add_prepare_options(run)
    run.add_argument("--judge-adapter")
    run.add_argument("--judge-model")
    run.add_argument("--judge-repetitions", type=int, default=1)

    matrix = subparsers.add_parser("matrix", help="combine comparable runs across agent hosts")
    matrix.add_argument("--run-dir", action="append", required=True)
    matrix.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if hasattr(args, "repetitions") and args.repetitions < 1:
        raise SystemExit("error: --repetitions must be positive")
    if hasattr(args, "judge_repetitions") and args.judge_repetitions < 1:
        raise SystemExit("error: --judge-repetitions must be positive")
    if args.command == "prepare":
        prepare_run(args)
        return 0
    if args.command == "execute":
        execute_run(Path(args.run_dir).expanduser().resolve())
        return 0
    if args.command == "grade":
        summary = grade_run(
            Path(args.run_dir).expanduser().resolve(),
            judge_adapter=args.judge_adapter,
            judge_model=args.judge_model,
            judge_repetitions=args.judge_repetitions,
        )
        return 1 if summary["status"] == "fail" else 0
    if args.command == "matrix":
        matrix = build_matrix(args.run_dir, args.output_dir)
        return 0 if matrix["cross_agent_stability_supported"] else 1
    run_dir = prepare_run(args)
    execute_run(run_dir)
    summary = grade_run(
        run_dir,
        judge_adapter=args.judge_adapter,
        judge_model=args.judge_model,
        judge_repetitions=args.judge_repetitions,
    )
    return 1 if summary["status"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
