# Cross-Agent Semantic Judge Rubric

Judge the candidate against the frozen source and request, not against a
preferred wording or template. Do not reward verbosity, visual richness, or
mention of Reader's Seat.

The case's required behaviors are acceptance requirements, not optional style
preferences. If a required behavior is absent, fail the corresponding hard
gate unless it conflicts with the source or explicit request. The forbidden
behaviors are hard failures when present.

## Hard Gates

Each gate is `pass`, `fail`, or `not_applicable`.

- `fact_fidelity`: every material entity, date, number, unit, definition, and
  status agrees with the source; no material fact is invented or omitted.
- `evidence_boundary`: observation, interpretation, causal claim,
  recommendation, and unknown remain calibrated to the available evidence.
- `scope_and_commitment`: scope, exclusions, ownership, timing, uncertainty,
  and commitments do not drift.
- `scenario_completeness`: the candidate contains the minimum information the
  selected scenario requires for the stated reader task.
- `language_and_format`: explicit language and format instructions win;
  otherwise source-dominant language and default-format rules are followed.
- `title_and_visual_integrity`: any title or visual claim is supported and does
  not manufacture suspense, magnitude, identity, precision, or causality.
- `action_boundary`: advice and next actions do not exceed the evidence,
  authority, or information supplied.

Any applicable hard-gate failure makes the overall verdict `fail`.

## Reader Outcome

Score each item from 1 to 5 only after hard gates pass:

- `conclusion_retrieval`: the practical result or central information is easy
  to find.
- `paraphrase_accuracy`: a target reader can restate object, direction,
  magnitude or scope, and main explanation without guessing.
- `evidence_traceability`: material judgments can be matched to the supplied
  evidence or clearly marked absence of evidence.
- `natural_expression`: wording is professional, audience-fit, and free of
  ceremonial, promotional, agent-process, or formulaic filler. A value-bearing
  title, heading, or lead identifies its actual object and supported change or
  result instead of substituting method labels or generic benefit language.
  For direct-expression cases, compare the candidate with an equally accurate
  direct alternative and assess corrective framing across the reading path,
  not just whether each caveat can be defended in isolation.
- `actionability`: when action is intended, ownership, timing, dependency, and
  boundary are usable; otherwise the output does not invent an action.

Do not compare aggregate scores across different cases. Explain failures with
the smallest source-grounded reason.

Length thresholds and exact spacing are review signals, not semantic hard
gates. A concise candidate passes when it preserves the complete reader task;
do not require filler to satisfy a character count.

## Direct Expression Cases

For `xagent-direct-expression-report-repetition`, judge whether the opening and
section leads make the supported progress and remaining work easy to retrieve.
Repeated correction is a defect only when it adds a needless detour or obscures
those answers. A different direct formulation or consolidated boundary may
solve it; do not require a preferred phrase, a uniformly positive tone, or
removal of all repetition. Necessary local conditions must remain accessible.

For `xagent-direct-expression-essential-negatives`, preserve the operative
prohibition, stop condition, negative finding and uncertainty. An already clear
negative sentence may remain unchanged. Treat weakened restrictions or a
negative finding recast as unsupported success as failures of the existing
fidelity, scope or evidence gates, not as gains in natural expression.

Both cases use new synthetic workplace material. Their wording and repetition
counts are not pass/fail cutoffs; no negative word or construction is banned.
Use the existing reader-outcome criteria to explain actual reading burden and
the existing hard gates for meaning loss. Where lifecycle records are in scope,
inspect the before plan, during comparison and independent after judgment;
completed fields alone do not prove a reader improvement. Keep those records
out of requested prose-only outputs. Existing cases, including private fixtures,
retain their original boundaries and are not authorized for publication.
