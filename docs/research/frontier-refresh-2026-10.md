# Frontier Refresh: October 2026

Review date: 2026-10-07. Base: `01a4c74`. This is a maintained decision record for the
requested portfolio refresh, not an always-loaded skill reference. No private conversation or
account telemetry is included.

## Findings and decisions

The portfolio contains 12 standalone skills and 35 plugin skills in 11 packages. All 47 were
reviewed. Descriptions and discovery boundaries were updated for 46; the Central University LMS
is explicitly deferred to the separate authenticated session and retains its existing source.
Low observed frequency does not justify removal: a focused rare workflow may still contain
valuable domain mechanics, and local logs omit web sessions and unsupported invocation paths.

The existing package architecture remains useful: portable behavior, deterministic helpers,
progressive loading, native managers, isolated DSH roots, and explicit effects. The stale parts
were workflow pressure and ambiguous triggers, not the existence of skills as a mechanism.
Descriptions previously enumerated adjacent tasks; primary routers could force plans, specialist
handoffs, wide audits, or extra approval loops. The update narrows those boundaries and retains
fragile domain protocols and write controls.

## Research ledger

All linked pages were opened on the review date, unless explicitly marked unavailable. Provider
claims are separated from repository inferences; external practitioner opinions are contextual,
not platform contracts.

