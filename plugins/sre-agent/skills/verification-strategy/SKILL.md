---
name: verification-strategy
description: Reconstruct requirements and design a proportional independent verification scope, behavioral model, evidence plan, and test matrix. Use when a feature, subsystem, pull request, or release needs a rigorous plan before tests run.
---

# Verification Strategy

Read `references/scope-model.md` before a subsystem, release, or multi-environment verification.

## Workflow

1. Identify the exact revision, component, environment, claim, authorization, and decision.
2. Reconstruct requirements, roles, permissions, states, data, events, failures, and architecture.
3. Separate accepted behavior from ambiguous docs and unverified assumptions.
4. Choose behavior-relevant unit, integration, contract, component, browser, E2E, migration,
   concurrency, performance, security, resilience, accessibility, and visual checks.
5. Define fixtures, isolation, observability, expected results, stop conditions, cleanup, and
   evidence retention.
6. Prioritize by impact, likelihood, change surface, and evidence gaps.
7. State what will remain unverified and how that affects the final claim.

## Guardrails

- Do not test every layer mechanically.
- Do not call an ambiguous requirement a defect oracle.
- Do not run writes, load, fault injection, staging, or production checks without their effect-level
  authorization.

## Output

Return scope, behavior model, matrix, environments, data, effects, stop/cleanup conditions,
observability, expected evidence, and exclusions.
