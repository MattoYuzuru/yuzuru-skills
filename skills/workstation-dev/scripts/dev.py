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
MAX_REPORTS = 5000
MAX_REPORT_BYTES = 20 * 1024 * 1024


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


def java_major(version):
    match = re.search(r'version "(?:1\.)?(\d+)', version)
    return match[1] if match else None


def java_home(executable, env):
    # PATH entries can be alternatives or version-manager shims, not JDK bin directories.
    rc, out, err = probe([str(executable), "-XshowSettings:properties", "-version"], env=env)
    match = re.search(r"^\s*java\.home\s*=\s*(.+)$", out + err, re.M)
    if rc or not match:
        raise Failure("java_home_unavailable")
    home = Path(match[1].strip()).resolve()
    if home.name == "jre" and (home.parent / "bin/java").is_file():
        home = home.parent
    if not (home / "bin/java").is_file():
        raise Failure("java_home_unavailable")
    return home


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
            rc, out, err = probe([str(executable), "-version" if name == "java" else "--version"], env=env)
            version = out + err
            match = re.search(r"v(\d+)", version) if name == "node" else None
            major = java_major(version) if name == "java" else (match[1] if match else None)
            if rc == 0 and major == wanted:
                selected = java_home(executable, env) / "bin" if name == "java" else directory
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
    git_env = {**os.environ, "LC_ALL": "C", "GIT_OPTIONAL_LOCKS": "0"}
    rc, root, err = probe(["git", "rev-parse", "--show-toplevel"], cwd=cwd, env=git_env)
    if rc:
        if rc == 128 and "not a git repository" in err:
            return None
        raise Failure("git_source_unavailable")
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
    unsupported = []
    for name in untracked.split("\0"):
        if not name or Path(name).name.startswith(".env"):
            continue
        path = Path(root) / name
        digest.update(name.encode())
        if path.is_symlink():
            digest.update(os.readlink(path).encode())
            target = path.resolve()
            try:
                relative = target.relative_to(root)
            except ValueError:
                unsupported.append(name)
                continue
            ignored, _, _ = probe(["git", "check-ignore", "--no-index", "-q", "--", str(relative)], cwd=root)
            if ignored not in (0, 1):
                raise Failure("git_ignore_unavailable")
            if ignored == 0 or any(part.startswith(".env") or part == ".git" for part in relative.parts) or not target.is_file():
                unsupported.append(name)
                continue
            path = target
        if path.is_file():
            with path.open("rb") as handle:
                while chunk := handle.read(65536):
                    digest.update(chunk)
    return {"root": root, "head": sha.strip(), "dirty": bool(status), "fingerprint": digest.hexdigest(),
            "verifiable": not unsupported, "unsupported_symlinks": unsupported[:10]}


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


def report_files(patterns, cwd):
    files, missing = set(), []
    for pattern in patterns:
        found = False
        for filename in glob.iglob(str(Path(cwd) / pattern), recursive=True):
            found = True
            files.add(filename)
            if len(files) > MAX_REPORTS:
                raise Failure("too_many_test_reports")
        if not found:
            missing.append(pattern)
    return sorted(files), missing


def report_snapshot(patterns, cwd):
    files, _ = report_files(patterns, cwd)
    return {filename: (Path(filename).stat().st_mtime_ns, Path(filename).stat().st_size)
            for filename in files}


