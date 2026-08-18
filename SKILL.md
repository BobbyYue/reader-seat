---
name: reader-seat
description: Create, rewrite, restructure, diagnose, or compare reader-ready internet-industry work documents while preserving facts, scope, evidence, uncertainty, and author voice. Use whenever the user wants a substantive document written or revised from the reader's perspective or made reader-friendly, including requests to reduce reading effort, help first-time or cross-functional readers understand without guessing, surface what readers need to know, judge, or do, or better match content to its audience. Also use for clearer, easier-to-scan, less AI-sounding, or more decision-ready news briefs, technical proposals, product documents, business updates, analysis reports, and SOPs. Finished documents default to self-contained HTML unless the user specifies Feishu/Lark, Markdown, Word, plain text, or another format. Do not use for short workplace-message polishing (use hit-send), source-to-one-page 3080 visual briefs (use 3080-brief), or purely visual styling.
---

# Reader's Seat

Create or improve a work document by routing it to the right document scenario, then applying shared output standards. Do not impose one universal body template.

Progressive disclosure is an information relationship, not a set of visible section names. Do not turn quality goals such as quick judgment, visual understanding, reader perspective, or evidence boundaries into default headings. Let headings name the actual subject, finding, tension, or question in the document.

Every loaded rule is operational, not optional background. Complete the mandatory execution record before delivery. A step may be marked `not-applicable` only with a task-specific reason; never skip it silently.

## Core Contract

Apply this priority when goals conflict:

`source truth and scope -> explicit user requirements -> scenario fit -> reader task -> natural expression -> brevity and polish`

- Preserve facts, numbers, definitions, distinctions, scope, stance, ownership, commitments, timing, uncertainty, and intended action.
- Never invent a source, reason, conclusion, decision, owner, deadline, result, or level of certainty.
- Organize the output around what the target reader must know, judge, or do, not around how the content was generated.
- Make reader-first design felt through ordering, emphasis, and explanation rather than announcing the method in generic labels.
- Use the selected scenario profile for body structure. Apply the shared output standards to every finished document.
- Select the output language before drafting. An explicit user language request wins; otherwise follow the dominant language of the primary source, not the language of the prompt. Follow the mixed-language rules in [references/output-standards.md](references/output-standards.md).
- Select the output format before drafting. For a finished document, an explicit user format or an existing artifact the user asks to edit wins; otherwise default to self-contained HTML. Follow the format decision and cross-format presentation rules in [references/format-decision.md](references/format-decision.md), then load [references/html-output.md](references/html-output.md) only when HTML is selected.
- Make the smallest change that materially improves the document. Preserve recognizable author voice.
- Keep facts, interpretation, causal claims, recommendations, assumptions, and unknowns distinguishable.
- Treat visuals as evidence-bearing communication. Every retained visual must reduce a real reader cost without distorting the source; a real-person or real-event image is also a factual identity and context claim, not decoration.
- Never deliver a deceptive or clickbait title. Reject or rewrite any title that uses falsehood, exaggeration, unrelated hooks, manufactured suspense, or a promise the body does not fulfill to obtain attention.
- Do not expose the skill name, routing labels, internal tools, commands, prompts, schemas, checks, or scores in the finished document unless the user asks or they affect a real decision.
- Do not publish, overwrite a source, or replace content in another application without explicit authorization.

## Language Selection Gate

Complete this gate before scenario routing or drafting:

1. Detect whether the user directly specified the output language, for example `write in English`, `用中文输出`, or `translate this into Japanese`.
2. Do not treat the language used to ask the question as an explicit output-language instruction.
3. If the user gave no direct language instruction, identify the dominant language of the primary source from its substantive prose and use that language for the output.
4. If there is no source or no source language can reasonably be treated as dominant, apply the fallback rules in [references/output-standards.md](references/output-standards.md).
5. Record the decision in `G1-task` and recheck the finished artifact in `G6-verify`.

Do not begin drafting until the output language is selected. A Chinese prompt about an English source produces English by default; an English prompt about a Chinese source produces Chinese by default. Only a direct language request overrides this behavior.

