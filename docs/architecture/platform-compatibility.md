# Platform Compatibility

Verified against Codex CLI 0.145.0, Claude Code 2.1.197, and DeepSeek Harness 0.1.0-rc.7, plus
current official platform documentation.

| Capability | Codex / OpenAI | Claude Code | DeepSeek Harness | Repository strategy |
|---|---|---|---|---|
| Agent Skills | `SKILL.md`, implicit and `$name` invocation | `SKILL.md`, implicit and `/plugin:skill` invocation | Native skill registry and progressive loading | One portable skill tree |
| Skill UI metadata | `agents/openai.yaml` | Skill frontmatter | Skill frontmatter | Optional Codex metadata only |
| Disable standalone skill | `[[skills.config]]` | Native skill/plugin state | Remove/override profile bundle | Do not rewrite user policy |
| Plugin manifest | `.codex-plugin/plugin.json` | `.claude-plugin/plugin.json` | `package.json` plus `cordis.patch.yml` | Thin host adapters |
| Distribution catalog | Repository marketplace | Repository marketplace | Profile dependencies and bundle layers | Native managers own installed state |
| Install/uninstall | `codex plugin add/remove` | `claude plugin install/uninstall` | `dsh plugin --profile ... add/remove` | Delegate to native managers |
| Custom agents | Personal/project TOML | Plugin `agents/*.md` | Agent presets and subagent providers | Portable delegation policy, host adapters only where proven |
| Hooks | Plugin hooks | Plugin hooks | Cordis event plugins, no direct parity claim | Adapt semantics explicitly |
| MCP | Plugin `.mcp.json` | Plugin `.mcp.json` | MCP client plugin when configured | No fictional server or implicit enablement |
| Writable data | Host plugin data | Host plugin data | Harness home/profile state | Never write package roots |
| Live reload | Component-dependent | Component-dependent | Provider watcher for skills; bundle changes require restart | Document component behavior |
| Version source | Host manifest | Host manifest | DSH package manifest | `plugin-version.json` remains authoritative |
| OS | Host-dependent | Host-dependent | Node-supported host platforms | Portable content; host adapters declare limits |

## Material limitations

Codex CLI 0.145.0 exposes no non-interactive plugin enable/disable subcommand and no public plugin
validation subcommand. The repository does not mutate `~/.codex/config.toml` to imitate them.

Codex custom agents are currently personal or project TOML files, not a documented plugin component.
Claude specialist files therefore remain an adapter; every orchestration skill contains the
portable delegation policy needed on Codex and future hosts.

Neither marketplace file is runtime state. Installation, enabled state, credentials, caches, and
plugin data remain owned by the native host.

DeepSeek Harness remains a developer preview. A Yuzuru config-only bundle activates one isolated
`dsh-skill-filesystem` provider at profile boot and watches the canonical package skill directory.
The model receives a catalog first and loads full skill bodies only on invocation; “everything is a
plugin” does not justify copying skill text into Cordis plugins or a permanent system prompt.

DSH bundle paths resolve through the profile's `node_modules`, so local absolute paths appear only
in machine-owned pnpm dependencies. Claude/Codex hooks, agents, and MCP declarations are not assumed
compatible with Cordis events, agent presets, or providers.

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
  [custom subagents](https://code.claude.com/docs/en/sub-agents);
- DeepSeek Harness [architecture](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md),
  [bundle publishing](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/publish.md),
  and [filesystem skill provider](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/skill-filesystem/README.md).

The installed CLIs remain the authority for executable command availability. Native isolated tests
record the tested versions and must be rerun when platform behavior changes.
