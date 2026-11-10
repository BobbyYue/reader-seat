# Reader Outcomes In The Existing Review

Ask what this reader can now understand or judge, and which necessary follow-up
the passage resolves. Use the complete message, section or chosen reading surface;
do not demand a new fact, action or conclusion in every sentence. Explanations,
transitions, orientation, source limits and intentional literary effects can help.
This is a contextual test, not a sentence quota or an AI-word blacklist.

## Fixed Questions, Raw Reading, Then Judgment

Reuse the pre-draft answer plan, the no-context reader's `answer_responses` and
the source reviewer's `answer_evaluation`. Do not show expected answers to the
blind reader, invent questions after seeing a draft, or add another reviewer.
Check what the raw reader actually understood, not whether the right labels
appear in the artifact. Unknown information can be a correct answer when the
source is unknown and the text clearly preserves that limit and its consequence.

Every existing `questions` evaluation now includes:

```json
{
  "surface_id": "opening",
  "index": 0,
  "group_id": "schedule-unknown",
  "answer_ids": ["A3"],
  "classification": "source_unknown",
  "rationale": "The source gives no release date and the surface explicitly says it is pending.",
  "disclosure_quote": "The release date has not been set."
}
```

The example is a schema illustration, not an actual reader result. `index` points
to the unchanged raw `remaining_questions` array. Use the same `group_id` for
paraphrases of the same communication gap; distinct necessary questions need
distinct groups. `answer_ids` references the locked questions; it can be empty
for optional detail or a newly discovered gap in the plan itself. A plan gap
still fails source coverage; do not add an easy question to rescue the score.

| Classification | Evidence and treatment |
| --- | --- |
| `missing_required_answer` | A necessary answer is omitted, ambiguous or contradicted; or necessary uncertainty was not disclosed. State the resulting misunderstanding and source-supported fix. Existing revision gate fails. |
| `source_unknown` | Related planned answers must be source-unknown, and `disclosure_quote` must occur on the actual reading surface. Preserve the uncertainty; do not invent a result to eliminate the question. |
| `detail` | Optional curiosity does not obstruct the frozen task. Explain why; an unresolved related required answer cannot be hidden here. |

No remaining questions is a valid empty array, not proof of understanding.
Correct answers, source fidelity and depth are still checked independently.
Code checks indexes, groups, answer IDs, quotes and counts; semantic grouping
and whether a disclosure really resolves a misunderstanding remain review judgments.
An identified missing answer must have a corresponding failed answer judgment;
it cannot be counted against a set of answers all judged correct or still pending.

## Recomputed Results

`reader_review.py aggregate` writes `reader_outcomes` into the existing aggregate;
standalone `reader_answers.py verify` writes it into the existing receipt.
Delivery reopens raw records and recomputes it, rejecting edited counts. Failed
drafts retain measurable outcomes; malformed or missing evidence is unmeasured,
never zero. Legacy locks are explicitly not measured rather than retrofitted.

- **Required-question correctness:** questions correctly understood on every
  required surface / all locked questions. Failures and unassessed questions stay
  in the denominator; one question appearing on two surfaces is not two questions.
  Unknown outcomes are reported separately. Counts aggregate AI judgments, not
  objective semantic truth or human comprehension.
- **Avoidable follow-ups:** unique groups classified `missing_required_answer`.
  Also retain raw question count, disclosed unknown groups and optional groups.
  Do not sum this count and required-answer failures as independent score penalties.
- **Version gain:** ordinary runs say `comparison.status=not_measured`. Only a
  requested comparison may calculate a correctness-rate difference and an avoidable
  follow-up count difference. Keep the original measures and task-level regressions.

## Optional Version Comparison

```bash
python3 scripts/reader_outcomes.py compare \
  --baseline-receipt old/answer-receipt.json \
  --candidate-receipt new/answer-receipt.json \
  --output comparison.json
```

Use receipts from the same reader background, goal, source snapshot, questions,
judging criteria, depth and reading scope. Each version needs its own fresh blind
reader; an old reader that has seen another version cannot establish a first-read
comparison. The command reopens both receipts and rejects changed evidence,
incompatible bases, pending answers and reused reader contexts. A failed baseline
is allowed when its raw records are valid; this does not authorize its delivery.

A positive rate difference is a descriptive same-task AI comparison, not proof
of human learning, measured reading-time savings or a stable population advantage.
Report any newly failed question and source-fidelity state even if the total rises.
Testing actual before/after human understanding requires a separate protocol and
observations. Do not run extra reviewers just to make an ordinary report contain
a comparison number, and do not add these internal checks to the finished article.
