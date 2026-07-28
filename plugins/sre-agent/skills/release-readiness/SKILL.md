---
name: release-readiness
description: Decide whether a release candidate is ready using requirements, end-to-end behavior, migrations, rollback, observability, and residual-risk evidence. Use when the user asks for an independent go/no-go assessment.
---

# Release Readiness

Read `references/readiness-gates.md` before issuing a go, conditional-go, or no-go result.

## Workflow

1. Pin the candidate revision, artifacts, environments, requirements, scope, and release method.
2. Validate the meaningful end-to-end path through entry, authn/authz, validation, business logic,
   persistence, events, downstream effects, UI, observability, failures, and cleanup.
3. Review unit/integration/contract/E2E evidence, known findings, migrations, compatibility,
   performance, security, backup/restore, rollback, and operational readiness.
4. Confirm deployment markers, health signals, dashboards/alerts, runbooks, ownership, and stop
   criteria exist where required.
5. Separate blockers, accepted residual risk, missing evidence, and post-release monitoring.
6. Issue go, conditional go, or no-go with explicit decision owners and conditions.

## Guardrails

- Passing unit tests, a successful build, or a written plan is insufficient alone.
- Do not transfer staging evidence to production without stating the gap.
- Do not silently accept unresolved high-impact findings.
- Readiness is not deployment or production verification.

## Output

Return candidate revision, environments, gates and evidence, blockers, residual risks, rollback and
observability readiness, unverified areas, decision, conditions, and owners.
