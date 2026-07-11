# Repositories And Git

## Repository Commands

```bash
python3 scripts/github.py --repo owner/repo repo-info
python3 scripts/github.py --repo owner/repo repo-languages
python3 scripts/github.py --repo owner/repo --cwd /checkout repo-context
python3 scripts/github.py --repo owner/repo repo-update-about \
  --description "Short project description" --homepage "https://example.com" --dry-run
python3 scripts/github.py --repo owner/repo repo-topics-set python automation agent-skills --dry-run
```

`repo-update-about` changes description and/or homepage. `repo-topics-set` replaces
the complete topic set; inspect the normalized dry-run list before confirming. Pass
no topics to clear the set.

After user confirmation, replace `--dry-run` with `--confirm-write`. The helper
reads the repository again after a successful update.

## Local Git Workflow

1. Run `git status --short --branch`, inspect remotes, and identify unrelated changes.
2. Run `git fetch --prune` when remote freshness matters.
3. Use `git pull --ff-only`; never create an implicit merge or rebase.
4. Read the default branch with `repo-info`; do not guess `main` or `master`.
5. Create a focused feature branch from the intended base.
6. Edit, test, inspect the diff, and stage only task files.
7. Commit coherent checkpoints with clear one-line messages.
8. Show exact remote and branch, then ask before `git push -u REMOTE BRANCH`.
9. After push, use `pr-candidate` and the PR route.

Do not wrap these Git commands in the API helper. Preserve the user's Git credential
configuration. Never put tokens in remote URLs or output.

## Push And Cleanup

Push is an external write even when a coding task authorized local edits and commits.
Require explicit confirmation of remote and branch. Never push directly to the
default upstream branch unless the user explicitly names it.

Do not use `--force`. If history repair is explicitly required, show the lease target
and require exact destructive confirmation before `--force-with-lease`.

Remote branch deletion is separate from PR close or merge. Use `branch-delete
BRANCH --dry-run`; then require exact confirmation such as `owner/repo@feature/name`.
