# Managed Writing Execution

Use `scripts/writing_execution.py` for managed task identity, actual review
dispatch and checked delivery. It does not replace the native writing method,
source review, reader answers, visual checks, or literary self-checks.

## Responsibility

`config/execution-policy.json` owns executable rule IDs, roles, dependencies and
limits. Unknown validator IDs or missing mandatory IDs fail resolution. Native
rule sources continue to own writing judgments; do not copy all their prose into
this policy. Candidate checks are computed by code; native judgments retain
their original evidence. A status sentence is not proof of a command or review.

The standard-library controller is shipped identically in all three packages.
It does not load tests or the complete implementation into writing context.

## Start Before Writing

After the native task and lifecycle are initialized, but before any unit:

```bash
python3 scripts/writing_execution.py init LIFE --task-id HOST_TASK_ID
python3 scripts/writing_execution.py next LIFE
```

The default registry is `~/.local/state/writing-skills/tasks.sqlite3`. A managed
host can set `--registry` during initialization. Use its same configured store
for all resumes. The host supplies a stable request/artifact-lane ID; do not
mint a new ID or select a new registry to reset a task. Independent output lanes
have distinct host IDs. Do not deduplicate different user requests solely by
source content. The registry rejects the same ID in a second working directory.
It uses SQLite transactions; existing lifecycle files retain atomic writes and
locks. Unmanaged old runs are local evidence, not upgraded acceptance. Do not
retroactively label a finished draft as a managed prewrite run.

3080 Fast must be explicitly chosen before writing: initialize with
`--mode self-check`. Its final result remains self-checked, not independently
accepted. This option records the caller's choice, not user-consent proof.

## Native Packets, Actual Calls

Register units and a complete measured candidate as before. Prepare Reader/3080
native review packets with `--lifecycle-run LIFE`; the builders register exact
files before dispatch. Writer uses its lifecycle's sealed native packets.
Start the lifecycle batch. Derive the packet map, do not retype
another task/answer plan:

```bash
# Reader: --source is its round-manifest.json.
# 3080: --source is build_review_packet.py's output directory.
# Writer: omit --source; use the current literary lifecycle packets.
python3 scripts/writing_execution.py packets LIFE --source NATIVE_PACKETS --output packets.json
# CLI backend only when the current account/model is supported:
python3 scripts/writing_execution.py review LIFE --packets packets.json
```

Writer review adds `--native-run NATIVE_RUN`. The controller binds draft IDs and
transport metadata; it does not edit verdicts, issues, quotes or judgment text.
Reader review imports its native result schema, binds identities from actual
CLI events, and computes answer/manifest hashes rather than asking a model to
invent them. No-context gets its extracted surface, not source or author answers.

In this app, prefer `scripts/writing_host.js`: load its source in the host's
code tool and call `runWritingHost(tools, {skillRoot, run, packets, nativeRun})`.
Omit nativeRun except for Writer. The bridge itself calls actual native
spawn/wait/close tools with `fork_context:false`, imports the untouched returns,
and supplies transport metadata from those calls. It does not ask the author to
write a successful tool receipt. `writing_host.py` owns prepared prompts,
request IDs, duplicate-launch prevention, imports and recovery. Missing host
capabilities block the bridge; never replace them with a fabricated response.
An uncertain launch with no stored return is blocked rather than resent. A
known live reviewer can be resumed without a second launch. Return-shape errors
are technical failures, not permanent cached successes or invented content issues.
Native required fields and evidence anchors are checked before caching; a
well-formed negative judgment remains a content failure, not a transport retry.

The optional CLI backend starts a fresh `codex exec --ephemeral --sandbox read-only`
process in a separate directory, without a resume ID or parent conversation.
It inherits the user's configured model/provider rather than silently choosing
another model. Shared system/user settings are not experimental isolation;
read-only execution is not a security sandbox against all filesystem reads.
Only the role's authorized packet/materials may be used. Original answer bytes,
CLI events, diagnostics, actual thread ID and derived native result are retained
privately. Final checking compares the derived result to the original return;
only transport/version metadata may be added by code. Private material is not
automatically made a public test case.

Independent jobs run concurrently. Reader's source-answer evaluation waits for
the frozen no-context answers, receiving only those answers, not the other
reviewer's opinions. This dependency is part of the same batch, not another
review round. Native aggregation remains mandatory after all returns arrive.

