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

The runtime flow therefore separates four concerns:

1. **Decision derivation:** compute language and format from explicit signals
   and defaults instead of letting later drafting choose again.
2. **Immutable lock:** hash task decisions so accidental later changes fail.
3. **Action authorization:** check any publish, overwrite, or replacement
   immediately before the side effect and retain a preflight receipt.
4. **Deliverable verification:** compare the real artifact and semantic review
   with the locked contract and issue one pass/fail receipt.

## Required Files

Keep runtime records outside the visible deliverable, for example:

```text
.reader-seat/
|-- task-contract.json
|-- semantic-review.json
|-- action-preflight-receipt.json  # only for an authorized external action
`-- verification-receipt.json
```

Do not expose these files inside the finished document. Preserve them when an
audit, regression diagnosis, or cross-agent comparison is requested.

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
  --source-file .reader-seat/source.txt \
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

Initialization creates every applicable semantic gate with `status=pending`.
After drafting, replace each pending status with `pass` only after inspecting
the actual artifact. Add concise, artifact-specific evidence. Generic evidence
such as `checked`, `looks good`, or `followed the skill` is insufficient.

Use `fail` while an issue remains. Fix the artifact, recheck affected gates, and
only then change the status. Do not remove a required gate or mark it
not-applicable; the runtime contract determines applicability before drafting.

The review is a completeness control, not independent proof. For high-risk work,
run an independent semantic judge using [evaluation.md](evaluation.md). Save a
JSON result with the runtime `contract_id`, `verdict=pass`, and every required
semantic gate set to `pass`; pass that file to verification with
`--judge-result`. A missing, mismatched, incomplete, or failed judge result
blocks a high-risk task. For a stability claim, also follow the repeated,
cross-host procedure in [agent-portability.md](agent-portability.md).

## Guard External Actions

Immediately before a publish, overwrite, or cross-application replacement tool
call, run the matching locked action:

```bash
python3 scripts/runtime_contract.py check-action \
  --contract .reader-seat/task-contract.json \
  --action publish \
  --target feishu \
  --receipt .reader-seat/action-preflight-receipt.json
```

A failure blocks the tool call. Retain the passing action receipt for final
verification. Do not publish first and validate afterward.
The same command uses `--action overwrite` or `--action replace` when that is the
explicitly authorized operation; one action never authorizes another.

## Verify The Actual Deliverable

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

Delivery is allowed only when the receipt contains `status=pass`. A failed or
missing receipt means the output is incomplete, even when a file was created,
an export succeeded, or a platform reported publication success.

## Host-Level Boundary

A skill cannot force a host to invoke its scripts or override a higher-priority
system instruction. Strong production enforcement requires the host or wrapper
to reject final delivery when any of these is missing or failed:

- locked task contract;
- action authorization for the exact external mutation;
- a passing action preflight receipt for the exact mutation and target;
- complete semantic review;
- passing verification receipt.

Without that host integration, the runtime flow materially reduces accidental
drift and makes skipped checks visible, but it cannot provide an absolute execution guarantee.
Do not claim cross-host stability until the frozen suite
passes on each named host at the required repetition count.
