---
name: documentation-reconciliation
description: Resolve contradictions and drift between documentation, code, tests, and runtime behavior while preserving decisions and history. Use when setup, architecture, API, runbook, diagram, or example documentation may be stale.
---

# Documentation Reconciliation

## Workflow

1. Identify the disputed behavior and every document, test, implementation, schema, example, and
   runtime signal that claims to define it.
2. Compare artifact status, recency, authority, intent, and evidence; inspect history when needed.
3. Classify the mismatch: stale docs, implementation defect, changed requirement, missing decision,
   duplicate source, or unresolved conflict.
4. If evidence cannot select the intended behavior safely, surface the conflict instead of silently
   choosing.
5. Update or supersede the incorrect sources, preserve rationale, and refresh inbound links.
6. Validate commands, examples, schemas, diagrams, and links affected by the correction.

Read `references/reconciliation-rules.md` before compacting or superseding a canonical document.

## Guardrails

Code is not automatically authoritative. Do not erase unresolved incidents or technical-debt
evidence, and do not mix wholesale formatting with semantic correction.

## Output

Report the conflict, sources considered, canonical decision, files changed or superseded, validation,
remaining uncertainty, and recovery through Git history.
