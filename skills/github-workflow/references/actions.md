# GitHub Actions

## Inspect

```bash
python3 scripts/github.py --repo owner/repo workflow-list
python3 scripts/github.py --repo owner/repo run-list --branch feature/x --limit 10
python3 scripts/github.py --repo owner/repo run-read RUN_ID
python3 scripts/github.py --repo owner/repo run-jobs RUN_ID
python3 scripts/github.py --repo owner/repo job-read JOB_ID
python3 scripts/github.py --repo owner/repo run-failures RUN_ID
```

`run-failures` returns failed jobs, steps, and bounded job-log excerpts. Defaults are
four jobs and 64 KiB per log; output marks truncation. Use `--no-logs` for metadata
only. Cross-host log redirects drop Authorization headers.

## Watch

```bash
python3 scripts/github.py --repo owner/repo run-watch RUN_ID --deadline 1200
```

Watch starts at a 5-second interval, grows by 1.5 with jitter, caps at 30 seconds,
and stops at the deadline. Progress is compact JSON on stderr; the final run and jobs
are emitted once on stdout. This is state polling, separate from transport retries.

## Rerun, Dispatch, And Cancel

Preview every mutation:

```bash
python3 scripts/github.py --repo owner/repo run-rerun-failed RUN_ID --dry-run
python3 scripts/github.py --repo owner/repo job-rerun JOB_ID --dry-run
python3 scripts/github.py --repo owner/repo workflow-dispatch validate.yml \
  --ref feature/x --inputs '{"suite":"full"}' --dry-run
python3 scripts/github.py --repo owner/repo run-cancel RUN_ID --dry-run
```

Use `run-rerun` for the entire run. Rerun and dispatch are writes and require
`--confirm-write`. Cancel is destructive and requires `--confirm-destructive` plus
the exact target `owner/repo:run:RUN_ID`.

Do not repeatedly rerun a failing job. Diagnose logs, change code, push after approval,
and watch the newly triggered run. Never retry mutating HTTP calls automatically;
their first outcome may be unknown.
