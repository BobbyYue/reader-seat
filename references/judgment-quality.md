# Question, Answer And Support Quality

Use this small extension of the existing answer plan and source review, not a
new reviewer, round, prose template or per-sentence claim ledger. New Reader's
Seat locks bind `judgment_quality_version:1`; standalone legacy answer locks do
not retroactively claim this check. The source packet supplies the exact schema.

## Before Writing

Each existing planned answer needs `reader_use`: the specific understanding,
judgment or action it enables. Missing fields stop the new lock before drafting.
Use a source-answerable question and supported expected information. Asking
"What differences exist?" and expecting "distinguish the dimensions" may merely
repeat the topic. Ask which objects differ, how and with what reader-relevant
consequence when the source supports that question. Do not force a numeric
result, recommendation or causal claim onto a task that does not need one.

Plan the supported answer first, then let the lead/heading convey that answer
when useful. Navigation headings can remain topics; not every heading must be
a conclusion. A question with unavailable evidence may be correctly answered
by the source's explicit unknown. Keep necessary explanations and transitions.

## During The Same Source Review

For each existing `answers[]` item, add `judgment`:

```json
{
  "question_fit": "pass",
  "answer_fit": "pass",
  "support_fit": "pass",
  "form": "finding",
  "inference": true,
  "candidate_quote": "An exact compact excerpt from this supplied reading surface.",
  "source_quote": "An exact compact excerpt from the locked source.",
  "bridge": "Why this evidence supports this claim for the frozen reader_use.",
  "rationale": "The actual blind answer and visible text satisfy the specific task.",
  "repair": ""
}
```

The example illustrates structure, not a measured result. `question_fit`,
`answer_fit`, `support_fit` each use pass/fail/unassessed. The actual answer form
is finding/fact/explanation/instruction/unknown/method_note/topic_label.
`inference` is explicitly true/false. An inferential claim needs a bridge;
direct facts, instructions and disclosed unknowns may use an empty bridge.
Use the existing `reader_quote` to test what the blind reader actually understood.
Do not replace it with the planned answer or show the plan to the blind reader.

- Question: does it serve the frozen reader task, with a usable expected answer?
- Answer: does the actual surface answer it? "Should analyze separately" is a
  valid instruction for a method request, but not a substitute for an available
  analytical finding. Topic labels do not establish that an explanation was read.
- Support: does the actual evidence justify the claim and inferential connection?
  A configuration count does not itself measure user behavior or revenue loss.
  Preserve scope and an actual unknown instead of inventing a stronger result.

## Results And Repair

Code verifies quote membership, required coverage, schema and declared status
consistency. Missing review, false quotes, missing inferential bridge, or a
non-pass review paired with a passed answer is rejected. Valid non-pass records
remain visible as repair items in `reader_outcomes.judgment_quality`; the existing
aggregate and delivery gate require repair. Re-reading raw inputs recomputes the
result, rejecting hand-edited summaries. No new weighted quality score is added.

A vague question is a planning problem, not proof of poor source writing. Fix
the plan through the existing task-revision path, preserving the failed record;
do not silently change locked questions to make an unchanged candidate pass.
Fix an insufficient answer in the draft; narrow or support an unjustified claim.
Use the existing combined-failure retry policy and three-round stopping limit.

These methods adapt Minto's reader-question approach, Toulmin's evidence/warrant
distinction, assertion-evidence messages and content comprehension testing:
[Minto](https://www.barbaraminto.com/),
[Toulmin](https://owl.purdue.edu/owl/general_writing/academic_writing/historical_perspectives_on_argumentation/toulmin_argument.html),
[assertion-evidence](https://www.craftscicom.org/ae_tutorial.html),
[content testing](https://digital.gov/guides/plain-language/test/).
Semantic usefulness, the truth of an inference and actual host isolation remain
review/host responsibilities. String matches and a filled schema do not prove them.
