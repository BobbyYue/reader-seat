# Evaluation And Regression

Use for explicit scoring or comparison, high-risk documents, or changes to the skill rules.

## Freeze The Test Card

Record before evaluation:

- source and candidate version;
- primary scenario and target reader;
- reader task and channel;
- critical propositions and source evidence;
- expected correct understanding and prohibited inference;
- allowed action boundary;
- time limit and scoring rules.

Do not compare results across different scenarios, readers, tasks, or sources.

## Layer 1: Hard Gates

Evaluate independently before any aggregate score:

- critical proposition fidelity: 100%;
- critical claim evidence coverage: 100% when evidence is required;
- critical number and definition accuracy: 100%;
- major certainty-calibration errors: 0;
- out-of-bound actions: 0;
- required scenario content that blocks the reader task: 0 missing items.

Any failure rejects the version regardless of readability score.

## Layer 2: Reader Outcomes

Use fixed questions and record correctness before speed.

- **Core information retrieval**: readers who find the scenario's main information within the limit / all readers.
- **Paraphrase accuracy**: correctly restated critical propositions / all critical propositions.
- **Evidence matching**: correctly matched claim-evidence pairs / all pairs.
- **Uncertainty recognition**: correctly distinguished fact, interpretation, causality, and unknown / all test items.
- **Action correctness**: readers choosing an evidence-supported action / all readers; mark N/A when no action is intended.
- **Task completion time**: compare only among correct responses.

## Layer 3: Cross-Scenario Output Standards

- reader-perspective noise count: unnecessary generation process, tools, commands, or internal machinery; target 0;
- scope fidelity: correctly retained definitions, distinctions, boundaries, and qualifiers / all critical scope items; target 100%;
- action-information completeness: correct applicable action, owner, timing, dependency, and risk items / all applicable items;
- correction propagation: correctly updated affected content / all affected content after a requirement change; target 100%;
- redundant information rate: passages two reviewers agree can be removed without loss / all passages; compare within scenario, no universal threshold.

## Layer 4: Proxy Risk Signals

Use sentence length, paragraph length, terminology density, passive-voice rate, heading depth, repetition rate, and readability formulas only to prioritize passages for review.

- Process flagged passages through [signal-processing.md](signal-processing.md).
- Report the threshold or formula used, the passages flagged, and the number confirmed, dismissed, and unresolved.
- Never convert a proxy threshold directly into a rewrite rule.
- Do not reward a lower proxy score unless reader outcomes improve and hard gates still pass.

## Scoring Rules

- Keep hard gates separate from reader outcomes.
- Choose three to five reader metrics that match the scenario; do not force every metric into every task.
- Set weights before viewing the result and calibrate them with target-reader data.
- Report individual metrics, sample size, distribution, reviewer agreement, and limitations alongside any aggregate score.
- A better readability formula score without better reader outcomes is not sufficient evidence to adopt a version.

## Regression Workflow

1. Add the failed behavior to `evals/behavior-cases.json` without including a solution that leaks the expected wording.
2. Mark affected and unaffected scenario routes.
3. Update only the responsible module or shared standard.
4. Run `python3 scripts/validate_skill.py`.
5. Add or update a frozen executable case in `evals/cross-agent-cases.json`
   when the behavior can affect more than one agent host.
6. Run `scripts/run_evals.py` so the producer receives the source and request
   but not the expected or forbidden behaviors.
7. Forward-test the affected case and one unaffected route in fresh contexts.
8. Compare facts, route, issue detection, output structure, and reader-task completion.

## Cross-Agent Stability

Use [agent-portability.md](agent-portability.md) and the executable suite when
the claim concerns more than one host or model.

- Freeze the case file, module-profile hash, skill version, source, and prompt.
- Run at least three repetitions for every named host and model.
- Keep deterministic checks separate from semantic judging.
- Run at least two automated semantic judge repetitions and aggregate the worst
  hard-gate result; one calibrated human review may replace automated judge
  repetition when the report identifies the reviewer method.
- Use all-run hard-gate success, not average quality, as the acceptance rule.
- Report the worst run, distribution, host and model versions, judge identity,
  and any unsupported automatic-discovery behavior.
- A deterministic-only pass is partial evidence. It cannot establish semantic
  or cross-agent stability.

Exact wording and non-material layout may vary. Facts, evidence boundaries,
scenario selection, language and format decisions, action boundaries, and
artifact usability must remain stable.
