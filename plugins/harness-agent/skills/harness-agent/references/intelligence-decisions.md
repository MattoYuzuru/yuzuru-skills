# Code Intelligence and Retrieval Decisions

## Prefer existing layers

1. Repository navigation and known build/test commands.
2. Lexical search with ignore rules.
3. Syntax-aware search.
4. Existing compiler/LSP indexes.
5. Lightweight dependency or API/schema maps.
6. Incremental vector retrieval only after simpler routes fail.

Useful query capabilities include find symbol/references/callers/implementations/tests, trace
request flow, list module dependencies, and map database or event producers/consumers.

## Vector gate

Require evidence that document/code volume and semantic queries defeat lexical/structural search.
Define exclusions for generated and sensitive data, incremental refresh, source revision, full
rebuild, quality evaluation, resource limits, data location outside Git, and fallback search.

## Measurement

Compare representative tasks: files read, elapsed orientation time, repeated questions, failed
commands, stale-doc findings, corrections, and evidence quality. Report unavailable telemetry rather
than inventing a baseline.
