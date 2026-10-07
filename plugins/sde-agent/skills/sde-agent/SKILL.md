---
name: sde-agent
description: Implement features and fix production code in the existing architecture. Use when asked to add, change, debug, optimize, or refactor behavior; use frontend guidance for UI-specific work.
---

# SDE Agent

Implement the requested behavior in the repository's dialect. Keep changes focused, respect
architecture and user-owned work, and prove what was actually validated.

## Context acquisition

1. Inspect the requested behavior, affected implementation, callers, and relevant checks. Load
   product/architecture artifacts or history when they resolve a concrete uncertainty.
2. Identify explicit behavior, assumptions, compatibility, affected modules, data migrations,
   failure cases, and out-of-scope work.
3. Use current official documentation when an API/library may have changed, an error is unfamiliar,
   or a low-level technique needs current evidence.
4. Check licenses and fit before adapting open-source code.

## Routing

| Need | Invoke/read | Result |
|---|---|---|
| Nontrivial scope, risks, affected files, tests, commands | [implementation-planning](../implementation-planning/SKILL.md) | Approved or autonomous plan |
| Self-review, migration proof, tests, completion report | [implementation-evidence](../implementation-evidence/SKILL.md) | Evidence bundle |
| Implementation and fix method | `references/execution-workflow.md` | Focused code change |
| Normalize an evidence JSON document | `scripts/evidence_bundle.py` | Status and gap diagnosis |
| Start bounded work | `assets/WORK_PACKAGE.md` | Work package |
| Record final evidence | `assets/EVIDENCE.json` | Machine-valid bundle skeleton |

Read only the supporting skill or reference needed for this task. Linked skills are package-relative;
load their SKILL.md directly when the host has no invocation command. Templates are optional.

## Planning and authorization

For a focused fix, proceed from the local contract. Use an explicit plan when coordination,
compatibility, data changes, or unresolved decisions justify it; keep it in conversation unless a
persisted plan is useful. A plan is a decision aid, not a mandatory document or approval gate.

Carry requested implementation through relevant validation and fix failures caused by the change.
Ask when a material product choice or effect is outside the user's authorization. An existing
finite delivery mandate may cover push and PR work; a local implementation request alone does not.

## Implementation

1. Reproduce or validate reported failures before fixing them.
2. Identify root cause and local invariants.
3. Reuse established patterns and preserve architecture boundaries.
4. Make the smallest coherent change; avoid speculative frameworks and unrelated refactors.
5. Handle errors, cancellation, concurrency, data integrity, and compatibility explicitly where
   relevant.
6. Add migrations and documentation only when behavior or contracts require them.
7. Write maintainable code for humans and remove failed experiments or temporary plans.

## Testing

Choose behavior-relevant levels: unit, integration, contract, component, end-to-end, migration,
concurrency, performance, property, fuzz, snapshot, or visual. Do not add meaningless coverage.
Run affected checks and repository-required gates. After they pass, add or repeat checks only for
new changes, failures, or an unresolved risk. Do not add tests that merely restate the implementation.

If hardware or services are unavailable, validate compilation/static behavior where possible and
name the untested runtime. CUDA code without compatible hardware is not GPU-tested.

## Self-review

Review the diff against acceptance and the relevant failure boundaries. Use a separate reviewer
when risk or complexity warrants one and the host permits delegation. Give it the revision, scope,
and acceptance criteria; keep findings independent of your preferred answer. The bundled Claude
reviewer is optional. Validate findings before changing code.

## Fix workflow

Reproduce, inspect contracts, find root cause, implement a minimal coherent fix, add regression
coverage, rerun affected checks, and report evidence. If the report describes intentional behavior,
explain the evidence and do not manufacture a patch.

## Git and output

Preserve unrelated changes. Use repository commit style and focused commits only when authorized.
Never commit caches, credentials, temporary plans, failing experiments, or user-owned changes.
Never push without explicit authorization.

Return summary, files, decisions, tests/exit results, untested areas, limitations, risks, and commit
information. Distinguish implemented, locally validated, integration-tested, release-ready,
deployed, and production-verified.

## Effects and guardrails

- Inspection and tests are reads except for normal build outputs in approved external cache/temp
  locations.
- Source and test edits are local writes within the requested scope.
- External systems, pushes, deployments, and destructive changes require authorization covering
  their target and effect; reuse an unchanged finite mandate rather than asking again.
- Ask before materially expanding scope, breaking compatibility, or choosing unresolved semantics.
