from pathlib import Path
import unittest

from hook_shell import AnalysisLimit, commands

ROOT = Path(__file__).resolve().parents[2]


class HookRuntimeTests(unittest.TestCase):
    def test_installed_copies_match_canonical_runtime(self):
        source = (ROOT / "scripts/hook_shell.py").read_bytes()
        for name in ["devops-agent", "sre-agent"]:
            with self.subTest(plugin=name):
                self.assertEqual((ROOT / "plugins" / name / "hooks/hook_shell.py").read_bytes(), source)

    def test_preserves_quoted_separators_as_arguments(self):
        self.assertEqual(commands("printf '%s' ';' 'echo' 'ok'"), [["printf", "%s", ";", "echo", "ok"]])

    def test_ignores_literal_data_and_checks_following_commands(self):
        self.assertEqual(commands("cat <<'TEXT'\necho data\nTEXT\necho real\n"), [["cat"], ["echo", "real"]])

    def test_expanding_heredoc_quotes_are_data_not_shell_quotes(self):
        self.assertIn(["echo", "expanded"], commands("cat <<TEXT\n'$(echo expanded)'\nTEXT\n"))

    def test_nested_quotes_and_substitutions(self):
        self.assertIn(["echo", "inner"], commands('echo "$(printf \'%s\' "$(echo inner)")"'))

    def test_comments_continuations_and_redirections(self):
        command = "echo " + "\\" + "\n" + "ok 2>ignored # example\necho next"
        self.assertEqual(commands(command), [["echo", "ok"], ["echo", "next"]])

    def test_limits_are_explicit(self):
        for text in ["echo 'unterminated", "cat <<'TEXT'\nmissing delimiter", "echo $(unterminated", "a" * 262145]:
            with self.subTest(size=len(text)):
                self.assertRaises(AnalysisLimit, commands, text)


if __name__ == "__main__":
    unittest.main()
