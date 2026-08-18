# Reader's Seat

> A reader-first AI writing skill that turns scattered work material into complete documents people can understand, judge, and act on.

[中文说明](README.zh-CN.md) · [Prompt examples](examples/quick-start.en.md) · [Install](#install)

[![Version](https://img.shields.io/badge/version-0.16.0-2563EB)](SKILL.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-16803C.svg)](LICENSE)
[![Validate](https://github.com/BobbyYue/reader-seat/actions/workflows/validate.yml/badge.svg)](https://github.com/BobbyYue/reader-seat/actions/workflows/validate.yml)

**Source material → complete document → a reader can form the right judgment**

Reader's Seat works with any agent that can load a `SKILL.md` file or follow explicitly provided skill instructions. It is not tied to one model, vendor, or invocation syntax.

## What It Changes For The Reader

AI-generated documents can sound polished while still making the reader reconstruct what matters.

| Find | Verify | Act |
| --- | --- | --- |
| The main conclusion appears early. | Claims remain connected to evidence, scope, and uncertainty. | Decisions, open questions, and next steps stay within the evidence boundary. |

## See It In Practice

| Scenario | Source material | Finished document |
| --- | --- | --- |
| **Project progress** | Weekly reports, milestone plan, meeting notes, issue list, delivery data | **Project status brief**<br>Conclusion · milestones · schedule · blockers · decisions · supported next steps |
| **Data analysis conclusion** | Metric definitions, query results, charts, methodology notes, data limitations | **Analysis report**<br>Question · finding and magnitude · evidence · data context · alternative explanations · uncertainty · next validation |
| **Technical route** | Requirements, constraints, candidate architectures, benchmarks, costs, migration concerns | **Technical decision document**<br>Decision · constraints · option comparison · trade-offs · recommendation conditions · implementation impact · rollback · unresolved risks |

It also supports news and industry briefs, product documents, retrospectives, performance summaries, SOPs, runbooks, and help articles.

> [!NOTE]
> Reader's Seat is for substantive documents. Short workplace-message polishing, unsupported content expansion, and visual decoration without a document task are outside its main scope.

## Install

### Option 1: Ask Your Agent To Install It

Give an agent with file and shell access this instruction:

```text
Install Reader's Seat from https://github.com/BobbyYue/reader-seat.
Place it in the skill directory supported by this agent, keep the folder name reader-seat,
then confirm that SKILL.md can be loaded. Do not overwrite an existing installation without asking.
If Python is available, run python3 scripts/validate_skill.py after installation.
```

If the agent cannot install local skills, use the manual method below.

### Option 2: Clone It Manually

Set the skill directory used by your agent, then clone the repository:

```bash
AGENT_SKILLS_DIR="/path/to/your-agent/skills"
git clone https://github.com/BobbyYue/reader-seat.git "$AGENT_SKILLS_DIR/reader-seat"
```

After cloning, register that directory according to the agent's documentation or ask the agent to load `reader-seat/SKILL.md` explicitly. Automatic skill discovery differs across agents.

## Use It

You usually need only four inputs:

```text
Use Reader's Seat to create or rewrite this document.
Material: the source text, data, files, or links
Reader: who will use the document and what they already know
Reader task: what they need to understand, judge, or do
Format: HTML, Feishu/Lark, Word, Markdown, plain text, or another target
```

See [ready-to-use prompts](examples/quick-start.en.md) for common document scenarios.

## Output Defaults

| Format | Language | Evidence | Visuals |
| --- | --- | --- | --- |
| Self-contained HTML unless another format is requested | The source material's dominant language unless the user requests another | Facts, quantities, definitions, ownership, commitments, and uncertainty are preserved | Used only when they reduce the effort to locate, compare, understand, or verify information |

Reader's Seat does not publish, overwrite, or send content without explicit authorization.

<details>
<summary><strong>Repository structure, validation, and licenses</strong></summary>

| Folder | Function |
| --- | --- |
| `.github/` | Runs repository checks on every push and pull request. |
| `agents/` | Helps supported agent hosts recognize and present Reader's Seat. |
| `assets/` | Provides the self-contained HTML template, local fonts, and chart and diagram runtimes. |
| `config/` | Defines document scenarios, module-loading profiles, agent adapters, and the enforceable skill contract. |
| `evals/` | Provides frozen trigger, behavior, and cross-agent cases with judging criteria. |
| `examples/` | Contains prompts users can adapt to common document tasks. |
| `references/` | Provides detailed rules selected for each scenario, format, title, evidence, and visual need. |
| `scripts/` | Validates the skill, selects modules, creates HTML report scaffolds, and runs evaluations. |

Validate an installation:

```bash
python3 /path/to/reader-seat/scripts/validate_skill.py
```

Update an installation:

```bash
git -C /path/to/reader-seat pull
```

Third-party font and visualization licenses are listed in [Third-Party Notices](assets/html/THIRD_PARTY_NOTICES.md).

</details>
