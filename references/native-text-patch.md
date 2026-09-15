# Scoped Native Text Replacement

This is a narrow alternative to the full-artifact runtime, not a waiver of final
render verification. Use it only for an explicitly authorized, standard-risk
Feishu text replacement in existing blocks. Do not use it for new publication,
structural/style/chart edits, unknown targets, sensitive/high-risk changes, or
to avoid a failed full-artifact review.

1. Read the live native document. Save a lossless normalized snapshot with
   `document_id`, `revision`, ordered `blocks` and their original IDs, text,
   styles and other native fields. Keep unrelated blocks unchanged. The format
   is specified in `scripts/native_text_patch.py`; it is a validation snapshot,
   not an upload payload or replacement for the actual native document.
2. Lock a source-backed reader-answer plan before writing candidate text. Use
   the changed headings plus necessary adjacent qualifiers as the reading
   surface. Create candidate JSON and exact `{block_id,before,after}` changes.
   Generate the readable XML with `native_text_patch.candidate_xml(candidate)`;
   pass that exact XML as `reader_answers.py prepare --content-snapshot`, with
   candidate JSON as `--artifact`. Complete the blind/source answer check.
3. Record the user's actual instruction, document ID, exact block IDs,
   `action: replace-text` and `risk: standard` in authorization JSON. Refresh
   the baseline immediately before preflight; if it changed, rebuild the patch.
4. Run the preparation command below. `prewrite-approved` permits only the
   declared authorized text replacement; it is not a completion verdict. Use
   native block-level editing and revision guards when available. Never replace
   the whole document or overwrite concurrent edits.
5. Re-fetch the document after the write and inspect its actual native render.
   Record the current readback/image hashes and concrete readability, overflow
   and claim-evidence adjacency findings. Run verify; only `verified` is final.
   If readback or rendering is unavailable, report “written, verification
   incomplete” and the missing evidence. Do not claim completion or blindly
   retry an uncertain write. On a mismatch, inspect it and seek direction if
   repair would exceed the authorized block scope.

```bash
python3 scripts/native_text_patch.py prepare \
  --baseline baseline.json --live-baseline live.json --candidate candidate.json \
  --changes changes.json --authorization authorization.json \
  --answer-receipt answers.json --output prewrite.json
python3 scripts/native_text_patch.py verify \
  --prewrite prewrite.json --readback readback.json --render native.png \
  --inspection inspection.json --output verified.json
```

The script performs no external mutation. Its input and inspection schemas are
documented in its module header. It rejects undeclared content/style/order
changes, stale baseline/answer evidence, mismatched readback and stale render
inspection. No local hash check can prove a screenshot came from Feishu or an
inspection was honest; retain actual read/capture provenance. Unit fixtures are
not live native verification.
