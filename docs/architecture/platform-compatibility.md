# Platform Compatibility

Verified against Codex CLI 0.145.0 and Claude Code 2.1.197 on 2026-07-28, plus current official
OpenAI and Anthropic documentation.

| Capability | Codex / OpenAI | Claude Code | Repository strategy |
|---|---|---|---|
| Agent Skills | `SKILL.md`, implicit and `$name` invocation | `SKILL.md`, implicit and `/plugin:skill` invocation | One portable skill tree |
| Skill UI metadata | `agents/openai.yaml` | Skill frontmatter | Optional Codex metadata only |
| Disable standalone skill | `[[skills.config]]` in Codex config | Native skill/plugin state | CLI does not rewrite user policy |
| Plugin manifest | `.codex-plugin/plugin.json`, required | `.claude-plugin/plugin.json`, optional but supplied | Dual thin manifests |
| Repo marketplace | `.agents/plugins/marketplace.json` | `.claude-plugin/marketplace.json` | Same stable IDs and source paths |
| Install/uninstall CLI | `codex plugin add/remove` | `claude plugin install/uninstall` | Delegated to native managers |
| Enable/disable CLI | Interactive `/plugins` browser in tested CLI | `claude plugin enable/disable` | Codex returns `interaction_required` |
| Custom agents | Personal/project TOML; plugin-bundled custom agents not documented | Plugin `agents/*.md` supported | Portable delegation policy plus Claude adapters |
| Subagents | Prompt/skill requested; local custom TOML | Agent tool and plugin agents | Parent owns synthesis and permissions |
| Hooks | Plugin `hooks/hooks.json`; trust review required | Plugin hooks supported | Only deterministic, bounded hooks |
| Hook root/data | `PLUGIN_ROOT`, `PLUGIN_DATA`; Claude aliases also set | `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA` | Scripts accept both |
| MCP | `.mcp.json` in a plugin | `.mcp.json` in a plugin | None in v1; no fictional server |
| Writable data | Host-provided plugin data directory | Persistent plugin data directory | Never write plugin root |
| Plugin cache | `~/.codex/plugins/cache/...` | `~/.claude/plugins/cache/...` | Package is self-contained |
| Local validation | Repository validator; no tested `codex plugin validate` command | `claude plugin validate --strict` | Structural validation always; Claude official validation when present |
| Local development | Marketplace + new session; installed copy is cached | `--plugin-dir`, marketplace, `/reload-plugins` | Isolated home integration tests |
| Live reload | Skills detected; plugin changes generally need reinstall/new session | Skill edits reload; other components need `/reload-plugins` | Docs state component-specific behavior |
| Version resolution | Explicit manifest version used here | Manifest, marketplace, then Git SHA | One `plugin-version.json` per plugin |
| OS | macOS, Linux, Windows host-dependent | macOS, Linux, Windows host-dependent | Python stdlib; no shell-only plugin runtime |

## Material limitations

Codex CLI 0.145.0 exposes no non-interactive plugin enable/disable subcommand and no public plugin
validation subcommand. The repository does not mutate `~/.codex/config.toml` to imitate them.

Codex custom agents are currently personal or project TOML files, not a documented plugin component.
Claude specialist files therefore remain an adapter; every orchestration skill contains the
portable delegation policy needed on Codex and future hosts.

Neither marketplace file is runtime state. Installation, enabled state, credentials, caches, and
plugin data remain owned by the native host.

## Official sources

Schema and behavior decisions were checked against:

- OpenAI [plugin packaging](https://developers.openai.com/plugins/build/plugins),
  [plugin architecture](https://developers.openai.com/plugins/concepts/plugins),
  [skills](https://developers.openai.com/plugins/build/skills), Codex
  [hooks](https://learn.chatgpt.com/docs/hooks), and
  [subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents);
- Anthropic [plugin reference](https://code.claude.com/docs/en/plugins-reference),
  [plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces),
  [skills](https://code.claude.com/docs/en/skills), and
  [custom subagents](https://code.claude.com/docs/en/sub-agents).

The installed CLIs remain the authority for executable command availability. Native isolated tests
record the tested versions and must be rerun when platform behavior changes.
