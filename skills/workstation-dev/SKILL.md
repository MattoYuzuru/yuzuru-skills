---
name: workstation-dev
description: "Diagnose local macOS/Linux build/test environment failures, coordinate shared Docker stacks and run checks with fresh evidence. Use when workstation setup or runtime fails; exclude product design and remote deployment."
---

# Workstation Development

Use for local macOS/Linux development environment failures and shared Docker stacks. Project
versions, gates and product behavior still come from that project's instructions.

Resolve this installed skill directory before calling `scripts/dev.py`. Read the
[development runbook](references/development.md) for Docker/Colima failures, retained stack
restarts, parallel sessions or evidence limitations; load only its relevant sections.

## Start from observed state

Run `python3 -B scripts/dev.py inspect --cwd /absolute/project --docker`, adding `--java MAJOR`,
`--node MAJOR`, `--require TOOL` and `--image EXACT_PIN` only when the task requires them.
It discovers Docker's effective context/endpoint and returns selected tool versions, source
revision, bounded container labels and mounts. It never starts Docker, pulls images or resets data.

Before a stack mutation, identify its project, retained mounts/state, config files and overlays.
Keep the existing data and credential sources unless their replacement is authorized. Memory
is a hint: prefer live labels and the maintained launcher. Do not infer an empty cache, low RAM,
broken Docker or a network failure from a generic failed command.

## Execute and bind evidence

For an authorized check, call `python3 -B scripts/dev.py run --cwd /absolute/project --docker
--resource heavy --reports 'module/build/test-results/test/TEST-*.xml' -- ./gradlew clean test`.
Choose the command and scoped report patterns from the project. Add `--dry-run` to preview the
selected executable, runtime, source, lock resources and report scope before execution; it does
not run the check, acquire locks or create evidence. Arguments are summarized without printing
their values. `--docker` gives SDKs the local endpoint even when the Docker CLI alone works;
Colima container-port access may also need a verified project-local host override.

Pass the executable and arguments directly. Avoid `check | tail; echo $?` and chains that continue
to push after failure. Run dependent stages sequentially and stop at the first nonzero result.
The runner saves redacted private output and a receipt outside Git, preserves the child exit
code and rejects missing/stale/invalid/failing declared JUnit reports or a changed source tree.
Read receipt errors even when the child returned zero. A targeted check proves only its declared
scope; project full gates still apply. Skipped counts follow the project's opt-in/skip policy.

Before reusing a result for push/review, use `python3 -B scripts/dev.py verify RECEIPT --cwd
/absolute/project`. A source edit or commit invalidates it. A non-Git directory or unsupported
source cannot produce reusable source-bound evidence; report that limitation instead of treating
missing fingerprints as equality. Only the caller's task authorization covers the executed command;
this runner is not a shell sandbox or a delivery grant.

## Shared sessions and completion

When delegating an environment task, pass this skill's resolved path, checkout/HEAD, project
requirements, Docker endpoint/Compose project, common state directory and lock resource, runtime
owner, allowed operations and report scope. Do not assume a subagent inherited loaded skills.
Use separate worktrees for independent edits, or agree on a quiet validation phase in a shared
checkout: the fingerprint covers the whole source tree, even another agent's disjoint edits.

`--resource heavy` coordinates heavy checks only among callers using the same state directory
and resource. Use `--resource stack-PROJECT` with one runtime owner for stack mutations. Busy means
wait or work independently. Do not kill another session or bypass its lock; uncooperative commands
and different state directories are outside this coordination.

For an environment repair, reproduce the observed failure, apply the smallest supported fix,
run the affected project checks and maintain its `AGENTS.md`/runbook with the durable command,
requirements and failure boundary. Report the verified scope and remaining uncertainty; finish
once the requested repair and required gates pass.

## Secrets and boundaries

Use `python3 -B scripts/dev.py env --file /path/to/.env KEY ...` for presence/nonempty checks.
It treats dotenv as data and prints no values; missing/empty requested keys or unsupported syntax
fail visibly. Presence does not prove authentication or provider readiness. Pass file paths to
launchers; do not dump interpolated Compose configuration or place secrets in command arguments/logs.
The optional Claude adapter `scripts/secret_guard.py` retains the installed dotenv guard while
recognizing literal quoted `cat` heredocs. Executable/unquoted heredocs remain checked.

Inspect/verify/env are reads. Run executes the supplied authorized command and writes private
local evidence; the effect of that command remains visible to the user. No helper here deletes
volumes, prunes caches, changes global toolchain defaults, deploys, installs tools or changes
networking. Preserve unknown volumes and other projects during recovery.
