# Model-Aware Instruction Design

Use this page when changing skills or repository prompt behavior. It is authoring guidance, not
startup context for every task. Sources were checked on 2026-10-07; recheck provider documentation
before changing a model, API parameter, or host adapter.

## Portable defaults

State the requested outcome, domain context, relevant resources, effect boundary, and observable
completion. Keep precise sequences for credentials, private protocols, fragile state transitions,
or destructive actions. Let the model choose ordinary implementation steps.

Use a small description with a concrete action trigger. Load mode-specific references on demand.
Do not require plan files, a minimum number of alternatives, mandatory specialist agents, or a
second verification round for every task. Preserve required checks and meaningful regression
evidence. Stop after the requested outcome and required checks are satisfied.

Separate discovery from execution permission. A model can load a deployment or messenger skill to
inspect or prepare a result; that does not authorize its writes. Reuse finite authorization while
its bound fields remain unchanged. Keep runtime enforcement in tools and host policy.

These are repository choices informed by current guidance, not a measured promise of better
performance on every model. See the [dated research and audit](../research/frontier-refresh-2026-10.md).

## Model-specific differences

| Requested model | Official guidance observed | Authoring implication |
|---|---|---|
| GPT-6.1 Sol | The GPT-6 family guide favors lean instructions, explicit completion/autonomy boundaries, and proportional testing. Its examples describe Astra behavior and require workload evaluation before assuming transfer to Sol. | Retain actual constraints and relevant checks; remove repeated prompts and automatic approval gates. Do not copy Astra-specific recipes wholesale. [Family guide](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6.1-sol) |
| Claude Opus 5.5 | Calibrate effort afresh, starting at its API default `medium`. Its guide treats Opus 5 prompting as a useful starting point and notes that unattended loops can stop at a progress-only end of turn. | Define observable completion. An end-of-turn report is not a completed workflow. The inherited Opus 5 over-verification warning supports removing universal reviewer rounds, while retaining required gates. [Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5), [Opus 5 scope guidance](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5) |
| Claude Sonnet 5.5 | API default is `high`; the guide suggests `medium` for well-specified agentic work. Low effort can omit useful coding checks, while higher effort can add unrequested work. | Keep concrete validation expectations and a scope stop condition. Do not delete all verification guidance merely because a larger model checks automatically. [Sonnet 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5) |
| DeepSeek-V4.1-Flash | The API identifies `deepseek-flash` as the serving name. Thinking defaults to enabled/high; effort aliases map differently from OpenAI/Claude. Tool conversations require preservation of `reasoning_content`. | Keep API/thinking mechanics in a host adapter, not portable skill prose. No separately verified V4.1 skill-authoring recipe was found; do not invent one. [API identity](https://api-docs.deepseek.com/), [thinking contract](https://api-docs.deepseek.com/guides/thinking_mode/) |

Effort names are not a cross-provider unit of intelligence, cost, or latency. Keep model selection
and effort outside portable packages unless a capability actually calls that API. Re-evaluate on
the same cases after a model upgrade. Do not request verbatim internal reasoning; ask for decisions,
evidence, uncertainty, and a concise explanation. [Claude thinking guidance](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)

## Host discovery

- Codex uses skill descriptions for selection; `agents/openai.yaml` may carry invocation policy
  and tool dependencies. [OpenAI skill packaging](https://developers.openai.com/plugins/build/skills)
- Claude Code exposes descriptions before loading bodies; invocation flags and user overrides
  affect availability. Do not reset them to force activation. [Claude skills](https://code.claude.com/docs/en/skills)
- DeepSeek Harness requires registry, provider, and model-facing consumer. A filesystem provider
  alone does not expose the model's skill tool. Its catalog defaults to a 500-character description
  cap; nested skill groups are not recursively discovered. [Consumer](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/tool-skill/README.md), [provider](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/skill-filesystem/README.md)

Keep native adapters thin and packages self-contained. Do not preload all bodies, invent universal
host flags, or bypass a disabled skill. A clearer description improves the input to selection;
activation still needs real host/model evaluation.
