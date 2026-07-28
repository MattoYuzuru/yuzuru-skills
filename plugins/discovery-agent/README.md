# Discovery Agent

Evidence-based opportunity discovery for a product, open-source project, local tool, internal
workflow, hobby, or major feature.

## Capabilities

- Preserves original intent and separates requirements from inferred opportunities.
- Researches direct, open-source, regional, global, and adjacent alternatives.
- Assesses regional access, literacy, privacy, regulation, distribution, and feasibility.
- Produces prioritized risks and honest `pursue`, `test-first`, `use-existing`, or stop decisions.

## Trigger examples

- “Assess a family scheduling tool; commercial potential does not matter.”
- “Research a service for elderly users in Russia before we write a PRD.”
- “Find opportunities for expanding this existing developer tool.”

## Non-trigger examples

- “Implement this focused bug fix.”
- “Choose a database for these accepted requirements.”
- “Write acceptance criteria from an already approved product definition.”

## External effects

Research is read-only. Creating requested artifacts is a local write. The plugin does not contact
competitors, buy services, create accounts, or publish results.

## Platform support

Portable skills work on Codex and Claude Code. Claude includes a bounded evidence-researcher agent.
Codex uses ordinary requested subagents because plugin-bundled custom agents are not documented.

## Local testing

Run `yuzuru plugin validate discovery-agent`, the evidence-index unit test, and the repository eval
suite. Current web claims require fresh official or primary-source research during actual use.

## Limitations

The plugin simulates user perspective but does not replace interviews, legal advice, measured
market demand, or production feasibility tests. It ships no MCP server.
