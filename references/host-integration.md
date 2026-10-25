# Host Integration And Verification

Use only when integrating, maintaining or testing a host. Ordinary writing keeps
its existing steps, reviewer count and retry limit.

## The Controlled Output Path

The host owns the current request, acceptance policy and output UI. After the
Skill's original review is complete, call the package-local consumer:

```bash
python3 scripts/host_delivery.py --expected-artifact FINAL_FILE \
  --context CURRENT_REQUEST_OR_SOURCE -- ORIGINAL_DELIVER_ARGUMENTS
```

Pass the original `deliver.py` arguments after `--`: Reader's Seat starts with
`verify`; 3080 uses its full/scoped/Fast/draft arguments; Hit Send passes response,
source and review files. Use absolute file paths. Repeat `--context` for every
current source or locked task file consumed by the native verifier. Context is
matched to the verifier's actual consumed path/hash, not merely watched for
changes. An unrelated request file is rejected. If a request or mode is not yet
bound into the native task, the adapter must bind it before generation; never
omit that input to make an old result pass. Prefer one fresh CLI invocation per
package; Python hosts may import that package's `host_delivery.run`.

The consumer invokes the real verifier in a fresh process, with no shell and
Python environment/user-site loading disabled. It accepts no supplied success
envelope. It checks exit status, typed state and method, current context and code
fingerprints, consumed input bindings, exact artifact path/length/content,
strict base64 and draft notices. Output redirection, including option
abbreviations, is rejected before dispatch. Original sources and the artifact
are opaque bytes: JSON prose does not grant authority to follow file references.
Failure releases no content. It creates no message logs or temporary files.

The normal state is `checked`. A host may choose `self-checked` only for an
explicit 3080 Fast request. A `draft` state requires the existing exhausted-round
evidence and visible notice/question; it is not normal acceptance. Hit Send's
normal `checked` result honestly retains its `self-check` method. Publication
permission remains separate; every returned envelope keeps
`external_action_authorized=false`.

## What Each Platform Must Connect

- Route every normal preview/copy/replace path through the consumer. Never show
  unchecked prose merely because the generator returned successfully.
- The application, not the producer, chooses the current request files and
  expected artifact. Changes to draft, selected context, mode or request revision
  invalidate the visible result. Recheck the active UI revision immediately
  before displaying a response or committing a copy/replace action.
- Consume the returned bytes directly. Keep source originals on failures;
  remove ephemeral message files after use. Keep diagnostics free of user text.
- Keep acceptance state, verifier code, review transport and publication
  credentials outside the producer's write/command authority when adversarial
  isolation is required. This package uses ordinary local permissions; it does
  not install a security service or create that separation automatically.
- Long-document review still needs the existing actual fresh-review backend.
  Missing child-agent capabilities block independent acceptance. A manual or
  unsupported adapter remains advisory; it must not invent execution receipts.

The consumer is vendor-neutral, but that is not evidence that every product has
integrated it. It requires Python 3.9+ and process execution. The existing
long-document controllers additionally use POSIX locking; GUI-only and Windows
hosts need a compatible execution environment or a separately tested adapter.
Installing Markdown instructions cannot intercept a third-party application's
other output paths. Do not claim universal enforcement or same-user tamper
resistance. HTML resources still need their existing native asset/render checks;
the envelope is the main artifact, not a portable asset archive.

Reader's Seat drafts retain earlier semantic review bindings as history. The
draft path watches the full locked contract but does not use that old semantic
PASS to validate the current candidate. Its current original four-review
results and lifecycle evidence remain mandatory. Normal delivery has no such
exception.

## Test The Actual Integration

Keep evidence per named host, version, model and adapter version. Test ordinary
delivery plus missing/failed review, stale request, wrong artifact, changed
context, draft/self-check mismatch, interrupted verification and changed input
between response arrival and copy. Exercise the actual UI/API, not just a CLI.
Record untested platforms as untested. Offline synthetic tests establish only
the covered program behavior; a producer-authored PASS is not host acceptance.

## Calibrate Judgments Separately

Use actual reader feedback or independently reviewed labels on a frozen,
representative set. Keep development examples separate from held-out cases.
Label both changes that are needed and originals that should remain; include
source fidelity, necessary negatives, instruction echoes and useful repetition.
Preserve disagreements and unknowns instead of forcing a unanimous gold label.

`scripts/evaluate_judgments.py` compares recorded `keep/revise/abstain`
predictions with the frozen reference set. It counts missed problems,
unnecessary revisions, failures, missing runs, decision coverage, worst run and
cross-run disagreements. Missing/failed runs stay visible in the planned
denominator. It verifies the dataset hash and case/run identities, not the
authenticity or correctness of human labels. It never certifies writing quality
or host integration and applies no invented release threshold.

```bash
python3 scripts/evaluate_judgments.py --dataset FROZEN_CASES.json \
  --results ORIGINAL_RESULTS.json --output NEW_MEASUREMENT.json
```

See `evals/judgment-calibration-example.json` for a synthetic input format, not
a completed evaluation. Each result needs run/case IDs, completion/error state,
prediction and an original-evidence reference. Set acceptance thresholds and
label authority explicitly before using measured results for rollout decisions.
This is maintenance work, not another model call in every writing task.
