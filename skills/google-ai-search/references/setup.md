# Setup troubleshooting

Use `scripts/bootstrap.py` for normal checks and installation. Keep the venv
outside the repository. Do not use `pip --break-system-packages`.

## macOS

Run:

```bash
python3 scripts/bootstrap.py check
python3 scripts/bootstrap.py install
```

The default venv is
`~/.config/yuzuru-codex-skills/google-ai-search/venv`. If `python3` is missing,
install Python from python.org or with `brew install python`.

## Linux

Run:

```bash
python3 scripts/bootstrap.py check
python3 scripts/bootstrap.py install
```

The default venv is
`~/.config/yuzuru-codex-skills/google-ai-search/venv`. On Debian or Ubuntu,
install missing Python venv support with `sudo apt install python3-venv`. Use the
equivalent Python package for other distributions.

## Windows

Run in PowerShell:

```powershell
py -3 scripts\bootstrap.py check
py -3 scripts\bootstrap.py install
```

The default venv is
`%LOCALAPPDATA%\yuzuru-codex-skills\google-ai-search\venv`. If `py` is missing,
install a current Python 3 release and enable the Python launcher during setup.
Run searches with `py -3 scripts\bootstrap.py run ...`; the POSIX launcher is
not installed on Windows.

## Overrides

- `GOOGLE_AI_SEARCH_VENV`: custom venv path.
- `GOOGLE_AI_SEARCH_BIN_DIR`: POSIX launcher directory, default `~/.local/bin`.
- `XDG_CONFIG_HOME`: base configuration directory on macOS and Linux.
