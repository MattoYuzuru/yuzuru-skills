# Architecture Design Method

## Candidate comparison

For each real candidate state assumptions, responsibilities, data model, consistency, failure
behavior, scaling boundary, operational burden, cost uncertainty, migration path, and rejected
alternatives. Avoid a fake option included only to make the preferred design win.

## HLD

Include context, deployable components, service boundaries, major flows, storage, external
dependencies, trust boundaries, scaling, deployment topology, failure domains, observability, and
major decisions.

## LLD

Add modules, interfaces, contracts, state machines, entities, tables/indexes, transaction
boundaries, concurrency, locking, retry/timeout budgets, cache keys, error and idempotency models,
and rollout behavior only when implementation needs them.

## Technology research

Use current official documentation and maintenance evidence. Consider semantic fit, guarantees,
failure model, maturity, ecosystem, operations, licensing, observability, migration, expertise,
cost, region, and managed-service access. Compare only a decision-relevant set.

## Adversarial review

Try to falsify workload assumptions, data ownership, consistency, isolation, recovery, security,
capacity, cost, and migration claims. Reconcile findings into one architecture rather than attaching
independent contradictory reviews.
