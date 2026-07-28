# Acceptance Quality

Good criteria answer:

- who can act and under which preconditions;
- what event occurs;
- which state changes;
- what each relevant actor observes;
- what is persisted, rejected, retried, or rolled back;
- how duplicate or concurrent actions behave when material;
- what happens on dependency failure, cancellation, and timeout;
- which accessibility or platform behavior is required.

Use examples rather than prescribing a test framework. For money, include currency, rounding,
precision, reversal, duplicate submission, and audit visibility. For permissions, cover both
allowed and denied behavior without leaking protected existence or data.
