# Lifecycle Adapter Integration

Reader's Seat is `0.31.0`; the native patch receipt is `native-text-patch-2`.
No installed skill directory was synchronized. Shared engine, quality config
and shared fixture are supplied by the coordinating agent, not edited here.

## Integration Boundaries

- `review_evidence` is the original reader-review aggregate path, not a copied
  pass receipt. Existing validation reopens all four original reader results.
- Native-linked fixtures derive the real task format, reader, required answers
  and source refs from the locked native inputs; the shared fixture supplies
  clearly synthetic assessment data. They prove wiring, not actual target QA,
  independent identity, chronology or reader improvement.
- `check-action --preview` solves the write-before-layout sequence with the
  same existing authorization. It checks only registered prewrite/unit/current
  candidate readiness and returns `preview-only`. Final action/verification
  rejects that receipt even after later full review passes.
- Native JSON snapshots use their existing exact canonical XML extraction as
  the lifecycle artifact, not a new blanket extension exemption. The native
  gate still binds candidate JSON, original answer plan/source and four raw reviews.
- Three completed rounds plus a current last-round failure/issues permit only
  a labeled draft. Earlier passes neither hide the regression nor block this exit.
- Low-level semantic and native checks remain available, explicitly local and
  non-completing. Host delivery must consume the checked wrapper or checked
  native CLI, not interpret a local `status=pass` as full acceptance.

## Verification

Run from this staged package:

```bash
python3 -B -m unittest discover -s tests -q
python3 -B scripts/validate_skill.py
python3 -B /path/to/skill-creator/scripts/quick_validate.py "$PWD"
```

The official validator needs PyYAML; no production dependency was added.
After the coordinator's frozen shared-engine sync, all 248 package tests passed
on 2026-10-20, including 33 shared regressions. Static and official entrypoint
validation passed. Engine, quality config and shared fixture match `shared/`
byte-for-byte. The entrypoint remains 145 lines under its 150-line budget.
Fresh model-writing trials, cross-host quality claims and live Feishu actions
are outside these structural tests and were not performed.

## Changed Files

- `SKILL.md`
- `config/agent-adapters.json`
- `config/runtime-rules.json`
- `config/skill-contract.json`
- `evals/behavior-cases.json`
- `references/agent-portability.md`
- `references/checked-delivery.md`
- `references/lifecycle-adapter-notes.md`
- `references/native-text-patch.md`
- `references/runtime-enforcement.md`
- `references/writing-lifecycle.md`
- `scripts/checked_delivery.py`
- `scripts/deliver.py`
- `scripts/lifecycle_guard.py`
- `scripts/native_text_patch.py`
- `scripts/runtime_contract.py`
- `scripts/validate_skill.py`
- `tests/lifecycle_support.py`
- `tests/test_checked_delivery_cli.py`
- `tests/test_lifecycle_delivery.py`
- `tests/test_native_text_patch.py`
- `tests/test_runtime_contract.py`
