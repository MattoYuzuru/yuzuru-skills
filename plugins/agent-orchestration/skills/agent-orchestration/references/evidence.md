# Evidence Behind the Policy

Sources checked on 2026-10-27. This is a directed engineering review, not a preregistered systematic
review or meta-analysis. Preserve benchmark, model generation, compute comparator, and publication
status when citing a result. The implemented policy has no established universal speedup.

## Comparative evidence

| Primary source | Observed result | Application and limit |
|---|---|---|
| [Kim et al., Capable language models can outgrow the benefits of collaboration](https://www.nature.com/articles/s42256-026-01268-y), Nature Machine Intelligence 8, 1157–1172 (2026), DOI 10.1038/s42256-026-01268-y | Controlled comparison: 260 configurations, six agentic benchmarks, five architectures, three model families. Finance Agent centralized gains about 80.8% relative to single-agent; PlanCraft loses 39–70%; SWE-bench Verified team means are lower. | Task decomposability and verification matter. Tested GPT-5, Gemini 2/2.5, Sonnet 3.7/4/4.5; SWE/Terminal have 20 tasks per cell. The roughly 45% threshold is an empirical selection rule, not a universal law. Earlier preprint title: Towards a Science of Scaling Agent Systems. |
| [Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/html/2503.13657v3), arXiv v3 (2025) | MAST analyzes 1,642 traces from seven systems and identifies 14 failures involving system design, inter-agent alignment, and verification. | Use failure modes for negative tests. This diagnostic study does not establish optimal team size. |
| [Debate or Vote](https://proceedings.neurips.cc/paper_files/paper/2025/hash/934252acd87f254d5d4672fbde283bd2-Abstract-Conference.html), NeurIPS 2025; [full text](https://arxiv.org/html/2508.17536v2) | Across seven NLP datasets, substantial debate gains are explained by ensembling; some debate configurations reduce accuracy. | Avoid discussion without new evidence as a default protocol. Static questions and small open models do not establish the effect in repository engineering. |
| [AsynCodeBench](https://arxiv.org/html/2609.32662v1), preprint (2026) | Nineteen repository tasks, 52 dependencies, ten open models. Six benefit from their best multi-agent protocol; four do worse. Local test and dependency-test results diverge. | Check producer-consumer behavior after integration. Small recent benchmark; partial test scores are not complete task success or current frontier-model performance. |
| [CodeCRDT](https://arxiv.org/html/2510.18893v1), preprint (2025) | Sonnet 4.5, six small UI tasks, 600 runs; parallel execution ranges from faster to slower and is slower on average. | Text convergence does not guarantee semantic correctness. Small tasks, LLM quality judging, and outlier removal limit transfer. |
| [RouteLLM](https://openreview.net/pdf?id=8sSqNntaMr), ICLR 2025; [arXiv v4](https://arxiv.org/html/2406.18665v4) | Trained routers improve cost-quality tradeoffs; distribution mismatch can erase the advantage. | Calibrate routing on relevant tasks. Query routing between GPT-4/Mixtral is not direct evidence for coding-epic scheduling. |
| [MasRouter](https://aclanthology.org/2025.acl-long.757/), ACL 2025 | Joint collaboration, role, and model routing reduces inference overhead in tested settings, including HumanEval. | This is a trained controller on older models and mostly static tasks; a prose skill does not reproduce its measured gains automatically. |
| [LLMRouterBench](https://arxiv.org/html/2601.07206v1), preprint (2026) | More than 400,000 instances, 21 datasets, 33 models, ten routing baselines; several routers fail to beat Best Single. | Include simple baselines. Large model pools and complex routers are not guarantees of a better tradeoff. |
| [Snell et al., Scaling LLM Test-Time Compute Optimally](https://arxiv.org/html/2408.03314v1), ICLR 2025; inspected arXiv text | Difficulty-aware inference and verifiers change the efficient allocation of compute. | Math reasoning on PaLM 2 supports adaptive allocation as a hypothesis, not a cross-provider coding effort map. |

## Reanalysis and protocol sensitivity

The [author release v2.2.3](https://github.com/ybkim95/agent-scaling/tree/8673d6a8d5a764a07b08e4283492380d80257223)
contains 260 aggregate configurations and 52 complete benchmark × model choice sets. Independent
standard-library arithmetic in the design research checked aggregate means and correctness flags
from released predictions; it did not rerun model trials or refit regressions.

The [complete-choice-set holdout analysis](https://github.com/ybkim95/agent-scaling/blob/8673d6a8d5a764a07b08e4283492380d80257223/scripts/architecture_selection_eval.py)
uses a different protocol from the article's 87% held-out-configuration result. Intelligence Index
with measured single-agent baseline selects the observed best in 23/52 sets (44.2%). Author
self-check constants report ACI with measured baseline at 31/52 (59.6%), versus the simple
benchmark-mean rule at 27/52 (51.9%); exact McNemar p=0.5572 does not establish superiority. These
ACI predictions were not independently refitted in the design research. ACI also requires a
measured baseline. Do not claim universal 87% routing accuracy or that all router variants lose to
the simple baseline. The absence of a linked notice in the checked Crossref record is not an
exhaustive correction/retraction check.

## Engineering experience

- [Anthropic multi-agent research system](https://www.anthropic.com/research/multi-agent-research-system)
  reports +90.2% on an internal research evaluation with Opus 4 leading Sonnet 4 workers. Its 15×
  token comparison is against ordinary chat, not a single agent. This is internal vendor evidence.
- [Anthropic C compiler experience](https://www.anthropic.com/research/building-c-compiler) used 16
  agents and an external compiler oracle to partition failures. It illustrates the value of
  independent verification, but has no single-agent control establishing an optimal count.
- [Cursor self-driving codebases](https://cursor.com/blog/self-driving-codebases) reports drawbacks
  from rigid upfront planning and a central integration bottleneck. Continuous replanning is a
  useful design lesson; their experimental delivery conditions do not replace acceptance gates.

Use these results as priors. Establish benefit with observed, held-out workload evaluation after
implementing or changing the policy, model version, client, or tools.
