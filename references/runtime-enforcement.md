# Runtime Enforcement

This module turns critical Reader's Seat decisions into a fail-closed runtime
contract. It applies to every task. The contract supplements semantic judgment;
it does not replace source review, scenario reasoning, or rendered inspection.

## Why It Exists

Instructions alone can be skipped, reinterpreted, or overridden by a host. A
static skill validator proves only that rules and files exist. An HTML validator
proves only structural properties. Neither proves that one actual deliverable
used the required language, format, authorization, evidence boundary, or
scenario contract.

The runtime flow therefore separates six concerns:

1. **Decision derivation:** compute language and format from explicit signals
   and defaults instead of letting later drafting choose again.
2. **Immutable lock:** hash task decisions so accidental later changes fail.
3. **Minimum complete context:** resolve the selected modules into one compact
   task contract and bind it to the entrypoint, routing source, rule source, and
   selected module hashes.
4. **Action authorization:** check any publish, overwrite, or replacement
   immediately before the side effect and retain a preflight receipt.
5. **Independent reader validation:** require four fresh subagents to pass one
   parallel review batch for the exact artifact, with at most three rounds.
6. **Deliverable verification:** compare the real artifact, reader aggregate, and semantic review
   with the locked contract and issue one pass/fail receipt.

## Required Files

Keep runtime records outside the visible deliverable, for example:

```text
.reader-seat/
|-- task-contract.json
|-- resolved-task-contract.md
|-- module-manifest.json
|-- semantic-review.json
|-- reviews/
|   `-- round-N/
|       |-- round-manifest.json
|       |-- four packet and result files
|       `-- aggregate.json
|-- action-preflight-receipt.json  # only for an authorized external action
`-- verification-receipt.json
```

Do not expose these files inside the finished document. Preserve them when an
audit, regression diagnosis, or cross-agent comparison is requested.

`init` creates `resolved-task-contract.md` and `module-manifest.json` beside the
runtime contract unless `--task-bundle` and `--module-manifest` provide explicit
paths. Use the generated task contract as the default model context. It contains
the selected compact rules and the active scenario contract, while the manifest
binds them to canonical source hashes. Full references remain available for
troubleshooting and maintenance but are not loaded by default.

## Lock The Task Before Drafting

After reading the substantive source, initialize the contract. This example is
an English-source article requested in Chinese, with no explicit language or
format override:

```bash
python3 scripts/runtime_contract.py init \
  --contract .reader-seat/task-contract.json \
  --review .reader-seat/semantic-review.json \
  --scenario news \
  --operation create \
  --channel artifact \
  --reader-profile "Internet-industry reader without project history" \
  --source-file .reader-seat/source.txt \
  --source-bundle .reader-seat/source-bundle.txt \
  --language-override none \
  --explicit-format none \
  --existing-format none \
  --publication-target none \
  --title \
  --visual none
```

Save the substantive source prose, excluding navigation and unrelated page
chrome, as `.reader-seat/source.txt` before initialization. The script detects
its dominant language, records its SHA-256 fingerprint, and rejects a conflicting
manual declaration. Use `--source-language` only when a source snapshot is not
available; that fallback is weaker and should be explained in the task record.

The result must lock `output_language=en`, `output_format=html`, and
`publication_target=none`. Do not draft if initialization fails.

For mixed or unknown source language, pass `--selected-language` and a concrete
`--language-reason`. For an explicit translation request, pass
`--language-override`. The script rejects a selected language that conflicts
with either an explicit override or a clear source-dominant default.

For a user-authorized Feishu deliverable, record both the format and publication
authorization. Keep the evidence short and specific, such as the user's direct
request to create a new Feishu document:

```bash
python3 scripts/runtime_contract.py init \
  --contract .reader-seat/task-contract.json \
  --review .reader-seat/semantic-review.json \
  --scenario business \
  --operation create \
  --channel artifact \
  --reader-profile "Business leader without project history" \
  --source-bundle .reader-seat/source-bundle.txt \
  --source-language zh \
  --explicit-format feishu \
  --publication-target feishu \
  --external-action publish \
  --external-action-authorized \
  --authorization-evidence "User explicitly requested a new Feishu document"
