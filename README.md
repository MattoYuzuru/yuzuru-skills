# yuzuru-skills

Personal agent skills and plugin experiments for matto user, shared between **Codex** and
**Claude Code** (and future agents that adopt the same format).

Maintainer: `matto user <MattoYuzuru@users.noreply.github.com>`

This repository contains reusable instructions, scripts, and future plugins that let coding
agents work with external systems in a controlled way. Each skill is one folder used by
every agent that supports it — see [AGENTS.md](AGENTS.md) for the authoring standard.

## Quick Start

Clone the repository and install the local CLI command:

```bash
git clone git@github.com:MattoYuzuru/yuzuru-skills.git
cd yuzuru-skills
./install.sh
```

The installer creates a symlink:

```text
~/.local/bin/skill -> ./skill
```

If `~/.local/bin` is not in `PATH`, add it to your shell config:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then install skills into each agent's user skill directory:

```bash
skill list                          # show all skills and per-agent status
skill install                       # interactive menu
skill install all                   # install everything, for every agent it targets
skill install gitlab-workflow       # install one skill, for every agent it targets
skill install --agent claude NAME   # install for one agent only (codex or claude)
skill uninstall NAME                # uninstall (add --agent to target one agent)
skill update                        # git pull --ff-only in this repository
skill doctor                        # show paths and current status
```

Which agent(s) a skill installs for is declared in optional `skill.yaml` target metadata;
a skill without that file installs for both. Legacy `agents:` frontmatter remains supported.

By default, installed skills are symlinks in:

```text
~/.agents/skills    # Codex
~/.claude/skills    # Claude Code
```

Override either only when needed:

```bash
YUZURU_CODEX_SKILLS_DIR=/custom/path skill install all
YUZURU_CLAUDE_SKILLS_DIR=/custom/path skill install all
```

Restart the agent or start a new session/thread after installing skills.

## Skill Vs. Plugin

Skill is the right shape when an agent needs:

- a domain workflow;
- a repeatable command sequence;
- safety rules;
- small helper scripts.

Plugin is the right shape when an integration should be installable and more stable:

- it needs an MCP server or app connector;
- it has several related skills and scripts;
- it needs shared authentication setup;
- it should be reused across projects.

## Current Skills

All current skills target both Codex and Claude Code.

### `github-workflow`

GitHub repository, issue, pull request, Projects, and Actions workflow without MCP:

- token-safe REST and GraphQL helper with compact JSON;
- repository About, topics, languages, and local Git context;
- issue search/create/update/close plus labels, assignees, milestones, and Projects V2;
- pull request detection, creation, metadata, checks, close, and guarded merge;
- Actions workflow/run/job inspection, bounded logs, watch, rerun, dispatch, and cancel;
- bounded read retries, no automatic write retries, and explicit effect confirmations.

### `gitlab-workflow`

GitLab repository and merge request workflow:

- PAT check;
- read repo/tree/file/commit/MR/pipeline/job-log/comments;
- code search;
- reply to and resolve MR discussion threads;
- fork-based workflow;
- push branch;
- create MR;
- strict rules: never print tokens, avoid direct upstream pushes, confirm write actions,
  and require the user to have asked for that specific write/destructive action first.

### `jira-workflow`

Jira issue read, search, create, link, and transition workflow:

- PAT check via `~/.jira.env`;
- read issue/search via JQL/creation metadata/link types/transitions/open epics;
- create issues and epics from wiki-markup templates with a generic custom-field mechanism;
- epic decomposition into sub-tasks;
- link two issues and move an issue's status;
- quality-check an issue against a checklist before Review;
- strict rules: never invent custom field ids, preview and confirm before every write,
  double-confirm closing/cancelling transitions, dedupe via JQL before retrying after a 5xx.

### `google-ai-search`

Token-efficient web research through Google AI Mode:

- query optimization;
- Playwright-based browser search;
- compact JSON output;
- source extraction when available;
- fallback rules when Google blocks the request.

### `central-university-lms`

Read-only Central University LMS workflow:

- official API or XHR discovery when available;
- Playwright session automation when API is not known;
- course list extraction;
- homework and deadline discovery;
- compact Markdown/JSON summaries;
- no secrets in this repository.

### `google-sheets-workflow`

Google Sheets/Drive workflow via a headless service account (no OAuth browser consent):

- isolated per-skill venv bootstrap for `google-auth` (RSA JWT signing only);
- list spreadsheets shared with the service account, inspect sheet metadata, read ranges;
- create spreadsheets (auto-shared back to the user), write/append values and formulas;
- generic `batchUpdate` escape hatch for formatting, freeze panes, merges, pivot tables;
- clear ranges, delete sheet tabs, trash spreadsheets;
- strict rules: never print the service-account key or cached token, confirm before every
  write/destructive action, `list` only covers sheets already shared with the service account.

## Authoring

Read [AGENTS.md](AGENTS.md) and [docs/skill-authoring.md](docs/skill-authoring.md), then use the
repository CLI for the mechanical steps:

```bash
./skill new my-skill \
  --description "What it does. Use when the user asks for a concrete task." \
  --resources scripts,references
./skill validate my-skill
./skill validate all
```

Keep `SKILL.md` as a short router, put deterministic behavior in `scripts/`, and load detailed
knowledge from `references/` only when needed. Add `evals/<skill-name>.json` for ambiguous
triggering or side effects. Use `--targets codex` or `--targets claude` only for a restricted skill;
the default targets both agents without creating `skill.yaml`.

## Security

- Do not commit secrets. Store them in `~/.config/yuzuru-codex-skills/` (the existing
  per-skill config namespace — kept as-is so already-installed API keys/sessions/venvs
  keep working), keychain, or separate `~/.service.env` files with `chmod 600`.
- Prefer official APIs and scoped tokens.
- Use browser cookies/session tokens only when no API is available and the user explicitly agrees.
- Do not bypass 2FA, CAPTCHA, access restrictions, or service rules.
- Ask for separate confirmation before any external write action.

## Structure

```text
skills/     # shared skills, one folder per skill, used by every agent it targets
evals/      # repository-only trigger and side-effect contracts
plugins/    # future plugins
scripts/    # shared helper scripts
AGENTS.md   # skill-authoring standard: frontmatter, metadata, conventions
```
