# Pull Requests

## Detect And Read

After pushing a feature branch:

```bash
python3 scripts/github.py --repo owner/repo --cwd /checkout pr-candidate
python3 scripts/github.py --repo owner/repo pr-list --state open
python3 scripts/github.py --repo owner/repo pr-read 17
python3 scripts/github.py --repo owner/repo pr-files 17
python3 scripts/github.py --repo owner/repo pr-checks 17
```

`pr-candidate` derives the local branch, origin owner, repository default base, and
detects an existing open PR. Resolve ambiguous fork/upstream targets explicitly.

## Create And Update

```bash
python3 scripts/github.py --repo owner/repo pr-create \
  --title "Add GitHub workflow skill" \
  --head OWNER:feature/github-workflow \
  --body-file /tmp/pr.md --draft --dry-run
```

If `--base` is omitted, the helper reads the default branch. It rejects a duplicate
open head/base PR. After confirmation, use `--confirm-write` and return the verified PR.

Use `pr-update NUMBER` for title, body, base, or reopening. Use
`pr-metadata-update NUMBER` for assignees, labels, and milestone; PR metadata is
implemented through GitHub's issue-compatible endpoint. Add a PR to Projects V2 with
`project-add-item --pull-number NUMBER`.

## Close, Merge, And Delete Branch

- Preview `pr-close NUMBER`; require exact target `owner/repo#NUMBER`.
- Before merge, run `pr-read` and `pr-checks` again.
- Run `pr-merge NUMBER --expected-head-sha SHA --method squash --dry-run`.
- Merge requires the current SHA and green checks. `--allow-non-green` is allowed only
  after the user explicitly approves that exception.
- Require exact destructive confirmation of PR number, SHA, and merge method.
- Delete a feature branch separately with `branch-delete` and target
  `owner/repo@branch` only when the user requests cleanup.

GitHub cannot delete a pull request. Close it, and optionally delete its branch.
