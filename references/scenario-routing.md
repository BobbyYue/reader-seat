# Scenario Routing

Route by the reader's primary task, not by the file title or current section names.

## Primary Routes

| Route | Reader's main question | Typical artifacts |
| --- | --- | --- |
| News | What happened, who confirms it, why does it matter, and what remains unknown? | News brief, industry update, policy or market digest |
| Technical | What problem and constraints exist, which option should be chosen, and how will it be implemented safely? | Technical proposal, RFC, architecture decision, design doc |
| Product | Who has what problem, what value is offered, what are the boundaries, and how is success measured? | Product introduction, launch note, PRD, feature proposal |
| Business | What was the goal, what happened, what is the impact, and what decision or support is needed? | Weekly/monthly update, project review, retrospective, performance summary |
| Analysis | What changed, what evidence supports it, how far can the explanation go, and what does it imply? | Data-analysis report, experiment readout, research memo |
| Procedure | What must be prepared, what steps should be followed, what proves success, and how can failure be recovered? | SOP, runbook, help article, operating guide |

## Decision Process

1. Identify the most important task the target reader must complete after reading.
2. Select the route whose main question best matches that task.
3. Ignore the existing format when it conflicts with the reader task. A slide titled “analysis” may still be a business decision update.
4. If two routes appear equally important, choose the route that controls the whole-document decision path as primary.
5. Apply a secondary route only to a clearly bounded subsection. Do not merge two full templates.

## Confidence And Clarification

Proceed without asking when the route is reasonably clear and a conservative choice will not change the claims or commitments.

Ask one concise question when a route choice changes any of the following:

- whether the document informs, recommends, or instructs;
- the required evidence standard;
- the expected decision or action;
- the body relationship, such as chronology versus option tradeoff;
- the acceptable level of technical detail.

Do not reveal a confidence score or routing label unless the user asks for diagnosis.

## Mixed Documents

- Technical proposal with an analysis section: use Technical as primary; apply Analysis evidence rules only to the analysis section.
- Business update announcing a product: use Business when the reader must judge progress or provide support; use Product when the reader must understand value or adoption.
- Industry brief with recommendations: use News when the main value is verified developments; use Analysis when the main value is interpreting evidence and recommending action.
- Procedure with rationale: use Procedure as primary; keep rationale brief unless it changes safe execution.

## Routing Failure Signals

- A news brief ends with recommendations but lacks source attribution or time.
- A technical proposal lists a solution but no problem, constraints, alternatives, or rollback.
- A product document lists features without a target user, problem, boundary, or success measure.
- A business update lists activities without goal-versus-result, impact, owner, or ask.
- An analysis report gives opinions without definitions, evidence, uncertainty, or alternatives.
- A procedure explains concepts but does not enable successful execution and recovery.
