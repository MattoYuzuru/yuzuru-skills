# Technical and instructional writing

Optimize for a reader completing a task or building an accurate mental model.

## Task-oriented order

1. State the outcome and relevant scope.
2. Give prerequisites and permissions before the procedure.
3. Put each action before its expected result.
4. State conditions where they change the action.
5. Include failure states, recovery, and verification proportional to risk.

Use meaningful headings that let the reader locate a task or concept. Use a
numbered list for an ordered procedure and bullets for an unordered set. Do not
turn explanatory prose into steps when there is no sequence.

## Precision

- Keep code, commands, flags, paths, identifiers, API fields, and UI labels exact.
- Use one term for one concept; do not decorate repeated terms with synonyms.
- Define an unfamiliar term at first useful occurrence, near the task it affects.
- Distinguish requirement, recommendation, default, example, and possibility.
- Name the version, platform, permission, or precondition when behavior depends on it.
- Prefer an imperative for direct actions, but do not invent an actor for system behavior.

Active voice helps when the reader needs responsibility: “Сервис записывает
событие”. Passive voice can correctly foreground a result or procedure:
“Событие сохраняется до подтверждения”. Choose by information focus, not a ban.

Nominalizations can name stable technical concepts such as “аутентификация” or
“развёртывание”. Unpack them only when they conceal an action the reader must
understand: “после выполнения валидации” may become “после того как сервер
проверит запрос”.

## Verification

Check that prerequisites are sufficient, every placeholder is explained, steps
can be followed in order, expected output is observable, and failure guidance
does not promise recovery the system cannot provide. Preserve byte-sensitive
fragments and run the invariant checker for substantial rewrites.

Operational conventions are consistent with the
[Google developer documentation style guide](https://developers.google.com/style)
and [Microsoft Writing Style Guide](https://learn.microsoft.com/style-guide/),
but local project terminology and tested behavior remain authoritative.
