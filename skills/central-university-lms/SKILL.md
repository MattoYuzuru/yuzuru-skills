---
name: central-university-lms
description: Read-only workflow for Central University LMS at my.centraluniversity.ru. Use when the user asks to inspect their current courses, homework, assignments, task descriptions, solutions, comments, statuses, deadlines, LMS course pages, or study workload using an authenticated local browser session.
---

# Central University LMS

## Overview

Use this skill to inspect the user's own Central University LMS account and produce compact summaries of courses, homework, deadlines, task descriptions, solutions, comments, and task history. It is read-only and uses Playwright with a local browser storage state.

Default LMS URL:

```text
https://my.centraluniversity.ru/learn/courses/view/actual/all
```

## Safety Rules

- Only access the user's own LMS account with their consent.
- Do not ask for or store the LMS password.
- Do not bypass 2FA, CAPTCHA, access controls, or paywalls.
- Store browser session state outside the repo at `~/.config/yuzuru-codex-skills/central-university-lms/storage-state.json`.
- Do not commit cookies, tokens, screenshots with private data, assignment files, or downloaded course materials.
- Do not submit homework, change profile data, mark lessons complete, or send messages in this skill version.

## Routing

| Intent | Run | Effect |
|---|---|---|
| Set up or repair the local runtime | `python3 scripts/bootstrap.py` | local setup |
| List courses | `lms.py list-courses` | read |
| Inspect a course's materials and exercises | `lms.py course-overview <course_id>` | read |
| Find upcoming assignments | `lms.py deadlines` | read |
| Read a task's description, solution, comments, history, and metadata | `lms.py task-details <longread_id>` | read |
| Verify the supported API route chain | `lms.py api-health <course_id> <longread_id>` | read |

## Setup

Resolve the installed skill directory and run all commands below from it. Never assume the current directory is this repository.

1. Create or reuse the skill's isolated environment. It works on macOS, Linux, and Windows; its JSON output contains the exact Python executable to use for `lms.py`:

```bash
# macOS/Linux
python3 scripts/bootstrap.py
# Windows
py -3 scripts/bootstrap.py
```

2. If no storage state exists, let the user log in manually in a headed browser. Yandex SmartCaptcha flags headless Chrome, so do not pass `--headless` to `login`:

```bash
<python-from-bootstrap> scripts/lms.py login
```

3. If an API command reports `self-signed certificate in certificate chain`, export the organization's trusted PEM bundle before retrying:

```bash
export NODE_EXTRA_CA_CERTS=/path/to/trusted-corporate-root.pem
```

Read `references/environment.md` only for OS-specific setup, CA bundle export, or headless-operation questions.

## Workflow

Prefer the JSON API commands below over DOM scraping — they read the LMS's own structured data instead of guessing from rendered text.

1. List current courses:

```bash
<python-from-bootstrap> scripts/lms.py list-courses
```

Returns `{totalCount, count, items[]}` with course id/name/category; auto-paginates.

2. Drill into a course's stages/materials/homework (course id from step 1):

```bash
<python-from-bootstrap> scripts/lms.py course-overview <course_id>
```

Returns `themes[]` (stages, e.g. "Неделя 1: ...") → each theme's `longreads[]` (materials/lab-work blocks) → each longread's `exercises[]` (homework items with `name`, `maxScore`, `activity.name`, `deadline`).

3. Course score summary:

```bash
<python-from-bootstrap> scripts/lms.py course-progress <course_id>
```

4. Upcoming deadlines across all published courses (walks step 1 + step 2 for every course, flattens exercises with a `deadline`, filters to the future by default):

```bash
<python-from-bootstrap> scripts/lms.py deadlines --limit 20
# add --include-past to see everything, including already-passed deadlines
```

5. Read one assignment in full (use the longread id from `course-overview`). The result includes a direct LMS URL, plain-text description and links, solution, task information, status history, and comments:

```bash
<python-from-bootstrap> scripts/lms.py task-details <longread_id>
# add --exercise-id <id> only if the longread has more than one task
```

6. After an LMS API or frontend change, validate the supported API chain for a known course/longread:

```bash
<python-from-bootstrap> scripts/lms.py api-health <course_id> <longread_id>
```

### DOM fallback

Only fall back to these if an API endpoint above starts returning errors. `click-text-discover` is a diagnostic tool, not a routine navigation mechanism:

```bash
<python-from-bootstrap> scripts/lms.py discover-api --seconds 20   # re-capture real endpoints; run headed
<python-from-bootstrap> scripts/lms.py snapshot                     # raw DOM dump
<python-from-bootstrap> scripts/lms.py deadlines-dom                # regex over rendered text
```

## Output Contract

When reporting to the user, prefer:

- course name;
- stage/theme name (for course-overview);
- assignment/homework title;
- deadline as returned by the API (ISO 8601, already reliable — no need to flag as inferred);
- max score / activity weight if relevant to the question;
- course id if the user may want to drill in further;
- direct task URL, description links, status, solution, and comments for task-detail requests;
- if a DOM fallback command was used instead, mark results as inferred/uncertain.

## References

Read `references/discovery.md` before changing extraction logic or adding new endpoints.
