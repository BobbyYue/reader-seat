# Changelog

## 0.24.1 - 2026-09-16

- Review empty abstraction, template-driven structure, purposeless repetition, rhetorical overstatement, audience mismatch, and empty visual packaging in the existing draft and review passes.
- Require a located quote, reader impact, disposition, smallest fix, and protected meaning; record completion even when no issue is found.
- Preserve justified terminology, formal notices, useful repetition, and already-clear passages. These are contextual signals, not word bans or AI-authorship detection.
- Reuse the four isolated reviewers and existing three-round limit. Subjective style preference alone cannot block delivery or start another round.
- Add synthetic forward cases and regression coverage for task-bundle inclusion, reviewer instructions, source isolation, and nonblocking style judgments.
- The entrypoint and context budget remain unchanged. Offline tests and bounded component trials do not certify cross-host stability or live publication.

## 0.24.0 — 2026-09-15

### Added

- Source-backed required-reader answers: lock the intended reader, known context, decision, required facts, and their source locations before drafting.
- Extracted reading surfaces for isolated comprehension checks. The reader sees only the actual selected headings, opening, or native blocks, not expected answers or the full source.
- Hash-bound replay and evaluation records that require every necessary answer, classify unresolved questions, and reject stale evidence.
- A scoped native-text patch workflow that checks authorization and unchanged surrounding content before writing, then requires post-write readback and rendered inspection before completion. The validator itself performs no external document writes.
- Unit regressions and an explicitly synthetic cross-agent case for vague headings, omitted comparisons, missing qualifiers, and unauthorized or unverified patches.

### Changed

- Reuse the existing isolated reader and source-review roles to check required answers; do not add a universal review round or force longer titles.
- Separate source-supported but omitted information from genuine source unknowns and optional detail.

### Upgrade notes

- Artifact initialization requires `--reader-answer-plan`.
- Existing review records without the new answer evidence cannot authorize verified delivery. Regenerate the affected review records.
- `prewrite-approved` is not `verified`: native patches require fresh readback and layout evidence after the authorized write.

### Verification scope

Offline unit, contract, and workflow checks validate the implementation. Synthetic fixtures are not real business results or live Feishu evidence. This release does not claim cross-host stability or live document certification.
