# Cleaner Agent

Conservative repository, documentation, and code hygiene that preserves rationale and requires
evidence before deletion.

## Capabilities

- Classifies stale, temporary, generated, superseded, and contradictory artifacts.
- Reconciles code, tests, documentation, history, and intended behavior.
- Investigates dead code and abstraction opportunities without treating static search as proof.
- Refreshes existing navigation and indexes after verified cleanup.

## Trigger examples

- “Audit this repository for safe cleanup candidates.”
- “The runbook and deployment code disagree; reconcile them.”
- “Compact these ten iterations of design notes without losing decisions.”

## Non-trigger examples

- “Implement a new feature.”
- “Delete all user data.”
- “Format every file while fixing one stale paragraph.”

## External effects

Audits are L0 and local edits are L1. Nontrivial deletion requires explicit approval and a recovery
path; external resource deletion is not a default capability.

## Platform support

Portable skills and scripts work in Codex and Claude Code. Claude includes a cleanup-reviewer
adapter; other hosts use requested ordinary subagents. The optional pollution hook runs only after
plugin hook trust.

## Local testing

Run `yuzuru plugin validate cleaner-agent`, its script and hook unit tests, and cleaner evals.

## Portable instruction refresh

Version 0.1.1 narrows implicit selection and uses direct package-relative skill routes. Supporting
skills, templates, and specialist adapters apply only when the task needs them. Required domain
controls remain in the portable workflow; native host policy and enabled state remain authoritative.

## Limitations

The filename inventory is deliberately conservative and cannot prove dead code, external API use,
reflection, or retention requirements. No deletion is automatic.
