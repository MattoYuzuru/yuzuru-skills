---
name: architecture-migration
description: Plan measured compatibility-safe system and data migrations with backfill, cutover, rollback, and decommissioning. Use when architecture must evolve without unacceptable downtime or data loss.
---

# Architecture Migration

Read `references/migration-phases.md` for storage replacement, monolith decomposition, regional
move, queue introduction, or growth-driven redesign.

## Workflow

1. Define the measured trigger, target requirements, protected behavior, and acceptable risk.
2. Capture current data, traffic, dependencies, ownership, and failure/recovery behavior.
3. Establish compatibility boundaries and observability before changing traffic or data.
4. Plan schema/contract compatibility, shadowing, dual read/write only when justified, backfill,
   reconciliation, cutover, rollback, and decommissioning.
5. State idempotency, ordering, data-loss windows, retry, and partial-failure behavior.
6. Define stage gates, stop conditions, health signals, and exact success criteria.
7. Estimate migration load and ensure it cannot starve production.
8. Remove the old path only after retained rollback windows and evidence justify it.

## Guardrails

- Do not introduce dual writes without conflict ownership and reconciliation.
- A backup is not a rollback until restore behavior and time are known.
- Avoid big-bang cutover when a compatibility phase can reduce blast radius.
- Do not decommission evidence, old data, or rollback paths prematurely.
