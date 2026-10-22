# Source Attribution In Existing Reviews

For a mixed source/interpretation passage, check who said each proposition,
what the evidence supports, and what a reader will attribute to the source.
Do not let one citation endorse an adjacent interpretation or recommendation.
Do not invent speaker identity from a mentioned company, reply thread or label.

Unknown is not negative. A quoted sentence not discussing a mapping does not
prove that the whole email omits it, that a mapping is impossible, or that the
two fields differ. "But" and "therefore" need a supported relationship too.
Boundaries, negative assertions, headings, quote boxes and captions are subject
to the same checks as positive factual statements. Merely adding a full stop
does not repair a misleading attribution.

## Execution

Reuse the current review, not a new role or round. `source_attribution.py`
prepares clause windows only for likely mixed passages. They are review units,
not a universal grammar or forbidden-word list. Inspect the whole visible text
for other cases; manually add an anchored item if the cue scan misses one.

- Functional source review completes `meaning.source_attribution` against the
  actual bound source. Keep the source speaker separate from the document author.
- Existing reader/context review completes `attribution_replay` from its allowed
  reading surface, without unseen sources or expected classifications.
- Aggregation compares source ownership and confirmed/unconfirmed negative
  status. Mismatches return for revision; do not coach the blind reader.
- Literary review separates narrator/character voices from external testimony.
  Preserve intentional ambiguity; do not force a report-style factual answer.
- Other writing skills reuse the existing `context_value.py` check. Supply an
  authorized exact source snapshot via `--source SOURCE` when making source-backed
  claims; never retrieve or save private material merely to satisfy a field.

Code checks coverage, anchors, source hashes and declared agreement, not whether
an entailment or identity judgment is true. The existing source reviewer still
checks support and contradictory evidence. No visible audit table is required.

## Fictional Pairs

Bad: "The email says field_x was added, so it cannot be official_time."
The first fact does not establish the second, and the email is not automatically
the speaker of both clauses.

Better: "The email says field_x was added. My recommendation is to verify its
mapping to official_time before using it in this calculation."

If the source explicitly states the fields differ, retain that sourced negative
fact. If the sender is a submitter rather than a support agent, do not rewrite
the statement as an official support confirmation. Preserve a limited quotation
as limited; do not claim the full thread was searched from a snippet alone.
