# Agent Orchestration

Coordinate large tasks through useful parallelism and explicit completion evidence.
The portable skill delegates through the host's native tools and can choose one agent.

## Capabilities

- Assess independent workstreams, shared contracts, critical paths, and coordination costs.
- Validate a global task plan and compute a deterministic admissible next batch from declared state.
- Detect dependency cycles, running-task conflicts, missing estimates, and declared budget limits.
- Record actual host/model/effort and summarize accepted, failed, and timed-out attempts separately.
- Preserve domain-skill ownership and verify the final integrated revision.

The [skill](skills/agent-orchestration/SKILL.md) loads decision, host, evidence, and evaluation
references only when needed. Helpers use Python's standard library and no network or credentials.

## Trigger examples

- “Close this multi-service epic, agree interfaces, delegate independent work, and verify integration.”
- “Распредели большую задачу между агентами с общим лимитом ресурсов.”
- “Investigate independent causes of these failures and consolidate verified findings.”

## Non-trigger examples

- Fix one spelling mistake or explain one expression.
- Execute a small, fully specified sequential command chain.
- Wait for one external operation that has no independent work to overlap.

## External effects

Both helpers are read-only: they consume explicitly supplied JSON and print bounded JSON.
They do not spawn agents, call model APIs, write plans, acquire runtime locks, edit host settings,
or enforce native spending. The caller creates requested artifacts outside the installed package
and delegates only within the user's existing task scope and host policy. Push, deployment,
external messaging, destructive work, and additional environments retain their authorization bounds.

## Platform support

| Host | Support and boundary |
|---|---|
| Codex | Portable skill and config-only package; use available native subagent tools and actual model/effort controls. Context forks may share one checkout. |
| Claude Code | Portable skill and native plugin; model, effort, nesting, and worktree capabilities depend on installed version and policy. |
| DeepSeek Harness | Config-only isolated filesystem-skill bundle; model selection and delegation depend on enabled tools and backend support. |

See [host adapters](skills/agent-orchestration/references/host-adapters.md). An installed skill does
not guarantee implicit activation. A short project instruction may request assessment for large
tasks; this package installs no orchestration hook or global instruction changes.

## Local testing

From the resolved installed skill directory:

```bash
python3 -B scripts/plan.py validate assets/example-plan.json
python3 -B scripts/plan.py analyze assets/example-plan.json --limit 20
python3 -B scripts/evaluate.py validate assets/example-results.json
python3 -B scripts/evaluate.py summarize assets/example-results.json --limit 20
```

The example results are synthetic documentation, not benchmark evidence. The plan and run-result
schemas are package-local under `references/`. Copy examples to a task-owned location outside the
package before changing them.

From the repository root, run the required gates and optional native lifecycle checks:

```bash
python3 -B scripts/run_tests.py --match /plugins/agent-orchestration/
./yuzuru validate --strict
python3 -B scripts/smoke_scripts.py
python3 -B scripts/run_tests.py
python3 -B scripts/run_evals.py
python3 -B scripts/test_native_plugins.py --agent both --plugin agent-orchestration
```

The native lifecycle runner uses temporary agent homes and preserves real user settings.
Selection contracts do not execute models; see the
[evaluation protocol](skills/agent-orchestration/references/evaluation.md) for real-client and
comparative tests. Keep observed results outside the clone and bind evidence to the tested source.

## Limitations

The helper validates a declared snapshot; native tools and host policy enforce actual execution.
Path scopes are logical relative prefixes, not filesystem sandbox rules. Undeclared writes,
external resources, stale state, underestimated tokens, and uncooperative clients are outside its
control. All descendants must be registered in the same plan before admission.

There is no universal scientifically optimal agent count, model, or effort. Duration estimates
produce conditional lower bounds, not a proven fastest schedule. Frontier-model names and effort
mappings remain caller/host choices. Tokens, API-cost estimates, and subscription quota are separate.
No speed, cost, or quality improvement is claimed from unit tests or package validation.
