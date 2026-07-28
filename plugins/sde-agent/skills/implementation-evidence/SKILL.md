---
name: implementation-evidence
description: Normalize implementation and review evidence into explicit validation states and residual risks. Use when code changes need self-review, regression proof, migration validation, or a completion evidence bundle.
---

# Implementation Evidence

Read `references/review-contract.md` before an independent review or a release-readiness claim.

## Workflow

1. Re-read the acceptance contract and actual diff.
2. Review correctness, missed requirements, security, concurrency, errors, compatibility, data
   integrity, complexity, tests, and docs.
3. Validate findings against code and behavior; reject generic or unsupported comments.
4. Run exact relevant tests and record command, exit code, result, and environment.
5. Record changed artifacts, limitations, unverified environments, and residual risks.
6. Set release readiness only when evidence supports it.
7. Use the primary skill's evidence helper to detect contradictory status claims.

## Guardrails

- Compilation, lint, coverage, and unit tests are different evidence.
- Do not hide failed checks or unavailable environments.
- A reviewer finding is a hypothesis until validated.
- Do not call locally validated work deployed or production-verified.