## Conditional Loading

Load only the resources needed for the current task.

| Condition | Read |
| --- | --- |
| Every task | [references/scenario-routing.md](references/scenario-routing.md), [references/output-standards.md](references/output-standards.md), and [references/signal-processing.md](references/signal-processing.md) |
| Every task that produces or edits a finished artifact | [references/format-decision.md](references/format-decision.md) to select the format and apply its portable presentation baseline, and [references/visual-decision.md](references/visual-decision.md) to make the no-visual or retain-visual decision cheaply |
| The selected output format is HTML by explicit request, inherited target, or default | [references/html-output.md](references/html-output.md) for the complete self-contained HTML implementation |
| Primary scenario is news or industry brief | [references/scenario-news.md](references/scenario-news.md) |
| Primary scenario is technical proposal or architecture decision | [references/scenario-technical.md](references/scenario-technical.md) |
| Primary scenario is product introduction, launch note, or PRD | [references/scenario-product.md](references/scenario-product.md) |
| Primary scenario is business update, project review, retrospective, or performance summary | [references/scenario-business.md](references/scenario-business.md) |
| Primary scenario is data analysis or research | [references/scenario-analysis.md](references/scenario-analysis.md) |
| Primary scenario is procedure, runbook, help article, or SOP | [references/scenario-procedure.md](references/scenario-procedure.md) |
| Rewriting or diagnosing an existing document | [references/diagnosis-and-revision.md](references/diagnosis-and-revision.md) |
| The user requests scoring/comparison, risk is high, or rules are being changed | [references/evaluation.md](references/evaluation.md) |
| The visual decision retains or reviews a chart, diagram, table, screenshot, callout, semantic color, card group, or visually encoded layout | [references/visual-communication.md](references/visual-communication.md) before implementing or revising the form |
| The task selects, generates, replaces, captions, or publishes any photo, illustration, chart, diagram, screenshot, or cover visual | [references/visual-evidence.md](references/visual-evidence.md) |
| The output needs a document title, article headline, subtitle, or title diagnosis | [references/title-design.md](references/title-design.md) |
| The task installs, adapts, or regression-tests the skill in another agent host | [references/agent-portability.md](references/agent-portability.md) |

For a mixed document, select one primary scenario for the whole document. Load one secondary scenario only when a clearly bounded subsection has a different reader task.

When script execution is available, resolve the ordered module list with
`python3 scripts/resolve_modules.py` using the recorded scenario, operation,
artifact, selected output format, risk, title, and visual decisions. Treat
[config/module-profiles.json](config/module-profiles.json) as the loading source
of truth. The resolver changes context cost only; it may never waive a rule or
prevent a required module from loading. When scripts are unavailable, reproduce
the same decision with the table above. Use the resolver's
`active_scenario_contract` as a silent completion checklist; it is extracted
verbatim from the selected scenario module and does not replace that module.

## Mandatory Execution Record

Maintain an internal record for every task. Do not expose it in the finished document unless the user requests a diagnosis, score, or audit.

| Gate | Required record | Exit condition |
| --- | --- | --- |
| `G1-task` | operation, primary scenario, target reader, reader task, channel, depth, source-dominant language, any explicit language override, chosen output language, explicit or inherited format signal, chosen output format, and consequence of misunderstanding | The intended reader outcome, output language, and output format are concrete enough to guide structure and expression |
| `G2-source` | immutable facts, numbers, definitions, scope, claims, evidence, uncertainty, ownership, commitments, any title claim, and any visual claims and provenance | Unsupported material is identified and the source boundary is explicit; each used title and visual has a source-status decision |
| `G3-route` | loaded shared modules, selected scenario module, required content, evidence requirements, acceptance questions, and title, visual-decision, visual-communication, or visual-evidence modules when applicable | One primary route is selected and all applicable requirements are accounted for |
| `G4-build` | status for all eight output standards and every applicable scenario requirement; visible-structure classification and heading proposition map; when a title is needed, title-material inventory, candidate comparison, and winner rationale; for a finished artifact, visual decision state, reader question, prose alternative, and deletion result; for each retained visual, form, color semantics, and full visual specification | Each item is `pass`, `issue`, or `not-applicable` with a reason; no decorative structural text remains, content-bearing headings expose the document path, the visible title is the strongest supported candidate, and every retained visual reduces a recorded reader cost without distorting evidence |
| `G5-signals` | signal register defined in [references/signal-processing.md](references/signal-processing.md) | Every detected signal is `confirmed`, `dismissed`, or `unresolved`; no signal directly causes rewriting |
| `G6-verify` | hard-gate results, meaning-preservation result, scenario acceptance result, signal recheck, visual provenance and labeling when applicable, and unresolved limitations | No hard failure remains; material unresolved issues are either fixed or disclosed |

