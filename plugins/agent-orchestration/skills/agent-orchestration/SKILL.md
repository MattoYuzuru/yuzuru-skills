---
name: agent-orchestration
description: Coordinate independent workstreams in epics, multi-service implementations, or substantial research. Use when a large task needs bounded subagent delegation; exclude small fixes and strictly sequential work.
---

# Agent Orchestration

Choose useful parallelism, delegate bounded work, and deliver an accepted integrated result.
A valid outcome is one agent. No universal agent count, model, effort, or speedup is established.

## Choose the execution shape

Assess acceptance, dependencies, uncertainty, shared writes/resources, and available native tools.
Delegate concrete independent workstreams when this reduces time or isolates useful context and
host policy permits. Keep urgent work on the critical path local while children handle independent
work. Batch simple independent tool calls without creating extra agents when that is sufficient.

As the session leader, own the overall objective, contracts, global limits, and final acceptance.
As a delegated worker, execute the assigned scope; do not restart the session-wide planner.
Register any useful nested delegation in the same global plan before dispatch; obtain the leader's
allocation when it was not supplied. A child does not acquire its own copy of the root budget.

Use [decision-policy.md](references/decision-policy.md) when decomposition, shared resources,
replanning, or a tradeoff between time and usage needs a concrete decision. Use
[host-adapters.md](references/host-adapters.md) when resolving model/effort, concurrency, context,
or workspace capabilities. Preserve user pins and host policy; disclose unavailable controls.

## Prepare and dispatch

Agree on the interfaces needed by parallel consumers: schemas, API behavior, errors, versions,
and ownership. Refine the graph as evidence arrives; avoid a full-project design prerequisite.
Give each worker its objective, inputs, contract version, owned paths/resources, acceptance checks,
allowed effects, limits, and expected evidence. Include applicable instruction and skill paths,
checkout/revision, runtime target/owner, and common check lock when development checks are shared.
Provide the context needed for that work rather than copying the entire conversation by default.

For concurrent work needing persistent coordination, keep a small plan outside the repository and
installed package in an explicit task directory or platform state directory. The
[plan schema](references/orchestration-plan.schema.json) defines its fields; the
[example plan](assets/example-plan.json) shows a contract followed by independent services and
integration. Do not add these scheduling fields to an unrelated work-package contract.

Resolve this installed skill directory before running its helpers. Run from that directory:

```bash
python3 -B scripts/plan.py validate PLAN
python3 -B scripts/plan.py analyze PLAN --limit 20
```

Inspect readiness, blocked reasons, running reservations, and the proposed conflict-free batch.
The helper validates declared state and computes estimates; it neither spawns agents nor locks
resources, measures model quality, or enforces native spend. Do not interpret a valid plan as
permission, a reservation as a runtime lock, or a time lower bound as a promised completion time.

Use the host's native spawn/message/wait tools to dispatch the admitted work. Record actual agent
IDs, applied model/effort, scopes, and statuses in task evidence. Keep the global task registry
current across the entire delegation tree. Respect the smaller of the user limit, measured useful
parallelism, and native capacity; an unrestricted request does not remove host limits.

## Adapt and integrate

Continue independent local work while children run. Wait when their result blocks the next useful
step. Resolve overlap at its owner; do not ask another worker to repeat an unresolved assignment.
On contract changes, failure, or stalled progress, update affected dependencies and allocations.
Change context, decomposition, model profile, or approach when evidence warrants it; repeated
identical retries are not a recovery strategy. Reuse existing effect authorization within scope.

Give writes distinct owners and isolate checkouts when appropriate. Worktrees do not isolate
shared ports, volumes, schemas, lockfiles, or logical interfaces. Coordinate shared checks with the
project's runtime owner and locks. Never assume a conversation fork creates a Git worktree.

Accept a completed task only with its required evidence. Verify producer-consumer behavior and
acceptance on the integrated revision and actual environment. A worker's report, local test pass,
or progress-only end of turn is not sufficient. Add independent review where a concrete risk
justifies it; no minimum reviewer count or universal extra round is required.

Stop after the requested outcome and required checks pass. Report the accepted result, actual
configuration, validation scope, unavailable evidence, and remaining limitations. Cancel or close
unneeded workers through native tools without discarding their owned changes.

## Evidence and evaluation

Read [evidence.md](references/evidence.md) when making a scientific claim or changing the policy's
assumptions. Its dated findings support hypotheses, not a universal routing formula.
Read [evaluation.md](references/evaluation.md) when testing activation, comparing execution modes,
or recording runs. Use the [run results schema](references/run-results.schema.json) for observed
measurements. The [synthetic results example](assets/example-results.json) demonstrates the format;
validate/summarize supplied observations without model calls:

```bash
python3 -B scripts/evaluate.py validate RESULTS
python3 -B scripts/evaluate.py summarize RESULTS
```

Keep measured tokens, API cost estimates, and native subscription usage separate. Label missing
telemetry unknown; do not infer quota from token prices or claim speedups from static evals.

## Effects

Plan and result inspection are reads. Task files and requested code changes are local writes.
Delegation inherits the parent's permissions, target, payload, and user restrictions; it grants no
additional access. External writes and destructive actions retain their original authorization
requirements. Do not change host configuration, bypass disabled tools/skills, launch another client,
or call a paid API merely to obtain a model unavailable through the authorized native interface.
