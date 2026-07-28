# Engineering Plugin Catalog

| Plugin | Owns | Does not own |
|---|---|---|
| `discovery-agent` | Opportunity research, regional fit, feasibility signals | Product requirements or architecture |
| `product-agent` | Product behavior, PRD, MVP, acceptance | Technology selection |
| `architecture-agent` | System design, contracts, capacity, migration | Product prioritization or deployment execution |
| `devops-agent` | Delivery, infrastructure, rollout, rollback, operations | Product semantics |
| `harness-agent` | Agent readiness, navigation, inventories, context efficiency | Feature implementation |
| `sde-agent` | Production implementation and focused fixes | Independent release verification |
| `frontend-agent` | UX, visual direction, frontend architecture and implementation | Backend ownership |
| `sre-agent` | Independent verification, reliability, performance, security evidence | Agreeing with implementation claims |
| `cleaner-agent` | Conservative code/doc/artifact hygiene | Unapproved deletion or hidden debt |

Typical flow:

```text
idea → discovery → product → architecture
     → devops + harness → sde + frontend
     → sre → devops release → cleaner
```

This is not a mandatory waterfall. Each plugin can inspect missing context, state assumptions, and
work independently. Cross-plugin artifacts use `schemas/artifacts/` and the handoff rules in
`architecture/artifact-contracts.md`.
