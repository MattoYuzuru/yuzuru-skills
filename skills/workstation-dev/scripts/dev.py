#!/usr/bin/env python3
"""Inspect a workstation and run development checks with reliable local evidence."""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import glob
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import xml.etree.ElementTree as ET

SECRET = re.compile(r"KEY|SECRET|TOKEN|PASSWORD|PASSWD|CREDENTIAL|PRIVATE|AUTH", re.I)
MAX_LOG = 20 * 1024 * 1024


class Failure(Exception):
    def __init__(self, code: str):
        self.code = code


def emit(value):
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def probe(argv, *, env=None, cwd=None, timeout=8):
    try:
        p = subprocess.run(argv, env=env, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, check=False)
        return p.returncode, p.stdout, p.stderr
    except (OSError, subprocess.TimeoutExpired):
        return 127, "", ""


def docker_endpoint(env):
    # Docker's explicit context takes precedence over DOCKER_HOST. SDKs need the endpoint.
    context = env.get("DOCKER_CONTEXT")
    if not context and env.get("DOCKER_HOST"):
        return env["DOCKER_HOST"], "DOCKER_HOST"
    if not context:
        rc, out, _ = probe(["docker", "context", "show"], env=env)
        if rc:
            raise Failure("docker_context_unavailable")
        context = out.strip()
    rc, out, _ = probe(["docker", "context", "inspect", context, "--format",
                        "{{.Endpoints.docker.Host}}"], env=env)
    if rc or not out.strip():
        raise Failure("docker_endpoint_unavailable")
    return out.strip(), "context:" + context


def prepared_environment(args):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    additions = []
    for name, wanted in (("java", args.java), ("node", args.node)):
        if not wanted:
            continue
        choices = []
        if name == "java" and env.get("JAVA_HOME"):
            choices.append(Path(env["JAVA_HOME"]) / "bin")
        for prefix in (Path("/opt/homebrew/opt"), Path("/usr/local/opt")):
            root = prefix / ("openjdk@" + wanted if name == "java" else "node@" + wanted)
            choices.append(root / "libexec/openjdk.jdk/Contents/Home/bin" if name == "java" else root / "bin")
        found = shutil.which(name, path=env.get("PATH"))
        if found:
            choices.append(Path(found).parent)
        selected = None
        for directory in choices:
            executable = directory / name
            rc, out, err = probe([str(executable), "-version" if name == "java" else "--version"])
            version = out + err
            match = re.search(r'version "(\d+)' if name == "java" else r"v(\d+)", version)
            if rc == 0 and match and match[1] == wanted:
                selected = directory
                break
        if selected is None:
            raise Failure(name + "_major_unavailable")
        additions.append(str(selected))
        if name == "java":
            env["JAVA_HOME"] = str(selected.parent)
    env["PATH"] = os.pathsep.join(additions + [env.get("PATH", "")])
    if args.docker:
        endpoint, _ = docker_endpoint(env)
        if not endpoint.startswith("unix://"):
            # Do not discard TLS/SSH context credentials or silently switch a remote daemon.
            raise Failure("docker_requires_local_unix_endpoint")
        env["DOCKER_HOST"] = endpoint
        env.pop("DOCKER_CONTEXT", None)
        if ".colima/" in endpoint:
            env.setdefault("TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE", "/var/run/docker.sock")
        rc, _, _ = probe(["docker", "info", "--format", "{{.ID}}"], env=env)
        if rc:
            raise Failure("docker_daemon_unavailable")
    return env


