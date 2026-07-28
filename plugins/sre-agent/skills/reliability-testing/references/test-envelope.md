# Reliability Test Envelope

Record:

- exact scheme/host/service/environment and owner authorization;
- test objective and acceptance threshold;
- clients, data, accounts/tenants, isolation, and cleanup;
- rate, concurrency, payload, duration, growth, and maximum total requests;
- injected failure or constrained resource;
- expected impact and protected traffic;
- monitoring, alerts, abort signals, rollback, and responsible operator;
- baseline, test window, recovery window, and correlation identifiers;
- environment revision and configuration;
- limitations and unverified paths.

Use a local, disposable, or staging target by default. Production needs explicit authorization for
the exact envelope immediately before execution.
