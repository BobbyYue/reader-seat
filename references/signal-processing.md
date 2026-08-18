# Standardized Signal Processing

Use this module on source documents and completed drafts. Signals identify passages that require judgment; they are not violations and never directly authorize rewriting.

## Signal Register

Record every material signal internally using these fields:

| Field | Required content |
| --- | --- |
| Location | Exact sentence, paragraph, heading, table, figure, or document-level pattern |
| Signal | Observable trigger without claiming it is already an error |
| Context test | Reader-, scenario-, and consequence-specific question used to judge the signal |
| Decision | `confirmed`, `dismissed`, or `unresolved` |
| Reader impact | The concrete effect on understanding, judgment, trust, or action |
| Action | `none`, `local-edit`, `section-rebuild`, `full-restructure`, or `surface-to-user` |
| Verification | Check that proves the issue improved without factual or scope drift |

Do not expose the full register in a normal finished document. For diagnostic requests, present only material confirmed or unresolved signals as `location -> reader impact -> smallest effective fix`. Mention dismissed signals only when they prevent a likely mechanical rewrite or explain why no change is recommended.

## Mandatory Decision Flow

Process each detected signal in this order:

1. **Locate**: identify the smallest affected unit. Do not diagnose an entire document from an aggregate score alone.
2. **Name the observation**: describe what is measurable or visible, such as a long sentence, dense terminology, delayed conclusion, repeated claim, or unnamed actor.
3. **Run the context test**: judge against the target reader, scenario task, local context, and consequence of misunderstanding.
4. **Decide**:
   - `confirmed`: evidence shows the signal impairs the reader task or factual integrity;
   - `dismissed`: the pattern is justified in context and does not materially impair the reader;
   - `unresolved`: required context or evidence is missing.
5. **Choose the smallest action**:
   - use `none` for a dismissed signal;
   - use `local-edit` when one unit can be repaired safely;
   - use `section-rebuild` when the reader path within one section is wrong;
   - use `full-restructure` only when the primary route or whole-document relationship fails;
   - use `surface-to-user` when uncertainty cannot be resolved without user or source input.
6. **Revise without drift**: preserve the source boundary and author voice.
7. **Verify**: rerun the context test, meaning-preservation check, affected output standard, and any affected hard gate.

No signal may remain unclassified. A confirmed signal may remain unchanged only when the record explains why revision would create a greater factual, legal, technical, or usability risk.

## Signal Families And Context Tests

