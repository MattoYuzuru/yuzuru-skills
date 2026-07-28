# Repository Navigator

Use this page to choose the smallest relevant context.

| Need | Canonical document |
|---|---|
| Repository boundaries and ownership | [`architecture/repository.md`](architecture/repository.md) |
| Claude Code vs Codex capabilities | [`architecture/platform-compatibility.md`](architecture/platform-compatibility.md) |
| Cross-plugin artifacts and handoffs | [`architecture/artifact-contracts.md`](architecture/artifact-contracts.md) |
| Standalone Agent Skills | [`skill-authoring.md`](skill-authoring.md) |
| Plugin packages and adapters | [`authoring/plugins.md`](authoring/plugins.md) |
| Deterministic script contract | [`authoring/scripts.md`](authoring/scripts.md) |
| Hook rules | [`authoring/hooks.md`](authoring/hooks.md) |
| MCP decision rules | [`authoring/mcp.md`](authoring/mcp.md) |
| Marketplaces and native commands | [`distribution/marketplaces.md`](distribution/marketplaces.md) |
| Skills-only migration and repairs | [`distribution/migration.md`](distribution/migration.md) |
| Release and versioning | [`distribution/releasing.md`](distribution/releasing.md) |
| Trust, credentials, and runtime state | [`security/trust-model.md`](security/trust-model.md) |
| Effects and permission levels | [`security/effect-model.md`](security/effect-model.md) |
| Tests, evals, and completion evidence | [`testing.md`](testing.md) |
| Plugin catalog and handoffs | [`plugins/catalog.md`](plugins/catalog.md) |
| Troubleshooting | [`troubleshooting.md`](troubleshooting.md) |
| Contribution lifecycle | [`CONTRIBUTING.md`](CONTRIBUTING.md) |

## Canonical surfaces

- `skills/`: independently installed portable skills retained for compatibility.
- `plugins/<id>/skills/`: canonical behavior shipped by one plugin.
- `plugins/<id>/.codex-plugin/plugin.json`: Codex package adapter.
- `plugins/<id>/.claude-plugin/plugin.json`: Claude Code package adapter.
- `.agents/plugins/marketplace.json`: Codex repository marketplace.
- `.claude-plugin/marketplace.json`: Claude Code marketplace.
- `schemas/`: stable artifact, migration, manifest, and hook contracts.
- `evals/`: repository-only trigger, routing, safety, and handoff contracts.
- `scripts/`: repository validation and authoring tools.
- `yuzuru`: canonical CLI; `skill` is the compatibility launcher.

Generated reports, dependency environments, indexes, credentials, logs, screenshots, and session
state belong outside this repository.
