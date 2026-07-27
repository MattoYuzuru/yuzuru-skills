# Kotlin Design Decisions

Use this reference only for non-routine design, concurrency, interop, compatibility, or performance
choices. Repository evidence and the priority order in `SKILL.md` still win.

## Abstraction gates

| Candidate | Use when | Prefer something simpler when |
|---|---|---|
| Interface | Multiple implementations exist now, a volatile external boundary needs isolation, or the framework requires one | It would have one implementation created only for “testability” or hypothetical substitution |
| Base class | There is a stable is-a relationship with shared invariant-bearing state or behavior | Composition or delegation expresses the relationship |
| Extension | Stateless behavior naturally reads as an operation on the receiver and belongs in the receiver's domain | It hides important dependencies, ownership, or side effects |
| `data class` | Value semantics and generated `equals`, `hashCode`, `toString`, `copy`, and destructuring are all acceptable | Identity or lifecycle matters, or generated API would leak mutable/sensitive state |
| Value class | One value needs a distinct domain type and its runtime/interop limitations are acceptable | Serialization, reflection, generic boxing, or Java consumers make representation important |
| Sealed hierarchy | The variant set is intentionally closed and exhaustive handling is valuable | Third parties or distant modules must extend it |
| Enum | Instances are fixed singleton constants with little variant-specific state | Variants need distinct payloads or behavior |
| Type alias | A repeated type has a clearer domain name without needing a new type boundary | Runtime distinction or validation is required |
| Builder or DSL | Construction has many optional/nested parts and the repository already values declarative APIs | A constructor, defaults, or named arguments remain clear |

Create an abstraction only after naming its present responsibility, current consumers, and actual
variation axis. Apply SRP at the repository's normal granularity. Apply dependency inversion at
volatile boundaries, not between every class. Treat repeated syntax as evidence only after it
represents the same concept and changes for the same reason.

## Language-feature gates

- Prefer a direct expression body only while error handling and control flow remain obvious.
- Use `when` exhaustively for closed domains. Do not add a catch-all branch that masks a newly added
  variant when exhaustiveness is part of the safety.
- Use scope functions by receiver/result intent and keep chains short. Avoid nested implicit
  receivers or repeated `it`; name values when more than one role is present.
- Use `let` for a scoped transformation or nullable branch, not as punctuation around every value.
  Use `apply`/`also` only when their returned receiver matches the surrounding expression's intent.
- Use operator, infix, delegated-property, context-receiver, and DSL features only when the
  repository already establishes the semantics or the domain notation is unmistakable.
- Use `inline`/`reified` for a measured call-site or type-erasure need. Account for code size,
  non-local returns, and public inline ABI before exposing them.
- Prefer explicit validation (`require`, `check`, domain errors, or an established result type) to
  a forced non-null assertion. Match existing boundary semantics instead of standardizing locally.
- Prefer immutable snapshots and single ownership of mutation. Read-only Kotlin collection
  interfaces are not proof that the backing collection cannot change.

## Public API and compatibility

- Determine whether the declaration is internal application code, a module boundary, or a published
  API before changing its shape.
- Preserve source, binary, and behavioral contracts independently. Defaults, overloads, generated
  `componentN`/`copy`, sealed variants, nullability, variance, and exception behavior can affect
  callers differently.
- Follow explicit-API mode when enabled. Otherwise, still write intentional public return types
  where inference could expose an implementation detail.
- Treat public inline bodies and declarations reachable from them as published implementation.
- Add `@JvmName`, `@JvmStatic`, `@JvmField`, `@JvmOverloads`, wildcards, or use-site targets only for
  a demonstrated Java/framework consumer.
- At Java boundaries, contain platform types early and decide nullability explicitly. Do not let an
  inferred platform type spread into domain code.
- Check serialization and reflection frameworks before changing constructor parameters, property
  names, defaults, visibility, annotations, or class kind.

## Coroutines, Flow, and shared state

- Preserve structured concurrency and the lifecycle owner. Do not introduce `GlobalScope`,
  fire-and-forget jobs, or an unmanaged `CoroutineScope`.
- Let suspend functions inherit caller context unless the established layer owns dispatcher
  selection. Do not wrap non-blocking suspend calls in arbitrary dispatchers.
- Keep cancellation cooperative. Do not swallow cancellation in broad exception handlers; clean up
  resources in cancellation-safe constructs.
- Use `async` for concurrent results, not as a default wrapper around sequential work. Await children
  inside their owning scope.
- Choose `Flow`, `StateFlow`, `SharedFlow`, or `Channel` from delivery and ownership semantics, not
  popularity. Define hot/cold behavior, replay, buffering, backpressure, and terminal lifecycle.
- Prefer confined or immutable state. When sharing mutation, make synchronization and atomic update
  semantics explicit and consistent with the platform.

## Platforms and feature stability

- Keep common source sets free of platform APIs. Place platform behavior in the repository's
  established `expect`/`actual`, interface, or source-set boundary.
- Verify language/API version and component stability before using a recent or experimental feature.
  Add an opt-in only when the task needs the feature and the repository accepts that stability cost.
- Respect JVM target, Android API/desugaring limits, Native memory/concurrency constraints, and
  JavaScript/Wasm export rules that apply to the actual source set.

## Performance gates

- Prefer eager collection operations for small, simple pipelines. Use `Sequence` when laziness,
  short-circuiting, repeated stages on meaningful input, or avoided intermediates plausibly matters.
- Avoid allocation or boxing workarounds until the relevant target and call shape are known. Value
  classes, primitive arrays, inline functions, and sequences each have contexts where their expected
  optimization disappears.
- Preserve clarity unless the task states a budget, the path is already known to be hot, or a
  benchmark/profile demonstrates the tradeoff. Record the evidence behind a less-readable choice.

When feature availability or stability is uncertain, verify it against the configured Kotlin
version and official Kotlin documentation rather than relying on memory.
