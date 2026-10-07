---
name: cleanup-audit
description: Assess stale, generated, unused, or duplicate repository artifacts. Use when asked for cleanup candidates or deletion evidence; an audit does not delete files.
---

# Cleanup Audit

## Workflow

1. Read repository instructions, ignore rules, Git status/history, packaging, builds, deployments,
   tests, and generators.
2. Run the cleanup-candidate helper routed by the primary skill for a bounded filename inventory.
3. Search each candidate by basename, path, identifier, configuration, reflection, assets, and
   deployment usage.
4. Classify ownership, retention, reproducibility, historical value, confidence, and recovery path.
5. Rank retain, correct, archive, regenerate, or delete recommendations.
6. Keep speculative candidates out of automatic cleanup.

Read `references/candidate-evidence.md` for the required evidence and deletion thresholds.

## Output

Return candidates with reason, direct and indirect references, dynamic-use risk, Git status/history,
recommended action, confidence, validation, and whether approval is still required. Do not delete
anything during an audit.
