# Readiness gates

Select gates proportional to the change:

- intended requirements and acceptance are traceable;
- meaningful E2E and failure behavior pass on the candidate revision;
- compatibility and migrations have validation and rollback;
- security and performance risks are within agreed bounds;
- deployment, health, observability, alerts, and ownership are actionable;
- backups/restores or data recovery are tested when data risk requires them;
- confirmed blockers are closed or explicitly accepted by an authorized owner;
- residual and unverified risks have monitoring or follow-up.

Use `go` only when required gates pass. Use `conditional go` for explicit bounded conditions owned
before or during rollout. Use `no-go` when a required gate fails or critical evidence is absent.
