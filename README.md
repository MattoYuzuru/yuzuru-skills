# Yuzuru Skills

Yuzuru Skills is a repository of reusable agent skills and deterministic helper scripts for
controlled work with development tools and external systems. The library prioritizes efficiency,
accuracy, and low token usage while remaining portable across Codex, Claude Code, and other agents
that support the open Agent Skills format.

The architecture is designed around how language models consume context: compact metadata selects
a skill, `SKILL.md` routes the task, references are loaded only when needed, and scripts handle
repeatable or credential-sensitive operations without putting their implementation into the prompt.
The repository is also agent-readable: `AGENTS.md`, the authoring standard, eval contracts, and the
CLI give an agent enough structure to inspect the library, select and install compatible skills, and
develop new ones safely.

## Use Yuzuru Skills

Clone the repository and install its local CLI:

```bash
git clone https://github.com/MattoYuzuru/yuzuru-skills.git
cd yuzuru-skills
./install.sh
```

The installer creates `~/.local/bin/skill`. Add that directory to `PATH` if necessary, then use:

```bash
skill list                          # inspect skills and per-agent install status
skill install                       # choose skills interactively
skill install all                   # install every compatible skill
skill install NAME                  # install one skill for every agent it targets
skill install --agent codex NAME    # install for Codex or Claude Code only
skill uninstall NAME                # remove repository-managed symlinks
skill update                        # pull repository updates with --ff-only
skill doctor                        # show paths and installation status
```

Skills are installed as symlinks in `~/.agents/skills` for Codex and `~/.claude/skills` for
Claude Code. Override these locations with `YUZURU_CODEX_SKILLS_DIR` or
`YUZURU_CLAUDE_SKILLS_DIR`. Start a new agent session after installation.

| Skill | Purpose |
|---|---|
| `central-university-lms` | Headless LMS inspection, unfinished-homework export, solution-manifest validation, and safe write discovery. |
| `github-workflow` | GitHub repositories, issues, pull requests, Projects, Actions, and local Git workflows. |
| `gitlab-workflow` | GitLab repositories, merge requests, discussions, pipelines, logs, and fork-based delivery. |
| `google-ai-search` | Token-efficient public-web research through the Gemini API with Google Search grounding. |
| `google-sheets-workflow` | Google Sheets and Drive reads, controlled writes, formulas, formatting, and structural changes. |
| `jira-workflow` | Jira Data Center/Server issue discovery, creation, linking, quality checks, and status transitions. |

To create or update a skill, give the repository to an agent and point it to
[`AGENTS.md`](AGENTS.md). The detailed architecture, context budgets, script contract, effect model,
and review checklist live in [`docs/skill-authoring.md`](docs/skill-authoring.md). Mechanical checks
are available through the same CLI:

```bash
./skill new my-skill \
  --description "What it does. Use when the user asks for a concrete task." \
  --resources scripts,references
./skill validate my-skill
./skill validate all
python3 scripts/smoke_scripts.py
python3 scripts/run_tests.py
```

Secrets and browser sessions must remain outside the repository. Skills prefer official APIs,
scoped credentials, bounded outputs, dry runs, and explicit confirmation for external writes or
destructive actions; each skill documents any additional setup and guardrails it requires.
