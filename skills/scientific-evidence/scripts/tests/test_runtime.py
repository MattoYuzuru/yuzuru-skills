from contextlib import nullcontext
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.request

import _runtime as runtime


class RuntimeTests(unittest.TestCase):
    def test_concurrent_first_use_preserves_arxiv_interval(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {"XDG_CACHE_HOME": root}, clear=True):
            ready = threading.Barrier(2)
            starts, errors = [], []
            def worker():
                try:
                    ready.wait(timeout=5)
                    with runtime.request_slot("arxiv", wait_limit=10):
                        starts.append(time.monotonic())
                        time.sleep(0.01)
                except BaseException as exc:
                    errors.append(type(exc).__name__)
            threads = [threading.Thread(target=worker) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=15)
            self.assertEqual(errors, [])
            self.assertEqual(len(starts), 2)
            self.assertGreaterEqual(starts[1] - starts[0], 3.0)

    def test_private_key_is_complete_and_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {"XDG_CONFIG_HOME": root}, clear=True):
            path = runtime.save_key("test-key-not-a-real-secret")
            self.assertEqual(runtime.load_key(), ("test-key-not-a-real-secret", "private-config"))
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            with self.assertRaisesRegex(runtime.EvidenceError, "key_already_exists"):
                runtime.save_key("different-test-key")
            self.assertEqual(path.read_text().strip(), "test-key-not-a-real-secret")
            self.assertEqual(list(path.parent.glob(".openalex-*")), [])

    def test_environment_precedes_private_file_and_empty_is_explicit(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {"XDG_CONFIG_HOME": root}, clear=True):
            runtime.save_key("stored-test-key")
            with patch.dict(os.environ, {"OPENALEX_API_KEY": "environment-test-key"}):
                self.assertEqual(runtime.load_key(), ("environment-test-key", "environment"))
            with patch.dict(os.environ, {"OPENALEX_API_KEY": ""}):
                self.assertEqual(runtime.load_key(), (None, None))

    def test_insecure_or_symlinked_credential_is_refused(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {"XDG_CONFIG_HOME": root}, clear=True):
            path = runtime.save_key("stored-test-key")
            if os.name != "nt":
                path.chmod(0o644)
                with self.assertRaisesRegex(runtime.EvidenceError, "permissions"):
                    runtime.load_key()
                path.chmod(0o600)
            target = path.with_name("elsewhere")
            path.rename(target)
            try:
                path.symlink_to(target)
            except OSError:
                self.skipTest("symlink creation not available on this platform")
            with self.assertRaisesRegex(runtime.EvidenceError, "symlink"):
                runtime.load_key()

    def test_redirect_cannot_forward_authorization_to_other_origin(self):
        request = urllib.request.Request("https://api.openalex.org/works", headers={"Authorization": "Bearer private-test-key"})
        with self.assertRaisesRegex(runtime.EvidenceError, "cross_origin"):
            runtime.SameOriginRedirect().redirect_request(request, None, 302, "", {}, "https://example.org/collect")

    def test_arbitrary_target_and_query_secret_are_rejected_before_network(self):
        client = runtime.HttpClient()
        client.opener = Mock()
        for provider, path, params in [("other", "/works", {}), ("epmc", "//evil.invalid", {}),
                                       ("epmc", "/../private", {}), ("openalex", "/works", {"api_key": "test-value"})]:
            with self.assertRaises(runtime.EvidenceError):
                client.get(provider, path, params)
        client.opener.open.assert_not_called()

    def test_response_is_bounded_and_no_raw_body_leaks(self):
        client = runtime.HttpClient()
        response = Mock()
        response.read.return_value = b"x" * 101
        client.opener = Mock()
        client.opener.open.return_value.__enter__ = Mock(return_value=response)
        client.opener.open.return_value.__exit__ = Mock(return_value=False)
        with patch.object(runtime, "MAX_BYTES", 100), patch.object(runtime, "request_slot", return_value=nullcontext()):
            with self.assertRaisesRegex(runtime.EvidenceError, "response_too_large"):
                client.get("epmc", "/search")
        response.read.assert_called_once_with(101)

    def test_read_retries_are_finite_and_diagnostics_redact_body(self):
        client = runtime.HttpClient(openalex_key="private-test-key")
        client.opener = Mock()
        client.opener.open.side_effect = [urllib.error.HTTPError("https://api.openalex.org", 429, "private-test-key", {}, io.BytesIO(b"private-test-key")) for _ in range(3)]
        with patch.object(runtime, "request_slot", side_effect=lambda *a: nullcontext()), patch.object(runtime.time, "sleep"):
            with self.assertRaises(runtime.EvidenceError) as raised:
                client.get("openalex", "/works")
        self.assertEqual(client.opener.open.call_count, 3)
        self.assertNotIn("private-test-key", json.dumps(raised.exception.result()))
        self.assertEqual(raised.exception.status, 429)

    def test_nonretryable_http_error_is_not_replayed(self):
        client = runtime.HttpClient()
        client.opener = Mock()
        client.opener.open.side_effect = urllib.error.HTTPError("https://www.ebi.ac.uk", 404, "", {}, io.BytesIO(b""))
        with patch.object(runtime, "request_slot", return_value=nullcontext()):
            with self.assertRaises(runtime.EvidenceError):
                client.get("epmc", "/PMC1/fullTextXML")
        self.assertEqual(client.opener.open.call_count, 1)


if __name__ == "__main__":
    unittest.main()
