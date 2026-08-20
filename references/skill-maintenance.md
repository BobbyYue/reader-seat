# Skill Maintenance

Use this module only when changing, packaging, or regression-testing Reader's
Seat. It is not part of ordinary document-generation context.

## Source Responsibilities

- `config/skill-contract.json` is the capability, version, and acceptance
  contract.
- `config/module-profiles.json` is the only routing source.
- `config/runtime-rules.json` is the compact operational rule source used to
  build a task-specific instruction packet.
- `config/skill-contract.json#runtime_rule_inventory` is the versioned exact
  rule-ID inventory; deleting or renaming a rule without updating the behavior
  contract must fail resolution and validation.
- Scenario references own their required content, evidence requirements, common
  failures, and acceptance questions.
- Other references retain detailed rationale, examples, and troubleshooting
  procedures. They are not default runtime context.

Do not duplicate routing decisions in `SKILL.md` or another reference. Do not
copy an operational rule into multiple runtime groups. A detailed reference may
explain a rule, but the generated task contract must obtain its instruction from
`runtime-rules.json`.

## Context Budget

Keep `SKILL.md` below 150 lines and 16 KB. It should contain only:

1. purpose and boundaries;
2. non-negotiable invariants;
3. the runtime sequence;
4. delivery states and failure behavior;
5. links to the routing, runtime, and maintenance sources.

Do not reduce context by removing capability. Reduce it by routing conditional
detail, extracting the selected scenario contract, and putting deterministic
mechanics in scripts. The generated task bundle must contain every selected
runtime rule and the active scenario contract, with a manifest that binds them
to canonical source hashes.

## Change Procedure

1. Change only the affected operational rule, scenario, detailed reference, or
   script.
2. Update `skill-contract.json` according to behavioral impact.
3. Add or update a regression case under `evals/` and focused unit tests.
4. Run `python3 -m unittest discover -s tests -v`.
5. Run `python3 scripts/validate_skill.py` and the official
   `quick_validate.py`.
6. Run the affected frozen case through `scripts/run_evals.py` without exposing
   its expected answer to the producer.
7. Forward-test at least one affected case and one unaffected scenario in fresh
   contexts.

For a cross-agent stability claim, test at least two named hosts, at least three
repetitions per host and model, semantic judging, and the worst run. Do not infer
cross-agent stability from static checks or one successful generation.

## Canonical Synchronization

Do not overwrite or synchronize the canonical skill directory as part of an
isolated implementation step. First verify the isolated copy, show the intended
file-level diff and risks, create a timestamped backup, and obtain explicit user
approval for the canonical mutation. After synchronization, rerun validation in
the canonical directory and compare it with the verified isolated copy.

## Acceptance

- All retained capabilities remain listed and routable.
- Every selected module has compact runtime rules or an extracted scenario
  contract.
- The task bundle and module manifest are created by `runtime_contract.py init`.
- The task bundle includes the target reader and full `G1-task` through
  `G6-verify` record and exit conditions.
- Only rules explicitly marked conditional may be recorded not-applicable.
- Semantic, execution-gate, and runtime-rule reviews are bound before completion
  to the exact artifact and content snapshot hashes.
- Verification rejects a missing, changed, or stale bundle, manifest, routing
  source, rule source, entrypoint, or selected module.
- The entrypoint and representative task bundles stay within their declared
  context budgets.
