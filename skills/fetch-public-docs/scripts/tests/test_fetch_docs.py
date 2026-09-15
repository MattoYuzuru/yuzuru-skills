from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "fetch_docs.py"
SPEC = importlib.util.spec_from_file_location("fetch_docs", SCRIPT)
assert SPEC and SPEC.loader
fetch_docs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fetch_docs)


class PublicUrlValidationTests(unittest.TestCase):
    def test_accepts_public_https_url(self) -> None:
        fetch_docs.validate_public_url("https://docs.example.com/guide")

    def test_rejects_credentials_and_non_https(self) -> None:
        for url in (
            "http://docs.example.com/guide",
            "https://user:secret@docs.example.com/guide",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                fetch_docs.validate_public_url(url)

    def test_rejects_local_and_private_ip_literals(self) -> None:
        for url in (
            "https://localhost/guide",
            "https://service.local/guide",
            "https://127.0.0.1/guide",
            "https://10.0.0.1/guide",
            "https://[::1]/guide",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                fetch_docs.validate_public_url(url)


class BridgeOriginTests(unittest.TestCase):
    def test_rejects_cross_origin_artifact_before_network(self) -> None:
        with self.assertRaises(fetch_docs.ClientError):
            fetch_docs.request(
                "https://bridge.example",
                "not-a-real-token",
                "https://other.example/artifact.md",
            )

    def test_origin_normalizes_case(self) -> None:
        self.assertEqual(
            fetch_docs.origin("https://BRIDGE.example/path"),
            ("https", "bridge.example", None),
        )


if __name__ == "__main__":
    unittest.main()
