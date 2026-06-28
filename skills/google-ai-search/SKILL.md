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
3. Follow the bootstrap workflow below.
4. Run the search through `scripts/bootstrap.py run` or the installed `google-ai-search` launcher.
5. Summarize the result, cite source URLs from the JSON, and mention uncertainty when the script falls back to raw page text.

## Bootstrap Workflow

Before each search, resolve this skill directory and run:

```bash
python3 scripts/bootstrap.py check
```

On Windows, use `py -3 scripts\bootstrap.py check`. Parse the JSON result:

- If `ready` is `true`, continue without prompting.
- If `ready` is `false`, explain the missing items and ask the user for explicit
  consent to create the config venv and download Playwright/Chromium.
- After consent, run `scripts/bootstrap.py install` yourself. Do not ask the
  user to open another terminal when agent tools can perform the installation.
- If execution or permissions prevent installation, give the matching command
  from [references/setup.md](references/setup.md).

Never install into the system Python and never use `--break-system-packages`.

## Usage

```bash
google-ai-search \
  --query "OpenAI latest model announcements 2026" \
  --include-sources \
  --lang en
```

Options:

- `--query`: required search query.
- `--lang`: Google UI language, default `en`.
- `--max-chars`: maximum answer length, default `4000`.
- `--include-sources`: include source links.
- `--headless`: run Chromium headless (the default).
- `--headed`: open a visible Chromium window for troubleshooting.
- `--timeout`: page timeout in milliseconds.

## Dependencies

`scripts/bootstrap.py` detects the operating system, venv, Playwright package,
Chromium binary, and POSIX launcher. With user consent, install everything with:

```bash
python3 scripts/bootstrap.py install
```

The default venv is `~/.config/yuzuru-codex-skills/google-ai-search/venv` on
macOS/Linux and `%LOCALAPPDATA%\yuzuru-codex-skills\google-ai-search\venv` on
Windows. Read [references/setup.md](references/setup.md) only when Python/venv
prerequisites are missing or the user asks for OS-specific setup details.

## Guardrails

- Use this for ordinary public-web research, not as the only source for medical, legal, financial, or other high-stakes answers.
- Prefer primary sources when the task needs exact documentation, policy, pricing, legal text, or API behavior.
- If Google shows CAPTCHA or returns no AI answer, report that clearly and use another search path.
- Do not paste raw full HTML into the conversation.
- When the user explicitly asks not to search the web, do not use this skill.
