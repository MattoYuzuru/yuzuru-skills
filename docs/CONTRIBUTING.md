# Contributing

1. Read `AGENTS.md` and the relevant navigator entry.
2. Inspect the tree, history, closest package, evals, and current official integration docs.
3. Fetch and create a dedicated branch without touching unrelated work.
4. Define trigger boundaries, effects, outputs, platform support, and test evidence.
5. Implement portable behavior first and adapters second.
6. Run focused tests before each logical commit and the complete suite before handoff.
7. Review path portability, runtime cleanliness, secret handling, and completion language.
8. Create local Conventional Commit-compatible commits.

Follow the task-scoped authorization model in `AGENTS.md` for pushes, pull requests, comments,
uploads, publication, and other external writes. Do not invent a second approval loop for effects
already covered by an unchanged finite mandate.
