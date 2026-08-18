# Cross-Scenario Output Standards

Apply all eight standards after selecting the scenario profile. These are quality constraints, not a universal document template.

## 1. Practical Information First

- Open with the information that best serves the scenario's reader task.
- When the content is analytical or decision-oriented, state the object, change or impact, strongest support, and practical meaning when applicable.
- Do not force a conclusion or call to action into news, reference material, or procedures that only need to inform or instruct.

## 2. Reader Perspective

- Organize around the reader's questions, decisions, and workflow.
- Include methodology or implementation process only when it changes trust, interpretation, replication, or execution.
- Exclude prompts, skill names, tool names, commands, schemas, checks, and generation history unless they materially affect a reader decision.

## 3. Progressive Disclosure

- Put task-critical information first, essential support second, and full detail last.
- Make a mixed-audience opening understandable to a non-specialist; place specialist reasoning afterward.
- Answer a simple need briefly. Do not inflate it into a report.
- Treat “quick to judge” and “easy to visualize” as reader outcomes, not mandatory chapter names or components.
- Use an opening summary only when the reader benefits from previewing the whole document. Use a visual only when spatial encoding makes a relationship, comparison, sequence, magnitude, location, or verification task easier than prose. When visual form is considered, follow [visual-communication.md](visual-communication.md), including the prose comparison and deletion test.

## 4. Natural, Audience-Fit Language

- Choose the output language in this order:
  1. an explicit user instruction about output language;
  2. the dominant language of the primary source document;
  3. a language requirement imposed by the target reader or delivery channel;
  4. the prompt or conversation language only when there is no source language to follow or no source language can reasonably be treated as dominant.
- An explicit language instruction must directly name or request the output language or translation. The language in which the user writes the request is not, by itself, an explicit language instruction.
- Do not translate or switch languages merely because the prompt uses a different language from the source.
- Determine the source's dominant language from its substantive prose. Ignore code, commands, citations, URLs, proper names, product names, isolated UI strings, quoted passages, and small translated fragments when estimating which language dominates.
- For a mixed-language source, use the language that carries most of the document's reasoning and reader task. When no language clearly dominates, prefer the primary source's editorial language; if that is also unclear, use the target reader's working language. Ask only when the choice would materially affect use; otherwise record the conservative assumption and keep the artifact internally consistent.
- Preserve code, commands, names, metrics, and familiar domain terms in their original form when translation would reduce precision. Translate quotations only when the reader needs it, and distinguish a translation from the original wording.
- Match the selected language's terminology, register, and formality rather than producing literal translation syntax.
- Prefer natural workplace language over bureaucratic, ceremonial, promotional, or template-like prose.
- Keep familiar domain terms. Explain a niche or ambiguous term at first use when misunderstanding is plausible or costly.
- Do not invent labels, frameworks, slogans, or jargon for ordinary work.
- Name sections after the actual content, finding, tension, decision, or reader question. If a heading could be moved unchanged into an unrelated document, make it more specific.
- Unless explicitly requested as part of a named format, do not use method labels such as `30秒判断`, `一张图读懂`, `读者视角`, `一句话总结`, or English process kickers as visible scaffolding.
- Treat the document title as a factual promise. It should identify the object and accurately preview one central relationship, change, decision, or useful question without claiming hidden intent.

## 5. Evidence And Calibrated Certainty

- Keep material claims traceable to their source when evidence matters.
- Treat photos, screenshots, charts, diagrams, captions, and cover visuals as evidence-bearing content. Verify their apparent claims and provenance, not only whether the files render.
- Use a real-person or real-event image only when identity and material context are traceable to an original, official, or otherwise authoritative source.
- Label generated or conceptual visuals visibly near the asset so readers cannot mistake them for documentary evidence.
- Distinguish observation, interpretation, correlation, causal claim, recommendation, assumption, and unknown.
- State material uncertainty, missing information, conflicting evidence, and credible alternative explanations.
- When numbers matter, include the applicable object, direction, magnitude, comparison basis, unit, period, denominator, sample, and definition.

## 6. Scope And Assumption Fidelity

- Preserve definitions, distinctions, scope, exclusions, responsibilities, commitments, and output boundaries.
- Label assumptions outside the artifact or in the artifact when readers need them to interpret the content.
- If the user changes a definition or requirement, revisit every affected claim and section. Do not patch only the named sentence.

## 7. Useful Structure And Concision

- Use headings, lists, tables, and visuals only when they improve scanning, comparison, or execution.
- Make each paragraph contribute a necessary fact, reasoning step, decision, or action.
- Remove throat-clearing, request restatement, duplicated conclusions, repeated evidence, and details that do not change understanding or action.
- Do not repeat one conclusion in the opening, a table, and the closing unless each occurrence serves a distinct reader need.
- Avoid mechanical symmetry: every section does not need the same kicker, guiding question, card grid, callout, and takeaway. Let section depth and form vary with the material.

