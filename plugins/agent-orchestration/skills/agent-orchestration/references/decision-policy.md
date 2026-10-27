# Execution Decisions

Use task structure and observed results to choose concurrency. These are engineering defaults to
calibrate, not experimentally established optima for every task or model.

## Select useful work

| Situation | Decision |
|---|---|
| Small local fix or one ordered reasoning chain | Complete it in the current agent. |
| Independent searches or reads with no separate reasoning needed | Batch native tool calls. |
| Separate verifiable components, sources, or hypotheses | Delegate bounded branches with distinct outputs. |
| Consumers depend on an unsettled interface | Resolve the necessary contract, then release consumers. |
| Several failures share a likely root cause | Investigate the shared cause before splitting fixes. |
| Shared writable state cannot be isolated | Serialize its owner; delegate independent analysis if useful. |
| Another agent already owns the unresolved question | Send new evidence to that owner instead of duplicating work. |

The relevant unit is an independently acceptable result. A service boundary can provide one, but
a service can also contain parallel components or an inseparable sequence. Do not equate file
count, task difficulty, or available slots with useful team size.

## Allocate and replan

Build the dependency graph from observable prerequisites. Assign one owner per task and shared
interface. Keep its acceptance checks and effects explicit. Limit the initial wave to independent
ready work; expand when additional ready tasks justify startup, context, and integration cost.

Apply one concurrency, depth, and usage allocation to the whole delegation tree. Register nested
work before dispatch. The plan's task depth records delegation depth, not dependency-chain length.
Host tool limits and permissions still apply when the user places no numerical cap.

Resolve candidate models from authorized host capabilities and workload measurements. Use the
smallest measured adequate profile for the task, preserving the user's model and effort pins.
Where no relevant calibration exists, use current authorized host metadata or official workload
guidance as a disclosed prior, falling back to the caller default; label the choice uncalibrated.
A benchmark score or a model's confidence does not establish success probability on this task.

Escalate when a worker lacks needed context or capability; split an oversized assignment only if
the new pieces have independently verifiable results. On dependency or contract changes, notify
consumers and invalidate incompatible results. On budget exhaustion, admit no new work; preserve
partial artifacts and report the unfinished scope. Do not retry an ambiguous external mutation.

## Interpret helper results

The helper sees JSON declarations, not live agents or the filesystem. Keep actual task status and
spent usage current before each admission. Declare all running tasks and exclusive resources,
including workers created by children. Missing budget estimates are uncertainty, not free work.

Concrete relative write-path prefixes describe logical ownership. Prefix conflicts are deliberately
conservative; they do not detect undeclared writes, symlink aliases, generated paths, or a shared
service hidden behind distinct directories. Separate worktrees can prevent concurrent text writes
while leaving schema, migration, and integration conflicts intact. Use explicit exclusive-resource
names for those logical or runtime conflicts, and actual project locks where required.

Duration estimates are supplied assumptions. When complete, the critical path and total work per
slot give idealized lower bounds; startup, network queues, model throughput, retries, integration,
and resource contention can make execution slower. A greedy admissible batch is not a proof of an
optimal schedule or team configuration.

## Accept work

Require checks that exercise the declared behavior and interface, tied to the tested revision and
environment. Integration acceptance includes interactions between producer and consumer, not just
the workers' local tests. A verifier or reviewer can share the author's blind spots; use executable
or independent evidence where available. Preserve failures and unknowns in the final report.

Choose extra independent review for a specific unresolved risk. Avoid mandatory debates, reviewer
rounds, or alternative solutions when they add no new evidence. Stop after sufficient required
checks; improvements to the orchestration policy are separate scope unless needed for completion.
