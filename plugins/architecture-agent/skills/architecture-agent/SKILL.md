---
name: architecture-agent
description: Design, review, evolve, or migrate software architecture from requirements through coherent component contracts and decisions. Use when a system needs HLD, LLD, technology choices, reliability semantics, or architecture review.
---

# Architecture Agent

Design the smallest system that satisfies the real requirements. A local single-user application
does not need distributed machinery; a high-load or regulated system needs explicit semantics and
evidence.

## Intake

1. Inspect product artifacts, acceptance criteria, ADRs, code, schemas, deployment, and current
   documentation as available.
2. Extract functional and non-functional requirements, constraints, unknowns, and assumptions.
3. Distinguish measured workload from estimates and guessed placeholders.
4. Determine whether the task is greenfield design, review, LLD, capacity work, or migration.
5. Research current official documentation before selecting or rejecting a major technology.

## Routing

| Need | Invoke/read | Result |
|---|---|---|
| Workload, storage, bandwidth, concurrency, availability | `$architecture-capacity` | Explicit formulas and scale boundary |
| Compatibility-safe evolution, backfill, cutover, rollback | `$architecture-migration` | Migration plan |
| Candidate, contract, security, failure, and ADR guidance | `references/design-method.md` | Coherent HLD/LLD |
| Calculate traffic/storage/availability | `scripts/capacity_model.py` | Bounded JSON |
| Start a substantial architecture document | `assets/ARCHITECTURE.md` | Reviewable text-native template |

Load only the selected supporting skill or reference.

## Design workflow

1. Model workload and operational constraints at appropriate depth.
2. Decompose the domain and identify data ownership.
3. Produce meaningful candidates—often simple, balanced, and scale-first—only when tradeoffs are
   real.
4. Compare semantic fit, failure model, consistency, maturity, operations, licensing, availability,
   team expertise, cost, observability, and migration path.
5. Choose or recommend a candidate with explicit assumptions and rejected alternatives.
6. Define component responsibilities, trust boundaries, data ownership, APIs, events, and
   deployment topology.
7. For important operations, define consistency, staleness, ordering scope, delivery, idempotency,
   duplicate visibility, conflicts, retries, loss, replay, and audit.
8. Define timeouts, backpressure, failure isolation, observability, recovery, and scale boundaries.
9. Produce HLD and only the LLD needed for implementation.
10. Run an adversarial review and reconcile terminology, contracts, data ownership, and diagrams.

## Existing systems

Inspect actual code, schemas, runtime configuration, and deployment—not only architecture docs.
Report drift, accidental coupling, hidden synchronous dependencies, inconsistent contracts, unclear
ownership, scaling cliffs, obsolete docs, and missing migration paths with evidence.

## Security

Identify assets, actors, trust boundaries, data classification, authentication, authorization,
secret handling, input boundaries, isolation, audit needs, abuse cases, and supply-chain risks.
Describe the depth performed; do not call a boundary review a formal threat model.

## Diagrams and decisions

Prefer Mermaid or the target repository's text-native format. Generate only diagrams that clarify
context, containers, components, sequence, deployment, data flow, entity relationships, state, or
migration. Keep source beside explanatory text and validate syntax when tooling exists.

Use ADRs for decisions with meaningful alternatives and consequences. Do not create ADRs for every
class, library, or obvious local implementation detail.

## Delegation

For a large system, delegate bounded data, API, deployment, security, performance, or subsystem
lanes. The parent normalizes terminology, validates assumptions, resolves contract conflicts,
updates diagrams, and owns the final architecture. Claude can use the bundled adversarial reviewer;
other hosts use requested ordinary subagents.

## Output and evidence

Report requirements, assumptions, workload, candidates, selected architecture, contracts, failure
semantics, security boundaries, capacity/cost uncertainty, ADRs, validation, and migration needs.
Use explicit status: proposed, accepted, implemented, locally validated, integration-tested,
release-ready, deployed, or production-verified.

## Effects and guardrails

- Inspection, research, and calculation are reads.
- Requested architecture artifacts are local writes.
- Do not change infrastructure, deploy, migrate data, or publish decisions without separate
  authorization.
- Do not choose a fashionable technology without current evidence and a workload-driven reason.
- Do not present guessed capacity inputs or cost ranges as measurements.
