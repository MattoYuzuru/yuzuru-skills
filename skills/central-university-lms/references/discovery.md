# Central University LMS Discovery Notes

Use this reference before changing `scripts/lms.py`.

## Goal

Build a read-only extractor for `https://my.centraluniversity.ru/learn/courses/view/actual/all` that can list current courses, homework, deadlines, and visible statuses for the user's own account.

## Preferred Order

1. Use the documented JSON API endpoints below (`api_request` in `lms.py`).
2. Re-run `discover-api` / `click-text-discover` to find new endpoints if the LMS frontend changes and a documented endpoint starts 404ing.
3. Use DOM extraction (`snapshot`, `deadlines-dom`) only when no endpoint covers the need.

## Known API Endpoints

All are plain JSON GETs against `https://my.centraluniversity.ru`, authenticated via the saved storage state (no extra headers needed). Discovered 2026-07-14 via `discover-api` + `click-text-discover` while navigating the real UI.

| Endpoint | Purpose | Notes |
|---|---|---|
| `GET /api/micro-lms/courses/student?limit=&offset=&state=` | List the student's courses | `state=published` for current courses; response has `items[]` (`id`, `name`, `category`, `subjectId`, `settings.syllabusUrl`, `settings.timeChannelUrl`) and `paging.totalCount` |
| `GET /api/micro-lms/courses/{id}` | Course header (name/state/settings) | Subset of `overview` |
| `GET /api/micro-lms/courses/{id}/overview` | Full course structure | `themes[]` (stages, e.g. "Неделя 1: ...") → `longreads[]` (materials/lab blocks, has `type`, e.g. `common`) → `exercises[]` (homework: `name`, `maxScore`, `activity.name`, `activity.weight`, `deadline`) |
| `GET /api/micro-lms/courses/{id}/student/progress` | Score summary | `{earnedScore, leftToEarnScore, maxScore}` |
| `GET /api/micro-lms/deadlines?limit=&courseId=` | Was expected to aggregate deadlines | Returned `[]` in testing even with real courseIds/no filter — do not rely on it; use `course-overview` walk instead (see `deadlines_api` in `lms.py`) |
| `GET /api/micro-lms/longreads/{id}/materials?limit=100&offset=0` | Material and assigned task IDs for a longread | Use this to resolve `taskId`; do not scrape the theme accordion. |
| `GET /api/micro-lms/tasks/{id}` | Task description, state, solution, scores, and metadata | Contains student PII too; filter the response before reporting it. |
| `GET /api/micro-lms/tasks/{id}/events` | Task status history | Filter event payloads: `taskCreated` embeds student details. |
| `GET /api/micro-lms/tasks/{id}/comments` | Comments and their attachments | Read-only; never post or upload. |
| `GET /api/student-hub/students/me` | Full student profile | Contains real PII (full name, INN, SNILS, phone, email) — never print, log, or write this response to the repo |

Not found yet: a "ведомость"/transcript/grades-across-courses endpoint. `course-progress` only gives one course's score. If asked for a full transcript, say this isn't wired up yet rather than guessing from DOM.

## Auth

Do not store username or password. Save only browser storage state outside the repository:

```text
~/.config/yuzuru-codex-skills/central-university-lms/storage-state.json
```

This file contains private session material and must never be committed.

Storage state expires (observed after ~3 weeks). If any command redirects to `id.centraluniversity.ru`, re-run `login`.

## Environment Gotchas

- **Headless triggers Yandex SmartCaptcha at login.** Run `login` headed on the user's own machine. API-only commands with an already-valid storage state were verified with `--headless`; do not use headless mode to establish or refresh a session.
- **Corporate TLS-inspection proxy breaks `context.request.get()`.** Chromium page navigation trusts the OS keychain fine, but Playwright's Node-based request client does not, and raises "self-signed certificate in certificate chain" on every `api_request`/`api-get` call. Fix: export `NODE_EXTRA_CA_CERTS` pointing at a PEM containing the corporate root CA (see SKILL.md Setup step 2) before running any API-backed command. Do not "fix" this by disabling TLS verification (e.g. `ignore_https_errors=True`) in the script — that's a real security downgrade for a config problem that has a proper fix.

## Extraction Hints (DOM fallback only)

- anchors with non-empty text and `href`;
- visible cards, articles, list items, and table rows;
- text fragments containing deadline words: `дедлайн`, `до`, `сдать`, `домаш`, `задание`, `assignment`, `deadline`;
- dates in Russian numeric formats: `DD.MM`, `DD.MM.YYYY`, `DD Month`, `YYYY-MM-DD`.

Keep uncertain results marked as inferred.

## Write Actions

The first version must not submit homework, upload files, mark lessons complete, send messages, or mutate LMS state.