Do not deliver because the draft merely sounds clearer. Delivery requires all six gates to reach their exit condition. When the source is insufficient, return a bounded result and surface the missing information instead of manufacturing completion.

## Workflow

### 1. Define The Task

Determine:

- operation: create, rewrite, diagnose, or compare;
- primary scenario and any bounded secondary scenario;
- target reader, reader task, channel, expected depth, and professional familiarity;
- dominant language of the primary source, any explicit output-language request, and the resulting output language;
- source materials, any explicit or inherited output-format signal, chosen output format, and consequences of misunderstanding.

Ask only when one missing fact can materially change the structure, claim strength, tone, scope, or required action. Otherwise use a conservative assumption and state it outside the finished document when needed.

Record the result under `G1-task`. Do not proceed with an undefined target reader unless the task is low-risk and a conservative reader assumption is recorded.

### 2. Establish The Source Boundary

Before drafting or rewriting, inventory the information that cannot change:

- entities, events, dates, numbers, units, denominators, comparison bases, and metric definitions;
- definitions, scope, exclusions, constraints, ownership, commitments, and deadlines;
- observed facts, interpretations, causal claims, recommendations, disagreements, and unknowns;
- material claims and their supporting sources.
- every candidate or used visual, what it appears to claim, its original source, creator or agency when available, event context, and whether its identity and authenticity are verified.

If evidence is incomplete, shorten or qualify the claim. Do not make thin source material appear complete.

When visuals are involved, follow [references/visual-evidence.md](references/visual-evidence.md). Search-result metadata, aggregator captions, filenames, and alt text are discovery clues only. They do not verify a person's identity, an event, or an image's origin.

Record the result under `G2-source`. A missing source for a material claim is a hard failure, not a style signal.

### 3. Route The Document

Follow [references/scenario-routing.md](references/scenario-routing.md). Route by the reader's main task rather than the title, filename, or existing headings. Record the selected route internally; do not print it in the artifact.

Load the matching scenario reference and use its:

- required content;
- recommended relationship between sections;
- evidence requirements;
- failure modes;
- acceptance questions.

Record each applicable requirement under `G3-route`. Reading the scenario module is not completion; its required content and acceptance questions must be checked against the output.

### 4. Draft For The Reader

Build the document from the selected scenario profile. Then apply [references/output-standards.md](references/output-standards.md):

1. practical information first;
2. reader perspective;
3. progressive disclosure;
4. natural, audience-fit language;
5. evidence and calibrated certainty;
6. scope and assumption fidelity;
7. useful structure and concision;
8. action proportional to evidence.

For every finished artifact, also apply the portable presentation baseline in
[references/format-decision.md](references/format-decision.md). When the selected format
is not HTML, translate those principles into the target platform's native
headings, spacing, colors, tables, callouts, figures, captions, and source
components; do not copy HTML-only markup, assets, or runtime requirements.

For mixed audiences, make the opening understandable without specialist knowledge and place specialist detail later. Do not inflate a simple output into a report.

