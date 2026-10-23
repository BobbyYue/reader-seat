# Writing Lifecycle

Finished delivery requires both complete writing-stage records and the existing
native semantic review, including four isolated reader reviews. Neither replaces
the other. Keep one run directory, containing `lifecycle.json`, for the same task
across revisions. Do not restart a run to reset its cumulative three-round limit.
Use [writing-quality-records.md](writing-quality-records.md) for the complete
record protocol, task packet, metric assessments and raw layout geometry.

Reuse the original task and required-answer plan; do not maintain a second
source, reader or answer checklist. After normal runtime initialization:

1. Before writing, run `runtime_contract.py init-lifecycle --contract CONTRACT --lifecycle-run RUN`.
   It derives a functional plan and task packet from the original locked task,
   required-answer plan, reader, language, actual format and source references.
   Reading units default to the native reading surfaces. Keep the original plan
   authoritative; the generated `RUN.plan.json` is not another hand-maintained list.
   Include `expression_plan` in that original prewrite plan: lead answers,
   opening move and reason, and essential-boundary placements follow
   [required-reader-answers.md](required-reader-answers.md).
2. During writing, `unit RUN --text UNIT.txt --record UNIT.json`. Register every
   planned unit's actual text, quoted observation and reason; recheck changed units.
   Before registration, run `python3 scripts/direct_expression.py prepare --text PATH --stage during --output JSON`
   against the actual complete unit. Complete the generated `expression_review`
   in the existing complete-unit record. Compare original wording with an equally
   accurate direct alternative and assess repetition across the reading path;
   keeping a caveat needs more than showing that deletion loses information.
   The script owns the exact record fields and bindings; use its generated
   template rather than copying a separate schema. See
   [direct-expression.md](direct-expression.md) for judgment and examples.
3. For the stabilized whole candidate, `measure RUN --text TEXT --output METRICS.json`,
   then `candidate RUN --artifact ARTIFACT --text TEXT --report METRICS.json --record ASSESSMENT.json`.
   Fill the generated `METRICS.json.assessment.json` template: preserve its
   `text_sha256` and `report_sha256`; never transfer an assessment to new prose.
   Assess every applicable metric in context, dispose of every located candidate,
   preserve meaningful qualifiers and source boundaries, and record actual target
   layout evidence where applicable. A signal is a review prompt, not an automatic
   quality threshold. Unmeasured geometry or comprehension is not a measured result.
4. `review-start RUN --artifact ARTIFACT --stage after` registers the stable version.
   Run the existing four fresh, isolated reviewers concurrently. After all return,
   aggregate with `reader_review.py` and register that exact original aggregate:
   `review-finish RUN --result AGGREGATE.json --verdict pass` (or `fail`).
   The readability reviewer independently completes
   `reader_value.checks.expression.direct_expression` with `stage: after`, using
   the current generated review template. This checks the stable whole candidate,
   including accumulated corrective framing, without inheriting author keep
   rationales. It adds no reviewer or review round.
   During-writing review batches use `--stage during`; both stages count toward
   the same three-round limit. Do not fill a synthetic pass to replace a review.

Expression match counts are prompts for contextual review, never pass/fail
thresholds. Preserve necessary prohibitions, refusals, negative findings and
natural voice; favor affirmative phrasing only when equally accurate. Preparing
an author expression record is not an independent review batch and consumes no
additional round.

The final and action guards reopen these native references, require the same
task/decisions, reader, projected answers, actual format and captured source,
and retain the source-grounded (not fictional) boundary. The runtime contract may
gain its normal later semantic-review binding without changing this prewrite
basis. Source/requirement changes belong in the original task records; do not
retarget an old run by editing its hashes. These are identity/field checks, not
automatic proof that the sources support the prose or that the reader understands it.

Record paths are private evidence, not visible document content. Measurements,
candidate handling and layout observations must describe this exact version.
Changing a source, record, implementation, candidate or review invalidates its
binding; do not repair a stored hash to reuse acceptance.

