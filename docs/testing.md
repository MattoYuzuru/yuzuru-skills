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
