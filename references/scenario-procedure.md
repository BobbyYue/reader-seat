# Procedure, Runbook, Help Article, And SOP

## Reader Task

Enable the intended user to complete a task correctly, verify success, and recover safely from common failure.

## Required Content

- purpose, applicability, and excluded cases;
- prerequisites, permissions, inputs, environment, and safety warnings;
- ordered actions with one clear action per step;
- expected intermediate and final results;
- decision branches and exceptions at the point they matter;
- rollback, recovery, escalation, and support path;
- version, owner, or review date when operational drift is material.

## Recommended Relationship

`scope and prerequisites -> ordered steps -> expected result -> exception and recovery -> escalation or support`

Use numbered steps for sequence, bullets for non-sequential requirements, and tables only for genuine comparisons or mappings. Keep rationale near a step only when it prevents error.

## Evidence Requirements

- Verify commands, interface labels, permissions, paths, and expected outputs in the actual target environment when possible.
- Separate required steps from optional optimization.
- State destructive effects, reversibility, and data-loss risk before the relevant action.
- Avoid screenshots as the only source of truth; interfaces drift and images may be inaccessible.

## Common Failures

- missing prerequisite or permission;
- vague verbs such as “configure appropriately” or “handle as needed”;
- several actions hidden in one step;
- no signal that a step succeeded;
- error messages listed without recovery;
- screenshots, paths, or labels that no longer match the product;
- no rollback for a risky or destructive operation.

## Acceptance Questions

1. Can a first-time qualified reader identify prerequisites before starting?
2. Can they complete the task without guessing an action or value?
3. Does each important step have a visible success signal?
4. Can they recover from common failure without losing original work?
5. Are escalation, ownership, and version information available when needed?

## Industry Basis

- Google Technical Writing: https://developers.google.com/tech-writing/one/documents
- Microsoft Writing Style Guide: https://learn.microsoft.com/en-us/style-guide/brand-voice-above-all-simple-human
- GOV.UK User Needs: https://guidance.publishing.service.gov.uk/writing-to-gov-uk-standards/plan-manage-content/identify-user-needs/
