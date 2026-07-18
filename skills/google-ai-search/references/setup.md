# Gemini API key setup

Create a free-tier key at <https://aistudio.google.com/apikey>. Never paste the
key into chat or pass it as a command-line argument.

## macOS and Linux

Run from any directory, replacing `<skill-dir>` with the installed skill path:

```bash
python3 "<skill-dir>/scripts/setup.py" configure
```

The command requests the key through hidden input, validates it, and stores it
at `~/.config/yuzuru-codex-skills/google-ai-search/api-key` with mode `0600`.
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
- `GOOGLE_AI_SEARCH_MODEL`: override the default `gemini-3.1-flash-lite` model.
- `GOOGLE_AI_SEARCH_BIN_DIR`: override the POSIX launcher directory.

The Gemini free tier may allow Google Search grounding without billing, subject
to current model, quota, account, and regional limits. Check current details at
<https://ai.google.dev/gemini-api/docs/pricing>. Free-tier prompts and responses
may be used to improve Google products.
