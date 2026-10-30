# Hook Authoring

Hooks enforce fast deterministic invariants. They must not become hidden orchestration prompts.

Acceptable uses include secret-pattern blocking, manifest checks, forbidden-path checks, and
artifact-schema validation. Hooks must use fixture-testable stdin, bounded output, and clear
nonzero exits. Expensive tests, research, production calls, credential capture, automatic code
mutation, and unbounded logs are forbidden.

Plugin hook commands resolve the immutable package through `PLUGIN_ROOT` or
`CLAUDE_PLUGIN_ROOT`. Mutable state goes to `PLUGIN_DATA` or `CLAUDE_PLUGIN_DATA`. A missing host
variable must produce a clear diagnostic or select an XDG/temp fallback; never write the plugin
root.

Codex and Claude both require the user to trust plugin hooks. Installation must not be described as
hook trust. A user can disable a plugin; hooks may not fight that state.

Validate `hooks/hooks.json` with `schemas/hooks.schema.json` and run hook scripts with representative
JSON events before release.

Command hooks inspect executable command positions, not arbitrary matches in quoted data or
examples. Test shell wrappers, substitutions, heredocs, comments, and chained commands along with
the protected operation. The bounded inspector's canonical source is `scripts/hook_shell.py`;
run `python3 scripts/sync_hook_runtime.py` after changing it and `--check` to verify package copies.
Copies are intentional: installed plugins cannot depend on another plugin's filesystem location.
This heuristic does not replace native permissions or a sandbox. Keep its documented unsupported
syntax explicit and fail visibly when its bounded input cannot be analyzed.

Shell behavior references: [Bash shell operation](https://www.gnu.org/software/bash/manual/bash.html#Shell-Operation),
[Bash here-documents](https://www.gnu.org/software/bash/manual/bash.html#Here-Documents), and
[Python shlex limits](https://docs.python.org/3/library/shlex.html#improved-compatibility-with-shells).
