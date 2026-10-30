from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

from guard_command import blocked, extract_command


class GuardCommandTests(unittest.TestCase):
    def test_extracts_hook_command(self) -> None:
        self.assertEqual(extract_command({"tool_input": {"command": "echo ok"}}), "echo ok")

    def test_blocks_root_or_home_deletion(self) -> None:
        for command in ["rm -rf /", "rm -r /", "rm -f -r /", "rm --recursive --force /", "rm -rf -- /", "rm -rf ~", "rm -rf ~/", "rm -rf $HOME", 'rm -rf "${HOME}/"', f"rm -rf {Path.home()}", "rm -rf ~/*", "rm -rf /*", "sudo -u root /bin/rm -rf /", "env X=1 command rm -rf /", "true; rm -rf /", "if rm -rf /; then echo done; fi"]:
            with self.subTest(command=command):
                self.assertTrue(blocked(command))

    def test_allows_scoped_cleanup(self) -> None:
        for command in ["rm -rf /tmp/yuzuru-test-123", "rm -rf ~/Projects/example/.cache", 'rm -rf "$HOME/.cache/example"']:
            with self.subTest(command=command):
                self.assertFalse(blocked(command))

    def test_retains_explicit_powershell_home_control(self) -> None:
        self.assertTrue(blocked("Remove-Item $HOME -Recurse -Force"))
        self.assertTrue(blocked("del $HOME /s"))
        self.assertTrue(blocked("pwsh -Command 'Remove-Item $HOME -Recurse'"))

    def test_allows_quoted_examples_and_comments(self) -> None:
        for command in ["printf '%s' 'Example: rm -rf ~/'", "python3 -c 'commands = [\"rm -rf /\"]'", "echo ok # rm -rf /", "printf '%s' ';' 'rm' '-rf' '/'", "python3 - <<'PY'\ncommands = ['rm -rf /', 'rm -rf ~/']\nprint(commands)\nPY\n"]:
            with self.subTest(command=command):
                self.assertFalse(blocked(command))

    def test_checks_explicit_shell_execution(self) -> None:
        for command in ["sh -c 'rm -rf /'", "bash -lc 'rm -rf /'", "eval 'rm -rf /'", "echo $(rm -rf /)", 'echo "$(rm -rf /)"', "echo `rm -rf /`", "bash <<'SH'\nrm -rf /\nSH\n", "cat <<'SH' | sh\nrm -rf /\nSH\n", "cat <<DATA\n'$(rm -rf /)'\nDATA\n"]:
            with self.subTest(command=command):
                self.assertTrue(blocked(command))

    def test_quoted_data_does_not_hide_later_command(self) -> None:
        self.assertTrue(blocked("cat <<'DATA'\nrm -rf /\nDATA\nrm -rf /\n"))

    def test_shell_input_is_scoped_to_its_pipeline(self) -> None:
        self.assertTrue(blocked("bash <<< 'rm -rf /'"))
        self.assertTrue(blocked("cat <<< 'rm -rf /' | sh"))
        self.assertFalse(blocked("sh -c 'echo ok'; cat <<'DATA'\nrm -rf /\nDATA\n"))
        self.assertFalse(blocked("sh -c 'echo ok'; cat <<< 'rm -rf /'"))

    def test_hook_rejects_without_executing_fixture(self) -> None:
        hook = Path(__file__).resolve().parents[1] / "guard_command.py"
        result = subprocess.run([sys.executable, "-B", str(hook)], input=json.dumps({"tool_input": {"command": "rm -rf /"}}), capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("blocked broad destructive command", result.stderr)


if __name__ == "__main__":
    unittest.main()
