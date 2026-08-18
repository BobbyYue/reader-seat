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

An adapter has eight responsibilities:

1. make `SKILL.md` discoverable or load it explicitly;
2. create the runtime source snapshot and run `scripts/runtime_contract.py init`
   before generation;
3. resolve the required modules with `scripts/resolve_modules.py` or reproduce
   its result exactly from `config/module-profiles.json`, including the active
   scenario contract extracted from the canonical scenario file;
4. provide the complete user request and source material without summarizing
   them first;
5. preserve authorization boundaries and available-tool constraints;
6. run `runtime_contract.py check-action` with the exact locked action and target
   immediately before any publish, overwrite, or cross-application replacement;
7. run `runtime_contract.py verify` against the actual candidate or artifact and
   reject delivery unless the resulting receipt has `status=pass`;
8. return the verified artifact or response separately from logs, runtime files,
   and internal reasoning.

An adapter must not translate the request, compress the source, add a preferred
template, silently enable an external action, replace unavailable modules with
its own writing policy, or treat a generated file as a successful delivery
without a passing runtime receipt. If the host cannot enforce the runtime
preconditions, label the adapter `advisory-only`; it cannot support a stability
claim.

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
`--output-format word` leaves HTML-only mechanics unloaded. `--visual
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

For a headless agent, use the bundled Codex adapter or either vendor-neutral
command adapter in `config/agent-adapters.json`. `command-stdin` accepts a JSON
argv array through `READER_SEAT_AGENT_COMMAND_JSON`; `command-files` accepts one
through `READER_SEAT_AGENT_FILE_COMMAND_JSON` and substitutes `{prompt_file}`
and `{output_file}`. For a GUI-only or unsupported host, use the manual adapter:
prepare prompt bundles, run them in the host without edits, save each final
answer at the requested path, then resume grading.

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

For production delivery, the host integration must make the runtime receipt a
machine-checked return precondition rather than another prompt instruction. A
host that can return an answer after a missing or failed receipt is not a
conforming enforcement adapter, even when its prompt contains every Reader's
Seat rule.
