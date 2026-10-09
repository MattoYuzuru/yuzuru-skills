#!/usr/bin/env python3
"""Verify literal heredoc allowance while retaining credential disclosure denials."""
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import secret_guard as guard


class GuardTests(unittest.TestCase):
    def denied(self, command):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            try:
                guard.check_bash(command)
            except SystemExit:
                return json.loads(out.getvalue())["hookSpecificOutput"]["permissionDecision"] == "deny"
        return False

    def test_actual_disclosure_is_still_denied(self):
        for command in ("cat .env", "python3 -c 'print(open(\".env\").read())'",
                        "cat < .env", "echo $API_TOKEN", "printenv", "docker compose --env-file .env config"):
            with self.subTest(command=command):
                self.assertTrue(self.denied(command))

    def test_literal_quoted_cat_body_is_data_and_following_code_stays_checked(self):
        text = "cat > helper.sh <<'EOF'\ncat < .env\necho $API_TOKEN\nEOF\n"
        self.assertFalse(self.denied(text))
        self.assertTrue(self.denied(text + "cat .env\n"))
        self.assertTrue(self.denied("cat > .env <<'EOF'\nhello\nEOF\n"))

    def test_executable_unquoted_and_unterminated_bodies_are_not_exempt(self):
        for command in ("cat <<EOF\n$API_TOKEN\nEOF\n",
                        "bash <<'EOF'\ncat .env\nEOF\n",
                        "python3 <<'PY'\nprint(open('.env').read())\nPY\n",
                        "cat <<'EOF'\ncat .env\n"):
            with self.subTest(command=command):
                self.assertTrue(self.denied(command))

    def test_presence_helper_is_exact_and_uncombined(self):
        helper = Path(guard.__file__).with_name("dev.py")
        self.assertFalse(self.denied(f"python3 -B {helper} env --file .env TOKEN"))
        self.assertTrue(self.denied("python3 /untrusted/dev.py env --file .env TOKEN"))
        self.assertTrue(self.denied(f"python3 {helper} env --file .env; cat .env"))

    def test_existing_launcher_and_masked_routes_remain_usable(self):
        for command in ("MNEMA_LOCAL_OAUTH_ENV_FILE=/x/.env ./launcher.sh start",
                        "docker compose --env-file .env up -d", "~/.claude/bin/envpeek .env KEY",
                        "source .env; ./gradlew test", "cat .env.example"):
            with self.subTest(command=command):
                self.assertFalse(self.denied(command))


if __name__ == "__main__":
    unittest.main()