Choose section names and visual forms from the content. For every finished artifact, first follow [references/visual-decision.md](references/visual-decision.md): state the reader question, compare against concise prose, and apply the deletion test. Use no visual when removal would not make the target reader slower, less accurate, or less able to verify the answer. If the decision retains or reviews a material visual form, load [references/visual-communication.md](references/visual-communication.md) before selecting or implementing its form, geometry, scale, color, layout, or responsive behavior. Do not convert two to four simple conclusions into one card each merely to make the page look richer; keep them as a list or unframed rows unless repeated fields create a real comparison task. Unless the user explicitly requests a named format, avoid generic display labels such as `30秒判断`, `一张图读懂`, `读者视角`, `一句话总结`, or repeated English kickers. Replace them with content-specific language rather than merely finding new synonyms.

For any document with visible structure, follow the classification and heading proposition map in [references/output-standards.md](references/output-standards.md). Content-bearing headings must compress what the section establishes; conventional navigation labels are allowed only when useful; decorative importance or suspense labels must be removed or rewritten. Run a heading-only readback before delivery.

When a title or subtitle is needed, follow [references/title-design.md](references/title-design.md). Inventory the concrete object, central verified result or relationship, scope, and evidence boundary; then generate and compare at least three internal candidates. Prefer the candidate with the highest information value after every factual hard gate passes. Treat the title as a factual promise about the document, not a place to add unsupported certainty, hidden intent, or generic suspense.

Record all eight standards under `G4-build`. A standard cannot be omitted because another standard appears more important. Resolve conflicts using the priority in the Core Contract.

### 5. Diagnose And Revise

For an existing document, follow [references/diagnosis-and-revision.md](references/diagnosis-and-revision.md). For both existing and newly drafted documents, process review signals through [references/signal-processing.md](references/signal-processing.md).

- Fix hard failures first: factual drift, unsupported claims, scope changes, ambiguous ownership, missing critical context, or unsafe action.
- Then fix reader-task failures: wrong scenario, hidden main information, missing tradeoff, missing boundary, or unusable steps.
- Treat sentence length, terminology density, passive voice, headings, and formulas as review signals, not automatic errors.
- Make local edits when local edits are sufficient. Rebuild the whole structure only when the current structure cannot serve the reader task.

Record each signal under `G5-signals` with its location, trigger, context judgment, reader impact, decision, action, and verification. A confirmed signal requires a proportional action or an explicit reason for no change. A dismissed signal requires a reason. An unresolved signal that could materially change understanding must be surfaced to the user.

If the user asks only for diagnosis, do not silently rewrite the document. If they ask for a rewrite, return the usable result before a concise explanation.

### 6. Verify The Finished Output

Run the hard checks in [references/output-standards.md](references/output-standards.md). For high-risk work or explicit evaluation, also follow [references/evaluation.md](references/evaluation.md).

Verify that:

- every critical fact and number matches the source;
- the output language follows the user's explicit request or, when none exists, the dominant language of the primary source;
- the output format follows the user's explicit choice or existing target artifact; when neither exists, a finished document is self-contained HTML;
- a non-HTML artifact preserves the target platform's native behavior while applying the portable HTML presentation baseline;
- every material claim has adequate support and calibrated wording;
- no definition, distinction, scope boundary, responsibility, or commitment drifted;
- the selected scenario's required content is present;
- the target reader can find the main information quickly;
- no paragraph, heading, table, or repeated conclusion can be removed without reducing understanding or actionability;
- required actions are clear and do not exceed evidence or authority.
- headings, table labels, placeholders, and revised passages contain no obvious typo, truncation, or malformed text introduced during revision.
- every used visual has an explicit provenance decision; real-person and real-event images pass identity and context checks; generated or conceptual visuals are visibly labeled near the asset and cannot be mistaken for documentary evidence.
- every retained visual has a valid reader job and passes the visual need and deletion tests; the selected form, geometry, scale, order, labels, and omissions do not change the source-supported conclusion.
- chart context includes the applicable unit, denominator, period, baseline, definition, missing-data treatment, and uncertainty; quantitative bars start at zero, 3D is absent, and a dual axis is rejected unless its essential relationship survives explicit review.
- every derived chart annotation, difference, rate, average, share, and tooltip value is recomputed from the source with the correct denominator or interval count.
- color has a defined semantic role, remains consistent, meets applicable contrast requirements, and is never the only channel for a decision-critical distinction.
- headings describe the document's actual content rather than the writing method; repeated cards, labels, questions, and summaries each have a distinct reader function rather than forming a default template.
- every visible structural string is content-bearing or necessary navigation; no importance-only or suspense-only label remains; the heading-only readback exposes the document's object, main conclusion or development, reasoning path, and material boundary or action.
- the title names the actual object and gives an accurate expectation of the document's central relationship, change, decision, or reader value; title and subtitle do not duplicate or overstate the body.
- every material title claim maps to the body and source; no false, exaggerated, irrelevant, or unfulfilled click-inducing promise remains.

