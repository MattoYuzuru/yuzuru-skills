from __future__ import annotations

import unittest

from load_target_guard import blocked


class LoadTargetGuardTests(unittest.TestCase):
    def test_allows_local_target(self) -> None:
        self.assertEqual(blocked("k6 run http://127.0.0.1:8080/test.js", None), (False, None))

    def test_blocks_public_target(self) -> None:
        self.assertEqual(blocked("hey https://example.com/api", None), (True, "example.com"))

    def test_private_network_still_requires_exact_authorization(self) -> None:
        self.assertEqual(blocked("k6 run https://10.0.0.5/test.js", None), (True, "10.0.0.5"))

    def test_allows_exact_authorized_host(self) -> None:
        self.assertEqual(
            blocked("wrk https://staging.example.com/api", "staging.example.com"),
            (False, None),
        )

    def test_allows_examples_and_unrelated_urls(self) -> None:
        for command in ["printf '%s' 'Example: ab https://example.com/'", "echo hey https://example.com", "hey http://localhost/; curl https://example.com/", "python3 - <<'PY'\nfixtures=['hey https://example.com/']\nPY\n"]:
            with self.subTest(command=command):
                self.assertEqual(blocked(command, None), (False, None))

    def test_checks_wrapped_nested_and_chained_loads(self) -> None:
        for command in ["sudo /usr/local/bin/hey https://example.com", "env X=1 hey https://example.com", "true; hey https://example.com", "sh -c 'hey https://example.com'", "echo $(hey https://example.com)", "bash <<'SH'\nhey https://example.com\nSH\n"]:
            with self.subTest(command=command):
                self.assertEqual(blocked(command, None), (True, "example.com"))


if __name__ == "__main__":
    unittest.main()
