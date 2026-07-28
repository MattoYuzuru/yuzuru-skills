# Deep Verification Method

## End-to-end path

Trace entry, authentication, authorization, validation, domain logic, persistence, event
publication, downstream effects, frontend behavior, observability, failure, rollback, and cleanup.
Report the exact point where the path diverges.

## Evidence hierarchy

Prefer reproducible runtime behavior, persisted state, structured logs/metrics/traces, deterministic
tests, code/config evidence, and documentation in that order appropriate to the claim. A missing log
is missing evidence, not proof that an event did not occur.

## Release readiness

Require accepted requirements, clean relevant tests, meaningful E2E, migration/data checks,
security and reliability risk review, deployment/rollback evidence, observability, known residual
risk, and verified target environments. A passing unit suite alone is insufficient.

## Finding discipline

Use domain-specific reproduction and reject false positives caused by incomplete context. Separate
confirmed, probable, risk, inconsistency, intentional, and unverified states.