## Efficiency Without Weaker Acceptance

The native bridge releases a dependent job as soon as its required return is
captured, without waiting for unrelated reviewers. Active attempt IDs prevent
duplicate dispatch; failures drain already-running work without starting new
dependents. Resume still uses the original live agent and retry budgets.

`review_wire.py` compacts only the transport: duplicate context windows are
indexed, and registered metadata/anchors can be restored by code. Reviewers
must still choose evidence and return every judgment, reason and item ID.
Missing items, verdicts and observations are never generated. Supplied wrong
metadata or quotes are not repaired into passing evidence. Original returns
remain retained; final verification repeats the same deterministic expansion.
Full native records remain accepted. Source and reader inputs remain isolated.
Short packets retain the original protocol when the compact-protocol explanation
would cost more bytes than it saves; compaction must not add prompt overhead.

Managed tasks memoize program-computed measurements in their existing registry,
bound to exact text, plan/reader/profile, sources, rule/engine versions and
current wordlist/evidence/geometry bytes. Changed inputs cannot hit the old
entry. Missing or corrupt cache entries recompute; native content judgments are
never cached as computed facts. Four recent entries are an eviction bound, not
a limit on revisions. Lifecycle integrity, evidence hashes and delivered bytes
are still checked. No cache bypasses independent reviews or approval.

Reuse the same registered render/geometry files across checks for that frozen
version; do not recapture them for each reviewer. Different formats, viewports,
assets or target states need matching evidence. Publishing still needs a fresh
authorized target readback. This release does not reuse Reader/Writer judgments
across changed drafts or treat matching prose as proof of unchanged layout.

Inspect actual counters with `python3 scripts/writing_execution.py stats LIFE`.
It reports computed/reused measurements, controller timing, registered review
start/completion times, attempts and available prompt/answer bytes. These are
not token estimates, isolated model-inference times or writing-quality scores.
Do not infer an end-to-end speedup from a synthetic controller benchmark.

## Recovery And Delivery

Rerun `review` with the same run and packets after a technical interruption.
Captured unchanged jobs are reused; only missing/blocked jobs run again, up to
the configured technical-attempt limit. A live job cannot be stolen by a second
executor. A failed transport is blocked, never converted into semantic PASS or
an invented reviewer failure. Started semantic batches count once; changing the
working directory does not restart their budget under the same host ID.

If a spawn return was lost or rejected, the bridge retains `launch-uncertain`.
An operator must verify that no child started before using
`writing_host.py recover-launch LIFE --request REQUEST_ID --confirmed-no-agent
--reason REASON`. This records the recovery and permits the next technical
attempt in the same batch. Never use it to relaunch a known live reviewer or
to reset the semantic-round limit; if the launch cannot be established, stop.

Run the original native aggregation and `review-finish` on its exact result.
For the checked exit, put the original native exit arguments in a JSON string
array, omitting `--lifecycle-run`; the controller supplies that binding:

```bash
python3 scripts/writing_execution.py deliver LIFE --arguments exit-arguments.json
```

Reader arguments start with `verify`, `present-draft` or `lifecycle-draft`;
3080 uses the existing full, scoped, draft or Fast arguments. Writer arguments
start with `deliver NATIVE_RUN` (or `check NATIVE_RUN`) and its original options.
Existing checked native CLIs also reject missing managed execution evidence.
Scoped 3080 checks may reuse captured original returns only after native scope
verification; a newly filled scope receipt without a captured baseline cannot
substitute. Current third-round failed drafts retain notices and user questions.
Missing provenance is not waived by a draft flag.

## Exact Boundary

This verifies the cooperating entrypoint and collector, not unrestricted host
behavior, same-user tamper resistance, actual generation chronology, semantic
truth or human/literary effects. The host must retain its registry, protect the
collector's acceptance store from author mutation, and render only checked bytes
to enforce this as its sole delivery path. No such host-wide hook is installed.
This release provides this app's native tools and an optional Codex CLI transport;
other hosts need a trusted capture adapter, not self-filled identities. Without a working
backend, stop verified acceptance and report the blocked scope. Do not fall back
silently to manual PASS records. Existing low-level checks remain useful but are
not a complete managed delivery.
