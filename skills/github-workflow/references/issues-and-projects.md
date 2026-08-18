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
python3 scripts/github.py project-read \
  --project https://github.com/users/OWNER/projects/4/views/1
python3 scripts/github.py project-field-list \
  --project https://github.com/users/OWNER/projects/4
python3 scripts/github.py project-view-list \
  --project https://github.com/users/OWNER/projects/4
python3 scripts/github.py project-item-list \
  --project https://github.com/users/OWNER/projects/4 \
  --query 'status:"In review" is:open' --limit 20
python3 scripts/github.py project-count \
  --project https://github.com/users/OWNER/projects/4 \
  --query 'status:Backlog created:>=2026-08-01'
python3 scripts/github.py project-stats \
  --project https://github.com/users/OWNER/projects/4 \
  --group-by Status --scan-limit 1000
python3 scripts/github.py --repo owner/repo project-add-item \
  --project https://github.com/users/OWNER/projects/4 --issue-number 42 --dry-run
python3 scripts/github.py project-field-set \
  --project https://github.com/users/OWNER/projects/4 \
  --item-id PVTI_ID --field Status --value "In review" --dry-run
```

Project URLs under `/users/` and `/orgs/` are first-class targets and may include
`/views/NUMBER`; project-only reads do not require a repository checkout. `--query`
is passed as a GraphQL variable to GitHub's native Projects filter engine. Use
`project-count` for an exact cheap count and `project-stats` for bounded grouping;
an `exact: false` result means the scan limit was reached.

The URL view number records the user's intended context, but GitHub's API does
not expose the complete interactive view configuration as an executable query.
Do not claim that a URL suffix applies the browser view's filters, grouping, or
slicing. Pass an explicit `--query`; treat Status field options as workflow
values rather than assuming every saved view renders them as board columns.

`project-field-list` returns field and option IDs. `project-field-set --field
--value` resolves text, number, date, single-select, and iteration values by exact
case-insensitive names and rejects ambiguity. Moving a card means setting its
`Status` field. Assignees, labels, milestones, repository, and other issue/PR
properties must be changed through their owning APIs, not project field mutation.

Adding an issue/PR and setting its project field are separate mutations; GitHub
cannot combine them. Report partial success instead of hiding a created issue or
added item when a later step fails. Obtain `read:project` for reads and `project`
for writes when using a classic PAT.