def source_state(cwd):
    rc, root, _ = probe(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    if rc:
        return None
    root = root.strip()
    rc, sha, _ = probe(["git", "rev-parse", "HEAD"], cwd=cwd)
    if rc:
        raise Failure("git_head_unavailable")
    # Hash contents without putting diffs or file values into evidence. Ignored files stay ignored.
    rc, diff, _ = probe(["git", "diff", "HEAD", "--binary", "--", ".",
                         ":(exclude)**/.env", ":(exclude)**/.env.*"], cwd=root)
    if rc:
        raise Failure("git_diff_unavailable")
    rc, status, _ = probe(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=root)
    if rc:
        raise Failure("git_status_unavailable")
    digest = hashlib.sha256((diff + status).encode())
    rc, untracked, _ = probe(["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=root)
    if rc:
        raise Failure("git_untracked_unavailable")
    for name in untracked.split("\0"):
        if not name or Path(name).name.startswith(".env"):
            continue
        path = Path(root) / name
        digest.update(name.encode())
        if path.is_file() and not path.is_symlink():
            with path.open("rb") as handle:
                while chunk := handle.read(65536):
                    digest.update(chunk)
    return {"root": root, "head": sha.strip(), "dirty": bool(status), "fingerprint": digest.hexdigest()}


INSPECT = ('{"name":{{json .Name}},"image":{{json .Config.Image}},'
           '"status":{{json .State.Status}},"oom_killed":{{json .State.OOMKilled}},'
           '"project":{{json (index .Config.Labels "com.docker.compose.project")}},'
           '"working_dir":{{json (index .Config.Labels "com.docker.compose.project.working_dir")}},'
           '"config_files":{{json (index .Config.Labels "com.docker.compose.project.config_files")}},'
           '"mounts":{{json .Mounts}}}')


def inspect(args):
    env = prepared_environment(args)
    versions = {}
    for name, flags in (("python3", ["--version"]), ("java", ["-version"]), ("node", ["--version"]),
                        ("docker", ["--version"]), ("colima", ["version"]), ("shellcheck", ["--version"]),
                        ("actionlint", ["-version"]), ("yq", ["--version"])):
        executable = shutil.which(name, path=env["PATH"])
        rc, out, err = probe([executable, *flags], env=env) if executable else (127, "", "")
        versions[name] = {"path": executable, "available": rc == 0,
                          "version": (out + err).strip().splitlines()[:3]}
    missing = [name for name in args.require if not shutil.which(name, path=env["PATH"])]
    result = {"ok": not missing, "missing": missing, "cwd": str(Path(args.cwd).resolve()),
              "platform": sys.platform, "shell": env.get("SHELL"), "source": source_state(args.cwd),
              "tools": versions, "docker": None}
    if args.docker:
        rc, out, _ = probe(["docker", "info", "--format", '{"cpus":{{.NCPU}},"memory":{{.MemTotal}}}'], env=env)
        info = json.loads(out) if rc == 0 else {}
        rc, ids, _ = probe(["docker", "ps", "-a", "-q"], env=env)
        containers = []
        for cid in ids.splitlines()[:args.limit]:
            rc, out, _ = probe(["docker", "inspect", "--format", INSPECT, cid], env=env)
            if rc == 0:
                containers.append(json.loads(out))
        rc, compose, _ = probe(["docker", "compose", "version", "--short"], env=env)
        image_checks = {}
        for image in args.image:
            image_checks[image] = probe(["docker", "image", "inspect", "--format", "{{.Id}}", image], env=env)[0] == 0
        result["docker"] = {"endpoint": env["DOCKER_HOST"], "cpus": info.get("cpus"),
                            "memory_bytes": info.get("memory"), "compose_version": compose.strip(),
                            "containers": containers, "truncated": len(ids.splitlines()) > args.limit,
                            "cached_images": image_checks}
        result["ok"] = result["ok"] and all(image_checks.values())
    emit(result)
    return 0 if result["ok"] else 2


def report_summary(patterns, cwd, started):
    result = {"fresh": [], "stale": [], "missing_patterns": [], "tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for pattern in patterns:
        files = sorted(set(glob.glob(str(Path(cwd) / pattern), recursive=True)))
        if not files:
            result["missing_patterns"].append(pattern)
        for filename in files:
            p = Path(filename)
            if p.stat().st_mtime < started:
                result["stale"].append(str(p))
                continue
            try:
                root = ET.parse(p).getroot()
                suites = [s for s in root.iter("testsuite") if not list(s.iter("testsuite"))[1:]]
                if not suites:
                    raise ValueError("no suites")
                for suite in suites:
                    for key in ("tests", "failures", "errors", "skipped"):
                        result[key] += int(suite.get(key, "0"))
                result["fresh"].append(str(p))
            except (OSError, ValueError, ET.ParseError):
                raise Failure("test_report_invalid")
    if len(result["fresh"]) + len(result["stale"]) > 5000:
        raise Failure("too_many_test_reports")
    result["ok"] = not (result["stale"] or result["missing_patterns"] or result["failures"] or result["errors"]
                        or (patterns and result["tests"] == 0))
    return result


def redact(text, env):
    for value in sorted({v for k, v in env.items() if SECRET.search(k) and v}, key=len, reverse=True):
        text = text.replace(value, "[REDACTED]")
    text = re.sub(r"(?i)(bearer\s+)\S+", r"\1[REDACTED]", text)
    text = re.sub(r"\b(?:gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+)\b", "[REDACTED]", text)
    text = re.sub(r'(?i)((?:[\w-]*(?:token|secret|password|credential|api[_-]?key)[\w-]*)["\']?\s*[:=]\s*["\']?)[^\s,"\'}]+', r'\1[REDACTED]', text)
    return text


@contextlib.contextmanager
def resource_lock(directory, name, timeout):
    if not name:
        yield
        return
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", name):
        raise Failure("invalid_resource_name")
    locks = directory / "locks"
    locks.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (locks / (name + ".lock")).open("a") as handle:
        os.chmod(handle.name, 0o600)
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise Failure("resource_busy")
                time.sleep(min(0.1, max(0, deadline - time.monotonic())))
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def terminate(process):
    # EPERM is not evidence that a process group has disappeared.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=3)


def run(args):
    argv = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not argv:
        raise Failure("command_required")
    if not math.isfinite(args.timeout) or not math.isfinite(args.lock_timeout) or args.timeout <= 0 or args.lock_timeout < 0:
        raise Failure("invalid_timeout")
    env = prepared_environment(args)
    state = Path(args.state_dir).expanduser().resolve()
    cwd = Path(args.cwd).resolve()
    source = source_state(cwd)
    forbidden_root = Path(source["root"]) if source else cwd
    try:
        state.relative_to(forbidden_root)
        raise Failure("state_must_be_outside_working_tree")
    except ValueError:
        pass
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with resource_lock(state, args.resource, args.lock_timeout):
        directory = Path(tempfile.mkdtemp(prefix="check-", dir=state))
        source = source_state(cwd)
        started = time.time()
        timed_out = False
        capture_errors = []
        truncated = {"value": False}
        with (directory / "output.log").open("w", encoding="utf-8") as log:
            os.chmod(log.name, 0o600)
            process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, errors="replace", start_new_session=True)
            def capture():
                size = 0
                try:
                    for line in process.stdout:
                        safe = redact(line, env)
                        if size < MAX_LOG:
                            remaining = MAX_LOG - size
                            if len(safe) > remaining:
                                truncated["value"] = True
                            safe = safe[:remaining]
                            log.write(safe)
                            size += len(safe)
                        else:
                            truncated["value"] = True
                    log.flush()
                except (OSError, ValueError):
                    capture_errors.append("output_capture_failed")
            reader = threading.Thread(target=capture, daemon=True)
            reader.start()
            received = []
            handlers = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGHUP)}
            def stop_on_signal(signum, frame):
                received.append(signum)
                terminate(process)
            for sig in handlers:
                signal.signal(sig, stop_on_signal)
            try:
                code = process.wait(timeout=args.timeout)
                if received:
                    code = 128 + received[-1]
            except subprocess.TimeoutExpired:
                timed_out = True
                terminate(process)
                code = 124
            except KeyboardInterrupt:
                terminate(process)
                code = 130
            finally:
                for sig, handler in handlers.items():
                    signal.signal(sig, handler)
            reader.join(timeout=3)
            if reader.is_alive():
                terminate(process)
                reader.join(timeout=3)
                capture_errors.append("output_pipe_not_closed")
            if not reader.is_alive():
                process.stdout.close()
        reports = report_summary(args.reports, cwd, started)
        if args.no_skips and reports["skipped"]:
            reports["ok"] = False
        after = source_state(cwd)
        changed = source != after
        ok = code == 0 and reports["ok"] and not changed and not capture_errors
        result = {"ok": ok, "exit_code": code, "timed_out": timed_out, "capture_errors": capture_errors,
                  "executable": Path(argv[0]).name, "cwd": str(cwd), "started_at": dt.datetime.fromtimestamp(started, dt.timezone.utc).isoformat(),
                  "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(), "source": source,
                  "source_after": after, "source_changed": changed, "reports": reports,
                  "runtime": {"java_home": env.get("JAVA_HOME"), "node": shutil.which("node", path=env["PATH"]),
                              "docker_host": env.get("DOCKER_HOST") if args.docker else None},
                  "log_truncated": truncated["value"], "log": str(directory / "output.log")}
        receipt = directory / "result.json"
        receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        receipt.chmod(0o600)
        result["receipt"] = str(receipt)
        compact = dict(result)
        compact["reports"] = {**reports, "fresh": reports["fresh"][:10], "stale": reports["stale"][:10],
                              "fresh_count": len(reports["fresh"]), "stale_count": len(reports["stale"])}
        emit(compact)
        return (code if code > 0 else 128 - code) if code else (0 if ok else 3)


def verify(args):
    result = json.loads(Path(args.receipt).read_text())
    ok = (result.get("ok") is True and result.get("cwd") == str(Path(args.cwd).resolve())
          and result.get("source") == source_state(args.cwd))
    emit({"ok": ok, "error": None if ok else "failed_or_stale_evidence", "receipt": args.receipt})
    return 0 if ok else 3


def env_status(args):
    values = os.environ.copy() if not args.file else {}
    if args.file:
        for line in Path(args.file).read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key.strip()):
                values[key.strip()] = value.strip().strip("\"'")
    keys = args.keys or (sorted(values) if args.file else [])
    emit({"variables": {key: {"present": key in values, "nonempty": bool(values.get(key))} for key in keys}})
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("inspect", "run"):
        p = sub.add_parser(action)
        p.add_argument("--cwd", default=os.getcwd())
        p.add_argument("--java", help="Required installed Java major; selected only for this command")
        p.add_argument("--node", help="Required installed Node major; selected only for this command")
        p.add_argument("--docker", action="store_true", help="Require local Docker and pass its effective endpoint to SDKs")
        if action == "inspect":
            p.add_argument("--require", action="append", default=[])
            p.add_argument("--image", action="append", default=[], help="Require this exact image in cache; never pull")
            p.add_argument("--limit", type=int, choices=range(1, 101), default=30)
        else:
            p.add_argument("--state-dir", default=str(Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "agent-dev"))
            p.add_argument("--resource", help="Cooperative machine-wide lock, e.g. heavy or stack-project-name")
            p.add_argument("--lock-timeout", type=float, default=0)
            p.add_argument("--timeout", type=float, default=1800)
            p.add_argument("--reports", action="append", default=[], help="Scoped JUnit XML glob relative to cwd; stale/missing/failing reports fail the check")
            p.add_argument("--no-skips", action="store_true", help="Reject skipped declared tests for this explicitly required scope")
            p.add_argument("command", nargs=argparse.REMAINDER)
    p = sub.add_parser("verify")
    p.add_argument("receipt")
    p.add_argument("--cwd", default=os.getcwd())
    p = sub.add_parser("env")
    p.add_argument("--file")
    p.add_argument("keys", nargs="*")
    args = parser.parse_args()
    try:
        return {"inspect": inspect, "run": run, "verify": verify, "env": env_status}[args.action](args)
    except Failure as failure:
        emit({"ok": False, "error": failure.code})
        return 2
    except (OSError, ValueError, subprocess.SubprocessError):
        emit({"ok": False, "error": "local_operation_failed"})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
