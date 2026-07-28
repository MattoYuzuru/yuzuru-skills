# Architecture Agent

Designs, reviews, and evolves systems from product constraints through coherent component contracts.

## Capabilities

- Produces workload-driven candidates, HLD, proportional LLD, ADRs, and Mermaid diagrams.
- Defines data ownership, consistency, event semantics, failures, security, and observability.
- Calculates transparent capacity and availability estimates.
- Plans compatibility, backfill, cutover, rollback, and decommissioning.

## Trigger examples

- “Design a local single-user application without overengineering.”
- “Review the messenger architecture for regional scale.”
- “Plan PostgreSQL migration before growth from one to fifty-five million users.”
- “Find where code and architecture docs disagree.”

## Non-trigger examples

- “Change this one CSS color.”
- “Define product acceptance for this workflow.”
- “Deploy the already approved topology.”

## External effects

Inspection, research, and calculations are reads. Architecture documents are local writes. The
plugin does not deploy, provision, migrate data, or publish decisions without authorization.

## Platform support

Portable skills and calculations run on Codex and Claude Code. Claude includes an adversarial
architect adapter; other hosts use requested ordinary review subagents.

## Local testing

Run `yuzuru plugin validate architecture-agent`, capacity-model unit tests, and architecture evals.

## Limitations

Estimates depend on supplied inputs and current official evidence. The plugin does not replace load
tests, formal threat modeling, vendor quotes, or production migration rehearsal.
