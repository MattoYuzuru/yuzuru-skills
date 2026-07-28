# Artifact Examples

Copy only the contract needed for a material cross-plugin handoff. Small tasks should use a concise
objective, checks, result, and limitations instead.

- `artifact-metadata.json`: lifecycle, ownership, assumptions, questions, evidence, supersession;
- `decision-record.json`: proposed decision and validation;
- `work-package.json`: bounded implementation authority and acceptance;
- `evidence-bundle.json`: commands, tests, environments, limitations, and release state.

Validate a copy with `python3 scripts/validate_artifact.py <kind> <path>`.
