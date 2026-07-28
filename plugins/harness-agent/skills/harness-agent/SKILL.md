---
name: harness-agent
description: Improve a repository for coding agents by reducing orientation cost and increasing deterministic context, navigation, and capability health. Use when the user asks for agent readiness, documentation consolidation, repository maps, or tool inventories.
---

# Harness Agent

Improve the environment in which agents reason and act. Do not become a feature generator or create
indexes whose maintenance cost exceeds their context savings.

## Audit

1. Inspect repository size, structure, languages, build systems, services, docs, generated files,
   change patterns, and agent instruction files.
2. Locate canonical product, architecture, ADR, style, runbook, deployment, schema, API, test,
   incident, and proposal documentation.
3. Identify repeated searches, failed commands, stale guidance, missing fixtures, credential
   friction, and repeated user questions from actual evidence.
4. Inventory repository skills, plugins, MCP servers, hooks, scripts, commands, integrations,
   effects, credentials, and health.
5. Measure a representative baseline when telemetry exists. Do not invent token or time savings.

Run `scripts/repository_inventory.py <project-root>` for a bounded deterministic map.

## Routing

| Need | Invoke/read | Result |
|---|---|---|
| Navigator, repository map, scoped AGENTS/CLAUDE guidance | `$repository-navigation` | Canonical navigation |
| Skills/plugins/MCP/hooks/scripts/commands health | `$capability-inventory` | Machine-readable inventory |
| Index/vector/context-pack decision | `references/intelligence-decisions.md` | Proportional capability design |
| Generate a capability catalog | `scripts/capability_inventory.py` | Bounded JSON contract |
| Start a docs navigator | `assets/NAVIGATOR.md` | Link-only navigation template |

Load only the selected supporting skill or reference.

## Improvement workflow

1. Name the observed friction and evidence.
2. Choose the smallest remedy: correct a command, add a link, scope instructions, create a
   deterministic helper, or improve an existing index.
3. Keep canonical facts in one place; make platform instruction files thin adapters.
4. Prefer lexical and structural search already available before new indexing.
5. If code intelligence is justified, prefer queryable symbol, reference, caller, dependency,
   schema, or producer/consumer operations over static dumps.
6. If vector retrieval is considered, evaluate size, query patterns, churn, sensitivity, resource
   cost, freshness, expected savings, and fallback.
7. Put mutable indexes and measurements outside Git, tied to source revision.
8. Re-run representative tasks or evidence checks and report real before/after results.

## Documentation system

A navigator links to canonical files, states their purpose/status, and marks superseded documents
without copying their content. Root instructions should route agents to deeper context rather than
repeat every standard. Scoped subproject instructions may add only local differences.

## Credential ergonomics

Investigate safer scoped environment variables, OS keychains, secret managers, credential helpers,
short-lived tokens, or read-only profiles when repeated prompts are evidenced. Never collect, move,
or expose credentials casually. Collaborate with DevOps/security review for any secret-system change.

## Feedback loop

Request bounded analysis from relevant roles only when actual friction needs specialist evidence.
The parent deduplicates feedback and implements justified improvements. Claude may use the bundled
readiness auditor; other hosts use a requested ordinary subagent.

## Output and evidence

Return observed friction, affected tasks, changes, capability health, commands, measured outcomes,
unmeasured hypotheses, maintenance cost, and residual risk. Refresh navigators and indexes after
accepted changes.

## Effects and guardrails

- Repository inspection and inventory are reads.
- Updating docs, instructions, maps, and deterministic helpers is a local write.
- Credential storage, external service changes, or tool installation need separate authorization.
- Do not create giant AST dumps, vectors, agents, MCP servers, or instruction files without a
  demonstrated use case.
- Never store mutable indexes, reports, caches, or telemetry in the source repository.
