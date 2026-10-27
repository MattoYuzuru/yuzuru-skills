# Native Host Capabilities

Documentation checked on 2026-10-27. Verify the active tool schema, client version, enabled state,
and permissions before using an override. Documented support is not proof of local availability.
Keep concrete model IDs, effort mappings, and defaults in the host/caller configuration, not in the
portable skill. Identically named effort levels are not comparable compute budgets.

| Host | Selection and delegation | Boundary |
|---|---|---|
| Local Codex | Native subagents can expose model/effort defaults and overrides. | The current tool and configured agent may restrict or override selection. Inherited provider, sandbox, and permissions remain binding. A history fork does not imply a separate checkout. |
| Claude Code | Native subagents support model selection, effort, nested delegation, and optional worktree isolation. | Per-invocation effort and nesting depend on client version and policy. Without explicit isolation, the child may share the leader's cwd. Respect configured provider and allowlist. |
| DeepSeek Harness | Child routing is available with enabled model selection and a supporting backend. | Model discovery/selection can be disabled; some backends do not accept route overrides. A filesystem skills provider alone does not supply delegation tools. |
| Responses API Multi-agent | Hosted children use the request model. | This is a distinct product; local Codex's per-child controls cannot be assumed. |

## Resolve the actual configuration

1. Read exposed native capabilities and current limits without opening unrelated credential stores.
2. Preserve explicit user model/effort pins and ceilings. Select only supported, authorized routes.
3. Use calibrated profiles for the relevant task class when available. Without calibration, use
   current native model metadata or official workload guidance to choose an authorized candidate
   profile; label it an uncalibrated prior. Inherit the caller's default when no relevant selection
   evidence exists. A fast bounded worker and an uncertain architecture decision can warrant
   different profiles, but role names alone do not establish a model ranking.
4. Verify the applied model/effort where the host reports it; distinguish a requested override from
   an observed configuration. Record unavailable telemetry as unknown.
5. Fall back to the current agent or supported native configuration when controls are unavailable.
   Do not rewrite settings, enable a disabled plugin, spawn a different client, or silently switch
   provider to satisfy the plan.

Model selection for children does not imply that a skill can replace the leader's model mid-session.
Subscription usage and API dollar estimates are different measures. Use actual native quota/credit
telemetry when available; never manufacture a conversion from token counts.

## Discovery and startup

Skill descriptions enable implicit matching on supported hosts, subject to context budget, policy,
and enabled state. An installed package does not guarantee activation. Keep discovery text short
and specific to substantial independent workstreams. An explicit project instruction may ask the
leader to consider this skill for suitable tasks; it should not load every reference or require
workers to rebuild the entire orchestration plan. Do not inject hidden orchestration through hooks.

## Official sources

- [OpenAI subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [OpenAI skill authoring](https://learn.chatgpt.com/docs/build-skills)
- [Responses API Multi-agent](https://developers.openai.com/api/docs/guides/responses-multi-agent)
- [Claude Code subagents](https://code.claude.com/docs/en/sub-agents)
- [Claude Code skills](https://code.claude.com/docs/en/skills)
- [Claude Code costs](https://code.claude.com/docs/en/costs)
- [DeepSeek Harness subagent tools](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/subagent/tool-subagent/README.md)

Recheck affected documentation and workload cases after a client or model upgrade. Report native
validation separately for each tested host; passing package checks establishes no runtime parity.
