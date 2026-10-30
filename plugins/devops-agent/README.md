# DevOps Agent

Repository-adaptive CI, delivery, deployment, infrastructure, observability, and operational
hardening with an explicit L0–L5 impact model.

## Capabilities

- Inventories existing delivery and infrastructure without changing it.
- Builds or repairs CI/CD with current host documentation and safe trust boundaries.
- Plans and verifies VPS, Compose, systemd, cloud, IaC, and orchestration workflows.
- Covers rollback, backups/restores, observability, supply chain, capacity, and runbooks.

## Trigger examples

- “Improve this existing GitHub Actions pipeline without breaking deployment.”
- “Prepare a Docker Compose rollout to staging with rollback.”
- “Review Terraform, backups, and restore evidence.”

## Non-trigger examples

- “Design the service boundaries.”
- “Implement the application feature.”
- “Run an unapproved production load test.”

## External effects

L0 inspection is read-only; L1/L2 are local changes. L3–L5 infrastructure changes require explicit
scope, with exact confirmation for production and destructive operations.

## Platform support

Portable skills and scripts run on Codex and Claude Code. The command guard hook is supported by
both and requires native trust. Claude also includes a read-only release verifier.

## Local testing

Run `yuzuru plugin validate devops-agent`, helper/hook unit tests, hook fixtures, and devops evals.
Use native workflow validators when available.

## Portable instruction refresh

Version 0.1.1 narrows implicit selection and uses direct package-relative skill routes. Supporting
skills, templates, and specialist adapters apply only when the task needs them. Required domain
controls remain in the portable workflow; native host policy and enabled state remain authoritative.

## Limitations

No cloud, host, or secret-manager connector is bundled. Real deployment and production verification
are impossible without an explicitly authorized target and credentials.

The 0.1.2 command guard inspects command positions instead of matching deletion examples anywhere
in the tool text. Quoted arguments, comments, and literal data here-documents do not trigger it.
Explicit shell payloads, substitutions, pipelines, and shell-input here-documents remain checked.
Recursive deletion of the root or a home directory is blocked; an explicitly scoped descendant
is not treated as the whole home. Authorization for that descendant still comes from the task.

This bounded POSIX-shell inspector is an accidental-operation guard, not a shell sandbox or an
authorization engine. It does not resolve aliases, computed commands, sourced files, or arbitrary
program semantics. Parse/size/depth failures stop with a diagnostic. PowerShell grammar is not
implemented; only common explicit command forms are recognized. The shared canonical inspector is
`scripts/hook_shell.py` in the source repository; `scripts/sync_hook_runtime.py` vendors a tested,
self-contained copy into each consuming plugin.
