---
name: deployment-safety
description: Prepare, preview, execute, and verify an authorized deployment with target, rollback, health, and evidence controls. Use when a concrete environment change or rollout strategy is requested.
---

# Deployment Safety

Read `references/deployment-runbook.md` before any L3–L5 operation.

## Workflow

1. Resolve the exact environment, account/project, region, hosts/services, version, and permission
   level.
2. Capture current version, health, dependencies, relevant config, migrations, and active incidents.
3. Define protected behavior, rollback artifact/path, stop conditions, and monitoring.
4. Preview exact operations and affected resources.
5. Obtain the authorization required for L3–L5; L4/L5 need exact target confirmation.
6. Execute once, incrementally where possible. Do not automatically retry ambiguous mutations.
7. Verify health, smoke paths, logs, metrics, traces, version, and downstream effects.
8. Roll back on the defined condition; verify rollback rather than assuming it.
9. Report final state and update docs only when behavior changed.

## Guardrails

- Never target third-party or unspecified infrastructure.
- A successful command is not a healthy deployment.
- Do not expose secrets in previews, transcripts, evidence, or environment dumps.
- Database migrations need compatibility, backup/restore evidence, lock/runtime analysis, and a
  rollback or roll-forward strategy.
