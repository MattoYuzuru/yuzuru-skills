# Evaluation and Run Evidence

Separate helper correctness, native skill activation, and task-level effectiveness. A static eval
contract or valid JSON establishes none of the other levels. Store run logs, fixtures, plans, and
measurements outside the repository and installed plugin directory.

## Mechanical and native checks

Test helper invariants with credential-free fixtures: malformed input, dependency cycles, unknown
IDs, conflicting ownership/resources, missing estimates, exhausted limits, and incomplete evidence.
Run the repository's required packaging, references, help, tests, and eval checks.

For native activation, use fresh sessions and realistic English/Russian requests that do not name
the skill. Include nearby negative cases, such as a small fix, a sequential bug, or one slow
external operation. Record the skill actually loaded, the applicable host/client version, exact
model and effort where observable, available tools, and the resulting decision. Choosing one agent
can be the correct behavior after activation. Test disabled or unsupported controls without
changing user settings; report fallback and untested clients explicitly.

## Comparative task evaluation

Compare single-agent, fixed-team, and adaptive execution on the same tasks, initial revisions,
acceptance tests, tools, and allowed effects. First hold model and effort constant to isolate
orchestration; evaluate heterogeneous model routing as a separate comparison. Include independent
components, a shared contract, a sequential fix, research, and an integrated acceptance scenario.

Choose the objective before running: time to acceptance at adequate quality, success under an
agreed usage budget, or another explicit tradeoff. Equal-budget and speed-first experiments answer
different questions. Randomize or counterbalance run order, repeat runs, and reserve held-out tasks
for final evaluation. Do not tune and declare success on the same cases.

Count timeout, rejected acceptance, and unfinished integration as unsuccessful. Include failed
attempts, retries, root coordination, and child usage in totals. Report success with uncertainty;
report time among successful runs separately if used, so failures do not disappear from the
comparison. Track duplicated work, conflict/rework, missed checks, and external effects when they
can be observed. Do not substitute number of local tests passed for complete task acceptance.

A small pilot diagnoses mechanics and variance. Its size is not a universal proof threshold.
Choose a confirming sample from observed variability and a prespecified meaningful effect; report
uncertainty and negative findings. Obtain a finite allowed budget before substantial paid trials.

## Record and summarize

Use the sibling run-results schema linked from the skill to record observations. Set `data_kind`
to `synthetic` for examples or simulated data and `observed` only for actual runs. Record the
experiment ID, policy revision, and `study_phase` (`orchestration` or `routing`). Each run includes
its case ID, arm (`single`, `fixed`, or `adaptive`), repetition, initial fixture revision, host,
model/effort, outcome (`accepted`, `failed`, or `timeout`), wall time, usage, and acceptance evidence.
Keep the tested integrated revision and environment in evidence. Record actual native configuration,
not merely the requested override. Preserve missing token or API-cost measurements as null; never
treat them as zero. Native usage has a separate unit and value and may also be null.

Resolve the installed skill directory and run from it:

```bash
python3 -B scripts/evaluate.py validate RESULTS
python3 -B scripts/evaluate.py summarize RESULTS --limit 20
```

The helper validates and summarizes supplied observations without invoking models. Its arithmetic
is descriptive; it does not establish causal improvement, randomization, independent acceptance,
or a fair comparison unless the underlying experiment supplies those properties.

Keep total tokens, API dollar cost estimates, and native subscription usage separate. Report the
scope and denominator for each measure. Do not map token prices to quota/credits or label a partial
telemetry sample a complete cost comparison. Recalibrate after model/client/tool changes rather
than inheriting a prior version's measured performance.
