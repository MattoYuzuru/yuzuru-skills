# Homework Manifest Contract

Read this reference for export, local solution preparation, or future submission work.

## Pending Export

`export-pending` emits schema version 1 with bounded `items[]`. Each item includes stable LMS task,
exercise, and longread identifiers; course/theme labels; task and condition links; deadline; current
state; solution type; and a state snapshot. Treat the file as private student data.

The unfinished-state filter excludes tasks with submission/evaluation timestamps and known terminal
states. Review the exported list before treating it as authoritative because the private LMS can add
new state names.

## Completed Solutions

Prepare a separate file:

```json
{
  "schemaVersion": 1,
  "submissions": [
    {
      "taskId": "<task-id-from-export>",
      "solutionUrl": "https://example.com/completed-solution",
      "expectedState": "<state-from-export>"
    }
  ]
}
```

`solutionUrl` must be HTTPS and contain no embedded credentials. `taskId` must be unique. The
validator accepts at most 200 entries and performs no LMS requests.

## Write Enablement Gate

Before implementing `submit-link` or `submit-manifest`:

1. Obtain authorization for one exact task and solution URL.
2. Run headed `observe-action --confirm-write-observation` while the user submits it manually.
3. Store only the sanitized observation; never store cookies, CSRF values, or the solution URL body.
4. Add a sanitized request/response fixture and a mocked transport test.
5. Implement a task-state preflight, explicit finite-manifest confirmation, single write attempt,
   and post-write GET verification.
6. On timeout or 5xx, re-read the task before deciding whether a retry is safe.

Keep comments, attachments, draft saving, and lesson completion as separate capabilities with their
own observed contracts and effects.
