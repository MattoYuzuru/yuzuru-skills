---
name: central-university-lms
description: Read-only workflow for Central University LMS at my.centraluniversity.ru. Use when the user asks to inspect their current courses, homework, assignments, deadlines, LMS course pages, or study workload using an authenticated local browser session.
---

# Central University LMS

## Overview

Use this skill to inspect the user's own Central University LMS account and produce compact summaries of courses, homework, and deadlines. The first version is read-only and uses Playwright with a local browser storage state.

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

## Setup

1. If no storage state exists, run interactive login and let the user sign in manually. The LMS uses Yandex SmartCaptcha, which flags headless Chrome — this step must run headed:

```bash
python3 skills/central-university-lms/scripts/lms.py login
```

2. Before any command that hits `/api/...` (everything except `snapshot`, `deadlines-dom`, `discover-api`, `click-text-discover`), export a CA bundle that includes the corporate TLS-inspection root, or every API call fails with "self-signed certificate in certificate chain":

```bash
security find-certificate -a -p /Library/Keychains/System.keychain > /tmp/corp-ca.pem
security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain >> /tmp/corp-ca.pem
export NODE_EXTRA_CA_CERTS=/tmp/corp-ca.pem
```

## Workflow

Prefer the JSON API commands below over DOM scraping — they read the LMS's own structured data instead of guessing from rendered text.

1. List current courses:

```bash
python3 skills/central-university-lms/scripts/lms.py list-courses
```

Returns `{totalCount, count, items[]}` with course id/name/category; auto-paginates.

2. Drill into a course's stages/materials/homework (course id from step 1):

```bash
python3 skills/central-university-lms/scripts/lms.py course-overview <course_id>
```

Returns `themes[]` (stages, e.g. "Неделя 1: ...") → each theme's `longreads[]` (materials/lab-work blocks) → each longread's `exercises[]` (homework items with `name`, `maxScore`, `activity.name`, `deadline`).

3. Course score summary:

```bash
python3 skills/central-university-lms/scripts/lms.py course-progress <course_id>
```

4. Upcoming deadlines across all published courses (walks step 1 + step 2 for every course, flattens exercises with a `deadline`, filters to the future by default):

```bash
python3 skills/central-university-lms/scripts/lms.py deadlines --limit 20
# add --include-past to see everything, including already-passed deadlines
```

### DOM fallback

Only fall back to these if an API endpoint above starts returning errors (LMS backend change):

```bash
python3 skills/central-university-lms/scripts/lms.py discover-api --seconds 20   # re-capture real endpoints; run headed
python3 skills/central-university-lms/scripts/lms.py snapshot                     # raw DOM dump
python3 skills/central-university-lms/scripts/lms.py deadlines-dom                # regex over rendered text
```

## Output Contract

When reporting to the user, prefer:

- course name;
- stage/theme name (for course-overview);
- assignment/homework title;
- deadline as returned by the API (ISO 8601, already reliable — no need to flag as inferred);
- max score / activity weight if relevant to the question;
- course id if the user may want to drill in further;
- if a DOM fallback command was used instead, mark results as inferred/uncertain.

## References

Read `references/discovery.md` before changing extraction logic or adding new endpoints.

