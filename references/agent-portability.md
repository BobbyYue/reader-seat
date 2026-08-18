# Agent Portability And Stability

Use this module only when installing, adapting, or regression-testing Reader's
Seat in another agent host. It does not change the writing rules.

## One Canonical Source

Treat this skill directory as the only maintained source of behavior. An agent
adapter may map discovery metadata, invocation syntax, prompt transport, result
transport, and tool permissions, but it must not copy or rewrite the content
rules. Generate host-specific packages from the canonical directory when a host
requires a different layout.

Cross-agent stability means stable decisions and safety boundaries, not
identical wording. The required invariants are:

- facts, numbers, definitions, scope, ownership, commitments, and uncertainty
  do not drift;
- the same primary scenario and reader task are selected from the same input;
- unsupported inference and out-of-bound action remain rejected;
- explicit language and format requests are honored;
- retained titles and visuals make claims within the same evidence boundary;
- the finished artifact remains usable in its selected format.

Natural wording, paragraph rhythm, and non-material layout details may vary.

## Adapter Contract

An adapter has five responsibilities:

1. make `SKILL.md` discoverable or load it explicitly;
2. resolve the required modules with `scripts/resolve_modules.py` or reproduce
   its result exactly from `config/module-profiles.json`, including the active
   scenario contract extracted from the canonical scenario file;
3. provide the complete user request and source material without summarizing
   them first;
4. preserve authorization boundaries and available-tool constraints;
5. return the final artifact or response separately from logs and internal
   reasoning.

An adapter must not translate the request, compress the source, add a preferred
template, silently enable publishing, or replace unavailable modules with its
own writing policy.

For high-risk or regression work, use explicit invocation. Automatic discovery
is a host feature and must be tested separately; it is not evidence that the
loaded skill executed correctly.

## Deterministic Module Resolution

Resolve only the minimum complete set. For example:

```bash
python3 scripts/resolve_modules.py \
  --scenario analysis \
  --operation rewrite \
  --artifact \
  --output-format html \
  --title \
  --visual retained \
  --risk high \
  --emit json
```

`--artifact` always loads the short format and visual decision gates.
`--output-format html` additionally loads the complete HTML implementation;
`--output-format native` leaves HTML-only mechanics unloaded. `--visual
retained` loads the full visual implementation rules; `--visual asset` also
loads provenance rules. This changes context cost, not capability: every full
rule remains available before the corresponding output is built.

## Evaluation Protocol

Use `scripts/run_evals.py` with the frozen cases in
`evals/cross-agent-cases.json`.

- Run the same case, source, resolved modules, and output instruction in every
  host.
- Use at least three repetitions per agent and model when measuring stability.
- Evaluate hard gates before reader-quality scores.
- Reject a run for any critical fact, evidence-boundary, scope, format,
  language, or action-boundary failure.
- Report the worst run as well as the distribution. Do not let an average hide
  one severe failure.
- Keep deterministic checks and semantic judging separate.
- Use a different model or a human reviewer for the semantic judge when
  practical; disclose when producer and judge are the same.
- For an automated stability claim, run at least two semantic judge repetitions
  and aggregate the worst hard-gate result and lowest reader-outcome score.
- Combine completed run directories with `scripts/run_evals.py matrix`. A
  single host can establish only within-agent repeatability; a cross-agent
  claim requires at least two distinct, explicitly named agent IDs.

For a headless agent, configure a command adapter in
`config/agent-adapters.json`. For a GUI-only or unsupported host, use the manual
adapter: prepare prompt bundles, run them in the host without edits, save each
final answer at the requested path, then resume grading.

### Command Adapters

The built-in command adapters are vendor-neutral and execute an argv array
directly without a shell.

Use `command-stdin` when the agent command reads the frozen prompt from standard
input and returns only its final answer on standard output. Provide the command
as a JSON string array through `READER_SEAT_AGENT_COMMAND_JSON`:

```bash
export READER_SEAT_AGENT_COMMAND_JSON='["your-agent", "run", "--model", "{model}", "-"]'
python3 scripts/run_evals.py run \
  --adapter command-stdin \
  --agent-id your-agent \
  --model your-model \
  --case xagent-analysis-causality \
  --output-dir /tmp/reader-seat-eval
```

Use `command-files` when the agent command reads and writes files. Provide its
argv array through `READER_SEAT_AGENT_FILE_COMMAND_JSON`; the placeholders
`{prompt_file}`, `{output_file}`, `{model}`, `{skill_root}`, and
`{judge_schema}` are available:

```bash
export READER_SEAT_AGENT_FILE_COMMAND_JSON='["your-agent", "run", "--input", "{prompt_file}", "--output", "{output_file}"]'
python3 scripts/run_evals.py run \
  --adapter command-files \
  --agent-id your-agent \
  --case xagent-analysis-causality \
  --output-dir /tmp/reader-seat-eval
```

Replace the example argv array with the real command documented by the target
agent. Do not insert a shell wrapper or bypass its permission model.

## Acceptance

A cross-agent claim is supported only when:

1. at least two explicitly named agent hosts run the same frozen cases;
2. all repetitions pass every hard gate;
3. no forbidden behavior appears;
4. scenario, language, format, and evidence-boundary decisions agree;
5. output artifacts pass their native structural and rendering checks;
6. reader-outcome review is calibrated against the same rubric and target
   audience;
7. the report names every tested host, model, version, case, repetition, and
   unresolved limitation.

Passing static skill validation or one successful generation is not sufficient
evidence of cross-agent stability.
