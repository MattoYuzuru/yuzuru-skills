# yuzuru-codex-skills

Personal Codex skills and plugin experiments for matto user.

Maintainer: `matto user <MattoYuzuru@users.noreply.github.com>`

This repository contains reusable instructions, scripts, and future plugins that let Codex work with external systems in a controlled way.

## Quick Start

Clone the repository and install the local CLI command:

```bash
git clone git@github.com:MattoYuzuru/yuzuru-codex-skills.git
cd yuzuru-codex-skills
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

Then install skills into Codex's user skill directory:

```bash
skill list          # show all skills and status
skill install       # interactive menu
skill install all   # install everything
skill install gitlab-workflow google-ai-search
skill uninstall google-ai-search
skill update        # git pull --ff-only in this repository
skill doctor        # show paths and current status
```

By default, installed skills are symlinks in:

```text
~/.agents/skills
```

Override this only when needed:

```bash
YUZURU_SKILLS_DIR=/custom/path skill install all
```

Restart Codex or start a new thread after installing skills.

## How To Think About Codex

Skill is the right shape when Codex needs:

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

- Do not commit secrets. Store them in `~/.config/yuzuru-codex-skills/`, keychain, or separate `~/.service.env` files with `chmod 600`.
- Prefer official APIs and scoped tokens.
- Use browser cookies/session tokens only when no API is available and the user explicitly agrees.
- Do not bypass 2FA, CAPTCHA, access restrictions, or service rules.
- Ask for separate confirmation before any external write action.

## Structure

```text
skills/   # Codex skills
plugins/  # future Codex plugins
scripts/  # shared helper scripts
```
