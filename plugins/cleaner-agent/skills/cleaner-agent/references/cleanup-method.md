# Cleanup method

Use four passes:

1. **Inventory:** locate candidates without changing state.
2. **Evidence:** search static and dynamic references, history, ownership, retention, and generation.
3. **Action:** retain, correct, compact, supersede/archive, regenerate, or propose deletion.
4. **Verification:** run relevant tests/builds/links and refresh only existing indexes.

Confidence is not permission. A high-confidence nontrivial deletion still needs approval unless the
user explicitly named the exact deletion. Prefer Git-recoverable changes and state the recovery path.

Compaction preserves facts, decisions, constraints, rationale, operational instructions, and open
risks. It may remove repetition, session chronology, resolved speculation, and obsolete examples.
