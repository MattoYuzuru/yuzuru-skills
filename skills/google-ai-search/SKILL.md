---
name: google-ai-search
description: Token-efficient web research through Google AI Mode. Use when the user asks to search the web, google something, check current public information, compare options, or get a compact research summary with sources while avoiding large raw HTML pages in context.
---

# Google AI Search

## Overview

Use this skill to run a compact Google AI Mode search through Playwright and return JSON with an answer, query, and source links when available.

## Query Workflow

1. Rewrite the user's request into a precise search query.
2. Pick the search language:
   - use English for broad technical topics;
   - use Russian for Russia-specific or Russian-language topics;
   - use the user's language when the target source language matters.
3. Run `scripts/search.py`.
4. Summarize the result, cite source URLs from the JSON, and mention uncertainty when the script falls back to raw page text.

## Usage

```bash
python3 skills/google-ai-search/scripts/search.py \
  --query "OpenAI latest model announcements 2026" \
  --include-sources \
  --lang en
```

Options:

- `--query`: required search query.
- `--lang`: Google UI language, default `en`.
- `--max-chars`: maximum answer length, default `4000`.
- `--include-sources`: include source links.
- `--headless`: run Chromium headless.
- `--timeout`: page timeout in milliseconds.

## Dependencies

The script needs Playwright and Chromium:

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Guardrails

- Use this for ordinary public-web research, not as the only source for medical, legal, financial, or other high-stakes answers.
- Prefer primary sources when the task needs exact documentation, policy, pricing, legal text, or API behavior.
- If Google shows CAPTCHA or returns no AI answer, report that clearly and use another search path.
- Do not paste raw full HTML into the conversation.
- When the user explicitly asks not to search the web, do not use this skill.

