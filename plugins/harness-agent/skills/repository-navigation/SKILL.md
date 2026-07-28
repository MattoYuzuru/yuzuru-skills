---
name: repository-navigation
description: Build or refresh concise documentation navigation, repository maps, and scoped agent instructions. Use when agents struggle to locate canonical docs, commands, ownership, or component boundaries.
---

# Repository Navigation

Read `references/navigation-contract.md` before consolidating a large or contradictory documentation
tree.

## Workflow

1. Inventory documentation, instructions, build/test commands, components, ownership, and status.
2. Identify canonical, superseded, duplicated, temporary, generated, and missing navigation.
3. Create or update one concise navigator that links to canonical sources without copying content.
4. Make root AGENTS/CLAUDE adapters short and route to scoped instructions.
5. Add repository maps and command references only where agents repeatedly need them.
6. Mark status and supersession explicitly.
7. Validate links, commands, and instruction scope.

## Guardrails

- Do not duplicate hundreds of lines across AGENTS.md and CLAUDE.md.
- Do not declare a document canonical without checking code, tests, history, and ownership.
- Do not bury operational commands in narrative prose when a short command reference is clearer.
- Preserve useful history through status or supersession links.
