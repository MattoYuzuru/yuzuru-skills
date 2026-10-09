# Development environment runbook

Applies to local macOS/Linux checks, Docker/Colima and CI parity. Keep project-specific commands,
version requirements, image pins and release policies in their repository. The helper needs only
Python's standard library and POSIX process/lock APIs.

## Contents

[Commands](#command-contract), [Docker discovery](#docker-cli-works-but-tests-fail),
[retained stacks](#shared-stack-restart-and-volumes), [evidence](#failure-and-report-evidence),
[Linux parity](#maclinux-parity-and-compose), [tools](#tool-and-shell-friction),
[secret guard](#secret-guard).

## Command contract

Resolve the installed skill directory. `scripts/dev.py --help` and each subcommand's `--help`
describe flags. On a workstation with the local `agent-dev` adapter, use it in place of
`python3 -B /resolved/skill/scripts/dev.py`.

```bash
agent-dev inspect --cwd /absolute/project --java 25 --node 24 --docker --require actionlint
agent-dev run --cwd /absolute/project/backend --java 25 --docker --resource heavy \
  --reports 'module/build/test-results/test/TEST-*.xml' -- ./gradlew clean quality
agent-dev verify /outside/repository/check-ID/result.json --cwd /absolute/project/backend
agent-dev env --file /absolute/project/.env OAUTH_CLIENT_ID OAUTH_CLIENT_SECRET
```

Majors above are examples, not workstation-wide defaults. The helper selects an already installed
matching executable using JAVA_HOME, Homebrew keg paths or PATH. It never installs/upgrades one.
On a host with a different Java layout, put the selected JAVA_HOME on the invocation environment.
Node/npm receive the selected Node directory before the ordinary PATH.

Run commands as argv, one stage at a time; shell substitutions are not interpreted. A shell script
that internally hides failures can still return false success, so repair that script or split its
stages. For intentionally shell-specific logic select `/bin/bash` or `/bin/zsh` explicitly and use
`set -euo pipefail`; that does not replace explicit status handling in conditional/pipeline code.

Receipts contain UTC times, the child's exit code, selected checkout/HEAD, a source fingerprint,
report counts and the redacted log path. No command arguments or environment dump are saved.
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

## Shared stack restart and volumes

Read Compose project/working-directory/config-file labels and Mounts from `inspect`. Confirm:
source checkout, state/certificate directory, credential file *path*, overlays, ports and volumes.
Keep them consistent through the restart. A worktree's missing `.env` must not implicitly remove
configured login providers. A launcher with fewer `-f` files can remove an intentional overlay.
Use `env` presence checks and the project's public provider/readiness smoke to verify the result.

Use one stack integrator and `--resource stack-PROJECT` around authorized mutations. Different
agents can edit disjoint files while only one controls that runtime. Preserve volume contents:
no reset, `down -v`, volume removal, `system prune --volumes`, Colima delete, shared cache removal
or broad cleanup as a remedy for a test failure. Disposable fixtures need their own project and
distinct ports; destroy only that fixture when its deletion is authorized.

Bind sources belong to the Docker daemon's host, not necessarily the CLI host. Inspect configured
Colima mounts before selecting a fixture temp directory. Do not assume `/tmp` or `/var/folders`
is shared; named volumes or a verified shared directory avoid that mismatch.
See [Docker bind mounts](https://docs.docker.com/engine/storage/bind-mounts/).

## Failure and report evidence

A pipeline's final `tail`/`grep` status is not the test status. Never continue delivery merely
because that pipeline returned zero. The runner's exit code and receipt are authoritative for
the invoked process; a log line reading "pass" is not.

Declare JUnit globs only for the suites this check should execute. Missing, stale, malformed,
failing or errored declared reports make the runner fail. Files from a prior run cannot prove
the second Gradle module executed. Use Gradle `--continue` when collecting both modules'
failure evidence, then require its final exit code to be zero for acceptance. Use `--no-skips` for
an explicitly required live/integration scope that must execute every declared test. Inspect skipped
tests by the project's opt-in rules. A green unit gate does not prove a live provider ran.

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

The Claude adapter checks tool JSON on stdin and returns a PreToolUse denial for accidental dotenv
disclosure. It is not a sandbox. Use the env helper for presence/nonempty output and the existing
masked envpeek for masked values. A blocked executable heredoc should be rewritten with the file
tool and invoked as a reviewed helper, not disguised or routed around the guard.

Only a literal, quoted heredoc fed to `cat` is omitted from lexical scanning; the shell does not
expand its body. Its header, output target and following commands remain checked. Unquoted
heredocs, shell/Python executable bodies and credential-bearing redirects remain checked.
The [Claude hook contract](https://code.claude.com/docs/en/hooks#pretooluse-decision-control)
defines the adapter's JSON response, not execution authorization.
