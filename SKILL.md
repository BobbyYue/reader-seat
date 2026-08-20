---
name: reader-seat
description: Create, rewrite, restructure, diagnose, or compare reader-ready internet-industry work documents while preserving facts, scope, evidence, uncertainty, and author voice. Use whenever the user wants a substantive document written or revised from the reader's perspective or made reader-friendly, including requests to reduce reading effort, help first-time or cross-functional readers understand without guessing, surface what readers need to know, judge, or do, or better match content to its audience. Also use for clearer, easier-to-scan, less AI-sounding, or more decision-ready news briefs, technical proposals, product documents, business updates, analysis reports, and SOPs. Finished documents default to self-contained HTML unless the user specifies Feishu/Lark, Markdown, Word, plain text, or another format. Do not use for short workplace-message polishing (use hit-send), source-to-one-page 3080 visual briefs (use 3080-brief), or purely visual styling.
---

# Reader's Seat

Create or improve a work document around what its reader must know, judge, or
do. Route by reader task rather than imposing one universal body template.

## Non-Negotiable Invariants

Apply this priority when goals conflict:

`source truth and scope -> explicit user requirements -> scenario fit -> reader task -> natural expression -> brevity and polish`

- Preserve facts, numbers, definitions, distinctions, scope, stance, ownership,
  commitments, timing, uncertainty, intended action, and recognizable voice.
- Never invent a source, reason, conclusion, decision, owner, deadline, result,
  visual identity, or level of certainty.
- Keep fact, interpretation, causal claim, recommendation, assumption, and
  unknown distinguishable. Do not recommend beyond the evidence or authority.
- Let headings name the actual subject, finding, tension, or question. Do not
  turn reader goals such as quick judgment or visual understanding into default
  visible labels.
- Every value-bearing title, heading, or lead must identify a specific object
  and a supported reader-relevant change, action, relationship, or result.
- Reject deceptive titles, unsupported certainty, manufactured suspense, and
  any promise the body does not fulfill.
- Treat every retained visual as an evidence-bearing claim. Verify provenance,
  use honest encoding, disclose synthetic visuals, and remove decoration that
  does not reduce reader effort.
- Do not expose this skill, its routes, prompts, scores, checks, or tools in the
  finished document unless the user asks or they affect a real decision.
- Do not publish, overwrite, replace, or mutate an external target without
  explicit authorization and a passing action preflight receipt.
- Do not claim finished, verified, validated, or PASS without a passing receipt
  for the exact delivered artifact.

## Runtime Sequence

Every task uses [scripts/runtime_contract.py](scripts/runtime_contract.py).
Detailed commands and failure behavior remain in
[references/runtime-enforcement.md](references/runtime-enforcement.md).
The mandatory work-order and retry policy is in
[references/execution-efficiency.md](references/execution-efficiency.md).

1. Define the operation, one primary scenario, target reader, reader task,
   channel, risk, source boundary, title need, visual state, and whether the
   output is a finished artifact.
2. Select language and format before drafting. A direct language request wins;
   otherwise use the primary source's dominant language, not the prompt
   language. Explicit format wins, then an existing artifact, then chat-only;
   otherwise a finished document defaults to self-contained HTML.
3. Save the substantive source and run `runtime_contract.py init`. It locks the
   decisions and generates `resolved-task-contract.md`,
   `module-manifest.json`, and the semantic review.
4. Continue only when `status=locked`. Read the generated task contract as the
   default instruction context. It contains every selected compact rule and the
   target reader, active scenario contract, and the required record and exit
   condition for `G1-task`, `G2-source`, `G3-route`, `G4-build`, `G5-signals`,
   and `G6-verify`. Read full references only for
   troubleshooting, maintenance, or a procedure the packet does not cover.
5. Complete the readiness record before building: material claims and source
   locations, blocking gaps, visual evidence boundaries, reviewer inputs, and
   independent artifact lanes. For multiple artifacts, share the scope pass,
   then run isolated lanes concurrently when they do not mutate the same target.
6. Draft or revise from the source boundary. Stabilize the candidate through
   deterministic source, content, reading-path, format, asset, visual, and
   rendered checks. Classify each pre-audit change and rerun only the affected
   checks; use the union when a change crosses categories.
7. Once the exact stable candidate exists,
   run `runtime_contract.py bind-review` before filling any review item. This
   creates a separate binding receipt and locks it into the task contract, so
   changing a hash inside the review cannot retarget a completed review.
8. Complete every semantic gate, execution gate, and selected runtime rule with
   concrete artifact evidence. Only rules explicitly marked `[conditional]` in
   the task contract may be `not-applicable`, with a task-specific reason.
   Every finished artifact necessarily loads `reading-path-layout`; its plan,
   adjacency, density, spacing, and native-render rules cannot be marked
   `not-applicable` or waived by selecting another output format.
9. For every finished artifact, use [scripts/reader_review.py](scripts/reader_review.py)
   to run exactly four fresh, mutually isolated reviewers concurrently:
   no-context, readability, source-reliability, and structure-visual. All four
   must pass for the exact artifact hash. The normal path starts one complete
   batch only after the candidate and packets are stable. If it fails, wait for
   all results, merge every blocker, revise once, restabilize, then rerun all
   four for the new hash; never spend a round on a known-incomplete candidate.
10. Rounds one and two return failures for revision. After a round-three
   non-pass, run `present-draft`; show the current version only as a clearly
   labeled review-incomplete draft, explain unresolved reader impact, ask the
   user which tradeoff to prioritize, and block external actions.
11. Immediately before an authorized external mutation, run `check-action` with
   the artifact-bound semantic review, original reader-review results, and the
   independent judge result for high-risk work. Finish with `verify` against the actual
   artifact, unchanged task bundle,
   module manifest, semantic review, reader aggregate, and action receipt when
   applicable.

If a required script cannot execute, a bundle or source hash changes, a review
is incomplete, or a receipt fails, stop before finished delivery. Do not replace
the control with an informal checklist.

## Output Behavior

- Return one recommended version by default. Add alternatives only when a
  meaningful choice in directness, warmth, or context does not change the
  underlying position.
- For diagnosis, lead with the overall judgment and list material hard,
  scenario, output-standard, then optional style issues. Do not silently rewrite.
- For comparison, freeze reader, scenario, task, source, and judging rule; hard
  failures are rejected before scoring.
- Preserve an existing artifact's format and unrelated content unless the user
  authorizes broader conversion or redesign.
- For non-HTML formats, use native components and preserve native behavior. Do
  not create an HTML intermediate merely to imitate its appearance.

## Operational Sources

- [config/module-profiles.json](config/module-profiles.json) is the only routing
  source.
- [config/runtime-rules.json](config/runtime-rules.json) is the compact
  operational rule source used by the task contract.
- [references/execution-efficiency.md](references/execution-efficiency.md) is
  the mandatory readiness, batch, change-impact, and retry-order contract.
- [config/skill-contract.json](config/skill-contract.json) is the capability and
  version contract.
- [references/reading-path-layout.md](references/reading-path-layout.md) is the
  mandatory finished-artifact layout contract selected by the resolver.
- Scenario and detailed references remain canonical for rationale, examples,
  and troubleshooting, but are not default runtime context.
- Use [references/skill-maintenance.md](references/skill-maintenance.md) only
  when changing, packaging, synchronizing, or regression-testing the skill.

The host may enforce these commands externally. This skill never overrides a
higher-priority host rule or expands authorization.