```

Do not infer publication authorization from `document`, `report`, `shareable`,
the source platform, available tools, or a successful login.

## Complete The Semantic Review

Initialization creates every execution gate, semantic gate, and selected runtime
rule with `status=pending`. After the exact candidate exists and before filling
any item, bind the review to that artifact version:

```bash
python3 scripts/runtime_contract.py bind-review \
  --contract .reader-seat/task-contract.json \
  --review .reader-seat/semantic-review.json \
  --artifact path/to/report.html
```

For Word or slides, also pass the same UTF-8 `--content-snapshot` later used by
`verify`. Binding fails after any review item has been completed. If the artifact
or snapshot changes, start a fresh review file under a new contract; changing a
stored hash is not a review.

`bind-review` also creates a separate `*.binding-receipt.json` and locks its
hash and artifact binding into the runtime contract. Verification checks the
review, receipt, contract, artifact, and content snapshot together. Editing the
binding inside a completed review cannot authorize a different artifact.

After binding, replace each pending status with `pass` only after inspecting the
exact artifact. Add concise, artifact-specific evidence. Generic evidence such
as `checked`, `looks good`, or `followed the skill` is insufficient.

Initialization also creates one `runtime_rules` entry for every compact rule in
the generated task contract. Mark each entry `pass` with concrete evidence.
Only rules visibly marked `[conditional]` in the task contract may be
`not-applicable`, with a task-specific reason. Core rules and unmarked module
rules cannot be waived. A missing rule, invalid or unexplained not-applicable
status, pending status, or generic evidence blocks verification.

Complete `G1-task` through `G6-verify` against the required record and exit
condition embedded in the task contract. All six execution gates require
`status=pass` and artifact-specific evidence.

Use `fail` while an issue remains. Fix the artifact, recheck affected gates, and
only then change the status. Do not remove a required semantic gate or mark it
not-applicable; the runtime contract determines gate applicability before
drafting.

The review is a completeness control, not independent proof. For high-risk work,
run an independent semantic judge using [evaluation.md](evaluation.md). Save a
JSON result with the runtime `contract_id`, `verdict=pass`, and every required
semantic gate set to `pass`; pass that file to verification with
`--judge-result`. A missing, mismatched, incomplete, or failed judge result
blocks a high-risk task. For a stability claim, also follow the repeated,
cross-host procedure in [agent-portability.md](agent-portability.md).

## Complete Independent Reader Validation

For every finished artifact, follow [reader-validation.md](reader-validation.md).
After the draft passes cheap deterministic checks, use `reader_review.py prepare`
to create four immutable packets. Launch exactly four fresh subagents in one
parallel batch for `no-context`, `readability`, `source-reliability`, and
`structure-visual`. Do not pass parent context or another review to any child.

Use `reader_review.py aggregate` only after all four return. All dimensions must
pass for the current artifact hash. Later action and delivery checks reopen the manifest, packets, and four
original result files; they do not trust an edited aggregate status or copied
review records.
A non-pass in rounds 1 or 2 returns to the main agent for revision; every changed artifact reruns all four dimensions with
new sessions. A round-3 non-pass becomes `needs-user-decision`; it cannot be
overridden by the main agent or used for an external action. A missing child,
reused session, stale hash, malformed result, or absent render/source evidence
is also non-pass.

After a valid round-3 non-pass, run `runtime_contract.py present-draft` with the
exact current artifact and aggregate. A `review-incomplete-draft` receipt allows
the current version to be shown directly to the user, provided the response
states which checks remain unresolved, explains their reader impact, and asks
the user which optimization direction to take. It does not satisfy final
verification or authorize publish, overwrite, or replacement. Do not run round
4 under the same task contract; a user decision, new evidence, or changed scope
starts a new contract.

```bash
python3 scripts/runtime_contract.py present-draft \
  --contract .reader-seat/task-contract.json \
  --artifact path/to/current-report.html \
  --reader-review-aggregate .reader-seat/reviews/round-3/aggregate.json \
  --receipt .reader-seat/review-incomplete-draft-receipt.json
