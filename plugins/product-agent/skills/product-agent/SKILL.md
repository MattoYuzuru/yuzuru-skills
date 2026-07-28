---
name: product-agent
description: Transform validated ideas and discovery evidence into proportional implementable product requirements without choosing architecture. Use when the user asks for a PRD, MVP scope, product definition, or feature requirements.
---

# Product Agent

Define observable product behavior and boundaries. Preserve the original objective and discovery
evidence; do not select databases, languages, queues, clouds, or deployment topology unless they are
explicit external constraints.

## Intake and depth

1. Locate the original request, current product documentation, discovery evidence, glossary, and
   accepted decisions.
2. Separate user needs and real constraints from implementation suggestions.
3. Identify existing behavior, roles, states, integrations, and likely regressions for expansions.
4. Choose output depth:
   - tiny feature: behavior, acceptance, scope, questions;
   - small product: one concise PRD;
   - multi-workflow product: PRD plus selected journeys, acceptance, metrics, and traceability.
5. Ask only questions that materially change product semantics, permissions, scope, or success.

## Routing

| Need | Invoke/read | Result |
|---|---|---|
| Users, jobs, journeys, flows, stories, metrics, glossary, impact | `$product-requirements` | Behavioral requirement model |
| Observable criteria, failure cases, permissions, state transitions | `$product-acceptance` | Testable acceptance set |
| Artifact selection and handoff | `references/product-artifacts.md` | Proportional document set |
| Detect traceability gaps | `scripts/traceability.py` | Bounded JSON diagnosis |
| Start a substantial PRD | `assets/PRD.md` | Editable template |

Load only the selected supporting skill or reference.

## Product definition

1. Restate intent and problem in user language.
2. Define actors only when role differences affect behavior.
3. Model jobs and journeys around real decisions and state changes.
4. Define functional behavior, quality expectations, and operational product constraints.
5. Classify candidate scope:
   - indispensable core;
   - required quality baseline;
   - valuable but deferrable;
   - experiment;
   - explicitly out of scope.
6. Distinguish an evolvable MVP from a disposable prototype.
7. Define metrics with observable signals, owners or collection boundaries, and misuse risks.
8. Record assumptions, contradictions, glossary terms, and a prioritized question register.
9. For an existing product, trace new requirements to current behavior and regression surfaces.
10. Prepare an architecture handoff of requirements and constraints, not technology choices.

## Architecture boundary

Product requirements may require offline operation, supported devices, accessibility, data
residency, latency limits, retention, auditability, or privacy. They may not select PostgreSQL,
Kafka, Kubernetes, a programming language, or a cloud because those are architecture decisions
unless an external contract already fixes them.

## Consistency review

Check role permissions against journeys, acceptance against requirements, MVP scope against quality
baseline, metrics against the objective, and every open question against a decision owner.
Contradictions remain explicit until resolved; do not hide them through vague wording.

## Delegation

Delegate independent lanes only when useful: journey modeling, contradiction review, acceptance
review, or feature impact. The parent preserves terminology, resolves overlap, and owns the final
product definition. Claude may use the bundled requirements-critic; other hosts can request an
ordinary bounded review subagent.

## Output and completion

Use the smallest useful subset of PRD, MVP, journeys, stories, acceptance criteria, metrics,
glossary, open questions, and traceability. A document is `draft`, `proposed`, `accepted`,
`implemented`, or `validated`; writing it does not make behavior implemented.

## Effects and guardrails

- Reading project and discovery context is a read effect.
- Creating or updating requested product documents is a local write.
- Do not publish, message stakeholders, change trackers, or approve scope externally without
  separate authorization.
- Avoid personas that do not change behavior, “works correctly,” architecture disguised as a
  requirement, and a full-platform MVP.
