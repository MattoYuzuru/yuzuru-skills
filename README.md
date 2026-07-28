# Yuzuru Engineering Extensions

Yuzuru is a cross-agent extension monorepo for Codex and Claude Code. It ships portable standalone
Agent Skills, nine independently installable engineering plugins, thin vendor adapters, deterministic
helpers, repository marketplaces, schemas, hooks, eval contracts, and a safe local CLI.

Canonical behavior lives in each skill package. Claude agents and hooks, Codex UI metadata, dual
manifests, and marketplaces adapt that behavior without maintaining independent prompt copies.

## Quickstart

```bash
git clone https://github.com/MattoYuzuru/yuzuru-skills.git
cd yuzuru-skills
./install.sh

yuzuru list
yuzuru skill install search-workflow
yuzuru marketplace add --agent codex
yuzuru marketplace add --agent claude
yuzuru plugin install sde-agent --agent codex
yuzuru plugin install sde-agent --agent claude
```

`install.sh` links `yuzuru` and the backward-compatible `skill` launcher into
`${YUZURU_BIN_DIR:-~/.local/bin}`. It does not install or enable capabilities by itself.

Standalone skills use managed symlinks in `~/.agents/skills` and `~/.claude/skills`; override them
with `YUZURU_CODEX_SKILLS_DIR` and `YUZURU_CLAUDE_SKILLS_DIR`. Plugins remain under their native
manager, which owns installed and enabled state.

## Everyday commands

```bash
yuzuru list --kind skill
yuzuru list --kind plugin
yuzuru plugin list --agent claude
yuzuru plugin inspect architecture-agent
yuzuru skill validate all --strict
yuzuru plugin validate all --strict
yuzuru validate --strict

yuzuru update
yuzuru marketplace update --agent codex
yuzuru marketplace update --agent claude
yuzuru plugin disable sde-agent --agent claude
yuzuru plugin uninstall sde-agent --agent claude
yuzuru doctor
yuzuru doctor --repair
```

Claude exposes non-interactive plugin enable/disable commands. Current Codex exposes this control in
the interactive `/plugins` view; `yuzuru plugin enable|disable ... --agent codex` reports
`interaction_required` and never rewrites Codex configuration.

The legacy commands remain available:

```bash
skill list
skill install NAME
skill uninstall NAME
skill new NAME --description "What it does. Use when ..."
skill validate NAME
skill update
skill doctor
```

Updates refuse a dirty tree and use only `git pull --ff-only`. They never reset, stash, merge,
rebase, re-enable plugins, or overwrite unmanaged installations.

## Plugin catalog

| Plugin | Purpose |
|---|---|
| `discovery-agent` | Evidence-based opportunity discovery, competitors, regional fit, feasibility, and risks. |
| `product-agent` | Proportional PRDs, user behavior, evolvable MVP boundaries, acceptance, and traceability. |
| `architecture-agent` | HLD/LLD, contracts, capacity, security boundaries, failure semantics, and migrations. |
| `devops-agent` | Repository-adaptive CI/CD, delivery, infrastructure, rollback, observability, and operations. |
| `harness-agent` | Agent readiness, documentation navigation, capability inventory, and code-intelligence decisions. |
| `sde-agent` | Focused implementation, debugging, testing, self-review, migrations, and completion evidence. |
| `frontend-agent` | UX direction, distinctive design, frontend architecture, implementation, accessibility, and visuals. |
| `sre-agent` | Independent behavioral, reliability, performance, security, E2E, and release verification. |
| `cleaner-agent` | Conservative documentation, code, and artifact hygiene with deletion evidence. |

Each package under `plugins/<id>/` has one logical identity, dual manifests, a primary orchestration
skill, focused supporting skills, scripts or hooks only where justified, a Claude specialist adapter,
README, and eval contract. No package relies on symlinks outside its directory.

## Standalone skill catalog

| Skill | Purpose |
|---|---|
| `central-university-lms` | Headless LMS inspection and safe homework/status workflows. |
| `github-workflow` | GitHub repositories, issues, pull requests, Projects, Actions, and local Git. |
| `gitlab-workflow` | GitLab repositories, merge requests, discussions, pipelines, and fork delivery. |
| `google-ai-search` | Token-efficient public research with Google Search grounding. |
| `google-sheets-workflow` | Google Sheets/Drive reads, controlled writes, formulas, and structure. |
| `jira-workflow` | Jira issue discovery, creation, linking, quality checks, and transitions. |
| `search-workflow` | Fast routing across local source, files, structured data, documents, and archives. |
| `write-kotlin` | Repository-adaptive Kotlin implementation and refactoring. |

Existing skill paths are unchanged. Managed stale links caused by moving the clone can be diagnosed
and repaired with `yuzuru doctor --repair`; unmanaged files and symlinks are never replaced.

## Marketplaces and lifecycle

The catalogs are committed source files:

- Codex: `.agents/plugins/marketplace.json`;
- Claude Code: `.claude-plugin/marketplace.json`.

Native equivalents and enable/disable/uninstall details are in
[Marketplace installation](docs/distribution/marketplaces.md). Version resolution and the canonical
per-plugin version source are in [Releasing](docs/distribution/releasing.md). No cache, enabled state,
credentials, or user configuration belongs in Git.

## Authoring and validation

Start at [docs/NAVIGATOR.md](docs/NAVIGATOR.md). It routes to repository architecture, standalone
skill authoring, plugin packaging, scripts, hooks, MCP policy, schemas, testing, distribution,
security, and contribution workflow. Root [AGENTS.md](AGENTS.md) stays deliberately compact.

```bash
yuzuru skill new my-skill \
  --description "Perform a bounded workflow. Use when the user requests that workflow." \
  --resources scripts,references
yuzuru plugin new my-plugin \
  --description "Package a bounded capability for supported agents."

python3 scripts/smoke_scripts.py
python3 scripts/run_tests.py
python3 scripts/run_evals.py
yuzuru validate --strict
```

Runtime state uses XDG configuration/cache/data locations (with platform-appropriate home
fallbacks), temporary directories, or native plugin data directories. Normal commands must not
create environments, dependency caches, logs, reports, indexes, screenshots, or bytecode inside the
clone.

## Trust model

Read-only inspection is the default. External writes, production changes, destructive cleanup, and
load/fault testing require explicit scope and authorization appropriate to their impact. Scripts
bound output, avoid credential output, validate targets, and offer dry runs for writes where
applicable. See the [trust model](docs/security/trust-model.md) and
[effect levels](docs/security/effect-model.md).