Record the result under `G6-verify`. Recheck every passage changed because of a signal and rerun any affected hard gate, output standard, and scenario acceptance question. Do not use a better formula score as proof that the revision is better.

For file or online outputs, verify the actual rendered artifact in proportion to risk before claiming completion.

## Output Modes

### Create Or Rewrite

Return one recommended finished version by default. Add a short `发送前提醒` only when a material gap, unsupported claim, ambiguity, emotional escalation, or likely reader misunderstanding remains. Offer alternatives only when directness, warmth, or context level creates a useful choice without changing the underlying position.

For a finished document or report, use self-contained HTML by default. Treat a
direct format request, a request to edit or append to an existing artifact, or
a request to return only chat text as an output-format signal and honor it.
When editing an existing artifact, preserve its format, unrelated content, and
unrelated formatting unless a broader redesign or conversion is authorized.

For Feishu/Lark, Word, Markdown, plain text, slides, or another explicitly
selected format, use that format's native components and delivery workflow.
Carry over the portable visual and structural principles from
[references/format-decision.md](references/format-decision.md), but never create an HTML
intermediate merely to imitate its appearance.

### Self-Contained HTML

When the finished artifact is HTML by default or explicit request, load and follow
[references/html-output.md](references/html-output.md). Use the bundled
scaffold, fonts, optional chart and diagram runtimes, and static validator from
this skill. Do not require or delegate to a separately installed HTML-report
skill. Preserve the selected scenario structure and Reader's Seat evidence
rules; HTML is the rendering layer, not a second content template.

### Diagnose

Lead with the overall judgment, then list only material issues in this order:

1. hard failures;
2. scenario-fit failures;
3. output-standard failures;
4. optional style refinements.

For each issue, state the affected passage or pattern, why it matters to the reader, and the smallest effective fix. Do not turn preference into a rule.

### Compare

Freeze the reader, scenario, task, source, and scoring rule before comparing versions. Reject any version that fails a hard gate before calculating reader outcome scores. Never compare aggregate scores across scenarios or audiences.

## Maintenance Contract

Treat [config/skill-contract.json](config/skill-contract.json) as the capability
and version contract, and [config/module-profiles.json](config/module-profiles.json)
as the deterministic loading contract. Do not remove an existing route, hard
gate, output standard, output mode, or implementation module to reduce context;
move detail behind a decision gate while keeping it resolvable before use.

When changing the skill:

1. change only the affected scenario or shared standard;
2. update the contract version according to behavior impact;
3. add or update a regression case under `evals/`;
4. run `python3 scripts/validate_skill.py` and the official `quick_validate.py`;
5. run the affected frozen case through `scripts/run_evals.py` without leaking
   the expected answer to the producer;
6. forward-test at least one affected case and one unaffected scenario in fresh
   contexts;
7. for a cross-agent stability claim, test at least two explicitly named agent
   hosts, run at least three repetitions per host and model, use semantic
   judging, combine runs with `scripts/run_evals.py matrix`, and report the
   worst run.

Do not duplicate a rule across scenario files. Shared rules belong in `references/output-standards.md`; scenario-specific rules belong in exactly one scenario file.
