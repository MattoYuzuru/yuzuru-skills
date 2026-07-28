# Troubleshooting

Run `yuzuru doctor` first. Add `--json` for machine-readable diagnostics and `--repair` only for
safe repository-managed link repairs.

- Marketplace missing: run `yuzuru marketplace status`, then add the exact agent marketplace.
- Plugin missing after install: start a new session; Claude can also run `/reload-plugins`.
- Codex enable/disable requested: open `codex`, run `/plugins`, select the installed plugin, and
  press Space.
- Claude manifest problem: run `claude plugin validate <plugin-dir> --strict`.
- Stale standalone skill link: run `yuzuru doctor --repair` or reinstall that skill.
- Dirty-tree update refusal: commit or otherwise resolve local changes yourself; the CLI never
  stashes or resets them.
- Unmanaged path conflict: move or remove it manually only after verifying ownership.
- Runtime file in clone: report the command that created it; helpers must use temp/XDG paths.

Use the native manager's own list command to resolve discrepancies. The wrapper never treats
installed and enabled as the same state.
