# Gemini API key setup

Create a free-tier key at <https://aistudio.google.com/apikey>. Never paste the
key into chat or pass it as a command-line argument.

## macOS and Linux

Run from any directory, replacing `<skill-dir>` with the installed skill path:

```bash
python3 "<skill-dir>/scripts/setup.py" configure
```

The command requests the key through hidden input, validates it, then prompts
for a model. Press Enter for the recommended `gemini-2.5-flash-lite`, or enter
another Gemini model explicitly. It stores the key and model in
`~/.config/yuzuru-codex-skills/google-ai-search/` as `api-key` and `model`,
each with mode `0600` on POSIX systems.
It also installs the optional `google-ai-search` launcher in `~/.local/bin`.

## Windows

Run in PowerShell:

```powershell
py -3 "<skill-dir>\scripts\setup.py" configure
```

The key is stored at
`%LOCALAPPDATA%\yuzuru-codex-skills\google-ai-search\api-key`. Run searches with
`py -3 "<skill-dir>\scripts\search.py" ...`.

## Environment and overrides

- `GOOGLE_AI_SEARCH_API_KEY` or `GEMINI_API_KEY`: use an environment key instead
  of the config file.
- `GOOGLE_AI_SEARCH_CONFIG_DIR`: override the config directory.
- `GOOGLE_AI_SEARCH_MODEL`: override the saved or default model for this session.
- `--model`: override all other model settings for one search.
- `GOOGLE_AI_SEARCH_BIN_DIR`: override the POSIX launcher directory.

As of 2026-09-24, Google's [pricing](https://ai.google.dev/gemini-api/docs/pricing)
lists `gemini-2.5-flash-lite` input/output tokens on Free Tier and Google Search
grounding free up to 500 requests per day, shared with `gemini-2.5-flash`.
The [grounding guide](https://ai.google.dev/gemini-api/docs/google-search) and
[model page](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash-lite)
confirm the feature. Recheck current pricing before relying on this choice;
Free Tier availability, quotas, and regional/account eligibility are controlled
by Google. Free-tier prompts and responses may be used to improve Google products.
