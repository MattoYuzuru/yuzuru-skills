# Search tool setup

Run `python3 scripts/search_setup.py check --profile core` first. Use `--profile minimal` for code-
only environments and `--profile full` when document adapters are required. The helper only checks
`PATH` and prints installation suggestions; it never runs them.

## Selected toolkit

| Tool | Unique route | Official source |
|---|---|---|
| ripgrep | Default text, regex, and workspace file discovery | <https://github.com/BurntSushi/ripgrep> |
| ast-grep | Tree-sitter syntax search and structural rewrite candidates | <https://github.com/ast-grep/ast-grep> |
| ripgrep-all | Adapter-backed documents, archives, SQLite, and media metadata | <https://github.com/phiresky/ripgrep-all> |
| jq | Typed JSON queries | <https://github.com/jqlang/jq> |
| Mike Farah yq | YAML, XML, TOML, CSV, and properties queries | <https://github.com/mikefarah/yq> |

Poppler and Pandoc are `rga` adapters in the full profile. Package names vary by platform; prefer
the command returned by the helper or the linked official installation instructions.

## Deliberate exclusions

- Do not require `fd`: `rg --files` plus a second `rg` covers agent file-name discovery without an
  additional dependency.
- Do not require `fzf`: its interactive TUI benefits humans but does not reduce non-interactive
  agent output.
- Do not require `ag`, `ack`, GNU grep, or another general grep when `rg` is available.
- Do not require `ugrep`: its TUI, fuzzy search, and broad grep compatibility are valuable, but
  overlap the selected `rg` and `rga` routes for this skill.
- Do not require Hypergrep: projects sharing that name are either old experiments or young indexed
  agent tools whose headline token benchmarks are self-published. Re-evaluate if independent,
  reproducible evidence and broad language support emerge.
- Do not require Semgrep for ordinary search: use it when the task is security/static-analysis rule
  evaluation, not as an interactive grep replacement.

Raw speed rankings change with corpus, cache, regex, match count, and output mode. Optimize the
semantic route and returned bytes before optimizing milliseconds.
