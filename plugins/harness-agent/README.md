# Harness Agent

Improves repository navigation, deterministic tooling, context efficiency, and capability health
for coding agents.

## Capabilities

- Audits agent readiness, documentation drift, commands, and repeated friction.
- Builds navigators, repository maps, scoped instructions, and capability inventories.
- Evaluates symbol/dependency indexing, context packs, and vector retrieval proportionally.
- Measures outcomes when real baseline evidence exists.

## Trigger examples

- “Agents keep reading the wrong docs; build a navigator.”
- “Inventory our skills, MCP servers, hooks, commands, and credentials.”
- “Decide whether this repository needs vector search.”

## Non-trigger examples

- “Change one README sentence.”
- “Implement the feature.”
- “Delete stale artifacts now.”

## External effects

Inspection and inventory are reads. Requested docs/maps/helpers are local writes. Tool installation,
credential movement, or external configuration requires separate authorization.

## Platform support

Portable skills and scripts run on Codex and Claude Code. Both can use the optional pollution hook
after trust. Claude includes a read-only readiness auditor.

## Local testing

Run `yuzuru plugin validate harness-agent`, inventory/hook tests, and harness evals.

## Limitations

No vector database, AST service, telemetry collector, or MCP server is bundled. Benefits are not
claimed without measured evidence.
