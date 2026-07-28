---
name: implementation-planning
description: Acquire engineering context and create an actionable implementation plan with scope, risks, tests, and validation commands. Use when a nontrivial coding task needs a plan before edits or an approved autonomous implementation.
---

# Implementation Planning

Read `references/plan-contract.md` for a multi-module, compatibility-sensitive, data, concurrency,
performance, or unfamiliar-technology change.

## Workflow

1. Locate the acceptance contract and related product/architecture decisions.
2. Inspect current implementation, tests, style, ownership, build, and recent related changes.
3. State objective, current behavior, proposed behavior, affected areas, risks, assumptions, and
   explicit exclusions.
4. Identify compatibility, migration, rollback, security, concurrency, and data implications.
5. Select behavior-relevant tests and exact validation commands.
6. Identify unresolved decisions that require user or owner input.
7. Mark whether the plan is approved, autonomous under an explicit request, or blocked on a
   material choice.

## Guardrails

- Do not turn planning into speculative architecture.
- A file list without behavior, risk, and validation is not an implementation plan.
- Do not ask for approval repeatedly after the approved scope remains unchanged.
- Re-plan when evidence invalidates a material assumption.
