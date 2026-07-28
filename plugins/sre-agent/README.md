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

## Limitations

No browser, load generator, monitoring connector, credential, test environment, or MCP server is
bundled. Production verification cannot be inferred from local evidence.
