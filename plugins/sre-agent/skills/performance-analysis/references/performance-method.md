# Performance method

Use rates and distributions, not averages alone. Record warm-up, duration, concurrency, dataset,
cache state, version, topology, resource quotas, client limitations, and time synchronization.

Correlate throughput and latency with saturation and errors. Inspect p50/p95/p99, allocation/GC,
plans and rows, lock waits, pool waits, queue age/depth, retry volume, cache hit rate, hot
partitions/tenants, disk and network pressure, and downstream timing as relevant.

A load generator can be the bottleneck. Validate the generator, preserve raw measurements outside
Git, and stop before an agreed safety threshold.
