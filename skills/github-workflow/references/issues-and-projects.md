# Issues And Projects

## Read And Search

```bash
python3 scripts/github.py --repo owner/repo issue-search "label:bug crash" --limit 20
python3 scripts/github.py --repo owner/repo issue-list --state open
python3 scripts/github.py --repo owner/repo issue-read 42
python3 scripts/github.py --repo owner/repo label-list
python3 scripts/github.py --repo owner/repo milestone-list --state all
```

Search is constrained to the resolved repository and `is:issue`. Repository issue
lists exclude pull requests even though GitHub's issue endpoint returns both.

## Create And Update

Put long Markdown in a file:

```bash
python3 scripts/github.py --repo owner/repo issue-create \
  --title "Handle interrupted uploads" \
  --body-file /tmp/issue.md \
  --assignees octocat \
  --labels bug backend \
  --milestone "Version 1" \
  --dry-run
```

The helper validates assignees, labels, and milestone before writing. It never creates
missing labels or milestones implicitly. Use `issue-update NUMBER` with the same
metadata options. Pass empty `--assignees` or `--labels` to clear them; pass
`--milestone none` to clear the milestone.

After the exact preview is approved, replace `--dry-run` with `--confirm-write`.
Close with `issue-close NUMBER --dry-run`, then exact destructive confirmation
`owner/repo#NUMBER`. GitHub does not expose issue deletion.

## Projects V2

Projects V2 uses GraphQL, not the REST Projects Classic endpoints:

```bash
python3 scripts/github.py --repo owner/repo project-list \
  --owner OWNER --owner-type user
python3 scripts/github.py --repo owner/repo project-add-item \
  --owner OWNER --owner-type user --project-number 2 --issue-number 42 --dry-run
python3 scripts/github.py --repo owner/repo project-field-set \
  --project-id PVT_ID --item-id PVTI_ID --field-id PVTSSF_ID \
  --single-select-option-id OPTION_ID --dry-run
```

Use `--owner-type organization` for organization projects. Adding an issue/PR and
setting its project field are separate mutations; GitHub cannot combine them. Report
partial success instead of hiding a created issue or added item when the second step
fails. Obtain `read:project` for reads and `project` for writes when using a classic PAT.