| Signal family | Examples of observable triggers | Confirm only when | Typical smallest action |
| --- | --- | --- | --- |
| Retrieval | Main result appears late; heading does not reveal the section purpose; key decision is scattered | The target reader cannot find task-critical information within the expected reading path | Move or summarize the critical information; rename a heading |
| Structure | Multiple reader tasks are mixed; evidence precedes an unstated claim; steps are out of execution order | The relationship prevents correct judgment or completion | Reorder a paragraph or rebuild the affected section |
| Template residue | Generic method heading; repeated English kicker plus Chinese title; every section repeats the same question-card-callout pattern; visual exists only to satisfy a format | The visible scaffolding draws attention to the writing method, creates repetition, or could be transplanted unchanged into an unrelated document | Rename the local heading from its content, remove the redundant label, vary the affected section, or omit the nonessential visual |
| Information-empty scaffolding | Heading or label says only `最值得关注`, `真正改变`, `核心洞察`, `背后`, `不能忽略`, `为什么重要`, or another importance or suspense cue | After reading it, the reader learns only that content is supposedly important and still cannot identify the object, result, relationship, action, or boundary | Derive a heading from the section proposition, retain only necessary navigation, or remove the element |
| Title fit | Object missing; generic promise; hidden intent claimed; title stronger than body; title and subtitle repeat; headline could fit an unrelated document | The reader cannot predict the true scope or is likely to infer a fact, cause, certainty, or value the body does not support | Add a concrete anchor, replace the overstated verb, express the core relationship, remove repetition, or rewrite the title |
| Sentence complexity | Long sentence; deep nesting; many conjunctions; multiple propositions | The reader cannot reliably identify subject, relationship, qualification, or conclusion | Split or reorder only the confusing propositions |
| Terminology | Dense acronyms; unexplained niche term; familiar abbreviation with ambiguous local definition | The intended reader is unlikely to share the meaning, or a different interpretation would matter | Define locally, add a plain-language gloss, or retain unchanged for expert readers |
| Responsibility | Passive voice; missing actor; vague pronoun; action without owner | The reader cannot tell who decides, executes, verifies, or responds | Name the known owner or flag the missing owner; never invent one |
| Evidence and certainty | Unsupported certainty; claim separated from source; correlation phrased as causality | The wording exceeds the available evidence or prevents traceability | Qualify the claim, move evidence closer, or surface the missing source |
| Visual provenance | Real-person or event image without original attribution; external visual found only through search or an aggregator; generated image resembling documentary evidence; missing synthetic label | Identity, origin, context, authenticity, or presentation could cause a reader to believe an unsupported fact | Reject or replace the asset, add bounded attribution or a visible synthetic label, or surface the missing provenance |
| Concision | Repeated conclusion; duplicated evidence; throat-clearing; process detail | Removal does not reduce understanding, trust, reproducibility, or actionability | Delete or consolidate the smallest redundant unit |
| Actionability | Request hidden; no timing or dependency; recommendation beyond evidence | The scenario requires action and the reader cannot execute or decide safely | Clarify the known action fields or surface what is missing |
| Visual encoding | Misleading scale; decorative color; inaccessible contrast; chart type conflicts with the comparison | The visual can cause a materially wrong interpretation or blocks access | Correct the encoding while preserving the underlying data |

Counts, thresholds, and formulas may prioritize review order, but they cannot confirm any family by themselves.

## Hard Failure Override

If a signal reveals a hard failure from [output-standards.md](output-standards.md), stop treating it as optional review. Correct it before delivery or state that the task is blocked or bounded. Examples include an altered number, invented source, unsupported causal claim, deceptive or clickbait title, material scope drift, unsafe action, an unverified real-person image, or a generated visual presented as documentary evidence.

For any visual-provenance signal, run the full decision flow in [visual-evidence.md](visual-evidence.md). Do not resolve it only by adding the page where the image was found as a citation.

For any title-fit signal, run the full decision flow in [title-design.md](title-design.md). A more clickable title is not an improvement when it weakens scope, evidence, relevance, or expectation accuracy. If the title is deceptive, treat it as a hard failure and replace it before delivery.

## Action Selection Rules

- Prefer no change when the signal is dismissed.
- Prefer a local edit over a section rebuild, and a section rebuild over a full restructure.
- Do not simplify precise language into a broader but less accurate statement.
- Do not add missing owners, evidence, definitions, results, or deadlines by inference.
- Do not optimize one metric at the expense of reader outcomes, factual accuracy, or author voice.
- Do not replace one generic template label with another. Make the revision content-specific or remove the component.
- Do not preserve an information-empty heading merely because the paragraph below eventually supplies the answer. Compress the section proposition into the heading or use a necessary navigation label.
- When several signals point to the same underlying problem, fix the cause once and verify all affected signals; do not perform repetitive edits.

## Verification Record

For every changed passage, confirm:

1. the original signal no longer impairs the target reader;
2. subject, object, direction, magnitude, conditions, uncertainty, responsibility, and intended action are preserved;
3. no new ambiguity or unsupported claim was introduced;
4. the relevant scenario acceptance question now passes;
5. the revision improves the intended reader outcome, not merely a proxy score.
6. for changed structural text, the heading-only readback now exposes the document path without overstating the body.

If verification fails, revert the ineffective part of the revision or choose a smaller, safer action.
