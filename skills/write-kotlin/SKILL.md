---
name: write-kotlin
description: Repository-adaptive Kotlin production-code implementation and refactoring with compatible, idiomatic design. Use when the user asks to add, change, fix, migrate, or refactor Kotlin source code; exclude test-only, review-only, explanation-only, and build-configuration-only work.
---

# Write Kotlin

## Goal

Implement the requested production behavior in the repository's Kotlin dialect. Prefer the smallest
design that is correct here over an idealized rewrite or a showcase of language features.

## Scope

- Include Kotlin source implementation, bug fixes, migrations, and refactoring needed by the task.
- Include formatting, linting, compilation, and static analysis that directly validate the edit.
- Do not own test design, test implementation, or a code-review pass. Hand those off as described
  below instead of duplicating another skill's workflow.
- Do not broaden a source task into dependency, framework, or build-system modernization unless the
  requested behavior requires it.

## Workflow

### 1. Establish the local contract

Before designing, inspect:

1. Repository instructions and the exact requested behavior.
2. Kotlin/Gradle/Maven configuration: language and API versions, target platforms and source sets,
   compiler options, enabled experimental features, dependencies, and framework versions.
3. `.editorconfig`, formatter, linter, static-analysis, and explicit-API configuration.
4. The changed declaration's callers plus two or three nearby representative Kotlin files. Inspect
   Java or other-language consumers when the boundary is shared.
5. Existing tests only as evidence of behavior, naming, and seams. Do not turn this step into a
   testing workflow.

Infer a small task-specific profile: required compatibility, local naming and file organization,
error/null conventions, state and concurrency ownership, abstraction level, and verification
commands. Prefer explicit repository rules over sampled style and sampled style over generic
conventions. Do not copy an obvious local defect merely for consistency.

### 2. Apply this decision order

Resolve conflicts from top to bottom:

1. Requested behavior, correctness, security, resource safety, and cancellation.
2. Source, binary, behavioral, serialization, and interoperability compatibility.
3. Repository architecture, conventions, dependencies, and supported Kotlin version.
4. KISS: make the smallest coherent change with clear control and data flow.
5. YAGNI: implement today's requirement; avoid speculative switches, layers, and extension points.
6. GRASP: keep behavior with its information owner; favor high cohesion and low coupling.
7. SOLID and DRY as diagnostics for demonstrated change pressure, not quotas. Tolerate small
   duplication until the shared concept and variation axis are real.
8. Kotlin idioms that make the result clearer within the local profile.
9. Performance specialization only for a stated constraint, a known hot path, or evidence.

Never optimize for using more Kotlin features. A lower item cannot justify violating a higher one.

### 3. Load conditional guidance

| Change shape | Read |
|---|---|
| Small implementation using established local patterns | No reference |
| New abstraction, domain model, or public API | `references/kotlin-design-decisions.md` |
| Coroutines, Flow, shared state, or cancellation | `references/kotlin-design-decisions.md` |
| Java/JVM interop, multiplatform, experimental features, or compatibility-sensitive API | `references/kotlin-design-decisions.md` |
| Performance-sensitive collections, allocation, or inline/value-class choice | `references/kotlin-design-decisions.md` |

Read the reference only when one of these conditions applies.

### 4. Implement in the repository's dialect

- Preserve unrelated code and keep the diff proportional to the task.
- Prefer narrow visibility, `val`, read-only collection interfaces, and explicit domain
  invariants when they fit surrounding code.
- Express nullability deliberately. Avoid `!!` unless the invariant is externally guaranteed and
  locally evident; do not hide contract failures behind chains of safe calls.
- Use expressions, scope functions, extensions, defaults, sealed types, data/value classes,
  delegation, builders, operators, or DSLs only when their semantics are clearer than the simpler
  construct and the configured Kotlin version supports them.
- Keep transformations readable. Do not replace a clear loop with a dense chain or `Sequence`
  without a concrete laziness, short-circuiting, or allocation reason.
- Follow the repository's exception/result/logging conventions. Do not invent a parallel error
  model for one change.
- Keep comments focused on constraints and reasons. Let names and types explain mechanics.

### 5. Verify production code

1. Re-read the diff against the requested behavior and the local profile.
2. Check boundary cases, nullability, ownership, cancellation, public compatibility, and accidental
   unrelated formatting.
3. Run the repository's formatter/linter, narrowest useful compile or type-check, and configured
   static analysis. Fix failures caused by the change.
4. Report which checks ran and which did not. Compilation and static analysis do not substitute for
   tests.

### 6. Hand off testing and review

After the implementation is coherent, inspect the skills available in the current session:

- If a dedicated testing skill exists and the user's request authorizes tests, use it next. If tests
  are outside the current scope, propose that exact skill as the next iteration.
- Apply the same rule to a dedicated code-review skill after tests.
- If neither exists, explicitly state the remaining targeted test/review work instead of claiming
  the change is fully validated.

Do not embed generic test or review checklists in this skill.

## Guardrails

- Do not introduce an unsupported language feature, opt-in, dependency, compiler flag, or platform
  API merely because it is newer.
- Do not redesign stable neighboring code to make the edited fragment look uniformly ideal.
- Do not create interfaces, factories, repositories, use cases, wrappers, or DSLs without a current
  consumer or a concrete variation boundary.
- Treat public Kotlin declarations, inline code, serialized models, Java-facing APIs, and
  multiplatform `expect`/`actual` contracts as compatibility-sensitive.
- Ask before a change that materially expands scope, breaks compatibility, or selects among
  unresolved product semantics.
