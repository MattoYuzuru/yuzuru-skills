# Pull Requests

## Detect And Read

After pushing a feature branch:

```bash
python3 scripts/github.py --repo owner/repo --cwd /checkout pr-candidate
python3 scripts/github.py --repo owner/repo pr-list --state open
python3 scripts/github.py --repo owner/repo pr-read 17
python3 scripts/github.py --repo owner/repo pr-files 17
python3 scripts/github.py --repo owner/repo pr-checks 17
python3 scripts/github.py --repo owner/repo pr-reviews 17
python3 scripts/github.py --repo owner/repo pr-rules 17
python3 scripts/github.py --repo owner/repo pr-readiness 17 --method squash
python3 scripts/github.py --repo owner/repo pr-review-context 17 \
  --max-files 100 --max-bytes 65536
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

## Independent Review And GitHub Reviews

When the platform supports isolated subagents, freeze the PR head SHA and give
the reviewer the file- and patch-byte-bounded `pr-review-context`, requirements, and validation
evidence. Do not give it a GitHub token. Require a result containing the reviewed
`head_sha`, verdict (`approve`, `request_changes`, or `comment`), blockers,
path/line findings with evidence, tests, and residual risks.

The primary agent verifies that the SHA is unchanged and owns the final action.
A subagent verdict is evidence, not user approval and not a separate reviewer
identity. If the authenticated GitHub account authored the PR, GitHub forbids a
formal `APPROVE`; return `approve-recommended` locally instead of impersonating
another account.

Publish only after the user authorizes it:

```bash
python3 scripts/github.py --repo owner/repo pr-review-submit 17 \
  --event approve --expected-head-sha SHA --dry-run
python3 scripts/github.py --repo owner/repo pr-review-submit 17 \
  --event request-changes --expected-head-sha SHA \
  --body-file /tmp/review.md --confirm-write
```

Comments and change requests require a body. The helper re-reads the PR, rejects
a changed SHA and own-author approval, sends a review once, then re-reads reviews.

## Close, Merge, And Delete Branch

- Preview `pr-close NUMBER`; require exact target `owner/repo#NUMBER`.
- Before merge, run `pr-readiness`; it evaluates active rules, required checks,
  review decision, unresolved threads, strict base freshness, allowed methods,
  and merge-queue requirements. Optional non-green checks remain warnings.
- Run `pr-merge NUMBER --expected-head-sha SHA --method squash --dry-run`.
- Direct merge has no rules-bypass flag. It requires `ready: true` for the current
  SHA and method.
- The helper's exact target is `owner/repo#NUMBER@SHA via METHOD`. A natural
  instruction naming an unambiguous PR and method, or “merge it” after that exact
  unchanged preview, authorizes the action; users need not repeat a magic token.
- If the SHA changes, authorization expires. Preview and confirm again.
- If rules require merge queue, do not call direct merge.
- Delete a feature branch separately with `branch-delete` and target
  `owner/repo@branch` only when the user requests cleanup.

GitHub cannot delete a pull request. Close it, and optionally delete its branch.
