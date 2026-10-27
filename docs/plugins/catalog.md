# Engineering Plugin Catalog

| Plugin | Owns | Does not own |
|---|---|---|
| `discovery-agent` | Opportunity research, regional fit, feasibility signals | Product requirements or architecture |
| `product-agent` | Product behavior, PRD, MVP, acceptance | Technology selection |
| `architecture-agent` | System design, contracts, capacity, migration | Product prioritization or deployment execution |
| `devops-agent` | Delivery, infrastructure, rollout, rollback, operations | Product semantics |
| `harness-agent` | Agent readiness, navigation, inventories, context efficiency | Feature implementation |
| `agent-orchestration` | Task dependencies, bounded delegation, shared-resource admission, outcome measurement | Product decisions, native runtime enforcement, or a universal model ranking |
| `sde-agent` | Production implementation and focused fixes | Independent release verification |
| `frontend-agent` | UX, visual direction, frontend architecture and implementation | Backend ownership |
| `sre-agent` | Independent verification, reliability, performance, security evidence | Agreeing with implementation claims |
| `cleaner-agent` | Conservative code/doc/artifact hygiene | Unapproved deletion or hidden debt |
| `time-messenger` | Bounded TiMe reads and authorized semantic writes over API v4 | Other messengers or implicit write authorization |
| `telegram` | Bounded Telegram user workflows over pinned TDLib | Bot API workflows or reuse of desktop session storage |

Typical flow:

```text
idea → discovery → product → architecture
     → devops + harness → sde + frontend
     → sre → devops release → cleaner
```

Choose SDE for a requested implementation and SRE for an independent review or operational claim.
Use a focused supporting skill directly when it already matches the question. Discovery, Product,
and Architecture serve explicit opportunity, behavior, or system-design decisions; DevOps owns
operational changes, Frontend owns interface work, Harness owns observed agent friction, and Cleaner
owns requested hygiene. A task does not need every role in the diagram.

This is not a mandatory waterfall. Each plugin can inspect missing context, state assumptions, and
work independently. Cross-plugin artifacts use `schemas/artifacts/` and the handoff rules in
`architecture/artifact-contracts.md`.

Use `agent-orchestration` for a large task with potentially independent workstreams. It coordinates
existing domain skills and can choose one agent; it does not add a mandatory role sequence. Its
[portable skill](../../plugins/agent-orchestration/skills/agent-orchestration/SKILL.md) uses native
delegation and keeps concrete model/effort selection in the host or caller.
