---
name: performance-analysis
description: Diagnose workload, latency, throughput, database, queue, cache, concurrency, and resource bottlenecks against measured or expected demand. Use when the user asks why a system is slow, where capacity fails, or whether it survives growth.
---

# Performance Analysis

Read `references/performance-method.md` before recommending scaling or infrastructure changes.

## Workflow

1. Define workload, traffic shape, tenant skew, SLOs, environment, baseline, and measurement quality.
2. Trace the critical path through algorithms, fan-out, serialization, network, database, cache,
   queue, locks, pools, CPU, memory, disk, and downstream services.
3. Inspect profiles, plans/indexes, saturation, queue depth, partitions, hot keys, tail latency,
   retries, backpressure, and resource limits as applicable.
4. Form competing hypotheses and design the smallest measurements that distinguish them.
5. Run only an authorized load envelope with rate, duration, concurrency, stop conditions,
   monitoring, rollback, and cleanup.
6. Relate observed boundaries to current and expected demand; include uncertainty.
7. Separate inefficient software, incorrect configuration, temporary anomaly, and true capacity
   shortage before recommending upgrades.

## Output

Return workload assumptions, baseline, measurements, bottleneck chain, threshold or failure mode,
confidence, correction options, and validation plan. Do not generalize one synthetic test to
production without evidence.
