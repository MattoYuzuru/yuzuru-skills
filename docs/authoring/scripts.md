# Deterministic Script Contract

Use a script when it adds validation, safety, structured output, repeatability, or a real
calculation. Do not wrap a trivial shell command.

Every public helper must:

1. provide credential-free `--help`;
2. resolve immutable resources from its installed location;
3. write mutable state only to an explicit output, temporary directory, XDG directory, or host
   plugin data directory;
4. emit compact JSON when another agent consumes the result;
5. send diagnostics to stderr and exit nonzero on failure;
6. cap collections and long strings;
7. redact secrets and avoid secrets in command arguments;
8. distinguish read, write, and destructive subcommands;
9. support `--dry-run` for writes and validate exact targets;
10. never automatically retry an ambiguous mutation;
11. apply timeouts to external processes and requests.

Third-party dependencies require a lockfile and an environment outside the clone, keyed by lock
hash. Prefer the Python standard library. Set `PYTHONDONTWRITEBYTECODE=1` in repository runners so
normal validation does not create bytecode caches.
