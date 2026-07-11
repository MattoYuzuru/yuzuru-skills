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

## Workflow

1. If no storage state exists, run interactive login and let the user sign in manually:

```bash
python3 skills/central-university-lms/scripts/lms.py login
```

2. Discover API/XHR endpoints if the DOM extractor is insufficient:

```bash
python3 skills/central-university-lms/scripts/lms.py discover-api --seconds 20
```

3. Capture a current read-only snapshot:

```bash
python3 skills/central-university-lms/scripts/lms.py snapshot
```

4. Extract likely homework/deadline rows:

```bash
python3 skills/central-university-lms/scripts/lms.py deadlines
```

## Output Contract

When reporting to the user, prefer:

- course name;
- assignment/homework title;
- deadline as displayed in LMS;
- status if visible;
- course or homework URL if visible;
- uncertainty notes if the extractor inferred data from text.

## References

Read `references/discovery.md` before changing extraction logic.

