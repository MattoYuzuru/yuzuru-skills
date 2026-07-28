---
name: architecture-capacity
description: Model workload, storage, bandwidth, concurrency, partitions, availability, and cost assumptions. Use when architecture decisions need explicit capacity calculations or scale boundaries.
---

# Architecture Capacity

Read `references/modeling.md` before a high-load, data-intensive, queue, cache, partition, or
multi-region estimate. Use the primary architecture skill's calculation script for repeatable base
formulas.

## Workflow

1. Identify which decision the model supports.
2. Separate measured inputs, externally fixed inputs, forecasts, and guesses.
3. Define units, horizon, average, peak, burst, growth, and safety assumptions.
4. Calculate traffic, concurrency, bandwidth, storage, replication/index overhead, cache working
   set, queue accumulation, partitions/consumers, and availability only as relevant.
5. Show formulas and uncertainty; use ranges when inputs are uncertain.
6. Compare estimates to technology or topology limits from current official evidence.
7. Identify the scale boundary and measurement that should trigger migration or expansion.
8. Validate the model against observed metrics when available.

## Guardrails

- Never present a guessed peak factor or compression ratio as measured.
- Do not convert approximate capacity into an exact infrastructure bill.
- Model failure amplification, retries, recovery, and backfill where they dominate steady state.
- Keep the model proportional for local and single-user systems.
