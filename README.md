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

Which agent(s) a skill installs for is declared in its `SKILL.md` (`agents:` frontmatter,
see AGENTS.md); a skill without that field installs for both.

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

### `gitlab-workflow`

GitLab repository and merge request workflow:

- PAT check;
- read repo/MR/pipeline/comments;
- code search;
- fork-based workflow;
- push branch;
- create MR;
- strict rules: never print tokens, avoid direct upstream pushes, confirm write actions.

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
plugins/    # future plugins
scripts/    # shared helper scripts
AGENTS.md   # skill-authoring standard: frontmatter, agents: field, conventions
```
