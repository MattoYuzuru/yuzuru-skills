#!/usr/bin/env python3
"""Behavioral regression checks for workstation evidence and Docker discovery."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import signal
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dev


class DevTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.cwd = self.root / "project"
        self.cwd.mkdir()
        self.state = self.root / "evidence"

    def args(self, code, **kwargs):
        values = dict(command=["--", sys.executable, "-c", code], cwd=str(self.cwd),
                      state_dir=str(self.state), docker=False, java=None, node=None,
                      timeout=5, lock_timeout=0, resource=None, reports=[], no_skips=False,
                      dry_run=False)
        values.update(kwargs)
        return argparse.Namespace(**values)

    def invoke(self, args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            rc = dev.run(args)
        return rc, json.loads(output.getvalue())

    def init_git(self, files=None):
        for name, content in (files or {"source.txt": "one"}).items():
            (self.cwd / name).write_text(content)
        self.git("init", "-q")
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "commit", "-qm", "fixture")

    def git(self, *argv):
        return subprocess.run(["git", *argv], cwd=self.cwd, check=True, capture_output=True)

    def verify_result(self, result):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            rc = dev.verify(argparse.Namespace(receipt=result["receipt"], cwd=str(self.cwd)))
        return rc, json.loads(output.getvalue())

    def inspect_env(self, content, keys, environment=None):
        file = self.root / "fixture.env"
        file.write_text(content)
        output = io.StringIO()
        with patch.dict(os.environ, environment or {}, clear=True), contextlib.redirect_stdout(output):
            rc = dev.env_status(argparse.Namespace(file=str(file), keys=keys))
        return rc, json.loads(output.getvalue())

    def test_failed_child_keeps_its_real_exit_and_cannot_be_a_green_receipt(self):
        rc, result = self.invoke(self.args("print('FAILED'); raise SystemExit(7)"))
        self.assertEqual(rc, 7)
        self.assertFalse(result["ok"])
        self.assertEqual(result["exit_code"], 7)
        self.assertIn("FAILED", Path(result["log"]).read_text())
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(dev.verify(argparse.Namespace(receipt=result["receipt"], cwd=str(self.cwd))), 3)

    def test_direct_argv_preserves_a_pipeline_like_literal(self):
        rc, result = self.invoke(self.args("print('literal | tail; echo exit=0')"))
        self.assertEqual(rc, 0)
        self.assertEqual(Path(result["log"]).read_text(), "literal | tail; echo exit=0\n")

    def test_env_secret_is_removed_from_the_persisted_log(self):
        secret = "private-fixture-credential-0123456789"
        with patch.dict(os.environ, {"FIXTURE_API_TOKEN": secret}):
            rc, result = self.invoke(self.args("import os; print(os.environ['FIXTURE_API_TOKEN']); print('Authorization: Bearer abcdef')"))
        text = Path(result["log"]).read_text()
        self.assertEqual(rc, 0)
        self.assertNotIn(secret, text)
        self.assertNotIn("abcdef", text)
        self.assertIn("[REDACTED]", text)
        self.assertEqual(Path(result["log"]).stat().st_mode & 0o777, 0o600)
        self.assertEqual(Path(result["receipt"]).stat().st_mode & 0o777, 0o600)

    def test_stale_missing_and_failing_reports_cannot_pass_a_successful_child(self):
        file = self.cwd / "TEST-one.xml"
        file.write_text('<testsuite tests="1" failures="0"/>')
        os.utime(file, (1, 1))
        args = self.args("pass")
        args.reports = ["TEST-*.xml"]
        rc, result = self.invoke(args)
        self.assertEqual(rc, 3)
        self.assertEqual(result["reports"]["tests"], 0)
        self.assertEqual(result["reports"]["stale"], [str(file)])
        file.unlink()
        rc, result = self.invoke(args)
        self.assertEqual(rc, 3)
        self.assertEqual(result["reports"]["missing_patterns"], ["TEST-*.xml"])
        args.command = [sys.executable, "-c", "from pathlib import Path; Path('TEST-one.xml').write_text('<testsuite tests=\"1\" failures=\"1\"/>')"]
        rc, result = self.invoke(args)
        self.assertEqual(rc, 3)
        self.assertEqual(result["reports"]["failures"], 1)

    def test_fresh_report_is_counted_once_and_no_skips_is_enforced(self):
        args = self.args("from pathlib import Path; Path('TEST-one.xml').write_text('<testsuites><testsuite tests=\"2\"><testsuite tests=\"2\" skipped=\"1\"/></testsuite></testsuites>')")
        args.reports = ["TEST-*.xml"]
        rc, result = self.invoke(args)
        self.assertEqual(rc, 0)
        self.assertEqual(result["reports"]["tests"], 2)
        args.no_skips = True
        rc, result = self.invoke(args)
        self.assertEqual(rc, 3)
        self.assertEqual(result["reports"]["skipped"], 1)

    def test_actual_testcase_outcomes_override_missing_or_zero_suite_counters(self):
        for outcome in ("failure", "error"):
            for counters in ("", ' tests="1" failures="0" errors="0" skipped="0"'):
                with self.subTest(outcome=outcome, counters=counters):
                    xml = f'<testsuite{counters}><testcase name="fixture"><{outcome}/></testcase></testsuite>'
                    args = self.args(f"from pathlib import Path; Path('TEST-one.xml').write_text({xml!r})",
                                     reports=["TEST-*.xml"])
                    rc, result = self.invoke(args)
                    self.assertEqual(rc, 3)
                    self.assertFalse(result["reports"]["ok"])
                    self.assertEqual(result["reports"]["tests"], 1)
                    self.assertEqual(result["reports"]["failures" if outcome == "failure" else "errors"], 1)

    def test_actual_skipped_testcases_are_counted_and_no_skips_is_enforced(self):
        for counters in ("", ' tests="1" skipped="0"'):
            with self.subTest(counters=counters):
                xml = f'<testsuite{counters}><testcase name="fixture"><skipped/></testcase></testsuite>'
                args = self.args(f"from pathlib import Path; Path('TEST-one.xml').write_text({xml!r})",
                                 reports=["TEST-*.xml"])
                rc, result = self.invoke(args)
                self.assertEqual(rc, 0)
                self.assertEqual(result["reports"]["tests"], 1)
                self.assertEqual(result["reports"]["skipped"], 1)
                args.no_skips = True
                rc, result = self.invoke(args)
                self.assertEqual(rc, 3)
                self.assertFalse(result["ok"])

    def test_overlapping_report_patterns_count_each_file_once(self):
        xml = '<testsuite tests="2"><testcase name="one"/><testcase name="two"/></testsuite>'
        args = self.args(f"from pathlib import Path; Path('TEST-one.xml').write_text({xml!r})",
                         reports=["TEST-*.xml", "*.xml", "TEST-one.xml"])
        rc, result = self.invoke(args)
        self.assertEqual(rc, 0)
        self.assertEqual(result["reports"]["tests"], 2)
        self.assertEqual(result["reports"]["fresh"], [str(self.cwd / "TEST-one.xml")])

    def test_untouched_report_with_future_mtime_is_stale(self):
        file = self.cwd / "TEST-one.xml"
        file.write_text('<testsuite tests="1"/>')
        future = time.time() + 3600
        os.utime(file, (future, future))
        rc, result = self.invoke(self.args("pass", reports=["TEST-*.xml"]))
        self.assertEqual(rc, 3)
        self.assertEqual(result["reports"]["stale"], [str(file)])
        self.assertEqual(result["reports"]["tests"], 0)

    def test_malformed_report_preserves_failed_child_exit_and_receipt(self):
        args = self.args("from pathlib import Path; Path('TEST-one.xml').write_text('<testsuite'); raise SystemExit(7)",
                         reports=["TEST-*.xml"])
        rc, result = self.invoke(args)
        self.assertEqual(rc, 7)
        self.assertFalse(result["ok"])
        self.assertEqual(result["exit_code"], 7)
        self.assertTrue(result["reports"]["invalid"])
        persisted = json.loads(Path(result["receipt"]).read_text())
        self.assertFalse(persisted["ok"])
        self.assertEqual(persisted["exit_code"], 7)
        self.assertTrue(persisted["reports"]["invalid"])

    def test_dry_run_does_not_launch_child_or_create_evidence_state(self):
        marker = self.cwd / "should-not-exist"
        args = self.args("from pathlib import Path; Path('should-not-exist').write_text('launched')",
                         dry_run=True, resource="heavy")
        rc, result = self.invoke(args)
        self.assertEqual(rc, 0)
        self.assertTrue(result["dry_run"])
        self.assertFalse(marker.exists())
        self.assertFalse(self.state.exists())
        self.assertNotIn("receipt", result)

    def test_dry_run_flag_is_available_on_the_public_cli(self):
        marker = self.cwd / "should-not-exist"
        process = subprocess.run([sys.executable, "-B", str(Path(dev.__file__)), "run", "--dry-run",
                                  "--cwd", str(self.cwd), "--state-dir", str(self.state), "--",
                                  sys.executable, "-c",
                                  "from pathlib import Path; Path('should-not-exist').write_text('launched')"],
                                 capture_output=True, text=True, timeout=5)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue(json.loads(process.stdout)["dry_run"])
        self.assertFalse(marker.exists())
        self.assertFalse(self.state.exists())

    def test_timeout_kills_the_attached_child_group(self):
        args = self.args("import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); print(p.pid,flush=True); time.sleep(30)")
        args.timeout = 0.2
        rc, result = self.invoke(args)
        self.assertEqual(rc, 124)
        self.assertTrue(result["timed_out"])
        pid = int(Path(result["log"]).read_text().strip())
        status = subprocess.run(["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True)
        self.assertTrue(status.returncode != 0 or status.stdout.strip().startswith("Z"))

    def test_a_busy_cooperative_resource_is_not_stolen(self):
        self.state.mkdir()
        with dev.resource_lock(self.state, "heavy", 0):
            with self.assertRaises(dev.Failure) as failure:
                with dev.resource_lock(self.state, "heavy", 0):
                    self.fail("lock stolen")
            self.assertEqual(failure.exception.code, "resource_busy")
        with dev.resource_lock(self.state, "heavy", 0):
            pass

    def test_parent_sigterm_is_forwarded_and_records_failure(self):
        marker = self.cwd / "started"
        code = "import os,time; from pathlib import Path; Path('started').write_text(str(os.getpid())); time.sleep(30)"
        p = subprocess.Popen([sys.executable, "-B", str(Path(dev.__file__)), "run", "--cwd", str(self.cwd),
                              "--state-dir", str(self.state), "--", sys.executable, "-c", code],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: p.kill() if p.poll() is None else None)
        deadline = time.monotonic() + 5
        while not marker.exists() and p.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(marker.exists())
        p.send_signal(signal.SIGTERM)
        stdout, stderr = p.communicate(timeout=5)
        self.assertEqual(p.returncode, 143, stderr)
        self.assertFalse(json.loads(stdout)["ok"])
        pid = marker.read_text()
        status = subprocess.run(["ps", "-p", pid, "-o", "stat="], capture_output=True, text=True)
        self.assertTrue(status.returncode != 0 or status.stdout.strip().startswith("Z"))

    def test_context_wins_and_sdk_gets_the_same_unix_endpoint(self):
        args = self.args("pass")
        args.docker = True
        def fake(argv, **kwargs):
            if argv[1:3] == ["context", "inspect"]:
                self.assertEqual(argv[3], "chosen")
                return 0, "unix:///home/u/.colima/default/docker.sock\n", ""
            self.assertEqual(kwargs["env"]["DOCKER_HOST"], "unix:///home/u/.colima/default/docker.sock")
            self.assertNotIn("DOCKER_CONTEXT", kwargs["env"])
            return 0, "daemon-id", ""
        with patch.dict(os.environ, {"DOCKER_CONTEXT": "chosen", "DOCKER_HOST": "unix:///wrong.sock"}), patch.object(dev, "probe", side_effect=fake):
            env = dev.prepared_environment(args)
        self.assertEqual(env["TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE"], "/var/run/docker.sock")

    def test_remote_context_is_not_silently_replaced(self):
        args = self.args("pass")
        args.docker = True
        with patch.object(dev, "docker_endpoint", return_value=("ssh://remote", "context:remote")):
            with self.assertRaises(dev.Failure) as failure:
                dev.prepared_environment(args)
        self.assertEqual(failure.exception.code, "docker_requires_local_unix_endpoint")

    def test_java_major_and_home_are_resolved_through_jvm_properties_not_shim_path(self):
        for wanted, version in (("8", "1.8.0_422"), ("17", "17.0.12")):
            with self.subTest(major=wanted):
                shim = self.root / ("shims-" + wanted)
                real_home = self.root / ("jdk-" + wanted)
                real_bin = real_home / "bin"
                shim.mkdir()
                real_bin.mkdir(parents=True)
                for executable in (shim / "java", real_bin / "java"):
                    executable.write_text("#!/bin/sh\nexit 0\n")
                    executable.chmod(0o755)
                def fake(argv, **kwargs):
                    if argv[0] not in (str(shim / "java"), str(real_bin / "java")):
                        return 127, "", ""
                    output = f'java version "{version}"\n'
                    if "-XshowSettings:properties" in argv:
                        output = f"Property settings:\n    java.home = {real_home}\n    java.version = {version}\n" + output
                    return 0, "", output
                with patch.dict(os.environ, {"PATH": str(shim)}, clear=True), patch.object(dev, "probe", side_effect=fake):
                    env = dev.prepared_environment(self.args("pass", java=wanted))
                self.assertEqual(Path(env["JAVA_HOME"]), real_home)
                self.assertEqual(Path(dev.shutil.which("java", path=env["PATH"])), real_bin / "java")

    def test_version_manager_probes_resolve_java_and_node_from_target_project_cwd(self):
        shim = self.root / "project-shims"
        real_home = self.root / "project-jdk"
        real_bin = real_home / "bin"
        shim.mkdir()
        real_bin.mkdir(parents=True)
        for executable in (shim / "java", shim / "node", real_bin / "java"):
            executable.write_text("#!/bin/sh\nexit 0\n")
            executable.chmod(0o755)
        calls = []
        def fake(argv, **kwargs):
            calls.append((argv, kwargs))
            self.assertEqual(Path(kwargs.get("cwd") or "").resolve(), self.cwd)
            if argv[0] == str(shim / "node"):
                return 0, "v22.8.0\n", ""
            if argv[0] in (str(shim / "java"), str(real_bin / "java")):
                output = 'java version "17.0.12"\n'
                if "-XshowSettings:properties" in argv:
                    output = f"Property settings:\n    java.home = {real_home}\n" + output
                return 0, "", output
            return 127, "", ""
        with patch.dict(os.environ, {"PATH": str(shim)}, clear=True), patch.object(dev, "probe", side_effect=fake):
            env = dev.prepared_environment(self.args("pass", java="17", node="22"))
        self.assertEqual(Path(env["JAVA_HOME"]), real_home)
        self.assertEqual(Path(dev.shutil.which("java", path=env["PATH"])), real_bin / "java")
        self.assertEqual(Path(dev.shutil.which("node", path=env["PATH"])), shim / "node")
        self.assertTrue(any("-XshowSettings:properties" in argv for argv, _ in calls))
        self.assertTrue(any(Path(argv[0]).name == "node" for argv, _ in calls))

    def test_changed_source_invalidates_a_receipt_even_with_same_dirty_paths(self):
        def git(*argv):
            subprocess.run(["git", *argv], cwd=self.cwd, check=True, capture_output=True)
        git("init", "-q")
        file = self.cwd / "source.txt"
        file.write_text("one")
        git("add", "source.txt")
        git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture")
        file.write_text("two")
        rc, result = self.invoke(self.args("pass"))
        self.assertEqual(rc, 0)
        file.write_text("three")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(dev.verify(argparse.Namespace(receipt=result["receipt"], cwd=str(self.cwd))), 3)

    def test_non_git_run_is_observable_but_not_reusable_evidence_after_edit(self):
        file = self.cwd / "source.txt"
        file.write_text("one")
        rc, result = self.invoke(self.args("pass"))
        self.assertEqual(rc, 0)
        self.assertTrue(result["ok"])
        self.assertIsNone(result["source"])
        self.assertFalse(result["source_verifiable"])
        self.assertFalse(result["reusable"])
        file.write_text("two")
        rc, verified = self.verify_result(result)
        self.assertEqual(rc, 3)
        self.assertFalse(verified["ok"])

    def test_git_source_probe_failure_is_not_treated_as_non_git(self):
        for response in ((127, "", ""), (128, "", "fatal: detected dubious ownership"),
                         (128, "", "permission denied"), (1, "", "not a git repository")):
            with self.subTest(response=response), patch.object(dev, "probe", return_value=response):
                with self.assertRaises(dev.Failure) as failure:
                    dev.source_state(self.cwd)
                self.assertEqual(failure.exception.code, "git_source_unavailable")
        with patch.object(dev, "probe", return_value=(128, "", "fatal: not a git repository (or any of the parent directories): .git")):
            self.assertIsNone(dev.source_state(self.cwd))

    def test_git_receipt_is_explicitly_verifiable_and_reusable(self):
        self.init_git()
        rc, result = self.invoke(self.args("pass"))
        self.assertEqual(rc, 0)
        self.assertTrue(result["source_verifiable"])
        self.assertTrue(result["reusable"])
        self.assertTrue(result["source"]["verifiable"])
        self.assertEqual(self.verify_result(result)[0], 0)

    def test_untracked_symlink_retargeting_invalidates_receipt(self):
        self.init_git({"first.txt": "same", "second.txt": "same"})
        link = self.cwd / "source-link"
        link.symlink_to("first.txt")
        rc, result = self.invoke(self.args("pass"))
        self.assertEqual(rc, 0)
        self.assertEqual(self.verify_result(result)[0], 0)
        link.unlink()
        link.symlink_to("second.txt")
        self.assertEqual(self.verify_result(result)[0], 3)

    def test_untracked_symlink_internal_target_content_change_invalidates_receipt(self):
        self.init_git()
        target = self.cwd / "target.txt"
        target.write_text("one")
        (self.cwd / "source-link").symlink_to("target.txt")
        rc, result = self.invoke(self.args("pass"))
        self.assertEqual(rc, 0)
        self.assertEqual(self.verify_result(result)[0], 0)
        target.write_text("two")
        self.assertEqual(self.verify_result(result)[0], 3)

    def test_symlinks_to_untracked_external_ignored_or_dotenv_state_are_not_reusable(self):
        self.init_git({".gitignore": "ignored.txt\n", "source.txt": "one"})
        targets = {"external": self.root / "outside.txt", "ignored": self.cwd / "ignored.txt",
                   "dotenv": self.cwd / ".env.fixture"}
        link = self.cwd / "source-link"
        for label, target in targets.items():
            with self.subTest(target=label):
                target.write_text("fixture-value")
                link.symlink_to(target)
                try:
                    try:
                        rc, result = self.invoke(self.args("pass"))
                    except dev.Failure as failure:
                        self.assertTrue(failure.code)
                    else:
                        self.assertFalse(result["source_verifiable"])
                        self.assertFalse(result["reusable"])
                        self.assertEqual(self.verify_result(result)[0], 3)
                finally:
                    link.unlink()

    def test_tracked_symlinks_to_external_ignored_or_dotenv_state_are_not_reusable(self):
        self.init_git({".gitignore": "ignored.txt\n", "source.txt": "one"})
        targets = {"external": self.root / "outside.txt", "ignored": self.cwd / "ignored.txt",
                   "dotenv": self.cwd / ".env.fixture"}
        link = self.cwd / "source-link"
        for label, target in targets.items():
            with self.subTest(target=label):
                target.write_text("fixture-value")
                if link.is_symlink():
                    link.unlink()
                link.symlink_to(target)
                self.git("add", "source-link")
                self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                         "commit", "-qm", "fixture symlink")
                rc, result = self.invoke(self.args("pass"))
                self.assertEqual(rc, 0)
                self.assertFalse(result["source_verifiable"])
                self.assertFalse(result["reusable"])
                self.assertEqual(self.verify_result(result)[0], 3)

    def test_tracked_symlink_internal_tracked_and_untracked_target_changes_invalidate_receipt(self):
        self.init_git({"tracked-target.txt": "one"})
        link = self.cwd / "source-link"
        link.symlink_to("tracked-target.txt")
        self.git("add", "source-link")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "commit", "-qm", "fixture symlink")
        for name in ("tracked-target.txt", "untracked-target.txt"):
            with self.subTest(target=name):
                target = self.cwd / name
                target.write_text("one")
                link.unlink()
                link.symlink_to(name)
                rc, result = self.invoke(self.args("pass"))
                self.assertEqual(rc, 0)
                self.assertTrue(result["source_verifiable"])
                self.assertTrue(result["reusable"])
                self.assertEqual(self.verify_result(result)[0], 0)
                target.write_text("two")
                self.assertEqual(self.verify_result(result)[0], 3)

    def test_dirty_submodule_content_changes_cannot_reuse_parent_receipt(self):
        self.init_git()
        origin = self.root / "fixture-submodule-origin"
        origin.mkdir()
        (origin / "source.txt").write_text("one")
        for argv in (("init", "-q"), ("add", "source.txt"),
                     ("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                      "commit", "-qm", "fixture")):
            subprocess.run(["git", *argv], cwd=origin, check=True, capture_output=True)
        self.git("-c", "protocol.file.allow=always", "submodule", "add", "-q", str(origin), "module")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "commit", "-qm", "fixture submodule")
        source = self.cwd / "module/source.txt"
        source.write_text("two")
        rc, result = self.invoke(self.args("pass"))
        self.assertEqual(rc, 0)
        self.assertFalse(result["source_verifiable"])
        self.assertFalse(result["reusable"])
        self.assertTrue(result["source"]["unsupported_submodules"])
        source.write_text("three")
        self.assertEqual(self.verify_result(result)[0], 3)

    def test_mutating_source_during_check_cannot_pass(self):
        with patch.object(dev, "source_state", side_effect=[None, {"head": "before"}, {"head": "after"}]):
            rc, result = self.invoke(self.args("pass"))
        self.assertEqual(rc, 3)
        self.assertTrue(result["source_changed"])

    def test_presence_inspection_never_returns_values(self):
        file = self.root / ".env"
        file.write_text("KEY=private-fixture\nEMPTY=\n")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            dev.env_status(argparse.Namespace(file=str(file), keys=["KEY", "EMPTY", "MISSING"]))
        self.assertNotIn("private-fixture", output.getvalue())
        self.assertEqual(json.loads(output.getvalue())["variables"], {
            "KEY": {"present": True, "nonempty": True}, "EMPTY": {"present": True, "nonempty": False},
            "MISSING": {"present": False, "nonempty": False}})

    def test_dotenv_empty_quotes_and_inline_comments_remain_empty(self):
        rc, result = self.inspect_env('DOUBLE="" # comment\nSINGLE=\'\' # comment\nBARE= # comment\n',
                                      ["DOUBLE", "SINGLE", "BARE"])
        self.assertEqual(rc, 2)
        self.assertFalse(result["ok"])
        for status in result["variables"].values():
            self.assertEqual(status, {"present": True, "nonempty": False})

    def test_dotenv_comments_hashes_export_and_presence_are_parsed_without_execution(self):
        marker = self.root / "should-not-execute"
        content = ("# ignored\n\nexport EXPORTED = value # trailing\n"
                   "DOUBLE=\"fixture # quoted\" # trailing\nSINGLE='fixture # quoted'\n"
                   "HASH=fixture#literal\nEMPTY=\n"
                   f"COMMAND=$(touch {marker})\n")
        keys = ["EXPORTED", "DOUBLE", "SINGLE", "HASH", "COMMAND", "EMPTY", "MISSING"]
        rc, result = self.inspect_env(content, keys)
        self.assertEqual(rc, 2)
        self.assertFalse(marker.exists())
        for key in keys[:5]:
            self.assertEqual(result["variables"][key], {"present": True, "nonempty": True})
        self.assertEqual(result["variables"]["EMPTY"], {"present": True, "nonempty": False})
        self.assertEqual(result["variables"]["MISSING"], {"present": False, "nonempty": False})
        self.assertNotIn("fixture", json.dumps(result))
        self.assertNotIn(str(marker), json.dumps(result))

    def test_dotenv_interpolation_reports_effective_empty_values_and_default_operators(self):
        content = ("EMPTY=\nDIRECT=$EMPTY\nBRACED=${EMPTY}\nUNDEFINED=${MISSING}\n"
                   "EMPTY_DEFAULT=${EMPTY:-}\nUNSET_DEFAULT=${MISSING-fallback}\n"
                   "PRESENT_EMPTY=${EMPTY-fallback}\nNONEMPTY_DEFAULT=${EMPTY:-fallback}\n"
                   "LITERAL='$EMPTY'\nFROM_ENV=$FIXTURE_EXISTING\n")
        keys = ["EMPTY", "DIRECT", "BRACED", "UNDEFINED", "EMPTY_DEFAULT", "PRESENT_EMPTY",
                "UNSET_DEFAULT", "NONEMPTY_DEFAULT", "LITERAL", "FROM_ENV"]
        rc, result = self.inspect_env(content, keys, {"FIXTURE_EXISTING": "fixture-nonempty"})
        self.assertEqual(rc, 2)
        for key in keys[:6]:
            self.assertEqual(result["variables"][key], {"present": True, "nonempty": False})
        for key in keys[6:]:
            self.assertEqual(result["variables"][key], {"present": True, "nonempty": True})

    def test_dotenv_unsupported_interpolation_cannot_silently_look_nonempty(self):
        file = self.root / "fixture.env"
        for value in ("${MISSING:?required}", "${MISSING:+alternative}", "${MISSING:-${OTHER}}"):
            with self.subTest(value=value):
                file.write_text("VALUE=" + value + "\n")
                with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(dev.Failure) as failure:
                        dev.env_status(argparse.Namespace(file=str(file), keys=["VALUE"]))
                self.assertEqual(failure.exception.code, "dotenv_syntax_unsupported")

    def test_quoted_multiword_and_multiline_secret_assignments_have_no_suffix_leak(self):
        code = ("print('TOKEN=\"fixture-first fixture-last\"'); "
                "print(\"PASSWORD='fixture-start\\nfixture-end'\"); "
                "print('{\"api_key\": \"fixture-json-start fixture-json-end\"}')")
        rc, result = self.invoke(self.args(code))
        self.assertEqual(rc, 0)
        log = Path(result["log"]).read_text()
        for value in ("fixture-first", "fixture-last", "fixture-start", "fixture-end",
                      "fixture-json-start", "fixture-json-end"):
            self.assertNotIn(value, log)
        self.assertIn("[REDACTED]", log)

    def test_persisted_logs_redact_passwd_authorization_private_key_and_multiline_values(self):
        lines = ("PASSWD=fixture-passwd-unquoted\n"
                 "PASSWD='fixture-passwd-start\nfixture-passwd-end'\n"
                 "AUTHORIZATION: Bearer fixture-auth-token\n"
                 '{"private_key": "fixture-private-first fixture-private-last"}\n'
                 '{"private_key": "fixture-private-start\nfixture-private-end"}\n'
                 "fixture-inherited-first\nfixture-inherited-last\n")
        with patch.dict(os.environ, {"FIXTURE_PRIVATE": "fixture-inherited-first\nfixture-inherited-last"}):
            rc, result = self.invoke(self.args(f"print({lines!r}, end='')"))
        self.assertEqual(rc, 0)
        log = Path(result["log"]).read_text()
        for value in ("fixture-passwd-unquoted", "fixture-passwd-start", "fixture-passwd-end",
                      "Bearer", "fixture-auth-token", "fixture-private-first", "fixture-private-last",
                      "fixture-private-start", "fixture-private-end", "fixture-inherited-first",
                      "fixture-inherited-last"):
            self.assertNotIn(value, log)
        self.assertIn("[REDACTED]", log)


if __name__ == "__main__":
    unittest.main()