| Source | Evidence used and limits |
|---|---|
| [OpenAI model family guide](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6.1-sol) | Leaner prompts, completion boundaries, task-specific validation. Examples often describe Astra; transfer to Sol needs measurement. |
| [OpenAI skill/prompt refresh](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) | Specific triggers and selective context. Recipes and repeated verification can overconstrain stronger models. This motivates the audit, not a claimed portfolio speedup. |
| [OpenAI skill packaging](https://developers.openai.com/plugins/build/skills) | Descriptions guide selection; evaluate both activation and output quality. |
| [Anthropic context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) | Curate relevant context and tools, use selective retrieval and progressive detail. |
| [Opus 5.5 prompting](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5) | Recalibrate effort and distinguish a progress-only turn from completed unattended work. |
| [Opus 5 scope/verification](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5) | Universal reviewer/verification prompts can cause redundant work. Opus 5.5 treats this prior guide as a starting point; the carryover is an inference, not a universal model rule. |
| [Sonnet 5.5 prompting](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5) | Bound initiative and retain concrete checks at low effort; do not apply Opus advice mechanically. |
| [Claude Code skills](https://code.claude.com/docs/en/skills) | Native implicit invocation, user overrides, and progressive loading. |
| [Agent Skills best practices](https://agentskills.io/skill-creation/best-practices) | Scope descriptions and useful resources to actual workflows rather than generic tutorials. |
| [DeepSeek API](https://api-docs.deepseek.com/) and [thinking mode](https://api-docs.deepseek.com/guides/thinking_mode/) | V4.1 Flash is served as `deepseek-flash`; thinking/tool-turn state belongs to API adapters. No distinct skill-authoring guide for this model was verified. |
| [DSH skill consumer](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/tool-skill/README.md) and [filesystem provider](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/skill-filesystem/README.md) | Registry/provider/consumer separation, catalog cap, invocation policy, shallow discovery, and isolated package roots. |
| [Google pricing](https://ai.google.dev/gemini-api/docs/pricing) and [Search grounding](https://ai.google.dev/gemini-api/docs/google-search) | Keep the existing free-tier search role and user-selected model precedence. A generated answer still needs source verification; a newer model is not automatically a better default. |
| [Simon Willison: Agent Skills](https://simonwillison.net/2025/dec/19/agent-skills/) | Practitioner perspective on a small portable specification and implementation differences. |
| [Simon Willison: context engineering](https://simonwillison.net/2025/jun/27/context-engineering/) | Practitioner discussion of selecting the right task context, including attribution to Karpathy. |
| [Karpathy original post](https://x.com/karpathy/status/1937902205765607626) | Direct retrieval returned 403. Willison supplies attributed context; no first-hand reading or new Karpathy-specific rule is claimed. |

Current model differences and host implications are distilled in
[model guidance](../authoring/model-guidance.md). Provider parameters are intentionally not copied
into every installed skill, nor are host/model defaults changed by this refresh.

## Complete skill audit

Each row has two implicit positive and two negative English/Russian cases plus a workflow
expectation in `evals/skill-selection.json`. A small supporting skill may retain its body because
it already encodes useful domain decisions; a refreshed description alone is not proof of a
behavioral improvement.

| Skill | Before/after description characters | Disposition and protected behavior |
|---|---:|---|
| [central-university-lms](../../skills/central-university-lms/SKILL.md) | 354 / 354 | Deferred; existing authenticated contract retained. |
| [fetch-public-docs](../../skills/fetch-public-docs/SKILL.md) | 284 / 173 | Updated discovery; Use the bridge only for public allowlisted URLs after a qualifying network failure. |
| [github-workflow](../../skills/github-workflow/SKILL.md) | 382 / 180 | Updated discovery; Resolve GitHub objects, use bounded helper output, and bind external writes to authorization. |
| [gitlab-workflow](../../skills/gitlab-workflow/SKILL.md) | 360 / 169 | Updated discovery; Use GitLab target IDs and compact REST reads; do not post review comments without authorization. |
| [google-ai-search](../../skills/google-ai-search/SKILL.md) | 263 / 189 | Updated discovery; Use focused public queries, inspect primary pages, and report missing grounding or truncation. |
| [google-sheets-workflow](../../skills/google-sheets-workflow/SKILL.md) | 387 / 186 | Updated discovery; Preserve the requested access mode; probe existing access before setup, and require writes to be authorized. |
| [jira-workflow](../../skills/jira-workflow/SKILL.md) | 296 / 161 | Updated discovery; Resolve real metadata, preserve finite authorization, and reconcile ambiguous writes without resending. |
| [meeting-artifacts-workflow](../../skills/meeting-artifacts-workflow/SKILL.md) | 226 / 167 | Updated discovery; Retrieve targeted meeting evidence, retain timestamps, and mark missing transcripts or ownership. |
| [messenger-workflow](../../skills/messenger-workflow/SKILL.md) | 222 / 160 | Updated discovery; Resolve provider/account/targets and preserve session grant boundaries and read state. |
| [russian-editorial-style](../../skills/russian-editorial-style/SKILL.md) | 447 / 187 | Updated discovery; Deliver the requested edit with facts, quotations, uncertainty, and voice preserved. |
| [search-workflow](../../skills/search-workflow/SKILL.md) | 257 / 170 | Updated discovery; Constrain local roots, use bounded lexical search first, and avoid optional installation gates. |
| [write-kotlin](../../skills/write-kotlin/SKILL.md) | 278 / 188 | Updated discovery; Respect configured Kotlin compatibility and finish relevant tests without a mandatory specialist handoff. |
| [architecture-agent](../../plugins/architecture-agent/skills/architecture-agent/SKILL.md) | 227 / 162 | Updated discovery; Choose proportional architecture and explicit contracts; do not deploy or invent workload measurements. |
| [architecture-capacity](../../plugins/architecture-agent/skills/architecture-capacity/SKILL.md) | 185 / 160 | Updated discovery; Show units, formulas, uncertainty, and the decision supported by capacity estimates. |
| [architecture-migration](../../plugins/architecture-agent/skills/architecture-migration/SKILL.md) | 192 / 179 | Updated discovery; Separate migration planning from execution and retain verifiable rollback and reconciliation. |
| [cleaner-agent](../../plugins/cleaner-agent/skills/cleaner-agent/SKILL.md) | 274 / 183 | Updated discovery; Classify before cleanup, check dynamic references, and obtain exact authorization for deletion. |
| [cleanup-audit](../../plugins/cleaner-agent/skills/cleanup-audit/SKILL.md) | 236 / 159 | Updated discovery; Return candidate evidence, confidence, retention, and recovery; keep the audit read-only. |
| [documentation-reconciliation](../../plugins/cleaner-agent/skills/documentation-reconciliation/SKILL.md) | 221 / 158 | Updated discovery; Compare authority and runtime evidence; preserve unresolved conflicts instead of assuming code is correct. |
| [delivery-pipeline](../../plugins/devops-agent/skills/delivery-pipeline/SKILL.md) | 216 / 149 | Updated discovery; Validate job semantics and trust boundaries; distinguish local simulation from hosted execution. |
| [deployment-safety](../../plugins/devops-agent/skills/deployment-safety/SKILL.md) | 189 / 162 | Updated discovery; Resolve environment and authorization, execute once, verify health and rollback conditions. |
| [devops-agent](../../plugins/devops-agent/skills/devops-agent/SKILL.md) | 239 / 154 | Updated discovery; Make scoped operational changes with effect levels and evidence; avoid implicit production work. |
| [discovery-agent](../../plugins/discovery-agent/skills/discovery-agent/SKILL.md) | 201 / 156 | Updated discovery; Preserve the user’s context and assess uncertainty without inventing market or interview evidence. |
| [discovery-research](../../plugins/discovery-agent/skills/discovery-research/SKILL.md) | 202 / 177 | Updated discovery; Answer decision-critical research questions with current primary evidence and coverage gaps. |
| [discovery-synthesis](../../plugins/discovery-agent/skills/discovery-synthesis/SKILL.md) | 187 / 161 | Updated discovery; Lead with a supported recommendation and decisive uncertainty; do not claim user validation. |
| [frontend-agent](../../plugins/frontend-agent/skills/frontend-agent/SKILL.md) | 213 / 160 | Updated discovery; Reuse established direction for focused fixes and verify relevant UI behavior without mandatory design rounds. |
| [frontend-verification](../../plugins/frontend-agent/skills/frontend-verification/SKILL.md) | 186 / 167 | Updated discovery; Report observed visual/device/accessibility evidence and explicit unverified surfaces. |
| [visual-direction](../../plugins/frontend-agent/skills/visual-direction/SKILL.md) | 195 / 168 | Updated discovery; Resolve meaningful aesthetic choices without enforcing a quota of alternatives or inventing brand constraints. |
| [capability-inventory](../../plugins/harness-agent/skills/capability-inventory/SKILL.md) | 191 / 169 | Updated discovery; Separate declared, installed, enabled, authenticated, healthy, and tested capabilities. |
| [harness-agent](../../plugins/harness-agent/skills/harness-agent/SKILL.md) | 251 / 176 | Updated discovery; Fix observed friction with the smallest maintainable remedy and do not invent savings. |
| [repository-navigation](../../plugins/harness-agent/skills/repository-navigation/SKILL.md) | 195 / 154 | Updated discovery; Use concise links and scoped instructions; preserve authoritative context and validate paths. |
| [product-acceptance](../../plugins/product-agent/skills/product-acceptance/SKILL.md) | 205 / 159 | Updated discovery; Define preconditions, events, and outcomes without prescribing architecture or implying test execution. |
| [product-agent](../../plugins/product-agent/skills/product-agent/SKILL.md) | 222 / 178 | Updated discovery; Produce proportional product requirements with observable behavior and explicit unknowns. |
| [product-requirements](../../plugins/product-agent/skills/product-requirements/SKILL.md) | 192 / 143 | Updated discovery; Model only roles and artifacts that change behavior; preserve stable IDs and conflicting requirements. |
| [implementation-evidence](../../plugins/sde-agent/skills/implementation-evidence/SKILL.md) | 209 / 174 | Updated discovery; Distinguish validation levels, exact executed checks, and missing evidence without mandatory report files. |
| [implementation-planning](../../plugins/sde-agent/skills/implementation-planning/SKILL.md) | 225 / 173 | Updated discovery; Use a proportional plan; no second approval gate for already authorized bounded local work. |
| [sde-agent](../../plugins/sde-agent/skills/sde-agent/SKILL.md) | 232 / 186 | Updated discovery; Complete scoped implementation and required checks; avoid mandatory plans, reports, or reviewer agents. |
| [defensive-security-review](../../plugins/sre-agent/skills/defensive-security-review/SKILL.md) | 222 / 156 | Updated discovery; Validate reachability and impact against trust boundaries without exposing secrets or expanding targets. |
| [finding-validation](../../plugins/sre-agent/skills/finding-validation/SKILL.md) | 210 / 154 | Updated discovery; Classify from evidence, separate confidence from impact, and retain rejection rationale. |
| [performance-analysis](../../plugins/sre-agent/skills/performance-analysis/SKILL.md) | 236 / 167 | Updated discovery; Use competing hypotheses and discriminating measurements; keep load execution within authorization. |
| [release-readiness](../../plugins/sre-agent/skills/release-readiness/SKILL.md) | 212 / 171 | Updated discovery; Tie readiness to candidate/environment evidence; a verdict neither deploys nor silently accepts risk. |
| [reliability-testing](../../plugins/sre-agent/skills/reliability-testing/SKILL.md) | 198 / 164 | Updated discovery; Exercise a defined claim inside the authorized envelope and verify restoration and cleanup. |
| [sre-agent](../../plugins/sre-agent/skills/sre-agent/SKILL.md) | 245 / 174 | Updated discovery; Match verification to the claim and stop after required checks; do not force a release audit or subagent. |
| [verification-strategy](../../plugins/sre-agent/skills/verification-strategy/SKILL.md) | 228 / 158 | Updated discovery; Define claims, expected evidence, isolation, and exclusions without testing every layer mechanically. |
| [telegram](../../plugins/telegram/skills/telegram/SKILL.md) | 236 / 166 | Updated discovery; Preserve TDLib IDs, forum/thread distinctions, bounded reads, and exact messenger authorization. |
| [telegram-setup](../../plugins/telegram/skills/telegram-setup/SKILL.md) | 195 / 175 | Updated discovery; Inspect runtime status before new login; use official authorization and never expose credentials. |
| [time-messenger](../../plugins/time-messenger/skills/time-messenger/SKILL.md) | 221 / 145 | Updated discovery; Preserve TiMe IDs and unsupported topic outcomes; execute authorized mutations once and verify. |
| [time-messenger-setup](../../plugins/time-messenger/skills/time-messenger-setup/SKILL.md) | 175 / 166 | Updated discovery; Use exact HTTPS origin and private credential entry; login does not authorize message writes. |

## Measured scope and limits

Description text totals 11,219 → 8,047 characters (28.3% fewer).
This is a character count over the same 47 frontmatter fields, including the unchanged LMS;
it is not measured token cost, latency, activation precision, or success-rate improvement.
The selection corpus has 188 cases, of which 184 are active and four LMS cases are deferred.
Static validation executes no model calls. [Testing](../testing.md) documents observed-run scoring,
quality assessment, partial coverage, and local usage evidence.

The helper changes are bounded: complete three-host plugin scaffolds, optional supporting skills
and specialist adapters, placeholder/description validation, private local usage summaries, and
explicit grounding/truncation status for Google Search. They use the standard library and add no
runtime dependencies. No package, credential, native state, or private data was deleted because
usage evidence alone does not establish obsolescence.

The current integration baseline is Codex CLI 0.160.0 and Claude Code 2.1.287. DSH is not installed
on the review machine: its bundle is statically checked against official source, not natively
verified here. Live account/service workflows and cross-model A/B quality/cost runs remain
unverified. The Central University session remains a separate user-led login and integration task.


## Completion evidence

- `./yuzuru validate --strict`: exit 0; skill/package/schema/link/eval/help/cleanliness gates passed.
- `python3 scripts/run_tests.py`: exit 0; 153 tests across 37 files, including usage-parser privacy
  and bounds, host-qualified scoring, scaffold rejection, and three-host version synchronization.
- `git diff --check`: exit 0.
- Claude Code 2.1.287: strict native validation passed for the marketplace and all 11 packages.
- `python3 scripts/test_native_plugins.py --agent both --plugin sde-agent --timeout 30`: exit 0;
  Codex and Claude lifecycle passed in disposable isolated profiles, without modifying user state.
- Independent forward testing: reproduced helper defects were fixed and regression-checked;
  focused skill scenarios were reviewed against raw instructions. This was not a live model A/B run.

All plugin packages and the standalone DSH bundle advance to 0.1.1. Native manifests and package
versions derive from the same canonical version. Installed caches still belong to their native
manager; a repository release does not force-enable plugins or replace user configuration.
