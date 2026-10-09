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
        return argparse.Namespace(command=["--", sys.executable, "-c", code], cwd=str(self.cwd),
                                  state_dir=str(self.state), docker=False, java=None, node=None,
                                  timeout=5, lock_timeout=0, resource=None, reports=[], no_skips=False, **kwargs)

    def invoke(self, args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            rc = dev.run(args)
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


if __name__ == "__main__":
    unittest.main()
