# Required Answers And Limited Reading

Use this contract before drafting or rewriting substantive reader-facing content.
It tests whether the chosen reading surface answers the reader's actual task,
not whether a sentence contains a universal set of slots.

## Plan Before Prose

Record the actual reader, their known context, the judgment they need to make,
and the surface they are expected to read. A job title alone is insufficient.
Choose the smallest surface that supports that task: headings, an opening,
explicit native blocks (including essential adjacent qualifiers), or a complete
document only when the task genuinely requires full reading.

From the source, write the minimum questions that must be answered on that
surface. Record the supported answer and source location, or an explicit
source-unknown. Check the plan against all decision-critical source findings;
do not quietly omit a difficult finding to make a draft pass.

Examples of task-dependent required information:
- An analytical finding may need the actual feature, compared groups, direction,
  outcome and a material scope condition. Put decisive magnitude nearby when it
  changes the judgment; not every title needs a number.
- A proposal may need the proposed change, expected benefit and unresolved choice.
- A status update may need what changed and whether the reader must act.
Do not force a contrast, action, mechanism, owner, number or recommendation the
source does not contain. Known context must not smuggle in the conclusion being
tested.

A heading such as “广告构成有助于识别长期价值” leaves “哪些构成、如何区分、
价值差多少” unanswered when the source already answers those questions.
Replace generic usefulness with the supported relationship; don't merely list
feature names or move the decisive comparison into distant body text.
A short heading plus a visibly adjacent qualifier can be a complete unit.
Keep prose natural; stop when the intended judgment is easy and accurate.

## Portable Plan And Commands

Save a plan with this structure (replace all example content with actual facts):

```json
{
  "version": "reader-answers-1",
  "reader": {
    "profile": "PM and RD leaders deciding whether a pilot merits further testing",
    "known_context": "Know common product metrics, not this pilot",
    "decision": "Judge the observed benefit and the remaining decision"
  },
  "surfaces": [{"id": "opening", "mode": "between", "start": "## Summary", "end": "## Details"}],
  "answers": [{
    "id": "A1",
    "question": "What changed in the pilot?",
    "expected_information": "Use the exact supported pilot finding here",
    "source_location": "Source section and evidence reference",
    "source_status": "supported",
    "required_on": ["opening"]
  }]
}
```

Surface modes: `headings` extracts Markdown or HTML headings; `blocks` selects
exact HTML/XML `block_ids`; `between` requires unique ordered anchors;
`opening` reads only `brief.json.opening.lines`; `full` requires a task-specific
reason. For native formats use an actual UTF-8 content snapshot and bind it to
the native candidate; never author a better “test version.”
Reader's Seat runtime init takes `--reader-answer-plan PLAN` and locks it against
the source; the no-context reviewer uses one selected primary surface.
3080 plans also map each answer to `claim_ids` and cover every non-appendix P0.

For standalone 3080 or a scoped native text patch:

```bash
python3 scripts/reader_answers.py lock --plan PLAN --source SOURCE --output LOCK
python3 scripts/reader_answers.py prepare --lock LOCK --artifact CANDIDATE --output-dir SURFACES
python3 scripts/reader_answers.py verify --manifest SURFACES/surface-manifest.json --responses RESPONSES --evaluation EVALUATION --output RECEIPT
```

Lock before drafting. If the reader task or source changes, create a new plan
and rerun affected checks. Changing a candidate invalidates its extracted
surface and comprehension receipt.

## Blind Response, Then Source Evaluation

Give a fresh reader only the generated blind packet and extracted surface.
Never give the source, full artifact, plan, answer checklist, expected answer,
author explanation, or another review. Do not coach a reader who asks a question.
Separate surfaces need separate fresh reading contexts; a full-reading response
cannot rescue a failed heading-only response.

The raw response is an array of objects with `surface_id`, `surface_sha256`,
`reader_id`, `findings` (independent own-word statements) and
`remaining_questions` (array). A source evaluator, not the blind reader, then
produces:

```json
{
  "manifest_sha256": "object_digest(manifest)",
  "response_sha256": "object_digest(raw_responses)",
  "reviewer_id": "a different reviewer identity",
  "plan_source_coverage": "pass",
  "source_coverage_evidence": "Why all decision-critical source information is represented",
  "source_fidelity": "pass",
  "answers": [{
    "answer_id": "A1", "surface_id": "opening", "status": "pass",
    "reader_quote": "An exact excerpt of the raw finding",
    "rationale": "How that finding preserves the source relationship and necessary conditions"
  }],
  "questions": [{
    "surface_id": "opening", "index": 0,
    "classification": "detail",
    "rationale": "Why this question does not block the intended judgment"
  }]
}
```

Use `reader_answers.object_digest` for object hashes; file hashes use SHA-256 of
bytes. Match every required answer exactly once and classify every remaining
question: `missing_required_answer` blocks; `source_unknown` preserves an actual
source gap; `detail` is optional for this task. Do not relabel a known decisive
omission as detail. False causality fails source fidelity even when all tokens
and numbers are present. No questions are needed when the reader has none.

Reader's Seat reuses its no-context and source reviewers: store raw responses in
the no-context result's `answer_responses`; after that result is frozen, the
source reviewer adds `answer_evaluation`. Only this raw replay crosses the
review boundary; other opinions do not. Launch the four original reviewers in
parallel, then finish this dependent source check, not a fifth full audit.
Aggregate, action preflight and final verify reopen the underlying evidence.

3080 reuses Primary's opening-only replay for this contract rather than adding
another full-document reader. The existing visual-only replay checks the image
separately. `validate_review_readiness.py --reader-answer-receipt RECEIPT` binds
the opening result; packet building and final artifact verification reopen it.

## What Automation Does And Does Not Prove

The scripts enforce extraction, isolation payloads, complete mappings, raw-quote
bindings and stale-evidence rejection. They cannot prove a semantic judgment is
correct or a claimed fresh reader really was isolated. Keep genuine invocation
and raw response evidence; inspect semantic judgments independently. Structural
unit fixtures are not live reader-test evidence.
