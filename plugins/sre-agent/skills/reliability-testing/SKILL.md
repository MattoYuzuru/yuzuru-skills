---
name: reliability-testing
description: Design and run authorized behavioral, load, resilience, fault, security, and observability tests within an explicit envelope. Use when a system needs independent reliability or performance evidence.
---

# Reliability Testing

Read `references/test-envelope.md` before load, stress, soak, spike, chaos, failover, destructive
migration, security regression, staging, or production verification.

## Workflow

1. Define requirement, target, owner authorization, environment, isolation, data, and side effects.
2. Define rates, duration, concurrency, fault, resource, stop conditions, monitoring, rollback, and
   cleanup.
3. Establish expected behavior and observability before execution.
4. Start with the smallest test that can falsify the claim.
5. Execute once within the envelope; stop on defined safety signals.
6. Correlate client results with server logs, metrics, traces, queues, database, dependencies, and
   release markers.
7. Restore state and verify cleanup.
8. Report exact limits, findings, confidence, and untested behavior.

## Guardrails

- Never run uncontrolled DDoS-like traffic.
- Never target third-party or public production endpoints without explicit exact authorization.
- Do not infer capacity from average latency alone; include tail, errors, saturation, queues, and
  recovery.
- Fault injection needs blast-radius isolation and rollback.
