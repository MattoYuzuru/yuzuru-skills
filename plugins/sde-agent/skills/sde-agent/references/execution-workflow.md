# Engineering Execution Workflow

## Research hierarchy

1. Official documentation.
2. Primary specifications, papers, or vendor source.
3. Maintained source code.
4. High-quality engineering publications.

Use research only when it resolves a current uncertainty.

## Implementation review

Check requested behavior, boundaries, invariants, public/API/serialization compatibility, errors,
resources, cancellation, concurrency, transactions, data migration, security, observability,
performance, tests, docs, and unrelated diff.

## Completion evidence

Record exact commands and exit codes, not “tests passed.” State fixtures, platforms, services,
hardware, and paths actually exercised. A compile or linter does not substitute for behavior tests.
An implementation is not release-ready while decisive checks or environments remain unverified.
