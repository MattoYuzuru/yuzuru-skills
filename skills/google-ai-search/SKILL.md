---
name: google-ai-search
description: Token-efficient public-web research through Gemini API with Google Search grounding and source links. Use when the user asks to search the web, google something, verify current public information, compare options, or get a compact research summary with citations.
---

# Google AI Search

## Workflow

1. Rewrite the request into a precise search query.
2. Pick the answer language: English for broad technical topics, Russian for
   Russia-specific topics, or the user's requested source language.
3. Resolve this skill directory and run the configuration check:

```bash
python3 scripts/setup.py check
```

On Windows, use `py -3 scripts\setup.py check`.

4. If `ready` is `false`, tell the user to:
   - create a key at <https://aistudio.google.com/apikey>;
   - run the `next_action` command in their own terminal;
   - paste the key into the hidden prompt and confirm when complete.
5. Never ask the user to paste an API key into chat, and never pass it as a
   command-line argument or print it in logs.
6. After confirmation, rerun `setup.py check`. If ready, run:

```bash
python3 scripts/search.py \
  --query "OpenAI latest model announcements 2026" \
  --include-sources \
  --lang en
```

Use the installed `google-ai-search` launcher when available. The default model
is the stable `gemini-3.1-flash-lite`; override it with
`GOOGLE_AI_SEARCH_MODEL` when Google announces a newer compatible model.

## Result Handling

- Summarize the JSON `answer` rather than pasting it blindly.
- Cite URLs from `sources` near the claims they support.
- Mention uncertainty when sources are weak or missing.
- If authentication, quota, regional access, or API availability blocks the
  request, report it clearly and use another search path.
- Prefer primary sources for documentation, policy, pricing, legal text, and API behavior.
- Do not use this as the only source for medical, legal, financial, or other high-stakes answers.
- When the user explicitly asks not to search the web, do not use this skill.

Read [references/setup.md](references/setup.md) only for OS-specific setup,
configuration overrides, or free-tier details.
