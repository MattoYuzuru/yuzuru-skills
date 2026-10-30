---
name: finding-validation
description: Confirm, reject, and classify suspected defects with requirements and evidence. Use when a review finding, bug report, or security claim needs validation.
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
8. For a machine-readable report, follow the repository's existing report schema and validator
   when required. If using the bundled [findings shape](../sre-agent/assets/FINDINGS.json), run
   the compatible [report helper](../sre-agent/scripts/finding_report.py) against the report;
   resolve its path from this installed skill, not the current project directory. If no
   compatible validator is available, check the fields in `references/finding-contract.md`
   manually and state that automated validation was unavailable. Do not invent a validator
   solely to complete this step.

## Guardrails

- Do not label intentional behavior a defect because context was omitted.
- Do not label speculative security impact a confirmed vulnerability.
- Severity describes evidenced impact, not reviewer confidence.
- Preserve rejected hypotheses and rationale when they prevent repeated false positives.
