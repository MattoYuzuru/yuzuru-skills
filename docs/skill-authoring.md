# Skill Authoring Standard

Use this standard for every skill in this repository. It supplements the repository-level
`AGENTS.md`; when they differ, `AGENTS.md` wins.

## Design Goal

Build the smallest reliable interface between an agent and a domain. Keep model-visible guidance
short, move deterministic behavior into scripts, and load domain detail only when the current task
requires it.

Use this mental model:

```text
SKILL.md    = trigger + router + core workflow
references/ = task-specific knowledge loaded on demand
scripts/    = deterministic capabilities executed without being read first
assets/     = output resources, not model instructions
```

Do not reproduce an entire API or product manual in a skill. Encode stable decisions and known
failure modes; let scripts handle protocol details, authentication, pagination, retries, and output
normalization.

## Context Budgets

These are repository defaults. Exceed them only when the extra context is demonstrably useful.

| Surface | Target | Rule |
|---|---:|---|
| `description` | 1-3 sentences | State capability and concrete trigger conditions. |
| `SKILL.md` | <=200 lines | Keep routing, core workflow, and guardrails only. |
| `SKILL.md` hard limit | 500 lines | Split before this point. |
| Reference | One domain per file | Add a contents list when longer than 100 lines. |
| Script stdout | Small structured result | Paginate, summarize, and cap collections by default. |

Line counts are proxies, not goals. Remove duplication even when a file is below the limit.

## Skill Layout

```text
skills/<skill-name>/
  SKILL.md
  skill.yaml             optional repository metadata
  agents/openai.yaml     optional Codex UI metadata
  references/*.md        optional model-readable detail
  scripts/*              optional deterministic helpers
  assets/*               optional output templates and static resources
```

Keep references one level below `SKILL.md`. Link every reference directly from `SKILL.md` and say
exactly when to read it. Do not make an agent recursively explore the skill directory.

Put API or database schemas in `references/` when the model must reason about them. Put templates,
fonts, images, boilerplate, and files copied into output in `assets/`.

## Frontmatter And Triggering

Portable frontmatter contains only the Agent Skills fields:

```yaml
---
name: gitlab-workflow
description: GitLab repository and merge request workflow. Use when the user asks to inspect a GitLab project, review an MR, check pipelines or jobs, or perform a controlled GitLab write operation.
---
```

The description is always visible before activation. Include:

- what the skill can do;
- user intents and artifacts that should trigger it;
- important scope boundaries that disambiguate it from nearby skills.

Do not put activation guidance only in a `When to use` body section; the body is unavailable until
after activation. Avoid marketing language and generic phrases such as "helps with development".

Repository target metadata belongs in `skill.yaml`:

```yaml
targets: [codex, claude]
```

Omit `skill.yaml` when both agents are supported. Legacy `agents:` frontmatter remains accepted for
backward compatibility.

## Router Pattern

Use a routing table when a skill has more than one distinct capability:

```markdown
## Routing

| Intent | Read | Run | Effect |
|---|---|---|---|
| Inspect a merge request | `references/merge-requests.md` | `mr-read` | read |
| Check failed jobs | `references/pipelines-and-jobs.md` | `pipeline-failures` | read |
| Create a draft MR | `references/merge-requests.md` | `mr-create --draft` | write |
```

Read only the selected row's reference. Do not preload every reference "just in case".

Keep scripts coarse enough to complete a meaningful operation. Prefer `pipeline-failures` returning
a compact diagnosis input over separate calls that fetch a pipeline, all jobs, every trace, and raw
metadata.

## Resolving Paths

Never assume the current working directory is this repository. Resolve the installed skill directory
first, then address `scripts/`, `references/`, and `assets/` relative to it.

Examples in `SKILL.md` should use skill-relative commands:

```bash
python3 scripts/tool.py status
```

Precede them with an explicit instruction to run from the resolved skill directory. Use absolute
paths only after resolution; never commit a maintainer-specific path.

## Script Contract

Every helper script should follow these rules:

1. Make `--help` work without credentials or network access.
2. Read secrets from environment variables, keychain, or config outside the repository.
3. Never accept a secret in an example command or print it in stdout, stderr, or exceptions.
4. Write machine-readable results to stdout and diagnostics to stderr.
5. Return a non-zero exit code on failure and a stable error code or error kind.
6. Emit compact JSON by default; make pretty or raw output opt-in.
7. Paginate collections and expose explicit `--limit` or cursor controls.
8. Filter API responses to fields required by the workflow.
9. Make side effects explicit in command names and support `--dry-run` when useful.
10. Avoid model-driven retries when a deterministic bounded retry is safe inside the script.

Prefer one discoverable CLI with subcommands over many tiny scripts when they share authentication
and transport. Split code only for maintainability, not to mirror documentation folders.

## Effects And Confirmation

Classify every capability:

- `read`: no external mutation; may run without confirmation when already in scope;
- `write`: creates or changes external state; require explicit user authorization;
- `destructive`: deletes, force-updates, resolves, closes, or overwrites; require confirmation of the
  exact target and action.

Instructions are not a security boundary. Enforce read-only behavior with credentials, API scopes,
database roles, sandboxing, and server-side validation.

## Writing Style

Write machine-facing instructions and references in concise English. Preserve official domain and
API terms. Respond to the user in the user's language unless the task requires another language.

Use imperative statements. Document non-obvious decisions and real failure modes; omit general
knowledge the agent already has. Prefer one representative example over several near-duplicates.

## Authoring Workflow

1. Collect concrete trigger and non-trigger examples.
2. Define capabilities and classify their effects.
3. Create the skill with `./skill new <name>`.
4. Implement deterministic scripts before documenting repeated command sequences.
5. Write `SKILL.md` as a router over those capabilities.
6. Add only the references required by identified tasks.
7. Run `./skill validate <name>`.
8. Run script smoke checks and at least one realistic read-only task.
9. Add trigger/effect eval cases for ambiguous or external-system skills.
10. Install for both target agents and test from a fresh session.

## Anti-Patterns

- A giant `SKILL.md` containing a complete API manual.
- Duplicating the same rule in `SKILL.md` and references.
- Reading every reference at activation.
- Deep reference chains that are not linked from `SKILL.md`.
- Raw unbounded API responses or database queries.
- Secrets in prompts, command arguments, fixtures, or logs.
- A broad shell escape presented as a safe domain-specific operation.
- Hypothetical edge cases without a real failure or requirement behind them.
- Agent-specific wording in a skill intended for multiple agents.

## Review Checklist

- Does the description trigger on realistic user language?
- Can an unrelated request avoid triggering the skill?
- Does `SKILL.md` route to exactly one relevant reference?
- Can scripts run without the agent reading their source?
- Are outputs bounded and compact?
- Are writes and destructive actions visibly classified?
- Are paths independent of the maintainer's machine and current directory?
- Are all secrets outside the repository?
- Does `./skill validate` pass?
- Was at least one realistic workflow smoke-tested?
