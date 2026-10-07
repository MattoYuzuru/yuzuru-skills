# SDE Agent

General software implementation across languages, systems, data, infrastructure code, algorithms,
performance work, and supported GPU environments.

## Capabilities

- Acquires local product, architecture, code, build, test, and history context.
- Plans and implements focused features, fixes, migrations, and refactors.
- Runs relevant checks and uses an independent reviewer when risk warrants it.
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
deployments, and destructive changes require authorization covering their target and effect.

## Platform support

Portable skills/scripts run on Codex and Claude Code. Claude includes an implementation reviewer;
reviewers are optional on every host and follow host delegation policy.

## Local testing

Run `yuzuru plugin validate sde-agent`, evidence-bundle tests, and SDE evals.

## Portable instruction refresh

Version 0.1.1 narrows implicit selection and uses direct package-relative skill routes. Supporting
skills, templates, and specialist adapters apply only when the task needs them. Required domain
controls remain in the portable workflow; native host policy and enabled state remain authoritative.

## Limitations

Actual framework, service, GPU, distributed, and production validation depends on the target
repository and available environment. The plugin ships no language runtime or MCP server.
