---
name: product-acceptance
description: Write and review observable acceptance criteria including permissions, state transitions, failures, accessibility, and platform behavior. Use when requirements need testable behavioral acceptance criteria.
---

# Product Acceptance

Read `references/acceptance-quality.md` before criteria for permissions, money, recovery, stateful
workflows, accessibility, or platform-specific behavior.

## Workflow

1. Link each criterion to a requirement or explicit product risk.
2. State precondition, action/event, and observable result.
3. Cover the meaningful happy path plus important validation, permission, failure, cancellation,
   retry, duplicate, and recovery cases.
4. Specify state transitions and visibility by role when relevant.
5. Include accessibility and supported-platform behavior as product behavior.
6. Remove implementation details unless the implementation itself is an external requirement.
7. Review for ambiguity, contradiction, unobservable language, and missing boundary values.
8. Use the primary skill's traceability helper when IDs span documents.

## Guardrails

- Reject “works correctly,” “is user friendly,” and other non-observable criteria.
- Do not require every theoretical edge case; prioritize domain risk.
- Do not imply automated coverage merely because a criterion is testable.
- Keep product acceptance separate from architecture and test implementation.