### Visible Structure Must Carry Information

Treat every visible structural string as part of the document's information, including titles, subtitles, section headings, chart titles, figure captions, card headings, callout labels, and summary labels. Classify each one internally:

- `content-bearing`: compresses a proposition about an object plus a result, relationship, decision, action, or boundary;
- `navigation-only`: a conventional locator such as sources, appendix, or glossary that is genuinely needed for navigation;
- `decorative`: announces importance, suspense, or transition without adding content.

Keep `navigation-only` labels only when they help the reader locate a standard section. Delete or rewrite `decorative` text. Do not disguise it by replacing one generic phrase with another.

For every content-bearing section heading, record this internal heading proposition map:

`full section proposition -> highest-value new information -> compressed heading -> supporting body or source location`

Run these checks before delivery:

1. **Information increment**: after reading the structural text, what specific fact, relationship, action, or boundary does the reader now know? “This section is important” is not information.
2. **Cross-document portability**: if the same wording could move unchanged to many unrelated documents, make it specific or classify it as necessary navigation.
3. **Deletion**: if removing words such as `真正`, `核心`, `最值得`, `背后`, `不能忽略`, or `为什么重要` preserves all meaning, remove them. These words are review signals, not a universal blacklist.
4. **Heading-only readback**: hide the body and read the visible hierarchy in order. For a substantive document, the reader should be able to reconstruct the object, main conclusion or development, reasoning path, and material boundary or action.

A heading may be concise, but it may not outsource all information to the paragraph below. Progressive disclosure puts compressed information first; it does not manufacture suspense and delay the answer.

## 8. Action Proportional To Evidence

- When action is required, include only the necessary action, owner, timing, dependency, validation, and risk.
- When no action is required, do not manufacture one.
- Recommendations must not exceed evidence, authority, scope, or the source's commitments.

## Hard Gates

Reject or revise the output before delivery when any of these occurs:

- invented or altered critical fact, number, source, decision, owner, deadline, or commitment;
- unrequested translation or language shift away from the dominant language of the primary source;
- unsupported causal claim or certainty stronger than the evidence;
- material scope, definition, or responsibility drift;
- critical claim with no supporting evidence when evidence is required;
- deceptive or clickbait title that uses falsehood, exaggeration, unrelated hooks, manufactured suspense, omitted material context, or an unfulfilled promise to obtain attention;
- title claim that cannot be mapped to a supporting body passage and source;
- repeated or material decorative structural text that prevents the heading-only readback from revealing the document's main path;
- unverified real-person identity, misleading real-event context, or a synthetic visual presented as documentary evidence;
- unrelated or weakly sourced visual that implies support for a claim the source does not establish;
- missing material disclosure that a visual is generated, conceptual, composited, or materially altered;
- chart geometry, scale, order, aggregation, color, or omission that materially distorts the source-supported conclusion;
- a decision-critical distinction communicated only through color, or a visual that cannot be interpreted because units, denominator, period, baseline, definition, missing data, or uncertainty are materially absent;
- action beyond evidence, authority, or stated boundary;
- omission that prevents the scenario's reader task from being completed safely.

## Final Check

1. Can the intended reader find the scenario's main information quickly?
2. Can they understand it without knowing the generation process or internal tools?
3. Are claims supported and certainty calibrated?
4. Does the language sound natural for this reader and situation?
5. Can any sentence, paragraph, heading, or repeated conclusion be removed without loss?
6. Are scope, assumptions, uncertainty, and boundaries accurate?
7. Is the next action clear when needed and absent when not needed?
8. Are headings, table labels, placeholders, and edited passages free of obvious malformed or accidental text?
9. Is every visual's source, identity, context, and synthetic status clear enough to prevent a false factual inference?
10. Do headings and components sound native to this document, or do they expose a reusable writing template?
11. Does the title accurately identify the object, calibrate certainty, and promise only what the body delivers?
12. Is the title free of false, exaggerated, irrelevant, or unfulfilled click-inducing claims?
13. Has every visible structural string been classified as content-bearing, navigation-only, or decorative?
14. Does every content-bearing heading add a specific fact, relationship, decision, action, or boundary rather than merely promise importance?
15. Can the reader reconstruct the document's object, main conclusion or development, reasoning path, and material boundary or action from a heading-only readback?
16. Does the output language follow the explicit user request, or otherwise the dominant language of the primary source, without being pulled toward the prompt language?
