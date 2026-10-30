# SRE Agent

Deep independent verification of behavior, reliability, performance, defensive security,
observability, architecture risks, incidents, and release readiness.

## Capabilities

- Reconstructs requirements before validating defects.
- Reviews code and runs behavioral, E2E, migration, concurrency, load, resilience, and security tests.
- Confirms, downgrades, deduplicates, or rejects findings with evidence.
- Correlates application behavior with persistence, events, logs, metrics, traces, and releases.

## Trigger examples

- “The implementation agent says complete; verify the whole path independently.”
- “Investigate this authorization defect and race condition.”
- “Test whether the current system fails at 2× load.”
- “Explain why passing unit tests still produce a broken E2E release.”

## Non-trigger examples

- “Implement the feature.”
- “Write a PRD.”
- “Run load against this public endpoint without authorization.”

## External effects

Review is read-only; local tests/fixtures are L1. Staging and production tests are L3/L4, while
destructive/fault/load operations may be L5 and require exact authorization and envelope.

## Platform support

Portable skills/scripts and the load guard run on Codex and Claude Code after hook trust. Claude
includes a bounded test actor; other hosts use requested ordinary subagents.

## Local testing

Run `yuzuru plugin validate sre-agent`, finding and hook tests, hook fixtures, and SRE evals.

Focused review stays within the requested claim; it does not force a release audit or test actor.
Report validation follows the repository's existing contract; the bundled findings helper applies
to its own findings shape. Without a compatible validator, check contract fields manually and
report the automation gap instead of creating a new validation framework.

## Portable instruction refresh

Version 0.1.1 narrows implicit selection and uses direct package-relative skill routes. Supporting
skills, templates, and specialist adapters apply only when the task needs them. Required domain
controls remain in the portable workflow; native host policy and enabled state remain authoritative.

## Limitations

No browser, load generator, monitoring connector, credential, test environment, or MCP server is
bundled. Production verification cannot be inferred from local evidence.

The 0.1.2 load guard checks URLs belonging to an actual load-tool command. Quoted documentation,
comments, and URLs in unrelated commands no longer trigger it. Explicit shell payloads and
substitutions remain checked; every non-loopback target still needs the exact approved host.
The guard does not discover URLs computed inside scripts, tool configuration, aliases or arbitrary
programs. It is a bounded POSIX-shell heuristic, not authorization or isolation. Parse/size/depth
failures stop with a diagnostic. The canonical `scripts/hook_shell.py` is vendored by
`scripts/sync_hook_runtime.py` so each installed plugin stays self-contained.
