from __future__ import annotations

import io
import json
import unittest
import urllib.error

from github_workflow.client import GitHubClient
from github_workflow.errors import GitHubError


class FakeResponse:
    def __init__(self, data, *, status=200, headers=None, url="https://api.github.com/test"):
        self.body = data if isinstance(data, bytes) else json.dumps(data).encode()
        self.status = status
        self.headers = headers or {}
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, amount=-1):
        return self.body if amount < 0 else self.body[:amount]

    def geturl(self):
        return self.url


def http_error(status, data, headers=None):
    return urllib.error.HTTPError(
        "https://api.github.com/test",
        status,
        "error",
        headers or {},
        io.BytesIO(json.dumps(data).encode()),
    )


class ClientTests(unittest.TestCase):
    def test_success_headers_and_rate_limit(self) -> None:
        seen = []

        def urlopen(request, **kwargs):
            seen.append(request)
            return FakeResponse({"login": "octo"}, headers={"X-RateLimit-Remaining": "42"})

        response = GitHubClient(token="secret", urlopen=urlopen).request("GET", "/user")
        self.assertEqual(response.data["login"], "octo")
        self.assertEqual(response.rate_limit["remaining"], 42)
        self.assertEqual(seen[0].get_header("Authorization"), "Bearer secret")

    def test_get_retries_but_write_does_not(self) -> None:
        get_calls = []
        sleeps = []

        def get_open(request, **kwargs):
            get_calls.append(request)
            if len(get_calls) == 1:
                raise http_error(503, {"message": "temporary"})
            return FakeResponse({"ok": True})

        client = GitHubClient(urlopen=get_open, sleeper=sleeps.append, jitter=lambda: 0)
        self.assertTrue(client.request("GET", "/test").data["ok"])
        self.assertEqual(len(get_calls), 2)
        self.assertEqual(sleeps, [1.0])

        write_calls = []

        def write_open(request, **kwargs):
            write_calls.append(request)
            raise http_error(503, {"message": "unknown outcome"})

        with self.assertRaises(GitHubError):
            GitHubClient(urlopen=write_open, sleeper=sleeps.append).request("POST", "/test", payload={})
        self.assertEqual(len(write_calls), 1)

    def test_retry_after_respects_max_wait(self) -> None:
        calls = []

        def urlopen(request, **kwargs):
            calls.append(request)
            raise http_error(429, {"message": "rate limited"}, {"Retry-After": "30"})

        with self.assertRaises(GitHubError) as caught:
            GitHubClient(urlopen=urlopen, max_wait=10).request("GET", "/test")
        self.assertEqual(len(calls), 1)
        self.assertEqual(caught.exception.kind, "rate-limit")
        self.assertEqual(caught.exception.retry_after, 30)

    def test_pagination_follows_link_and_caps_result(self) -> None:
        responses = [
            FakeResponse(
                [{"id": 1}, {"id": 2}],
                headers={"Link": '<https://api.github.com/items?page=2>; rel="next"'},
            ),
            FakeResponse([{"id": 3}, {"id": 4}]),
        ]

        def urlopen(request, **kwargs):
            return responses.pop(0)

        items, _ = GitHubClient(urlopen=urlopen).paginate("/items", limit=3)
        self.assertEqual([item["id"] for item in items], [1, 2, 3])

    def test_graphql_partial_and_fatal_errors(self) -> None:
        partial = FakeResponse({"data": {"viewer": None}, "errors": [{"message": "hidden"}]})
        client = GitHubClient(urlopen=lambda *args, **kwargs: partial)
        response = client.graphql("query X { viewer { login } }", {})
        self.assertTrue(response.data["partial"])

        fatal = FakeResponse({"data": None, "errors": [{"message": "denied"}]})
        with self.assertRaises(GitHubError) as caught:
            GitHubClient(urlopen=lambda *args, **kwargs: fatal).graphql("query X { viewer { login } }", {})
        self.assertEqual(caught.exception.kind, "graphql")

    def test_response_is_bounded(self) -> None:
        response = GitHubClient(
            urlopen=lambda *args, **kwargs: FakeResponse(b"abcdefgh")
        ).request("GET", "/raw", raw=True, max_bytes=4)
        self.assertEqual(response.data, b"abcd")
        self.assertTrue(response.truncated)


if __name__ == "__main__":
    unittest.main()
