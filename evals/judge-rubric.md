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
- `actionability`: when action is intended, ownership, timing, dependency, and
  boundary are usable; otherwise the output does not invent an action.

Do not compare aggregate scores across different cases. Explain failures with
the smallest source-grounded reason.

Length thresholds and exact spacing are review signals, not semantic hard
gates. A concise candidate passes when it preserves the complete reader task;
do not require filler to satisfy a character count.
