# Defensive review method

Prioritize reachable trust-boundary failures over generic checklists. Trace attacker-controlled data
to authorization decisions, interpreters, network requests, filesystem paths, serialization,
browser sinks, logs, and external effects.

For each suspected issue, record actor, access level, exact target, preconditions, controlled input,
expected control, observed behavior, evidence, impact, confidence, and safe regression. Check
project-specific compensating controls before severity assignment.

Redact values rather than printing secrets. Preserve enough structural evidence to reproduce without
including tokens, credentials, private keys, cookies, or unrelated personal data.
