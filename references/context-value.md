# Contextual Value In The Existing Review

Check the intended reader's whole context, not whether a sentence sounds true
in isolation. Preserve precise claims; do not attach a denial of a stronger
claim the document never made. Internal correctness checks belong in private
records unless the reader needs them to interpret a result.

In the existing drafting/review pass, compare suspect passages with and without
the line. Keep a line only for a concrete contribution: new information, an
actual ambiguity resolved, a changed judgment/action, a necessary connection,
a required disclosure, or an intentional teaching/literary/spoken effect.
Read the paragraph and relevant earlier context; do not invent a hypothetical
ignorant reader to justify repetition. Headings and table labels count as context.
Prefer fixing claim strength directly over adding a defensive tail.

Record only suspect passages, not every sentence. The program's phrase signals
request review, never automatic deletion or a banned-word decision. Scan for
other unnecessary explanation too; a clean phrase scan is not semantic approval.
Existing functional editorial reviews use `selection.context_review`; Writer
uses the professional return's `context_review`. Other writing skills run:

```bash
python3 scripts/context_value.py prepare --text visible.txt --review value-review.json --profile functional
# Complete the private record during the existing review.
python3 scripts/context_value.py check --text visible.txt --review value-review.json --profile functional
```

The same record now contains `attribution_replay`: what the visible text makes
the reader attribute to a source, author or fictional speaker. For mixed source
statements and author judgments, follow [source attribution](source-attribution.md).
In standalone reviews, add `--source source.txt` to both commands and complete
`source_attribution` from that exact authorized snapshot, then compare it with
the reader replay. Source claims cannot pass this CLI without their snapshot.
Core skills reuse their existing source and reader roles; do not send source
evidence to a source-free reader. No separate article-wide audit is added.

Use the exact visible text, slide text, course prose or spoken script, not raw
HTML/JSON or hidden material. Bind to the current version; check again if it
changes. Do not modify verbatim quotes or protected text; identify its role
instead. Keep selected message/CV text ephemeral and remove temporary records
unless retention is authorized. `record_checks_satisfied` verifies execution
and binding, not that a semantic judgment is correct. Tool unavailability must
be disclosed, not replaced by a fabricated success record.

## Source-Free Examples

| Passage and context | Treatment | Reason |
| --- | --- | --- |
| Heading says candidate options; text adds "This is a candidate, not proven benefit" | Remove redundant tail | Candidate status is already clear |
| A normal comparison table adds "rounded for reading, grouped at original precision" | Remove by default | Internal calculation practice does not help this decision |
| A displayed 1.00 appears in the below-1 group due to rounding | Keep "Grouped using unrounded values" beside the table | Explains a visible contradiction |
| "Revenue rose 8%" omits that the sample covers one region | Retain the region in the claim | Changes applicability, not generic caution |
| A beginner course repeats the meaning of a new term in a worked example | Keep when it advances learning | Not all repeated facts are padding |
| A fictional speaker repeats "我没说谎" while hiding a letter | Judge characterization and tension | Do not delete intentional dialogue as a disclaimer |
| A CV says the applicant contributed, not led | Preserve contribution scope without an extra denial | Do not inflate ownership or add self-undermining boilerplate |

For functional writing preserve evidence, denominators, real uncertainty and
required notices. For teaching preserve scaffolding, worked examples and useful
recaps. For spoken writing preserve turn-taking and useful reminders. For
literature preserve narrator knowledge, ambiguity, characterization, rhythm and
purposeful repetition; no business-conclusion template or information-density score.
No new reviewer, extra review round, forced rewrite, word quota or visible
audit section is added. Resolve findings in the existing revision budget.