```

## Guard External Actions

Immediately before a publish, overwrite, or cross-application replacement tool
call, run the matching locked action:

```bash
python3 scripts/runtime_contract.py check-action \
  --contract .reader-seat/task-contract.json \
  --review .reader-seat/semantic-review.json \
  --action publish \
  --target feishu \
  --artifact path/to/verified-export.md \
  --reader-review-aggregate .reader-seat/reviews/round-1/aggregate.json \
  --judge-result .reader-seat/independent-judge.json \
  --receipt .reader-seat/action-preflight-receipt.json
```

A failure blocks the tool call. Retain the passing action receipt for final
verification. Do not publish first and validate afterward.
Omit `--judge-result` only for standard-risk work. High-risk external actions
must pass the independent judge before the side effect, not only during final
verification.
The same command uses `--action overwrite` or `--action replace` when that is the
explicitly authorized operation; one action never authorizes another.

## Verify The Actual Deliverable

Every action and verification command first rechecks the locked task bundle,
module manifest, entrypoint, routing source, rule source, and selected module
hashes. A changed or missing runtime-context file blocks the command; restore
the locked files or initialize a new contract rather than editing stored hashes.

For chat-only output, save the exact proposed final response as
`.reader-seat/candidate.txt`, verify it with `--actual-format chat`, then return
that same text unchanged. Editing after verification invalidates the receipt.

For local HTML:

```bash
python3 scripts/runtime_contract.py verify \
  --contract .reader-seat/task-contract.json \
  --review .reader-seat/semantic-review.json \
  --artifact path/to/report.html \
  --actual-format html \
  --actual-publication-target none \
  --reader-review-aggregate .reader-seat/reviews/round-1/aggregate.json \
  --judge-result .reader-seat/independent-judge.json \
  --receipt .reader-seat/verification-receipt.json
```

Omit `--judge-result` only for a standard-risk task. Its presence never replaces
the deterministic language, format, authorization, asset, or publication checks.

For Feishu/Lark, export or re-read the published body into a UTF-8 text,
Markdown, or HTML file and verify that file with `--actual-format feishu` and
`--actual-publication-target feishu`, `--actual-external-action publish`, and
`--action-receipt .reader-seat/action-preflight-receipt.json`. Native visual and
interaction checks still apply after this content check. A missing or mismatched
action receipt blocks delivery even when publication itself succeeded.

For binary Word or slide artifacts, pass the real `.docx` or `.pptx` as
`--artifact` and a UTF-8 export of its visible text as `--content-snapshot`.
The runtime contract verifies format and language; the document-specific native
validator still owns package structure, layout, and rendered-page inspection.

A finished or externally publishable delivery is allowed only when the receipt
contains `status=pass`. A failed or missing receipt means the output is
incomplete, even when a file was created, an export succeeded, or a platform
reported publication success. The only direct-presentation exception is the
round-3 `review-incomplete-draft` flow above; it must remain visibly incomplete
and cannot be published externally.

## Host-Level Boundary

A skill cannot force a host to invoke its scripts or override a higher-priority
system instruction. Strong production enforcement requires the host or wrapper
to reject final delivery when any of these is missing or failed:

- locked task contract;
- action authorization for the exact external mutation;
- a passing action preflight receipt for the exact mutation and target;
- complete semantic review;
- four context-isolated reader results and a passing aggregate for the current artifact;
- passing verification receipt.

Without that host integration, the runtime flow materially reduces accidental
drift and makes skipped checks visible, but it cannot provide an absolute execution guarantee.
Do not claim cross-host stability until the frozen suite
passes on each named host at the required repetition count.
