# Checked Delivery

Use `scripts/deliver.py verify` with the same arguments as
`runtime_contract.py verify`, except `--receipt`. The wrapper owns a new private
temporary receipt, calls the existing verifier, and returns JSON only after
checking its typed state and unchanged inputs. It does not add a review round.
For agent tool calls, add `--output NEW_ENVELOPE.json`: only a short status is
printed, so the encoded document does not consume model context. The file is
created privately and cannot overwrite an input or an earlier result. Direct
host integrations may omit this option and consume the envelope from stdout.

For the existing third-round fallback, use `scripts/deliver.py present-draft`
with the corresponding runtime arguments except `--receipt`. This rechecks the
three-round condition and returns `delivery_state=draft`, actual unresolved
issues and required user notice/question. It never turns a draft into a pass.

The JSON envelope contains `delivery_state`, `review_method`, the local artifact
hash and base64 `payload`. Consumers must check process success AND
`delivery_state`, decode the payload, verify its hash, and display those bytes
without asking the model to regenerate them. The envelope covers the main local
artifact, not an archive of its assets. Keep its resource base and existing
asset/render checks; copying one HTML file does not prove portable delivery.

`external_action_authorized=false` is deliberate: a local content check is not
permission to publish or replace. Keep `check-action`, exact native readback,
and live render verification. Native text-patch delivery retains its separate
prewrite/readback protocol; do not claim this wrapper enforces that host path.

## Host Boundary

The wrapper rejects missing/pending/stale checks and in-call file changes. Hashes
are freshness evidence, not proof that a reviewer is independent or correct.
Use the existing isolated review calls; a managed host should capture original
review returns itself and keep the author from editing its acceptance state.
An unrestricted agent can still bypass the wrapper; installing the skill is not
host enforcement. A caller must make this the only path to its verified-output
UI. Until then, state the integration limitation rather than claiming enforced
delivery across hosts. Never replace missing semantic review with filled fields.

Keep reader relevance, natural syntax, necessary boundaries and progression in
the existing `reader_value` checks, quoting concrete passages and reader impact.
Do not add a score, reviewer, global word limit or stylistic retry loop.
