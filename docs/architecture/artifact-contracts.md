# Artifact and Handoff Contracts

Schemas live in `schemas/artifacts/`; valid copyable examples live in `assets/artifacts/`. Use them
when an artifact crosses plugin boundaries, drives a material decision, or supports a completion
claim. Tiny tasks may use a short paragraph or checklist instead of verbose metadata.

## Proportionality

- Small focused change: objective, checks, result, limitations.
- Multi-file feature: artifact metadata plus acceptance criteria and evidence bundle.
- Architecture, migration, deployment, or release: metadata, decisions, work package, and evidence.
- High-risk or long-lived work: stable IDs, owners, assumptions, unresolved questions, and explicit
  supersession.

## Handoffs

| Producer | Typical consumer | Contract |
|---|---|---|
| discovery-agent | product-agent | Opportunity, evidence, assumptions, risks, open questions |
| product-agent | architecture-agent | Observable requirements, quality constraints, acceptance criteria |
| architecture-agent | devops/sde/frontend | Decisions, component contracts, workload, migration constraints |
| harness-agent | every engineering plugin | Navigation, commands, capabilities, health, credential boundaries |
| sde/frontend | sre-agent | Work package, revision, changed behavior, expected evidence |
| sre-agent | devops/product/sde | Validated findings, release readiness, residual risk |
| devops-agent | sre/cleaner | Deployment evidence, rollback state, operational docs |
| cleaner-agent | all | Supersession and refreshed indexes without lost rationale |

When artifacts disagree, identify status, recency, evidence, and ownership. Do not silently select
one. Correct or supersede the wrong artifact and record the resolution.

Artifact paths follow the target project's existing conventions. If none exist, propose one compact
location before creating a large document tree.

## Orchestration plans and observed runs

The self-contained `agent-orchestration` package owns separate
[plan](../../plugins/agent-orchestration/skills/agent-orchestration/references/orchestration-plan.schema.json)
and [run-result](../../plugins/agent-orchestration/skills/agent-orchestration/references/run-results.schema.json)
contracts. A plan adds dependency, ownership, resource, and admission information; it does not
change the shared work-package schema. Refer to the accepted work package in each bounded task
brief, and preserve its authorization, architecture decisions, and checks.

Run records identify initial source revision, host, actual model/effort, outcome, all-attempt time,
and known or unknown usage. Observations, synthetic examples, mechanical validation, and measured
performance remain distinct. Mutable plans and observed-run data belong outside package roots.
