---
name: central-university-lms
description: Central University LMS workflow for headless course and homework inspection, exporting unfinished assignments, validating solution-link manifests, and safely discovering authenticated write requests. Use when the user asks to inspect or synchronize their courses, tasks, conditions, solutions, comments, statuses, or deadlines at my.centraluniversity.ru.
---

# Central University LMS

## Overview

Inspect the user's LMS through its structured API and export bounded homework manifests for
autonomous work. Prepare solution links locally and observe one user-performed submission to learn
the private write contract safely. The helper does not yet replay write requests.

Resolve the installed skill directory and run commands from it. API commands are headless by
default; pass `--headed` only for diagnostics.

## Routing

| Intent | Read | Run | Effect |
|---|---|---|---|
| Set up or repair runtime/auth | `references/environment.md` | `bootstrap.py`, `lms.py login` | local setup |
| Check saved session | `references/environment.md` | `lms.py session-check` | read |
| List courses or course structure | — | `list-courses`, `course-overview`, `course-progress` | read |
| Inspect deadlines or one task | — | `deadlines`, `task-details`, `api-health` | read |
| Export unfinished homework | `references/submissions.md` | `export-pending` | read / local write |
| Validate completed solution links | `references/submissions.md` | `validate-submissions` | local read |
| Discover a real submission request | `references/discovery.md` | `observe-action` | user-performed write |
| Diagnose a frontend/API change | `references/discovery.md` | `discover-api`, DOM fallbacks | read |

Read only the selected reference.

## Setup

Create or reuse the isolated runtime:

```bash
# macOS/Linux
python3 scripts/bootstrap.py
# Windows
py -3 scripts/bootstrap.py
```

Use the returned Python executable for `lms.py`. If no valid storage state exists, let the user
authenticate in the headed browser:

```bash
<python> scripts/lms.py login
<python> scripts/lms.py session-check
```

Never establish or refresh a session headlessly. If a command returns `reauth_required`, run
`login`; do not bypass SSO, CAPTCHA, 2FA, or access controls.

## Read Workflow

```bash
<python> scripts/lms.py list-courses
<python> scripts/lms.py course-overview <course_id>
<python> scripts/lms.py course-progress <course_id>
<python> scripts/lms.py deadlines --limit 20
<python> scripts/lms.py task-details <longread_id>
<python> scripts/lms.py api-health <course_id> <longread_id>
```

Use `--exercise-id <id>` for a longread containing multiple assigned tasks. Prefer these API
commands over DOM scraping.

## Homework Synchronization

Export unfinished work to stdout or a private `0600` JSON file:

```bash
<python> scripts/lms.py export-pending --output pending-homework.json
```

After work is completed, create the submission manifest described in
`references/submissions.md`, then validate it without touching LMS:

```bash
<python> scripts/lms.py validate-submissions completed-homework.json
```

`submit-manifest` remains intentionally unavailable until the actual endpoint, request body, and
post-write verification GET are captured and fixture-tested. Never invent or guess this private API.

## Guardrails

- Access only the user's own account with consent.
- Keep storage state, exported homework, observations, and solution manifests outside the repo.
- Never print profile endpoints, cookies, authorization/CSRF values, or raw task responses.
- Treat manual submission during `observe-action` as an external write. Require authorization for
  one exact task and solution URL, then pass `--confirm-write-observation`.
- Never click UI controls automatically during discovery and never replay an observed write.
- Do not automatically retry POST, PUT, PATCH, or DELETE. After an ambiguous result, read task state.
- A future batch write may use one approval for an exact finite manifest; never expand that batch.

## DOM Fallback

Only after an API endpoint fails:

```bash
<python> scripts/lms.py discover-api --seconds 20
<python> scripts/lms.py snapshot
<python> scripts/lms.py deadlines-dom --limit 20
```

Mark DOM-derived results as inferred.

## Output

Return compact course/task names, deadlines, status, direct task URLs, condition links, solution
state, and relevant comments. Preserve the API's ISO 8601 deadlines. Report `truncated` and limits
instead of silently returning unbounded collections.
