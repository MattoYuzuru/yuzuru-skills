# Development environment runbook

Applies to local macOS/Linux checks, Docker/Colima and CI parity. Keep project-specific commands,
version requirements, image pins and release policies in their repository. The helper needs only
Python's standard library and POSIX process/lock APIs.

## Contents

[Commands](#command-contract), [Docker discovery](#docker-cli-works-but-tests-fail),
[session handoff](#parallel-sessions-and-project-repair),
[retained stacks](#shared-stack-restart-and-volumes), [evidence](#failure-and-report-evidence),
[Linux parity](#maclinux-parity-and-compose), [tools](#tool-and-shell-friction),
[secret guard](#secret-guard).

## Command contract

Resolve the installed skill directory. `scripts/dev.py --help` and each subcommand's `--help`
describe flags. On a workstation with the local `agent-dev` adapter, use it in place of
`python3 -B /resolved/skill/scripts/dev.py`.

```bash
agent-dev inspect --cwd /absolute/project --java 25 --node 24 --docker --require actionlint
agent-dev run --dry-run --cwd /absolute/project/backend --java 25 --docker --resource heavy \
  --reports 'module/build/test-results/test/TEST-*.xml' -- ./gradlew clean quality
agent-dev run --cwd /absolute/project/backend --java 25 --docker --resource heavy \
  --reports 'module/build/test-results/test/TEST-*.xml' -- ./gradlew clean quality
agent-dev verify /outside/repository/check-ID/result.json --cwd /absolute/project/backend
agent-dev env --file /absolute/project/.env OAUTH_CLIENT_ID OAUTH_CLIENT_SECRET
```

Majors above are examples, not workstation-wide defaults. The helper selects an already installed
matching executable using JAVA_HOME, Homebrew keg paths or PATH. It never installs/upgrades one.
For Java, it queries the selected JVM for its actual home instead of deriving a JDK directory from
a jenv/asdf shim path; Java 8 uses its legacy version/home layout. On a host with a different Java
layout, put the selected JAVA_HOME on the invocation environment. Node/npm receive the selected
Node directory before the ordinary PATH.

`run --dry-run` performs the same environment/source preparation, then prints the executable name,
argument count and argv SHA-256, source state, resources, report patterns and runtime.
It does not start the supplied command, acquire locks or create a check directory/receipt. Keep the
concrete command available for review in the task; the digest binds its arguments without exposing
them in helper output. A preview is not an executed gate, authorization or a reservation of runtime
state; inspect changed state before execution.

Run commands as argv, one stage at a time; shell substitutions are not interpreted. A shell script
that internally hides failures can still return false success, so repair that script or split its
stages. For intentionally shell-specific logic select `/bin/bash` or `/bin/zsh` explicitly and use
`set -euo pipefail`; that does not replace explicit status handling in conditional/pipeline code.

Receipts contain UTC times, the child's exit code, selected checkout/HEAD, source verification
status/fingerprint, report counts/errors and the redacted log path. No raw command arguments or
environment dump are saved. Evidence failure cannot erase a nonzero child result.
State defaults to `$XDG_STATE_HOME/agent-dev` or `~/.local/state/agent-dev`; files are private.
Do not put state under a repository. Logs redact inherited secret-named variables, common bearer/
GitHub tokens and secret assignments. This is defense in depth, not permission to run commands
that disclose credential files. Review evidence before sharing it. Log retention is manual and
must target exact old check directories; it never includes Docker volumes or shared build caches.

## Docker CLI works but tests fail

1. Compare the endpoint discovered by `inspect` with the test process's configuration. An explicit
   DOCKER_CONTEXT wins over DOCKER_HOST for the CLI; an SDK or sanitized subprocess may not use it.
2. `run --docker` resolves the local Unix endpoint, exports DOCKER_HOST, removes the overriding
   context for that child and supplies Colima's VM socket override if absent. A remote TLS/SSH
   context is refused rather than silently losing its credentials.
   Daemon access and container-port access are separate: Testcontainers' Colima example also sets
   TESTCONTAINERS_HOST_OVERRIDE to the running profile's reachable address. Preserve an explicit
   project override and verify the actual profile/address before setting one. The helper does not
   start Colima with different network options or discover that address automatically.
3. If a test deliberately builds a minimal child environment, explicitly pass the verified
   DOCKER_HOST into that fixture. Do not weaken production's sanitized environment.
4. Check the exact cached image with `inspect --image DIGEST_OR_FIXTURE_TAG`. A missing image is
   not a daemon failure. Follow the project's pinned-image acquisition route; do not substitute a
   mirror or repeatedly pull an unavailable digest.

Do not restart or recreate Colima while other stacks use it. Diagnose the effective socket,
resource counters and requested image first. Ryuk disabling is a project/machine workaround,
not a general Colima requirement. An aborted run owns only its explicitly named containers.
See [Testcontainers Colima configuration](https://java.testcontainers.org/supported_docker_environment/#colima)
and [Docker contexts](https://docs.docker.com/engine/manage-resources/contexts/).

## Parallel sessions and project repair

For delegated environment work, include a compact handoff in the task message:

- Resolved skill path, project instruction/runbook paths and required Java/Node/tool/image pins.
- Absolute checkout, expected HEAD and owned source/report scope.
- Verified Docker endpoint, Compose project/config overlays and retained state/credential paths.
- Common absolute state directory, agreed lock resource, runtime owner and authorized operations.
- Check argv, expected report patterns and completion criteria; return receipt path and unresolved facts.

Share paths and nonsecret metadata, never credential values. Confirm the worker's actual checkout
and environment before relying on inherited context. Host behavior differs: ordinary Claude
subagents need explicitly supplied/preloaded skills, while conversation forks carry different
startup context. See [Claude subagent skill loading](https://code.claude.com/docs/en/sub-agents#preload-skills-into-subagents).
Do not add host-specific agent manifests or require a subagent for every repair.

Separate worktrees isolate source edits; they still share Docker, ports, volumes and caches. Assign
one owner to an existing runtime and common locks to competing heavy checks. Locks coordinate only
processes using the same state directory and resource, even across worktrees. In one checkout, agree
on a quiet validation phase: another agent's unrelated source edit invalidates whole-tree evidence.
Do not weaken the fingerprint to call a concurrent result reusable.

Complete a project repair with the observed failure, a minimal fix and fresh affected project gates.
Maintain the project's existing `AGENTS.md` or runbook with durable requirements, verified launcher
and known limitation so the next session can reproduce the setup. Keep machine facts in the machine
navigator and project commands in the project; avoid copying an environment inventory into every skill.

Evaluate this handoff with observed fresh-host runs, command/receipt artifacts and preserved runtime
state. JSON contract validation alone proves neither selection nor successful agent behavior; this
distinction follows [OpenAI's skill eval workflow](https://developers.openai.com/blog/eval-skills).
Keep the entrypoint short and load these sections by need, following the
[OpenAI skill guidance](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra).

## Shared stack restart and volumes

Read Compose project/working-directory/config-file labels and Mounts from `inspect`. Confirm:
source checkout, state/certificate directory, credential file *path*, overlays, ports and volumes.
Keep them consistent through the restart. A worktree's missing `.env` must not implicitly remove
configured login providers. A launcher with fewer `-f` files can remove an intentional overlay.
Use `env` presence checks and the project's public provider/readiness smoke to verify the result.

Use the agreed runtime owner and `--resource stack-PROJECT` around authorized mutations. Preserve
volume contents: no reset, `down -v`, volume removal, `system prune --volumes`, Colima delete,
shared cache removal or broad cleanup as a remedy for a test failure. Disposable fixtures need their own project and
distinct ports; destroy only that fixture when its deletion is authorized.

Bind sources belong to the Docker daemon's host, not necessarily the CLI host. Inspect configured
Colima mounts before selecting a fixture temp directory. Do not assume `/tmp` or `/var/folders`
is shared; named volumes or a verified shared directory avoid that mismatch.
See [Docker bind mounts](https://docs.docker.com/engine/storage/bind-mounts/).

## Failure and report evidence

A pipeline's final `tail`/`grep` status is not the test status. Never continue delivery merely
because that pipeline returned zero. The runner's exit code and receipt are authoritative for
the invoked process; a log line reading "pass" is not. A zero child exit code with receipt errors
is a failed check. Invalid XML still produces a failed receipt with the original child exit code,
so diagnose the command and report failure separately.

Declare JUnit globs only for the suites this check should execute. Missing, stale, malformed,
failing or errored declared reports make the runner fail. The helper checks actual testcase
failure/error/skipped elements as well as suite counters. Unchanged prior reports and timestamps
beyond this run are rejected. Freshness uses file metadata, which alone cannot prove suite execution;
when that distinction matters, use the project's clean operation or unique run-owned report directory.
Use Gradle `--continue` when collecting both modules' failure evidence, then require its final exit
code to be zero for acceptance. Use `--no-skips` for
an explicitly required live/integration scope that must execute every declared test. Inspect skipped
tests by the project's opt-in rules. A green unit gate does not prove a live provider ran.

Source verification binds the Git checkout, HEAD, tracked changes and supported untracked files.
It includes untracked symlink paths and eligible targets inside the checkout; external, ignored
or dotenv targets make source reuse unverifiable. Ignored build artifacts and dotenv values are
not part of this fingerprint, so it cannot prove that an external dependency or runtime stayed the
same. Declare and inspect those separately when the claim depends on them.

A check may execute outside Git, but its receipt explicitly marks source verification/reuse false.
`verify` refuses such a receipt; absence of Git data cannot certify unchanged sources. A real Git
error fails visibly instead of being converted into a non-Git success. For reusable evidence, run
from a verifiable project checkout and verify after the final source edit/commit. Never rewrite a
receipt to accept a new revision. Legacy unversioned receipts are not reusable; run a fresh check.

For a fresh-cache claim, create a task-owned disposable cache outside shared volumes, record
source/image pins and the cache path, and reproduce once. An ordinary successful rebuild only
proves that rebuild; keep an earlier unknown failure cause explicitly unknown. Do not delete
the owner's shared cache to obtain a clean-cache claim.

## Mac/Linux parity and Compose

Run ownership, process cleanup, filesystem and Python-sensitive checks in the target Linux image
early, under the intended UID. `/tmp` ownership is not the process UID; derive a fixture UID from
a file it creates. Separate privileged runner behavior from unprivileged tests. PermissionError
is not proof that a process group is dead. Use the target Python version for deep-tree cleanup,
not only the Mac's newer interpreter. Bound adversarial probes inside their own disposable
container; never run a PID-1/kill-all test directly on the workstation.

Record Compose version on both hosts. `compose config` is a rendered model, not a stable byte-for-
byte API across releases. Older compose-go boolean serialization omits false; a source default
can differ from that omitted zero value. For `create_host_path`, the source default is **true**:
require an explicit false in the maintained source, compare semantic fields in rendered output,
and test missing-path rejection when behavior is security-relevant. Use only synthetic/no-secret
inputs for printed config; do not print a production or credential-populated model.
See [Compose volumes](https://docs.docker.com/reference/compose-file/services/#volumes) and
[Compose config](https://docs.docker.com/reference/cli/docker/compose/config/).

## Tool and shell friction

- Check installed tools before assuming PyYAML or GNU userland. Prefer `yq -o=json` for YAML when
  the verified Mike Farah v4 implementation exists, and `actionlint` for Actions-specific rules.
  A project that requires Python YAML should use its declared environment; do not install into
  global Python or change the product dependency file just for an ad hoc inspection.
- macOS BSD `sed -i` differs from GNU sed. Use a bounded Python file edit or the native file tool
  for a portable change. Quote literal shell strings: zsh treats leading unquoted `=` specially.
- Use the host's exact tool identifiers; a native tool named Bash is case-sensitive.
- A 403 proves an HTTP response, not a network outage. Separate authentication, IAM/bucket policy,
  provider wire compatibility, transient API transport and vulnerability-gate failures. Use an
  allowed REST read fallback for a transient GraphQL failure; don't retry external mutations.
- Keep stacked branch ancestry and source pins explicit. After squash, inspect the complete delta
  from the pre-merge head, including auto-merged files. Resolve shared-file ownership before
  parallel changes; avoid indiscriminate ours/theirs conflict resolution.

## Secret guard

The `env` helper parses a supported dotenv subset as data: quoted/unquoted values, inline comments
and common variable/default interpolation. It does not source the file or execute substitutions;
unsupported advanced syntax fails visibly. `KEY="" # comment` remains empty. Explicitly requested
missing/empty keys return a failure; an inventory without keys does not certify project readiness.
Check the maintained launcher's parser semantics when they differ, then use the project's nonsecret
authentication/provider smoke. Populated keys alone do not prove valid credentials.

The Claude adapter checks tool JSON on stdin and returns a PreToolUse denial for accidental dotenv
disclosure. It is not a sandbox. Use the env helper for presence/nonempty output and the existing
masked envpeek for masked values. A blocked executable heredoc should be rewritten with the file
tool and invoked as a reviewed helper, not disguised or routed around the guard.

Only a literal, quoted heredoc fed to `cat` is omitted from lexical scanning; the shell does not
expand its body. Its header, output target and following commands remain checked. Unquoted
heredocs, shell/Python executable bodies and credential-bearing redirects remain checked.
The [Claude hook contract](https://code.claude.com/docs/en/hooks#pretooluse-decision-control)
defines the adapter's JSON response, not execution authorization.
