# Testing and Evaluation

Default checks are credential-free and network-free:

```bash
yuzuru validate
python3 scripts/smoke_scripts.py
python3 scripts/run_tests.py
python3 scripts/run_evals.py
```

The suite validates standalone and plugin skills, both manifests, both marketplaces, stable IDs,
versions, paths, hooks, artifact schemas, README tables, documentation links, helper `--help`, and
repository cleanliness.

Integration tests use temporary HOME, XDG config/cache/data, and agent directories. They never read
real user settings or credentials. Official platform validation runs only when the corresponding
CLI exists; absence is a reported skip, not an offline-suite failure.

DSH static validation checks package identity/version, the bundle declaration, unique provider IDs,
isolated roots, package-relative skill paths, and absence of lifecycle scripts. Native lifecycle
testing uses a temporary `DSH_HOME`, installs a local bundle through `dsh plugin --profile`, dumps
effective configuration, removes the bundle, and verifies that the profile remains bootable. It
must not read the real Harness home or credentials.

Run the optional native lifecycle test with:

```bash
python3 scripts/test_native_plugins.py --agent both --plugin discovery-agent
```

It validates/adds the local marketplace, installs one package, inspects state, exercises supported
enable/disable behavior, uninstalls, removes the marketplace, and deletes its temporary homes.

Eval contracts cover triggers, non-triggers, routing, safety, output expectations, and cross-plugin
handoffs. They are repository-only and are not shipped into skill context.

Completion states are distinct: proposed, implemented, locally validated, integration-tested,
release-ready, deployed, and production-verified. Reports must name commands, exit results,
verified environments, unverified environments, and residual limitations.

## Skill selection and behavior

`evals/skill-selection.json` covers every portable skill with English/Russian requests that do not
name it. `run_evals.py` validates coverage, identity, and positive/negative contracts. It performs
zero model calls and must not be presented as an activation or quality benchmark.

List a bounded evaluation set with:

```bash
python3 scripts/skill_eval.py --list --skill sde-agent
```

Run the listed requests in a fresh host session using a disposable fixture. Record the actual
loaded skill identifiers and independently review the output against the listed expectations.
Keep transcripts and results outside Git. Deferred cases remain in coverage but are excluded from
active behavioral scoring; the LMS requires its separately authorized login session.

Observed results use this shape:

```json
{
  "version": 1,
  "model": "exact model actually used",
  "effort": "exact effort actually used",
  "revision": "tested commit SHA",
  "runs": [{
    "case_id": "sde-agent:positive:1",
    "loaded_skills": ["sde-agent"],
    "expectations_passed": true
  }]
}
```

`expectations_passed` is an optional independent quality assessment, not something the scorer
infers from skill selection. Score with `--results /path/outside/repo/results.json`; add
`--allow-partial` for an explicitly incomplete sample. Selection and workflow quality are separate
metrics. Unknown, duplicate, deferred, malformed, and missing cases must not silently become passes.
Compare the same fixtures, task scope, host tools, model, and effort before and after a prompt change;
measure success, unnecessary activation/pauses, external effects, time, and tokens where available.

Claude Code 2.1.287 exposes native `plugin eval` with a no-plugin baseline arm. That format is not
this repository's JSON contract; inspect current `claude plugin eval --help` and the trusted suite
before running it. It can execute scaffold scripts and MCP servers and consume model budget.

## Local usage evidence

Usage is not installation, enabled state, catalog exposure, or a name appearing in conversation.
`scripts/skill_usage.py` reads only explicitly supplied Codex/Claude JSONL directories and reports
distinct sessions with native invocation, file-load, or helper-execution evidence. Wrapped exec
source calls are separately labeled candidates because static parsing cannot prove execution. It never exports
messages, account IDs, credential stores, or raw tool arguments, and never scans user homes by
default. Example:

```bash
python3 scripts/skill_usage.py --codex-root /path/to/codex/sessions \
  --claude-root /path/to/claude/projects --since 2026-07-09 \
  --exclude-cwd yuzuru-skills --output /path/outside/repo/usage.json
```

Reports disclose missing roots, read caps, truncated files, invalid records, and missing timestamps.
Plugin totals union their supporting-skill sessions instead of summing them. Counted requests do
not prove successful loading or utility; unsupported tools, indirect paths, forks, local retention,
and web-only history limit coverage. Do not retire a skill solely because it has no observed calls.
