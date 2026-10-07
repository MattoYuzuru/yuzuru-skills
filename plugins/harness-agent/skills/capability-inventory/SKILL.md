---
name: capability-inventory
description: Inventory declared skills, plugins, tools, hooks, effects, and health. Use when a capability catalog or tool audit is requested; installation alone does not prove usage.
---

# Capability Inventory

Read `references/inventory-contract.md` before producing a shared machine-readable inventory.

## Workflow

1. Discover repository and installed capabilities without exposing credentials.
2. For each capability record identity, kind, trigger/invocation, effect, required credentials,
   health, owner, and canonical documentation.
3. Distinguish available, installed, enabled, authenticated, healthy, and tested.
4. Validate referenced files and credential-free `--help`.
5. Mark unavailable or unverified capabilities rather than inventing support.
6. Store generated inventory outside Git unless the user explicitly wants a reviewed canonical
   snapshot.

Use the primary skill's capability-inventory helper to enumerate repository-provided skills,
plugins, hooks, scripts, and MCP declarations. Its `unknown` health/effect values are intentional:
declaration alone is not proof of runtime behavior.

## Guardrails

- Never enumerate secret values or dump environment/config files.
- A manifest is evidence of declaration, not runtime health.
- Do not call an MCP server available unless its configured endpoint/process is inspectable.
- Keep output bounded and tied to source revision.