def report_summary(patterns, cwd, started, before=None, finished=None):
    result = {"fresh": [], "stale": [], "invalid": [], "missing_patterns": [],
              "tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    try:
        files, result["missing_patterns"] = report_files(patterns, cwd)
    except Failure as failure:
        result.update(ok=False, invalid=[{"error": failure.code}])
        return result
    finished = time.time() if finished is None else finished
    for filename in files:
        p = Path(filename)
        try:
            stat = p.stat()
            if (stat.st_mtime < started or stat.st_mtime > finished + 1
                    or (before is not None and before.get(filename) == (stat.st_mtime_ns, stat.st_size))):
                result["stale"].append(filename)
                continue
            if stat.st_size > MAX_REPORT_BYTES:
                raise ValueError("oversize report")
            root = ET.parse(p).getroot()
            suites = [s for s in root.iter("testsuite") if not list(s.iter("testsuite"))[1:]]
            if not suites:
                raise ValueError("no suites")
            for suite in suites:
                cases = list(suite.iter("testcase"))
                actual = {"tests": len(cases)}
                for field, tag in (("failures", "failure"), ("errors", "error"), ("skipped", "skipped")):
                    actual[field] = sum(any(child.tag == tag for child in case) for case in cases)
                counts = {key: int(suite.get(key, str(actual[key]))) for key in actual}
                if any(value < 0 for value in counts.values()):
                    raise ValueError("negative count")
                for key in counts:
                    result[key] += max(counts[key], actual[key])
            result["fresh"].append(filename)
        except (OSError, ValueError, ET.ParseError):
            result["invalid"].append({"path": filename, "error": "test_report_invalid"})
    result["ok"] = not (result["stale"] or result["invalid"] or result["missing_patterns"] or result["failures"] or result["errors"]
                        or (patterns and result["tests"] == 0))
    return result


SECRET_ASSIGNMENT = re.compile(r'(?i)([\w-]*(?:token|secret|password|credential|api[_-]?key)[\w-]*["\']?\s*[:=]\s*)')


def closing_quote(text, start, quote):
    index = start
    while index < len(text):
        if text[index] == "\\":
            index += 2
        elif text[index] == quote:
            return index
        else:
            index += 1
    return None


def redact_assignments(text, continuation=None):
    result, offset = [], 0
    if continuation:
        end = closing_quote(text, 0, continuation)
        if end is None:
            return "[REDACTED]" + ("\n" if text.endswith("\n") else ""), continuation
        result.append("[REDACTED]" + continuation)
        offset = end + 1
    while match := SECRET_ASSIGNMENT.search(text, offset):
        result.append(text[offset:match.end()])
        start = match.end()
        if start < len(text) and text[start] in "\"'":
            quote = text[start]
            end = closing_quote(text, start + 1, quote)
            result.append(quote + "[REDACTED]")
            if end is None:
                result.append("\n" if text.endswith("\n") else "")
                return "".join(result), quote
            result.append(quote)
            offset = end + 1
        else:
            value = re.match(r'[^\s,"\'}]*', text[start:])
            result.append("[REDACTED]")
            offset = start + len(value[0])
    result.append(text[offset:])
    return "".join(result), None


def redact(text, env):
    secrets = {v for k, v in env.items() if SECRET.search(k) and v}
    # Streamed logs may split an inherited multiline value across several lines.
    secrets.update(part for value in tuple(secrets) for part in value.splitlines() if part)
    for value in sorted(secrets, key=len, reverse=True):
        text = text.replace(value, "[REDACTED]")
    text = re.sub(r"(?i)(bearer\s+)\S+", r"\1[REDACTED]", text)
    text = re.sub(r"\b(?:gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+)\b", "[REDACTED]", text)
    return redact_assignments(text)[0]


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
    if args.resource and not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", args.resource):
        raise Failure("invalid_resource_name")
    command_hash = hashlib.sha256(json.dumps(argv, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    runtime = {"java_home": env.get("JAVA_HOME"), "node": shutil.which("node", path=env["PATH"]),
               "docker_host": env.get("DOCKER_HOST") if args.docker else None,
               "testcontainers_host_override": env.get("TESTCONTAINERS_HOST_OVERRIDE") if args.docker else None}
    forbidden_root = Path(source["root"]) if source else cwd
    try:
        state.relative_to(forbidden_root)
        raise Failure("state_must_be_outside_working_tree")
    except ValueError:
        pass
    if getattr(args, "dry_run", False):
        emit({"ok": True, "dry_run": True, "executable": Path(argv[0]).name,
              "argument_count": len(argv) - 1, "command_sha256": command_hash,
              "cwd": str(cwd), "source": source, "runtime": runtime,
              "state_dir": str(state), "resource": args.resource, "report_patterns": args.reports,
              "timeout": args.timeout, "lock_timeout": args.lock_timeout})
        return 0
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with resource_lock(state, args.resource, args.lock_timeout):
        directory = Path(tempfile.mkdtemp(prefix="check-", dir=state))
        source = source_state(cwd)
        before_reports = report_snapshot(args.reports, cwd)
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
                secret_quote = None
                try:
                    for line in process.stdout:
                        # Carry quoted assignments across lines without retaining their values.
                        if secret_quote:
                            line, secret_quote = redact_assignments(line, secret_quote)
                        else:
                            line, secret_quote = redact_assignments(line)
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
        reports = report_summary(args.reports, cwd, started, before_reports)
        if args.no_skips and reports["skipped"]:
            reports["ok"] = False
        source_error = None
        try:
            after = source_state(cwd)
        except (Failure, OSError) as failure:
            after = None
            source_error = failure.code if isinstance(failure, Failure) else "source_read_failed"
        changed = source != after
        source_verifiable = bool(source and source.get("verifiable", False))
        ok = code == 0 and reports["ok"] and not changed and not capture_errors and not source_error
        result = {"ok": ok, "exit_code": code, "timed_out": timed_out, "capture_errors": capture_errors,
                  "version": 1, "command_sha256": command_hash, "report_patterns": args.reports,
                  "executable": Path(argv[0]).name, "cwd": str(cwd), "started_at": dt.datetime.fromtimestamp(started, dt.timezone.utc).isoformat(),
                  "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(), "source": source,
                  "source_after": after, "source_changed": changed, "reports": reports,
                  "source_verifiable": source_verifiable, "source_error": source_error,
                  "reusable": ok and source_verifiable, "runtime": runtime,
                  "log_truncated": truncated["value"], "log": str(directory / "output.log")}
        receipt = directory / "result.json"
        receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        receipt.chmod(0o600)
        result["receipt"] = str(receipt)
        compact = dict(result)
        compact["reports"] = {**reports, "fresh": reports["fresh"][:10], "stale": reports["stale"][:10],
                              "invalid": reports["invalid"][:10], "fresh_count": len(reports["fresh"]),
                              "stale_count": len(reports["stale"]), "invalid_count": len(reports["invalid"])}
        emit(compact)
        return (code if code > 0 else 128 - code) if code else (0 if ok else 3)


def verify(args):
    result = json.loads(Path(args.receipt).read_text())
    if not isinstance(result, dict):
        raise Failure("invalid_receipt")
    ok = (result.get("version") == 1 and result.get("ok") is True and result.get("reusable") is True
          and isinstance(result.get("source"), dict) and result["source"].get("verifiable") is True
          and result.get("cwd") == str(Path(args.cwd).resolve())
          and result.get("source") == source_state(args.cwd))
    emit({"ok": ok, "error": None if ok else "failed_or_stale_evidence", "receipt": args.receipt})
    return 0 if ok else 3


def interpolate(value, variables):
    result, index = [], 0
    while index < len(value):
        if value[index:index + 2] == "$$":
            result.append("$")
            index += 2
        elif value[index:index + 2] == "${":
            end = value.find("}", index + 2)
            if end == -1:
                raise Failure("dotenv_syntax_unsupported")
            match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)(?:(:-|-)([^${}]*))?", value[index + 2:end])
            if not match:
                raise Failure("dotenv_syntax_unsupported")
            name, operator, fallback = match.groups()
            replacement = variables.get(name, "")
            if (operator == ":-" and not replacement) or (operator == "-" and name not in variables):
                replacement = fallback
            result.append(replacement)
            index = end + 1
        elif value[index] == "$" and (match := re.match(r"[A-Za-z_][A-Za-z0-9_]*", value[index + 1:])):
            result.append(variables.get(match[0], ""))
            index += len(match[0]) + 1
        else:
            result.append(value[index])
            index += 1
    return "".join(result)


def dotenv_values(file):
    # Parse data, never source/eval it. Unsupported forms must not masquerade as configuration.
    if file.stat().st_size > 1024 * 1024:
        raise Failure("dotenv_too_large")
    lines = file.read_text(encoding="utf-8-sig").splitlines()
    values, index = {}, 0
    while index < len(lines):
        line = lines[index].strip()
        index += 1
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*(?:=|:\s+)(.*)", line)
        if not match:
            raise Failure("dotenv_syntax_unsupported")
        key, value = match.groups()
        value = value.lstrip()
        quote = value[0] if value and value[0] in "\"'" else None
        if quote:
            end = closing_quote(value, 1, quote)
            while end is None and index < len(lines):
                value += "\n" + lines[index]
                index += 1
                end = closing_quote(value, 1, quote)
            if end is None or (value[end + 1:].strip() and not value[end + 1:].strip().startswith("#")):
                raise Failure("dotenv_syntax_unsupported")
            value = value[1:end]
            if quote == "'":
                value = value.replace("\\'", "'")
            else:
                escapes = {"n": "\n", "r": "\r", "t": "\t", "\\": "\\", '"': '"', "$": "$$"}
                value = re.sub(r'\\([nrt\\"$])', lambda m: escapes[m[1]], value)
        else:
            value = re.split(r"\s+#|^#", value, maxsplit=1)[0].rstrip()
        if quote != "'":
            value = interpolate(value, {**values, **os.environ})
        values[key] = value
    return values


def env_status(args):
    values = dotenv_values(Path(args.file)) if args.file else os.environ.copy()
    keys = args.keys or (sorted(values) if args.file else [])
    if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) for key in keys):
        raise Failure("invalid_env_key")
    if len(keys) > 500:
        raise Failure("too_many_env_keys")
    variables = {key: {"present": key in values, "nonempty": bool(values.get(key))} for key in keys}
    ok = not args.keys or all(item["present"] and item["nonempty"] for item in variables.values())
    emit({"ok": ok, "variables": variables})
    return 0 if ok else 2


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
            p.add_argument("--resource", help="Cooperative lock within the same state directory, e.g. heavy or stack-project-name")
            p.add_argument("--lock-timeout", type=float, default=0)
            p.add_argument("--timeout", type=float, default=1800)
            p.add_argument("--reports", action="append", default=[], help="Scoped JUnit XML glob relative to cwd; stale/missing/failing reports fail the check")
            p.add_argument("--no-skips", action="store_true", help="Reject skipped declared tests for this explicitly required scope")
            p.add_argument("--dry-run", action="store_true", help="Inspect the planned check without executing it, creating state or acquiring a lock")
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
