# Product Behavior Model

For each important workflow capture:

- trigger, actor, permissions, and preconditions;
- current state and data visible to the actor;
- happy path decisions and state transitions;
- validation and important errors;
- cancellation, retry, duplicate, timeout, and recovery behavior;
- notifications or downstream visible effects;
- accessibility, device, localization, offline, and privacy behavior where relevant;
- terminal states and audit expectations.

For an existing product, record unchanged behavior and regression-sensitive integrations. Use
stable requirement IDs only when cross-document traceability is worth maintaining.

Metrics should state the behavior measured, collection boundary, interpretation, target or baseline
status, and possible gaming or harm.
