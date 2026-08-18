# Reader's Seat Prompt Examples

## Minimal Request

```text
Use Reader's Seat to organize these materials.
The reader is a manager seeing the project for the first time and needs to judge
current progress, major risks, and the next decision.
```

## More Reliable Request

```text
Material: source text, data, links, or files
Reader: role, subject familiarity, and existing context
Reader task: what they need to understand, judge, or do
Format: HTML, Feishu/Lark, Word, Markdown, plain text, or another target
```

## News And Industry Research

```text
Use Reader's Seat to summarize these industry updates in Markdown.
The readers are product and strategy teams. Separate official confirmation,
media reporting, and unverified claims. Preserve event dates and do not force
an action recommendation when the evidence does not support one.
```

## Technical Proposal

```text
Use Reader's Seat to turn these requirements, architecture notes, benchmarks,
and migration concerns into a technical decision document. The reviewers need
to compare constraints, options, trade-offs, risks, and rollback conditions.
Mark missing information instead of choosing an unsupported solution.
```

## Product Document

```text
Use Reader's Seat to rewrite this product introduction. Explain the intended
users, problem, supported capabilities, release scope, and current limits.
Remove unsupported claims such as “leading” or “highly efficient.”
```

## Project Progress Or Performance Summary

```text
Use Reader's Seat to turn these weekly reports, project documents, and review
notes into a half-year work summary for a manager. Separate activity,
deliverables, and outcomes. Do not turn work volume into business impact when
the source does not contain impact evidence.
```

## Data Analysis

```text
Use Reader's Seat to create a self-contained HTML analysis report from these
metric definitions, query results, charts, and methodology notes. The reader
needs the metric change, evidence quality, unverified explanations, uncertainty,
and the next validation. Preserve definitions, magnitude, denominator, period,
and causal boundaries.
```

## SOP Or Runbook

```text
Use Reader's Seat to turn these existing steps into an SOP a new teammate can
execute. Preserve the known order and include prerequisites, success signals,
exception paths, recovery, and escalation. Mark missing permissions, commands,
and owners as unresolved.
```

## Request Another Output Language

By default, the output follows the source material's dominant language. To
translate, state the target language directly:

```text
Use Reader's Seat to turn this English technical proposal into a Chinese review
document. Keep code, commands, API names, and product names unchanged.
```

## Diagnose Without Rewriting

```text
Use Reader's Seat to diagnose whether this report helps its target reader form
the right judgment. List only material problems in facts, evidence, structure,
and action boundaries, with the smallest useful fix. Do not rewrite the report.
```
