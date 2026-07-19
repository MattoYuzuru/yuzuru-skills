---
name: search-workflow
description: Token-efficient local search routing for files, source code, structured data, archives, and documents. Use when the user asks to locate local files, symbols, annotations, code patterns, configuration values, or content in PDFs and other workspace artifacts.
---

# Search Workflow

## Goal

Find the smallest sufficient result set with the cheapest correct tool. Prefer a staged search over
dumping matches: discover candidate files or nodes first, then inspect only the relevant slices.

## Setup check

Resolve this installed skill directory before running helpers. If tool availability has not been
established in the current environment, run from the skill directory:

```bash
python3 scripts/search_setup.py check --profile core
```

If `complete` is true, continue without discussing setup. If tools are missing, keep working with
the listed fallbacks and show only the relevant commands from `install_commands`. Never execute an
installer unless the user explicitly authorizes that local write. Read `references/setup.md` only
when installation, platform support, or tool-selection rationale matters.

## Routing

| Intent | First choice | Read | Effect |
|---|---|---|---|
| File name or path inside a workspace | `rg --files` filtered by `rg` | none | read |
| Literal, regex, annotation word, error text | `rg` | none | read |
| Tracked Git content only | `git grep` or `git ls-files` | none | read |
| Syntax shape, declarations, calls, safe rewrite candidates | `ast-grep` | `references/structural-search.md` | read |
| Resolved definitions or references | Existing repository LSP/index, else `ast-grep` plus `rg` | `references/structural-search.md` | read |
| JSON, YAML, XML, TOML, CSV structure | `jq` or Mike Farah `yq` | `references/documents-and-data.md` | read |
| PDF, Office, ebook, SQLite, media metadata, nested archive | `rga` | `references/documents-and-data.md` | read |
| Machine-wide indexed file search | `mdfind` on macOS; `plocate`/`locate` on Linux | none | read |

Do not load both references unless the task spans both routes.

## Search funnel

1. Constrain the root before searching. Preserve the user's scope and inspect repository ignore
   rules before overriding them.
2. Use literal mode (`-F`) unless regex semantics are required. Add file types or globs early.
3. Discover candidates with file-only or count output: `rg -l`, `ast-grep
   --files-with-matches`, or `rga -l`.
4. If the candidate set is broad, refine the query instead of reading every match.
5. Inspect bounded details with line numbers and small context, for example `rg -n -m 20 -C 2`.
6. Summarize the result; include exact paths and lines needed for the task, not raw command output.

## Core decisions

- Default to `rg`; switching tools must add semantics, format support, or a materially smaller
  result. Do not switch merely for a speculative speed advantage.
- Use `rg --files | rg PATTERN` instead of requiring `fd`; it avoids a dependency and keeps output
  equivalent for agent workflows.
- Use lexical search first when the user remembers only one word from an annotation or symbol.
  Escalate to AST search only when syntactic role or arguments matter.
- Treat `ast-grep` as syntax-aware, not symbol-resolving. Do not infer an exact call graph from a
  textual or AST match.
- Prefer tools already exposed by the environment, such as an LSP or code index, when they provide
  stronger symbol semantics than a CLI fallback.
- Fall back to `find`/`grep`, language runtimes, or direct file reads when a specialist is absent;
  do not block a simple search on optional setup.

## Guardrails

- Keep searches read-only. A rewrite flag, index creation, OCR conversion, package installation, or
  cache deletion is a write and requires scope-appropriate authorization.
- Do not bypass ignore rules with `-uuu`, follow symlinks, or search outside the requested roots
  without a concrete reason.
- Avoid unbounded JSON/JSONL, full-file, and binary output. Cap results before returning them to the
  model context.
