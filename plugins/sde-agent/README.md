# SDE Agent

General software implementation across languages, systems, data, infrastructure code, algorithms,
performance work, and supported GPU environments.

## Capabilities

- Acquires local product, architecture, code, build, test, and history context.
- Plans and implements focused features, fixes, migrations, and refactors.
- Selects behavior-relevant tests and performs bounded independent self-review.
- Produces explicit completion evidence and residual risk.

## Trigger examples

- “Implement this focused Java/Spring feature.”
- “Find and fix this Go concurrency bug.”
- “Add a database migration with rollback evidence.”
- “Implement CUDA code; report that compatible hardware is unavailable.”

## Non-trigger examples

- “Only review this pull request.”
- “Define the product workflow.”
- “Deploy to production.”

## External effects

Inspection and tests are reads; code/tests/docs are local writes. Pushes, external trackers,
deployments, and destructive changes require separate authorization.

## Platform support

Portable skills/scripts run on Codex and Claude Code. Claude includes an implementation reviewer;
other hosts use a requested ordinary review subagent.

## Local testing

Run `yuzuru plugin validate sde-agent`, evidence-bundle tests, and SDE evals.

## Limitations

Actual framework, service, GPU, distributed, and production validation depends on the target
repository and available environment. The plugin ships no language runtime or MCP server.