## Delivery And Actions

`deliver.py verify` and `deliver.py present-draft` require `--lifecycle-run RUN`
alongside their existing arguments. The wrapper verifies the lifecycle before
returning any document bytes, reopens the original native review evidence, and
watches the registered records for changes during verification. Its lifecycle
`review_evidence` contains the same `--reader-review-aggregate` path registered
by `review-finish`; a copied result or a different aggregate cannot substitute.

`runtime_contract.py check-action` also requires the run. The preflight receipt
binds the lifecycle evidence as well as action, authorization, exact artifact and
original reviews. Later external verification rechecks this same binding. Native
text-patch `prepare` requires the run, runtime contract and four-review aggregate;
native `verify` reopens that gate and still requires exact live readback and render
inspection. Its original answer receipt must use the same required-answer plan
and source as the native task/four-review route. A local payload never authorizes publication.

For native text patches, JSON is a lossless mutation snapshot, not a supported
generic text artifact. Register the exact canonical XML already checked by
`_validate_answer_receipt` as the lifecycle artifact. The native gate validates
that XML against candidate JSON and reopens the original four-review aggregate
bound to the JSON. This explicit mapping preserves block/content checks; it
does not silently accept arbitrary unknown artifact suffixes.

Without a lifecycle, low-level local `runtime_contract.py verify` may return
`status=pass` for its existing semantic/format checks, but explicitly returns
`verification_scope=semantic-and-format-only` and
`verified_finished_artifact=false`. Such a receipt cannot release a checked
payload. Native Python `prepare` without the gate returns
`patch-preconditions-pass`, not action approval; its local `verify` returns
`local-checks-pass`, `complete=false`. Use the checked CLI for action/completion.

## Authorized Preview Writes

To create the actual page needed for layout inspection, use the existing locked
authorization, action and target with `runtime_contract.py check-action --preview
--lifecycle-run RUN` (plus its normal contract, review, artifact and receipt paths).
This writing-stage preflight requires the current source/task binding, prewrite,
complete-unit checkpoints and registered candidate. It permits an unmeasured
layout and no independent review yet; it does not consume a review round.
The pending semantic-review path may still contain pending items. No additional
approval is needed for the same already-authorized output/scope. It does not
authorize a new target, recipient, sharing policy or broader replacement.

The receipt is `status=preview-only`, `action_phase=preview`, `publishable=false`
and `verified_finished_artifact=false`. Materialize only a pending review page,
then capture its actual layout, update the candidate records and complete the
original review process. Final action/delivery still requires the full guard and
a fresh final action receipt. A preview receipt is rejected as final evidence,
even if all reviews pass later. Local Word/file drafting with no external action
does not require publication authorization merely to render the draft.

## Draft-Only Exit

The original `present-draft` still requires a valid native third-round non-pass,
actionable current-version issues and three completed lifecycle rounds. The
additional `deliver.py lifecycle-draft` uses cumulative lifecycle rounds, allowing
the current native batch to have a lower round number after during-writing
reviews. It still revalidates all four original current-version reviews and
requires a valid non-pass aggregate with unresolved reader impact.
Earlier rounds may have passed: after three completed rounds, the current last
round must still fail with issues. An earlier pass neither hides a regression
nor prevents showing the current version as an explicitly incomplete draft.

Both return only `delivery_state=draft`, require an incomplete-draft notice and
a user decision question, and prohibit publication, overwrite, replacement and
verified-completion claims. One or two rounds, an unfinished batch, a stale version,
or an unrelated review never qualifies. Do not loosen review severity or start
a fourth round under the same task.

These controls verify registered stages, versions and evidence, not independent
identity, honest capture provenance, actual writing chronology, reader improvement
or host-wide enforcement. Synthetic test fixtures prove only the wiring.
Maintainers: see [lifecycle-adapter-notes.md](lifecycle-adapter-notes.md) for the
integration boundaries and changed-file inventory.
