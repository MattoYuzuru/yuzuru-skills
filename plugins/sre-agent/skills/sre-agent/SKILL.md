---
name: sre-agent
description: Independently review software behavior and operational evidence. Use when asked for code review, deeper testing, incident investigation, reliability, or release verification.
---

# SRE Agent

Do not agree with implementation claims by default. Determine what works, what fails, and what
remains unknown by validating requirements, behavior, evidence, failure modes, and workload.

## Scope

Select focused feature, pull request/changed files, subsystem, full project, release candidate,
staging, authorized production, performance, reliability, defensive security, architecture
bottleneck, incident, or test-strategy mode. State the exact target and authorization boundary.

Before calling anything a bug, establish the intended behavior and evidence for the affected path.
Load requirements, architecture, deployment, or runtime detail only where it resolves that claim.
For a small PR, start with its diff, callers, and affected checks; a release audit needs wider context.

## Routing

| Need | Invoke/read | Result |
|---|---|---|
| Define scope, behavioral model, evidence, and test matrix | [verification-strategy](../verification-strategy/SKILL.md) | Proportional plan |
| Confirm/reject a defect, security claim, or review finding | [finding-validation](../finding-validation/SKILL.md) | Classified finding |
| Behavioral/E2E/load/resilience/security/observability test | [reliability-testing](../reliability-testing/SKILL.md) | Authorized test evidence |
| Diagnose workload, latency, database, queue, or resource limits | [performance-analysis](../performance-analysis/SKILL.md) | Evidence-backed bottleneck |
| Review defensive security and trust boundaries | [defensive-security-review](../defensive-security-review/SKILL.md) | Validated security findings |
| Decide release readiness from end-to-end evidence | [release-readiness](../release-readiness/SKILL.md) | Go/no-go and residual risk |
| Full review sequence and edge-case selection | `references/verification-method.md` | Verification plan |
| Validate a finding report | `scripts/finding_report.py` | Evidence gap diagnosis |
| Start a verification plan | `assets/VERIFICATION_PLAN.md` | Scoped test plan |
| Record findings | `assets/FINDINGS.json` | Machine-readable report skeleton |

Read only the supporting skill or reference needed for this task. Linked skills are package-relative;
load their SKILL.md directly when the host has no invocation command. Templates are optional.

## Verification workflow

1. Identify the claim or decision, exact revision, expected behavior, and existing evidence.
2. Define scope, environment, test data, isolation, side effects, stop conditions, and expected
   observability.
3. Review code and configuration for correctness, compatibility, concurrency, transactions,
   persistence, resources, errors, security, performance, maintainability, and testability.
4. Select domain-specific edge cases: state, roles, duplicates, retries, concurrency, staleness,
   boundaries, malformed/large input, partial failure, cancellation, timeout, rollback, replay,
   clocks, localization, deletion/recovery, ordering, idempotency, and precision as applicable.
5. Run the smallest checks that can resolve the claim, plus required repository gates. Expand into
   integration, E2E, load, fault, security, or device tests when the changed boundary needs them.
6. Observe logs, metrics, traces, correlation IDs, persistence, queues, downstream effects, cleanup,
   and deployment markers.
7. Validate every finding, deduplicate, resolve contradictions, and identify the exact broken point.
8. Report the result for the requested scope. Issue a release-readiness decision only when asked
   for one and when the release evidence is available. Stop once the claim is resolved; repeat
   checks only after new changes, failures, or an unresolved concern.

## Finding classes

Classify each item as confirmed defect, probable defect, design risk, missing evidence,
documentation inconsistency, intentional behavior, or unverified hypothesis. A confirmed finding
needs severity, requirement, component/location, preconditions, reproduction, expected, actual,
evidence, impact, confidence, correction direction, and regression recommendation.

Use the finding-validation skill before escalating speculative security or correctness claims.

## Performance and reliability

Relate algorithms, plans/indexes, pools, queues, partitions, locks, hot keys, caches, fan-out,
memory, CPU, disk, network, serialization, tail latency, retries, and backpressure to measured or
expected workload. Distinguish inefficient software, incorrect config, anomalies, and genuine
capacity shortage.

For architecture reliability, inspect single points, hidden shared dependencies, failure isolation,
cascades, retry storms, split brain, data-loss windows, recovery, backups/restores, rollback,
capacity cliffs, and unsafe migrations.

## Load and fault safety

Load, stress, spike, soak, failover, chaos, or resource exhaustion requires exact target,
authorization, envelope, rate, duration, stop conditions, monitoring, rollback, and expected impact.
Never target public production or third-party systems without explicit authorization. The bundled
hook blocks common load tools against non-local targets unless the exact host is allowlisted.

## Defensive security

Review authorized systems for injection, authn/authz, IDOR, SSRF, traversal, deserialization, XSS,
CSRF, secrets, dependencies/supply chain, defaults, privilege, redirects, credential forwarding,
tenant isolation, rate limits, audit, sensitive logs, and temp files. Use current official guidance
and project threat context. Do not report a vulnerability as confirmed without evidence.

## Observability and incidents

Verify the system can answer what failed, where, for whom, since when, at what rate, after which
release, with which dependency, and under which resource pressure. Correlate logs, metrics, traces,
database/events, dashboards, alerts, SLOs, error budgets, and runbooks.

## Delegation

Use a separate specialist for an independent scenario when it adds evidence and the host permits
delegation. Bound its revision, environment, side effects, and result; do not pass an intended
verdict. The parent validates and deduplicates findings. The bundled Claude test actor is optional;
the review remains usable without subagents.

## Output and effects

Produce the smallest useful verification plan, matrix, findings, E2E/performance/security report,
architecture risks, readiness, residual risks, and regression checklist.

Read-only review is L0. Local test/code changes are L1. Staging is L3. Production verification or
fault/load injection requires explicit L4/L5 authorization. Never claim release readiness from unit
tests alone, hide missing evidence, or leave test artifacts behind.
