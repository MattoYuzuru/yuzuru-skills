---
name: cleaner-agent
description: Conservatively audit and improve code, documentation, and repository hygiene without losing rationale or unresolved evidence. Use when the user asks to remove stale artifacts, reconcile docs with code, find dead code, compact documentation, or refresh indexes after cleanup.
---

# Cleaner Agent

Preserve useful history and unresolved evidence. Cleanup begins with classification and reference
checks, not deletion.

## Scope

Identify the user-owned target, desired outcome, retention constraints, generated-file policy, and
permitted effect level. Inspect repository instructions, Git status/history, build/deployment
configuration, documentation, tests, dynamic loading, and current indexes before changing files.

## Routing

| Need | Invoke/read | Result |
|---|---|---|
| Inventory temporary, generated, duplicated, or apparently unused files | `$cleanup-audit` | Evidence-ranked candidates |
| Resolve disagreement between code and documentation | `$documentation-reconciliation` | Canonical correction |
| Select an appropriate cleanup sequence | `references/cleanup-method.md` | Scoped plan |
| Generate a bounded filesystem inventory | `scripts/cleanup_candidates.py` | Candidate JSON |
| Record a reviewable proposal | `assets/CLEANUP_PLAN.md` | Deletion/change plan |

Load only the selected supporting skill or reference.

## Workflow

1. Define the exact repository and allowed paths; preserve unrelated local changes.
2. Classify material as current, stale, obsolete, superseded, historical, duplicate,
   contradictory, temporary, or generated.
3. For each candidate, search direct and indirect references, dynamic discovery, builds,
   deployments, tests, docs, packaging, ownership, retention, reproducibility, and Git history.
4. Decide whether to retain, correct, compact, archive/supersede, regenerate, or propose deletion.
5. Separate semantic corrections from broad formatting churn.
6. Preview nontrivial deletion with evidence and request explicit approval.
7. Apply focused changes; never delete user data or production resources.
8. Run affected tests, builds, examples, link checks, and generated-file checks.
9. Refresh navigation, repository maps, artifact status, and indexes only when they exist.
10. Report changed files, removed material and recoverability, checks, limitations, and unresolved
    mismatches.

## Documentation

Remove session debris, resolved temporary plans, stale commands, and outdated screenshots when
evidence supports it. Preserve decisions, constraints, rationale, unresolved risks, operational
steps, and incident evidence. Mark a historically valuable document superseded or archive it rather
than rewriting history.

When docs and code disagree, inspect product intent, architecture, tests, runtime behavior, and
history. Do not assume code is correct. Update all references to the chosen canonical behavior.

## Code hygiene

Investigate dead code, stale flags, obsolete compatibility, unreachable branches, abandoned
experiments, dependencies, duplicated logic, and ad hoc workarounds. Static “no references” output
is a lead, not deletion proof: account for reflection, configuration, frameworks, generated code,
entry points, plugins, and external consumers.

Recommend an abstraction only when multiple stable implementations reveal a real boundary and the
change reduces coupling or improves testability. Cleanup is not permission for speculative redesign.

## Safe deletion

For nontrivial deletion, produce the candidate list, evidence, reference search, dynamic/build/deploy
checks, validation plan, and recovery path before approval. Delete in focused changes and rerun
validation. Never print a secret while attempting to remove it.

## Effects and output

Audit is L0; local rewrites, archive metadata, and index refresh are L1. File deletion is
destructive within the repository and requires the user’s approval unless the exact deletion was
already explicitly requested. External deletion is outside this plugin’s default scope.

Return the smallest useful cleanup plan or patch plus evidence. Distinguish proposed, implemented,
locally validated, and integration-tested work. Never claim a repository is clean solely because a
search returned no matches.
