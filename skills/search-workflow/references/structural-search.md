# Structural source search

Read this reference only when lexical matching cannot express the code shape or would return
comments, strings, and unrelated syntax.

## Funnel

1. Identify the language and write the smallest valid code pattern.
2. Use uppercase metavariables such as `$CALL` for one AST node and `$$$ARGS` for zero or more
   nodes.
3. Request files first, then inspect matches only in the shortlisted paths.
4. Use JSON stream output only when a downstream program needs fields; it is usually larger than
   concise human output.

```bash
ast-grep -p 'console.log($$$ARGS)' -l ts --files-with-matches src/
ast-grep -p 'console.log($$$ARGS)' -l ts src/selected.ts
ast-grep -p 'console.log($$$ARGS)' -l ts --json=stream src/selected.ts
```

Use `--globs` to constrain mixed-language trees. Respect ignore files by default.

## Annotation remembered by one word

Start lexically because a partial remembered word is not yet an AST shape:

```bash
rg -n -F 'Transactional' -g '*.java' .
```

Escalate only if the task requires distinguishing declarations, calls, arguments, or other
syntactic roles. This lexical-first step is typically cheaper than guessing a language-specific AST
pattern.

## Limits

- `ast-grep` understands syntax, not type resolution or symbol identity. Same-named functions may
  be unrelated.
- Prefer an existing language server or repository code index for definitions, references,
  implementations, and rename semantics.
- Treat rewrites as writes. Preview matches first; do not use `--update-all` without explicit user
  authorization and a verified target set.

Official documentation: <https://ast-grep.github.io/guide/pattern-syntax.html>
