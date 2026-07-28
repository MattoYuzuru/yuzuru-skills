---
name: finding-validation
description: Validate suspected defects and risks against requirements, runtime evidence, and reproduction steps. Use when a bug, security concern, or review finding must be confirmed, classified, deduplicated, or rejected.
---

# Finding Validation

Read `references/finding-contract.md` before escalating a high-severity or security finding.

## Workflow

1. Locate the affected requirement, intended behavior, state/permission model, component, config,
   fixture, and environment.
2. Reproduce safely or identify the exact missing evidence.
3. Compare expected and actual behavior under named preconditions.
4. Correlate code, persistence, downstream effects, logs, metrics, and traces as relevant.
5. Classify confirmed defect, probable defect, design risk, missing evidence, documentation
   inconsistency, intentional behavior, or unverified hypothesis.
6. Deduplicate findings by root cause and impact.
7. Recommend correction direction and a regression test only after validation.
8. Use the primary skill's report validator before finalizing a machine-readable report.

## Guardrails

- Do not label intentional behavior a defect because context was omitted.
- Do not label speculative security impact a confirmed vulnerability.
- Severity describes evidenced impact, not reviewer confidence.
- Preserve rejected hypotheses and rationale when they prevent repeated false positives.
