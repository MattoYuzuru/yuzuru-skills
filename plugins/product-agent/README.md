# Product Agent

Transforms discovery evidence or an accepted idea into proportional product requirements without
crossing into architecture ownership.

## Capabilities

- Creates or updates a lightweight or full PRD.
- Models roles, jobs, journeys, states, metrics, glossary, and feature impact.
- Scopes an evolvable MVP and distinguishes experiments and disposable prototypes.
- Produces observable acceptance criteria and a prioritized question register.

## Trigger examples

- “Create a lightweight PRD for our family application.”
- “Add this workflow to the existing product and trace regressions.”
- “Resolve these contradictory requirements and define an evolvable MVP.”

## Non-trigger examples

- “Choose PostgreSQL or DynamoDB.”
- “Implement the accepted API endpoint.”
- “Research whether this idea is worth pursuing.”

## External effects

Repository inspection is read-only. Requested product-document changes are local writes. The plugin
does not approve roadmaps, update external trackers, or publish requirements without authorization.

## Platform support

Portable skills run on Codex and Claude Code. Claude includes a requirements critic; other hosts
use a requested ordinary review subagent.

## Local testing

Run `yuzuru plugin validate product-agent`, the traceability unit test, and product eval cases.

## Limitations

It does not replace user research, stakeholder approval, architecture design, or actual behavioral
testing. It ships no MCP server.
