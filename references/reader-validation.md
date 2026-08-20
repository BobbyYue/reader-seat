# Independent Reader Validation

Use this workflow for every finished artifact. It is an outside-in outcome
check, not another writing template. The main agent writes and revises; four
fresh subagents independently identify reader-facing failures; the runtime
contract decides whether delivery may continue.

## Non-Negotiable Execution Model

Each review round is one parallel batch containing exactly four fresh
subagents:

1. `no-context` checks what a target reader can understand without project
   history or source access;
2. `readability` checks language, terminology, references, reasoning continuity,
   repetition, and natural professional expression;
3. `source-reliability` checks claim traceability, source quality and recency,
   factual fidelity, definitions, certainty, and visual provenance;
4. `structure-visual` checks reading path, headings, layout, tables, charts,
   visual encoding, responsive rendering, and accessibility.

Do not run the four dimensions sequentially in one conversation. Do not let a
reviewer inherit the main agent context, another review result, prior round
discussion, or the main agent's preferred answer. Context isolation is part of
the contract, not a suggestion. If the host cannot launch fresh subagents, the
finished artifact is blocked; a main-agent self-review is not a substitute.

Context isolation reduces anchoring but does not guarantee model independence.
For high-risk work, use a different model for `source-reliability` when the host
supports it, and retain the existing independent semantic judge requirement.

## Prepare One Review Round

Run cheap deterministic format, asset, and rendering checks first. Then prepare
the four immutable review packets:

```bash
python3 scripts/reader_review.py prepare \
  --contract .reader-seat/task-contract.json \
  --artifact path/to/report.html \
  --render-evidence .reader-seat/render-desktop.png \
  --render-evidence .reader-seat/render-mobile.png \
  --round 1 \
  --output-dir .reader-seat/reviews/round-1
```

For rounds 2 and 3, also pass the immediately preceding aggregate with
`--previous-aggregate`. The command rejects an unchanged artifact, a skipped
round, or a fourth round. HTML, Feishu/Lark, Word, and slide artifacts require
at least one real render. The source bundle is selected and hashed during
`runtime_contract.py init`; it must contain the substantive source material and
source metadata used by the artifact, not the main agent's summary of it.

Launch all four packet reviews concurrently. Give each subagent only its packet
and the artifact or evidence paths named by that packet. Require one JSON result
that follows `config/reader-review-result.schema.json`; do not ask the reviewer
to rewrite the document.

## Dimension Standards

### No-Context

The reviewer must state, in `reader_understanding`, the object, main conclusion,
supporting evidence, practical meaning, and required action. It must mark a
major issue when the artifact alone supports two materially different readings,
requires hidden project history, leaves a decision-critical term undefined, or
cannot identify who should do what and when when action is required.

### Readability

Judge whether the named reader can follow the prose accurately without decoding
unnecessary abstraction. Flag ambiguous references, unexplained niche terms,
broken reasoning transitions, repeated conclusions, empty framing, and stiff or
AI-sounding language only when they increase reader effort or error. Sentence
length, term density, and formula scores are risk signals, not automatic
failures. Preserve precise specialist language when the target reader needs it.

### Source Reliability

Inspect the source bundle directly. Every material claim must be traceable and
calibrated to the authority, recency, scope, and limitations of its source.
Distinguish source fact, interpretation, causal claim, advice, assumption, and
unknown. `User-provided` is provenance, not proof of independent accuracy. An
inaccessible or missing material source is `blocked`; weak evidence can pass
only when the artifact explicitly narrows the claim and discloses the limit.

### Structure And Visual

Inspect the artifact and supplied renders. Check the heading-only reading path,
information order, claim-evidence adjacency, dense-block rhythm, four-level
spacing hierarchy, page flow, table and chart legibility, scale and baseline,
color semantics, labels, contrast, responsive behavior, overlap, clipping, and
whether a retained visual actually reduces reader cost. A text-only artifact
may pass when no material visual is needed; it may not skip structural review.

## Result Contract

Every required check must be `pass`, `fail`, or `blocked` with at least 20
characters of artifact-specific evidence. A reviewer result may be `pass` only
when every required check passes and no `blocker` or `major` issue remains.

Use severity consistently:

- `blocker`: likely wrong fact, conclusion, decision, action, source claim, or
  materially misleading visual;
- `major`: likely failure to understand a necessary point without external help;
- `minor`: a real but non-material reading cost or preference.

Each issue must name its location, observed problem, reader consequence, and
the required outcome of a fix. Reviewers diagnose; they do not silently rewrite
the artifact or broaden its evidence.

## Aggregate And Revise

Aggregate the four results only after every parallel subagent finishes:

```bash
python3 scripts/reader_review.py aggregate \
  --contract .reader-seat/task-contract.json \
  --manifest .reader-seat/reviews/round-1/round-manifest.json \
  --result .reader-seat/reviews/round-1/no-context-result.json \
  --result .reader-seat/reviews/round-1/readability-result.json \
  --result .reader-seat/reviews/round-1/source-reliability-result.json \
  --result .reader-seat/reviews/round-1/structure-visual-result.json \
  --output .reader-seat/reviews/round-1/aggregate.json
```

The aggregator validates packet hashes, artifact hash, contract and batch IDs,
four unique agent and session IDs, fresh-context declarations, exact check sets,
and unanimous passage. It returns:

- `pass` when all four dimensions pass;
- `revision-required` after a non-pass in rounds 1 or 2;
- `needs-user-decision` after a non-pass in round 3.

Return all blocker and major issues to the main agent. The main agent fixes the
artifact without inventing evidence, then starts a new round with four new
subagents. Rerun all dimensions because one repair can regress another.

After round 3, do not lower severity, reuse an old review, or start round 4 in
the same contract. Instead run:

```bash
python3 scripts/runtime_contract.py present-draft \
  --contract .reader-seat/task-contract.json \
  --artifact path/to/current-report.html \
  --reader-review-aggregate .reader-seat/reviews/round-3/aggregate.json \
  --receipt .reader-seat/review-incomplete-draft-receipt.json
```

Only a receipt with `status=review-incomplete-draft` permits the current file to
be shown. Put the file first, label it as not fully reviewed, summarize each
unresolved issue as `location -> observed problem -> reader consequence ->
required outcome`, and ask the user which optimization direction to take. This
is a user-decision handoff, not a successful verification or publication.
External publish, overwrite, and replacement remain blocked.

New evidence, a changed scope, or the user's optimization decision starts a new
task contract and a new review cycle. Preserve the old aggregate and draft
receipt as the reason for the restart.

## Delivery Gate

Pass a successful aggregate to `runtime_contract.py verify` with
`--reader-review-aggregate`. For an external publish, overwrite, or replacement,
also pass the artifact and the same aggregate to `check-action`. The action
receipt binds the authorization, exact artifact hash, and reader review hash.
Both commands reopen the round manifest, packets, and four original result
files and recompute whether all dimensions passed. Editing only the aggregate's
status, review records, issues, or stored hashes cannot authorize delivery.
Any content change invalidates both the aggregate and action receipt.

A `review-incomplete-draft` receipt allows only direct presentation of the
current version to the user with its issues and required question. It never
satisfies `verify` or `check-action`, and it never supports `verified`, `passed`,
`ready to publish`, or equivalent wording.

The host or wrapper must treat the four subagent launches and the passing
aggregate as machine-checked delivery preconditions. Prompt text alone cannot
prove the subagents actually ran.
