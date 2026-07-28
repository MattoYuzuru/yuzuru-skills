# Migration from the Skills-Only Layout

Top-level `skills/<name>/` paths remain unchanged. Existing symlinks continue to resolve after an
ordinary pull in the same clone.

`skill` remains a compatibility launcher for:

```text
list, install, uninstall, update, doctor, new, validate
```

`yuzuru skill ...` is the canonical command tree. The installer creates both launchers.

## Managed links

The user-local registry records links created by the new CLI. Older links are recognized
conservatively when their target is the current repository or has the historic
`yuzuru-skills/skills/<name>` shape. An unmanaged file or unrelated symlink is always a conflict and
is never replaced.

`yuzuru doctor --repair` can recreate only recognized managed stale links and a recognized launcher.
It does not install every skill or plugin, enable plugins, or rewrite native platform settings.

Stable renames belong in `schemas/migrations.json`. The registry applies append-only rename records
to managed links and reports guidance for anything it cannot repair safely.

`yuzuru update` refuses a dirty worktree, performs only `git pull --ff-only`, validates the updated
repository, repairs safe managed links, and reports marketplace refresh actions. It never resets,
stashes, rebases, merges, or restores plugin enabled state.
