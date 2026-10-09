---
name: workstation-dev
description: "Inspect and run local development checks with Docker endpoint discovery, toolchain selection, process locks and fresh test evidence. Use when diagnosing workstation build/test failures or operating a shared local stack."
---

# Workstation Development

Use for local macOS/Linux development environment failures and shared Docker stacks. Project
versions, gates and product behavior still come from that project's instructions.

Resolve this installed skill directory before calling `scripts/dev.py`. Read the
[development runbook](references/development.md) when diagnosing a failure or preparing a
stack restart; do not load product documents for a machine setup question.

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
Choose the command and scoped report patterns from the project. `--docker` gives SDKs the local
endpoint even when the Docker CLI alone already works; it does not disable Ryuk. Use explicit
project-local Testcontainers options when required.

Pass the executable and arguments directly. Avoid `check | tail; echo $?` and chains that continue
to push after failure. Run dependent stages sequentially and stop at the first nonzero result.
The runner saves redacted private output and a receipt outside Git, returns the child failure,
and rejects missing/stale/failing declared JUnit reports or a changed source tree. A targeted
check proves only its declared scope; project full gates still apply. Skipped counts are visible,
not automatically accepted; use the project's opt-in/skip policy.

Before reusing a result for push/review, use `python3 -B scripts/dev.py verify RECEIPT --cwd
/absolute/project`. A source edit or commit invalidates it. Only the caller's explicit task
authorization covers the executed command; this runner is not a shell sandbox or a delivery grant.

`--resource heavy` coordinates heavy local checks across cooperating sessions. Use
`--resource stack-PROJECT` for stack mutations. Busy means wait or work independently, not kill
another session. Locks cannot serialize commands that do not use the helper.

## Secrets and boundaries

Use `python3 -B scripts/dev.py env --file /path/to/.env KEY ...` for presence/nonempty checks.
It treats dotenv as data and prints no values. Pass credential file paths to maintained launchers;
do not dump interpolated Compose configuration or place secrets in command arguments/logs.
The optional Claude adapter `scripts/secret_guard.py` retains the installed dotenv guard while
recognizing literal quoted `cat` heredocs. Executable/unquoted heredocs remain checked.

Inspect/verify/env are reads. Run executes the supplied authorized command and writes private
local evidence; the effect of that command remains visible to the user. No helper here deletes
volumes, prunes caches, changes global toolchain defaults, deploys, installs tools or changes
networking. Preserve unknown volumes and other projects during recovery.
