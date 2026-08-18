# Reader's Seat

> A reader-first AI writing skill that turns work material into documents people can understand, judge, and act on.

[中文说明](README.zh-CN.md) · [More examples](examples/quick-start.md)

[![Version](https://img.shields.io/badge/version-0.15.2-2563EB)](SKILL.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-16803C.svg)](LICENSE)
[![Validate](https://github.com/BobbyYue/reader-seat/actions/workflows/validate.yml/badge.svg)](https://github.com/BobbyYue/reader-seat/actions/workflows/validate.yml)

## The Problem It Solves

AI-generated documents can sound polished while leaving the reader to work out the conclusion, supporting evidence, uncertainty, and next step.

Reader's Seat restructures the material around what the reader needs to understand or decide. It preserves facts, numbers, scope, and uncertainty instead of making the content sound stronger than the evidence allows.

| Typical input | What Reader's Seat makes clear |
| --- | --- |
| “In the release week, 7-day retention fell from 42% to 38%, so the release probably caused it.” | Retention fell by 4 percentage points in the same week; the timing is known, but causality is not. Segmented or comparison data is still needed. |
| A half-year summary listing meetings, dashboards, and experiments | What work was done, what was delivered, what result is actually supported, and what impact is still unknown. |
| “Option A is better because it is more advanced.” | Which constraints each option satisfies, the trade-offs, decision conditions, risks, and missing rollback information. |

## When To Use It

| Your material | What the reader needs |
| --- | --- |
| News or industry research | Confirmed facts, source status, timing, and unknowns |
| Technical proposals | Constraints, options, trade-offs, risks, and rollback conditions |
| Product documents | Intended users, problem, supported capabilities, and limits |
| Business updates or performance reviews | Work, deliverables, outcomes, risks, and next steps |
| Data analysis or research | Metric definitions, magnitude, evidence, uncertainty, and causal boundaries |
| SOPs or runbooks | Preconditions, steps, success signals, exceptions, and recovery paths |

Reader's Seat is not intended for short chat-message polishing, unsupported content expansion, or visual decoration without a document task.

## Install In Codex

```bash
git clone https://github.com/BobbyYue/reader-seat.git ~/.codex/skills/reader-seat
```

Start a new Codex task, then call the skill explicitly:

```text
Use $reader-seat to rewrite this analysis for a product leader.
Preserve the metrics, magnitude, time period, and uncertainty.
Separate observed facts, plausible explanations, causal claims, and unknowns.
Return Markdown.
```

Requests that clearly ask for a reader-first or reader-friendly work document may also trigger the skill automatically in supported hosts.

## What To Provide

You usually need only four inputs:

```text
Material: the source text, data, or links
Reader: who will use the document and what they already know
Reader task: what they need to understand, judge, or do
Format: HTML, Feishu/Lark, Word, Markdown, plain text, or another target
```

See [ready-to-use prompts](examples/quick-start.md) for news, technical proposals, product documents, business updates, data analysis, and SOPs.

## Output Defaults

- Facts, quantities, definitions, ownership, commitments, and uncertainty are preserved.
- Observation, interpretation, causality, advice, and unknowns remain distinguishable.
- Titles state supported information instead of manufacturing suspense.
- Visuals are used only when they reduce the effort required to locate, compare, understand, or verify information.
- A new finished document defaults to self-contained HTML unless another format is requested.
- Output follows the source material's dominant language unless the user requests a different language.
- Reader's Seat never publishes, overwrites, or sends content without explicit authorization.

## What's Included

| Folder | Function |
| --- | --- |
| `.github/` | Runs the repository checks on every push and pull request. |
| `agents/` | Helps supported agent hosts recognize and present Reader's Seat. |
| `assets/` | Provides the self-contained HTML template, local fonts, and chart and diagram runtimes. |
| `config/` | Defines supported document scenarios, module-loading profiles, agent adapters, and the enforceable skill contract. |
| `evals/` | Provides frozen trigger, behavior, and cross-agent test cases with judging criteria. |
| `examples/` | Contains prompts that users can adapt directly to common document tasks. |
| `references/` | Provides the detailed writing rules selected for each scenario, format, title, evidence, and visual need. |
| `scripts/` | Validates the skill, selects the required modules, creates HTML report scaffolds, and runs evaluations. |

## Other Agent Hosts

Place the repository where the host can read it and explicitly load `SKILL.md`. Automatic discovery differs across hosts. See [Agent Portability and Stability](references/agent-portability.md) for manual and command-line evaluation options.

The repository does not claim cross-agent stability until at least two named hosts pass the same frozen cases.

## Validate And Update

```bash
cd ~/.codex/skills/reader-seat
git pull
python3 scripts/validate_skill.py
```

Third-party font and visualization licenses are listed in [Third-Party Notices](assets/html/THIRD_PARTY_NOTICES.md).
