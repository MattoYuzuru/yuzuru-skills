# Yuzuru Extension Repository

This repository is a cross-agent monorepo for standalone Agent Skills and installable plugins.
Portable behavior lives in `SKILL.md`, `references/`, `scripts/`, `assets/`, and shared schemas.
Claude Code and Codex manifests, hooks, and agent adapters must remain thin.

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

1. Inspect the working tree, history, closest implementation, and relevant official platform docs.
2. Fetch before branching. Never reset, stash, or overwrite unrelated work.
3. Keep stable plugin and skill identifiers. Record supported renames in `schemas/migrations.json`.
4. Implement deterministic capabilities before their model-facing router.
5. Keep ordinary `SKILL.md` files near 100–250 lines and below the 500-line hard limit.
6. Keep plugin packages self-contained. Do not distribute cross-package symlinks.
7. Put runtime state in XDG or platform data/cache directories, never in the clone or plugin root.
8. Validate behavior, manifests, references, help output, evals, and repository cleanliness.
9. Commit logical milestones without unrelated files. Push only after separate explicit approval.

External writes require explicit authorization; destructive writes require exact target
confirmation. Never commit credentials or bypass native plugin managers, 2FA, policy, sandboxing,
or user-disabled state.
