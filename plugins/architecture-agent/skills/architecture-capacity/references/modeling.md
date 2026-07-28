# Capacity Modeling

Consider:

- request/event rates by operation and tenant;
- peak, burst, seasonality, retries, fan-out, and backfill;
- concurrent sessions, connections, workers, and transaction duration;
- payload, protocol overhead, ingress/egress, and cross-region replication;
- logical vs physical storage, indexes, replicas, backups, tombstones, and growth;
- cache working set, hit rate assumptions, hot keys, and invalidation;
- queue arrival/service rate, accumulation, recovery drain time, and consumer parallelism;
- partition throughput, key distribution, resharding, and hot tenants;
- SLO measurement window, error-budget consumption, and dependency budgets;
- regional latency, managed-service limits, team operations, and cost range.

State sensitivity: which uncertain input changes the recommendation most?
