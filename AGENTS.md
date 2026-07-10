# Authoring Skills In This Repository

This repo is a shared skill library for **Codex** and **Claude Code** (and any future
agent that adopts the same format). One skill folder serves every agent that supports
it — there is no `skills/codex/` vs `skills/claude/` split. This file is the standard
to follow when writing a new skill or editing an existing one, by hand or by asking an
agent to generate one.

## The Agent Skills format

A skill is a directory under `skills/<name>/` containing:

```text
skills/<name>/
  SKILL.md            required — frontmatter + instructions
  scripts/             optional — deterministic code the skill runs
  references/          optional — detail loaded on demand, not at activation
  assets/               optional — templates, schemas, static files
  agents/openai.yaml    optional — Codex-only UI metadata, see below
```

This mirrors the open **Agent Skills** standard (agentskills.io) implemented natively
by both Codex and Claude Code. Only `SKILL.md` with `name` and `description` frontmatter
is required; everything else is convention.

### `SKILL.md` frontmatter

```yaml
---
name: skill-name
description: What this does and when to use it, one or two sentences.
agents: [codex, claude]
---
```

- `name` — kebab-case, must match the parent directory name exactly.
- `description` — the single most important field. State **what** the skill does and
  **when** to use it (trigger conditions). This is what the agent reads to decide whether
  to activate the skill, before it ever reads the body — vague descriptions ("helps with
  git things") are the most common reason a skill never gets used. Don't restrict wording
  to one agent ("Use when the user asks Codex to...") — write it so it reads naturally for
  any agent.
- `agents` — this repo's own convention (not part of the open standard, but safely
  ignored by tools that don't know it). A list of `codex`, `claude`, or both. **Omit it
  only if the skill is genuinely useful to both agents unchanged** — the `skill` CLI
  treats a missing field as `[codex, claude]`. If a skill only makes sense for one agent
  (e.g. it wraps something Codex-specific), tag it explicitly with just that one.

Other optional frontmatter is agent-specific and safely ignored by agents that don't
recognize it:

- **Claude Code** reads extra keys straight from this same frontmatter: `allowed-tools`
  (restrict tool access), `disable-model-invocation` (require explicit `/skill-name`
  instead of auto-triggering), `context: fork`, `effort` (`low`/`medium`/`high`), `hooks`.
  Add these directly to `SKILL.md` when a skill needs them — no side file.
- **Codex** reads UI metadata from a separate `agents/openai.yaml` file (see below), not
  from `SKILL.md` frontmatter.

### Body content and progressive disclosure

Keep `SKILL.md`'s body short (roughly under 500 lines) — it's loaded in full whenever the
skill activates. Anything bulky (long reference tables, API field docs, setup edge cases)
belongs in `references/*.md` and should only be pointed to from the body ("Read
`references/setup.md` for Windows-specific paths"), not inlined. Scripts belong in
`scripts/` — prefer a script over inline shell/API calls whenever the operation is
deterministic, credential-sensitive, or repeated (see `skills/gitlab-workflow/scripts/gitlab_api.py`
for the pattern this repo follows: read a token from env/file, never print it, emit
compact JSON for the agent to summarize).

### Codex extension: `agents/openai.yaml`

Optional. Add it when a skill should present nicely in Codex's UI or `$name` mention:

```yaml
interface:
  display_name: "Human-Readable Name"
  short_description: "One line, shown in skill pickers"
  default_prompt: "Use $skill-name to ..."
```

Claude Code ignores this file entirely; it's safe to leave in a skill tagged
`agents: [claude]` only, though there's no reason to add it in that case.

## Writing a good description

- State what the skill does and exactly when it should trigger, in plain language.
- Be specific, not generic: "Refactor Python functions to async/await" beats "help with
  Python."
- Don't hardcode one agent's name into the description or body unless the skill is
  genuinely agent-specific (and tagged accordingly in `agents:`).
- If the skill has a "gotchas" section, prioritize real problems you've hit over
  hypothetical ones — that's the highest-value content in the whole file.

## Security rules (apply to every skill)

- Never commit secrets. Read tokens from environment variables or files outside the repo
  (`~/.gitlab_token`, `~/.config/<namespace>/...`), never inline them in prompts, code
  blocks, or committed files.
- Prefer official APIs and scoped tokens over browser/session-cookie automation.
- Ask for separate, explicit confirmation before any write action against an external
  system (push, comment, file upload, secret set, etc.) — read actions don't need this.
- Don't bypass 2FA, CAPTCHA, or access restrictions.

## Adding a new skill: checklist

1. `mkdir -p skills/<name>/scripts` (and `references/`, `assets/` if needed).
2. Write `SKILL.md` with `name`, `description`, and `agents:` frontmatter, following the
   template below.
3. Put any deterministic/credential-handling logic in `scripts/`, called from the body.
4. Add `agents/openai.yaml` only if the skill should target Codex's UI.
5. Run `./skill list` — confirm the new skill shows up with the right per-agent status
   columns and a sane description.
6. Run `./skill install <name>` (optionally `--agent codex` or `--agent claude` to test
   one target at a time) and confirm the symlink lands where expected
   (`~/.agents/skills` for Codex, `~/.claude/skills` for Claude Code, both overridable via
   `YUZURU_CODEX_SKILLS_DIR` / `YUZURU_CLAUDE_SKILLS_DIR`).
7. Update the "Current Skills" list in `README.md`.

### Minimal template

```markdown
---
name: my-new-skill
description: What it does. Use when the user asks to <trigger condition>.
agents: [codex, claude]
---

# My New Skill

## Overview

One paragraph: what this skill is for and the one script/workflow it wraps.

## Workflow

1. Step one.
2. Step two, referencing `scripts/my_script.py` for the deterministic part.

## Guardrails

- Rules specific to this skill's write actions, if any.
```
