# Efficient Execution

Use this on every task. It changes work order, not the quality standard. Source
fidelity, layout, four-way review, authorization, and verification remain.

## Ready Before Building

Do not render or launch reviewers until these are complete:

- source boundary, language, format, reader, and publication target;
- material claims, numbers, uncertainty, and source locations;
- visual evidence limits and blocking versus labelable gaps;
- every source and render file required by reviewers.

Resolve missing evidence or ask before building. Never use repeated review to
discover an already knowable missing source excerpt.

## Batch Independent Artifacts

For multiple independent artifacts, use one shared scope pass and one lane per
artifact. Keep separate contracts, hashes, renders, and reviews. Run safe lanes
concurrently. Shared facts may be read once; never merge hashes or receipts.
Serialize writes to the same target.

## Stabilize Before Independent Review

The normal path uses one complete four-reviewer batch per artifact. Start only
after source and semantic checks pass; the candidate and renders exist; format,
asset, link, and render checks pass; and runtime rules and packets are complete.

Never review partial prose, stale renders, known clipping, or missing excerpts.

## Rerun By Change Impact Before Audit

Before review, classify each change and rerun only affected checks:

| Change | Required rerun |
| --- | --- |
| Source, number, certainty, or action | source, claim, semantic, and mapped visual checks |
| Heading, prose, term, or order | content, reading path, overflow, and responsive render |
| Chart, table, image, color, or spacing | provenance, encoding, accessibility, overflow, and render |
| Format, asset, link, or export | format, asset, link, fallback, and target render |
| Publication placement only | action preflight and live-target verification |

For cross-category changes, use the union. Record `change -> checks -> result`;
do not rerun unrelated retrieval or generation.

## Converge Review Failures

If a full batch fails, wait for all results, merge blockers and major issues,
make one coherent revision, stabilize again, then start the next complete batch
required by the artifact-hash contract. Never fix results one at a time.

The three-round limit is an emergency bound. Additional full batches require a
prior failed batch. Missing evidence, intent, permission, or external state
requires a stop and request, not another review round.

Record readiness, batch lanes, candidate stabilization, change-impact reruns,
merged fixes, reasons for extra batches, and final verification as runtime-rule
evidence. Keep it out of the reader-facing document.
