# Reading Path And Layout Contract

Use this module for every finished artifact. It governs how the selected scenario is turned into a readable native-format document without changing facts, scope, evidence, certainty, voice, or action boundaries.

## Plan Before Building

Record an internal layout plan before drafting the finished artifact:

- the reader and the decision, judgment, or task the artifact must support;
- the opening job: what the reader must understand first and why it matters;
- for every section: one reader question, one takeaway, the supporting evidence form, density (`light`, `balanced`, or `dense`), adjacent source or boundary, and the transition to the next reader question;
- the intended native output surface and the render evidence needed for verification.

The plan is not visible methodology. Do not expose these labels in the artifact unless they are natural content headings. Do not use the plan to add unsupported claims or force identical section shapes.

## Reading Path

- The opening lets the target reader form the main correct judgment quickly. Put the object and practical takeaway before background, method, and implementation detail.
- One section serves one primary reader job. Split a section when it asks the reader to make unrelated judgments; combine sections when they repeat the same conclusion.
- Headings carry the useful subject, finding, tension, decision, or question. A heading-only readback must expose the reasoning path without manufactured suspense or method labels.
- Put the section takeaway before dense support. Keep definitions, evidence, sources, uncertainty, and usage boundaries close to the claim they qualify.
- Use progressive disclosure as a relationship: quick judgment, essential support, optional detail. Do not turn it into fixed visible labels.

## Density And Rhythm

Tables, charts, diagrams, screenshots, code, and long lists are dense blocks. Do not place dense blocks back to back without a substantive bridge that tells the reader what changed, what comparison matters, or how the next block changes the judgment.

Do not create rhythm by alternating decorative cards. Vary form only when the reader job changes. Repeated callouts, cards, colored surfaces, or identical section templates are failures when removal does not reduce understanding or actionability.

Use four spacing relationships in the selected native format:

1. tight spacing binds a heading, label, caption, or evidence note to the item it belongs to;
2. normal spacing separates paragraphs or list items within one idea;
3. wider spacing separates subsections or changes of evidence form;
4. the widest spacing separates major sections or changes of reader question.

These are semantic relationships, not universal pixel values. HTML, Feishu/Lark, Word, Markdown, and slides must implement them with their strongest native primitives.

## Scenario Adaptation

- News: event and verified implication first; chronology and background later.
- Technical: decision or recommendation, constraints and tradeoffs, architecture evidence, rollout and rollback.
- Product: user problem and value, behavior and scope, evidence, adoption or operating implications.
- Business: result and variance, drivers, impact, action and owner, boundary.
- Analysis: question and conclusion, metric context, strongest evidence, explanation with calibrated certainty, action and uncertainty.
- Procedure: outcome and prerequisites, ordered actions, decision points, verification and recovery.

The active scenario remains authoritative. This module changes presentation, not the scenario's evidence or content contract.

## Hard Gates

A finished artifact is blocked when any of these conditions applies:

- no layout plan exists for the exact artifact;
- the opening hides the practical takeaway behind background or process;
- a section has no primary reader job or no takeaway before dense evidence;
- a material claim is separated from the evidence, source, definition, or boundary needed to interpret it;
- dense blocks are stacked without an interpretive bridge;
- heading-only readback does not reveal the document path;
- spacing, containers, or color obscure hierarchy or create repetitive visual noise;
- the actual target render has overlap, clipping, overflow, unreadable tables or figures, broken mobile/page behavior, or misleading emphasis.

These rules are mandatory runtime rules. They cannot be downgraded to style advice, marked not applicable for a finished artifact, or replaced by a self-review.

## Verification

Complete the `reading-path-layout` runtime rules with artifact-specific evidence in the semantic review. Then supply real target render evidence to the independent `structure-visual` reviewer. That reviewer separately checks reading path, heading information, claim-evidence adjacency, density and spacing, obstruction, table and visual readability, encoding, responsiveness, and accessibility.

After any structural or visual change, update the artifact hash and rerun all four reader-review dimensions. A local source or clean screenshot without an artifact-bound passing aggregate does not satisfy delivery.
