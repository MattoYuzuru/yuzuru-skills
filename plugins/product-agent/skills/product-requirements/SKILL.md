---
name: product-requirements
description: Model users, jobs, journeys, flows, stories, metrics, glossary, and traceability for a product. Use when product behavior or feature impact needs precise requirements rather than architecture.
---

# Product Requirements

Read `references/behavior-model.md` for a multi-role, stateful, or existing-product workflow.

## Workflow

1. Preserve the original intent and discovery evidence.
2. Define roles only where goals, permissions, information, or behavior differ.
3. Describe jobs and journeys from trigger through outcome, including alternate and recovery paths.
4. Express requirements as stable observable needs, with priority and source.
5. Use stories and use cases only when they make interaction or responsibility clearer.
6. Separate product quality constraints from implementation decisions.
7. Classify MVP scope and name explicitly deferred and out-of-scope behavior.
8. Define metrics with a decision they support; avoid vanity metrics.
9. Maintain one glossary for ambiguous domain terms.
10. Trace feature expansion to current behavior, requirements, and regression surfaces.

## Output

Keep identifiers stable when requirements will be traced. Prioritize unresolved questions by the
amount of rework or risk their answers could create.

## Guardrails

- A persona that does not change behavior is unnecessary.
- A user story does not replace a journey, state model, or acceptance criteria.
- Do not turn an implementation preference into a user need.
- Do not silently resolve contradictory stakeholder requirements.
