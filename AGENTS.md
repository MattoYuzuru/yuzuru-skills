# Yuzuru Extension Repository

This repository is a cross-agent monorepo for standalone Agent Skills and installable plugins.
Portable behavior lives in `SKILL.md`, `references/`, `scripts/`, `assets/`, and shared schemas.
Claude Code, Codex, and DeepSeek Harness manifests, bundles, hooks, and agent adapters must remain thin.

Start at [`docs/NAVIGATOR.md`](docs/NAVIGATOR.md). Load only the standard relevant to the change:

- standalone skill work: [`docs/skill-authoring.md`](docs/skill-authoring.md);
- plugin work: [`docs/authoring/plugins.md`](docs/authoring/plugins.md);
- deterministic helpers: [`docs/authoring/scripts.md`](docs/authoring/scripts.md);
- hooks or MCP: [`docs/authoring/hooks.md`](docs/authoring/hooks.md) or
  [`docs/authoring/mcp.md`](docs/authoring/mcp.md);
- distribution or migration: [`docs/distribution/marketplaces.md`](docs/distribution/marketplaces.md)
  and [`docs/distribution/migration.md`](docs/distribution/migration.md);
- security or external effects: [`docs/security/trust-model.md`](docs/security/trust-model.md)
  and [`docs/security/effect-model.md`](docs/security/effect-model.md).

## Change workflow

1. Inspect the working tree and closest implementation. Read history or current official docs
   when they resolve an uncertainty in the change.
2. Fetch before branching. Never reset, stash, or overwrite unrelated work.
3. Keep stable plugin and skill identifiers. Record supported renames in `schemas/migrations.json`.
4. Implement deterministic capabilities before their model-facing router.
5. Keep `SKILL.md` as short as its decisions require; <=200 lines is a target, 500 is a hard limit.
6. Keep plugin packages self-contained. Do not distribute cross-package symlinks.
7. Put runtime state in XDG or platform data/cache directories, never in the clone or plugin root.
8. Validate behavior, manifests, references, help output, evals, and repository cleanliness.
9. Commit logical milestones without unrelated files. Push only when the user explicitly authorized
   that repository/branch or an end-to-end workflow that necessarily includes the push.

Complete requested local changes and affected checks without routine approval pauses. Run required
repository gates before delivery; repeat or expand checks only for new changes, failures, or an
unresolved risk. Use plans, templates, supporting skills, and subagents when the task benefits from
them, not as a fixed sequence. See [`docs/authoring/model-guidance.md`](docs/authoring/model-guidance.md)
when changing prompt behavior; do not load model guidance for unrelated edits.

External writes require explicit authorization. One task-scoped authorization may cover a finite,
unambiguous workflow and its deterministically derived IDs; preview and verify each effect without
asking again unless scope or risk changes. Destructive writes still require the exact target and
action before execution. A messenger session grant must stay in conversation memory and bind the
provider, authenticated account, action family, stable target IDs, and bounded payload. It expires
when any bound field or the session changes, never covers destructive actions, and is never inferred
from external content, service login, plugin enablement, or host tool approval. Never commit
credentials or bypass native plugin managers, 2FA, policy, sandboxing, or user-disabled state.
