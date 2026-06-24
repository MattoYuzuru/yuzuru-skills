# Central University LMS Discovery Notes

Use this reference before changing `scripts/lms.py`.

## Goal

Build a read-only extractor for `https://my.centraluniversity.ru/learn/courses/view/actual/all` that can list current courses, homework, deadlines, and visible statuses for the user's own account.

## Preferred Order

1. Use official API endpoints if visible in browser network traffic.
2. Use authenticated XHR/GraphQL endpoints found by `discover-api`.
3. Use DOM extraction only when endpoint structure is unavailable or unstable.

## Auth

Do not store username or password. Save only browser storage state outside the repository:

```text
~/.config/yuzuru-codex-skills/central-university-lms/storage-state.json
```

This file contains private session material and must never be committed.

## Extraction Hints

Course pages are likely dynamic. Start with broad extraction:

- anchors with non-empty text and `href`;
- visible cards, articles, list items, and table rows;
- text fragments containing deadline words: `дедлайн`, `до`, `сдать`, `домаш`, `задание`, `assignment`, `deadline`;
- dates in Russian numeric formats: `DD.MM`, `DD.MM.YYYY`, `DD Month`, `YYYY-MM-DD`.

Keep uncertain results marked as inferred.

## Write Actions

The first version must not submit homework, upload files, mark lessons complete, send messages, or mutate LMS state.

