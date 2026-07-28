# Migration Phases

1. Baseline: measure current correctness, load, capacity, recovery, and dependency behavior.
2. Compatibility: introduce additive schemas, contracts, adapters, and idempotency.
3. Shadow: copy traffic or data without serving results; compare semantics.
4. Backfill: bounded batches, checkpoints, retry policy, throttling, and reconciliation.
5. Progressive cutover: a reversible tenant, shard, region, or percentage at a time.
6. Rollback: exact trigger, routing, data divergence handling, and maximum recovery time.
7. Stabilize: observe correctness, latency, errors, queues, resource pressure, and support signals.
8. Decommission: remove old writes, reads, data, dependencies, and operational procedures only after
   the retention gate.

Name who owns every stage gate and unresolved data conflict.
