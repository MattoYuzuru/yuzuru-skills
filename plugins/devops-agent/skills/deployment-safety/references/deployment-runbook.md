# Deployment Runbook Contract

Record:

- exact target and permission level;
- authorized operation and excluded resources;
- current version/state and desired version/state;
- dependencies and database/schema sequence;
- rollout method: rolling, blue-green, canary, feature flag, or bounded direct replacement;
- drain, shutdown, worker, cron, and queue behavior;
- stop conditions and named signals;
- rollback steps, artifact, data implications, and maximum recovery time;
- smoke paths, logs, metrics, traces, alerts, and observation window;
- commands, exit codes, final state, limitations, and unverified paths.

For production, require a human-confirmed target and plan immediately before the first mutation.
