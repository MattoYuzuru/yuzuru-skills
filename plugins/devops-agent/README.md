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

## Limitations

No cloud, host, or secret-manager connector is bundled. Real deployment and production verification
are impossible without an explicitly authorized target and credentials.
