# Technical Proposal And Architecture Decision

## Reader Task

Enable reviewers and implementers to understand the problem, constraints, options, decision rationale, consequences, and safe implementation path.

## Required Content

- problem, current impact, objective, and explicit non-goals;
- functional and non-functional constraints;
- viable options, including the status quo when relevant;
- decision criteria and material tradeoffs;
- chosen direction, rationale, confidence, and unresolved questions;
- implementation stages, ownership, dependencies, observability, failure handling, and rollback;
- security, privacy, reliability, performance, cost, and migration impact as applicable.

## Recommended Relationship

`problem and goals/non-goals -> constraints and decision criteria -> options and tradeoffs -> decision and rationale -> implementation, monitoring, and rollback -> consequences and open questions`

Use a decision table when multiple options share comparable criteria. Keep low-level implementation detail after the decision path unless implementers are the only audience.

## Evidence Requirements

- Link requirements, incidents, benchmarks, prototypes, or architecture constraints to the claims they support.
- Separate measured results from estimates and design assumptions.
- State test conditions, workload, scale, and confidence for performance claims.
- Record why rejected options were not selected, not merely that they were rejected.

## Common Failures

- solution presented before a stable problem definition;
- only one option, making the “decision” impossible to evaluate;
- tradeoffs hidden behind adjectives such as scalable, robust, or elegant;
- missing non-goals, migration cost, observability, or rollback;
- implementation plan mistaken for evidence that the design is correct;
- internal component detail obscuring the decision reviewers must make.

## Acceptance Questions

1. Can a reviewer reconstruct the problem and decision criteria?
2. Can they explain why the chosen option beats viable alternatives?
3. Are costs, constraints, risks, and confidence visible?
4. Can an implementer identify prerequisites, ownership, observability, and rollback?
5. Can a future reader understand why the decision was made at that time?

## Industry Basis

- Microsoft Azure Architecture Decision Record: https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record
- Google Technical Writing: https://developers.google.com/tech-writing/one/documents
