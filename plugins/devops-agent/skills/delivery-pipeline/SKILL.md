---
name: delivery-pipeline
description: Design or repair repository-adaptive CI and CD pipelines using current host documentation and safe secret boundaries. Use when a build, test, packaging, release, or deployment pipeline needs implementation or review.
---

# Delivery Pipeline

Read `references/pipeline-review.md` before changing a workflow with secrets, untrusted
contributions, deploy jobs, privileged runners, caches, or generated artifacts.

## Workflow

1. Detect repository host, branch strategy, build/test commands, existing workflow, and deployment
   coupling.
2. Confirm current syntax and actions/plugins from official host documentation.
3. Map jobs, dependencies, duplicate work, trust boundaries, credentials, caches, artifacts,
   retention, environments, and failure diagnostics.
4. Make the smallest change that meets the objective and preserves established behavior.
5. Use scoped identity, protected environments, and no secrets for untrusted pull requests.
6. Validate workflow syntax and execute safe local equivalents where possible.
7. Report which jobs were simulated, which need hosted integration, and how rollback works.

## Guardrails

- Do not pin mutable untrusted actions where immutable versions are available.
- Do not cache secrets, credentials, or uncontrolled build output.
- Do not make deployment success depend on an opaque log line.
- Avoid duplicated builds when one verified artifact can move between stages.
