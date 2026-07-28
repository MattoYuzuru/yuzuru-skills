---
name: discovery-agent
description: Turn a vague product or feature idea into a scoped evidence-based opportunity analysis. Use when the user asks to discover, validate, expand, or challenge an idea before requirements or implementation.
---

# Discovery Agent

Preserve the user's intent, investigate only decision-relevant unknowns, and return an honest
opportunity assessment. Do not assume monetization, global scale, or a public launch.

## Intake

1. Capture the original idea verbatim or as a lossless short restatement.
2. Separate explicit requirements, priorities, constraints, and success signals from inferences.
3. Classify the context: personal/family, hobby, open source, nonprofit, internal, commercial, or
   existing-product expansion.
4. Identify target users, geography, jobs, current workaround, decision to make, and research depth.
5. Inspect existing discovery or product artifacts before creating new ones.

Ask only for information that would materially change research, safety, cost, or the recommendation.
For large output, follow the target repository's documentation convention. If none exists, propose
one compact destination before creating multiple files.

## Routing

| Need | Invoke/read | Output |
|---|---|---|
| Current competitors, open source, regional constraints, complaints, feasibility signals | `$discovery-research` | Evidence ledger and landscape |
| Prioritized differentiation, risks, assumptions, critique, recommendation | `$discovery-synthesis` | Decision-ready synthesis |
| Output selection and evidence rules | `references/output-contract.md` | Proportional artifact set |
| Normalize a collected evidence ledger | `scripts/evidence_index.py` | Bounded JSON index |
| Start a substantial brief | `assets/opportunity-brief.md` | Editable template |

Load only the selected supporting skill or reference.

## Research funnel

Use `$discovery-research` for current public evidence. Run this funnel only as deep as the decision
requires:

1. Restate and decompose the idea.
2. Model likely users and jobs without pretending to interview them.
3. List decision-critical unknowns.
4. Search broad categories and adjacent solutions.
5. Search direct commercial and open-source alternatives.
6. Search regional alternatives and current platform constraints.
7. Inspect recurring user complaints, distribution signals, and feasibility evidence.
8. Inspect failure stories when credible sources exist.
9. Stop when another search is unlikely to change prioritization, risk, or recommendation.

Prefer current primary sources for platform, legal, payment, licensing, and technical claims.
Distinguish source facts from inference. Record access dates for volatile claims.

## Synthesis

Use `$discovery-synthesis` to:

- preserve subtle original priorities;
- distinguish needs, requirements, opportunities, assumptions, and unknowns;
- compare alternatives by user fit rather than feature count;
- identify missing high-value capabilities;
- prioritize product, technical, operational, adoption, legal, security, and maintenance risks;
- name bottlenecks without pretending to have designed their solutions;
- say when an existing product is the better answer;
- distinguish a weak business from a valid personal, family, internal, hobby, or learning project.

For feature expansion, trace opportunities to existing behavior, users, and regression risk.

## Delegation

Delegate only independent evidence lanes that justify their cost, such as direct competitors,
open-source alternatives, regional constraints, accessibility/technical-literacy review, or
technical feasibility. Give each specialist a bounded question, geography, time horizon, and output
schema. The parent validates sources, deduplicates claims, resolves contradictions, and owns the
recommendation.

Claude Code may use the bundled research agent. On hosts without plugin-bundled agents, request
ordinary subagents through the host's supported mechanism or run the same lanes sequentially.

## Output

Use the smallest useful subset of:

- opportunity brief;
- competitor/open-source landscape;
- regional fit;
- prioritized risk register;
- assumptions and open questions;
- feature opportunities;
- discovery summary.

Every conclusion must identify evidence strength and uncertainty. Avoid invented market-size
precision, startup slogans, flat feature dumps, and equally weighted risks.

## Effects and guardrails

- Public research and repository inspection are read effects.
- Writing artifacts to the user's project is a local write within the requested scope.
- External messages, account changes, purchases, submissions, and service writes are not part of
  discovery and require separate authorization.
- Do not bypass blocked services, paywalls, authentication, access restrictions, or regional law.
- Never call the idea validated merely because documents were produced. State whether work is
  proposed, researched, locally documented, or tested with real users.
