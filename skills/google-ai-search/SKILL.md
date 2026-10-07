---
name: google-ai-search
description: Research the public web through Gemini with Google Search grounding. Use when current facts, comparisons, or source-backed answers require web search; open primary sources to verify claims.
---

# Google AI Search

## Workflow

1. Turn one decision or unknown into a precise query. Split a broad research assignment into
   focused queries; include the relevant provider, topic, date, or official domain.
2. Pick the answer language: English for broad technical topics, Russian for
   Russia-specific topics, or the user's requested source language.
3. Resolve this skill directory and run the configuration check:

```bash
python3 scripts/setup.py check
```

On Windows, use `py -3 scripts\setup.py check`.

4. If `check` reports a model configuration error, show the error and have the
   user choose a valid model; do not search until it is resolved. If no key is
   configured, tell the user to:
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
is the stable `gemini-2.5-flash-lite`. Google currently lists its input/output
tokens as Free Tier and Search grounding as free up to 500 requests per day,
shared with `gemini-2.5-flash`. Eligibility and limits depend on the account,
region, and Google's current pricing; recheck the
[pricing](https://ai.google.dev/gemini-api/docs/pricing) and
[grounding](https://ai.google.dev/gemini-api/docs/google-search) docs periodically.
Model precedence is `--model` > `GOOGLE_AI_SEARCH_MODEL` > saved configuration >
default. `setup.py check` reports the selected model and source.

## Result Handling

- Treat `answer` as a research lead. Open the original primary pages before relying on technical
  claims; grounding links can be redirects, and a cited page may not support the claim.
- Check `grounding_observed` and `answer_truncated`. Missing grounding or an incomplete answer
  needs a narrower query or another source path, not a confident sourced conclusion.
- Cite URLs from `sources` near the claims they support.
- Keep the default 10-source bound; raise `--max-sources` only when comparison breadth requires it.
- Request `--include-usage` only when diagnosing cost or quota behavior.
- Mention uncertainty when sources are weak or missing.
- If authentication, quota, regional access, or API availability blocks the
  request, report it clearly and use another search path.
- Prefer primary sources for documentation, policy, pricing, legal text, and API behavior.
- Do not use this as the only source for medical, legal, financial, or other high-stakes answers.
- When the user explicitly asks not to search the web, do not use this skill.

Read [references/setup.md](references/setup.md) only for OS-specific setup,
configuration overrides, or free-tier details.
