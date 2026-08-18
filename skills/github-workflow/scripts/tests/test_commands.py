from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from github_workflow.client import Response
from github_workflow.commands import (
    _bounded_review_files,
    actions_command,
    issue_command,
    mutation,
    normalize_pr,
    pr_command,
    project_command,
    repository_command,
)
from github_workflow.errors import GitHubError
from github_workflow.targets import RepositoryTarget


TARGET = RepositoryTarget("github.com", "octo", "repo")


class FakeClient:
    def __init__(self, *, token=None, response=None, pages=None, graphql_data=None):
        self.token = token
        self.response = response or {}
        self.pages = pages or []
        self.graphql_data = graphql_data
        self.calls = []

    def request(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        return Response(self.response, 200, {}, "https://api.github.com/test")

    def paginate(self, path, **kwargs):
        self.calls.append(("GET*", path, kwargs))
        return self.pages, Response(self.pages, 200, {}, "https://api.github.com/test")

    def graphql(self, query, variables, **kwargs):
        self.calls.append(("GRAPHQL", query, variables))
        return Response(self.graphql_data, 200, {}, "https://api.github.com/graphql")


class CommandTests(unittest.TestCase):
    def test_mutation_dry_run_does_not_require_token(self) -> None:
        args = SimpleNamespace(dry_run=True, confirm_write=False)
        data, response = mutation(FakeClient(), args, TARGET, "PATCH", "/repos/octo/repo", {"description": "x"})
        self.assertTrue(data["dry_run"])
        self.assertIsNone(response)

    def test_write_requires_confirmation_and_token(self) -> None:
        args = SimpleNamespace(dry_run=False, confirm_write=False)
        with self.assertRaises(GitHubError) as missing_confirmation:
            mutation(FakeClient(), args, TARGET, "PATCH", "/test", {})
        self.assertIn("--confirm-write", str(missing_confirmation.exception))

        args.confirm_write = True
        with self.assertRaises(GitHubError) as missing_token:
            mutation(FakeClient(), args, TARGET, "PATCH", "/test", {})
        self.assertEqual(missing_token.exception.kind, "auth")

    def test_destructive_requires_exact_target(self) -> None:
        args = SimpleNamespace(dry_run=False, confirm_destructive=True, confirm_target="wrong")
        with self.assertRaises(GitHubError) as caught:
            mutation(
                FakeClient(token="secret"), args, TARGET, "PATCH", "/test", {},
                effect="destructive", exact_target="octo/repo#7",
            )
        self.assertIn("octo/repo#7", str(caught.exception))

    def test_issue_list_filters_pull_requests(self) -> None:
        client = FakeClient(pages=[
            {"number": 1, "title": "issue", "labels": [], "assignees": []},
            {"number": 2, "title": "pr", "pull_request": {}, "labels": [], "assignees": []},
        ])
        args = SimpleNamespace(state="open", sort="created", direction="desc", limit=20)
        data, _ = issue_command("issue-list", args, client, TARGET)
        self.assertEqual([item["number"] for item in data], [1])

    def test_repository_languages_add_percentages(self) -> None:
        client = FakeClient(response={"Python": 3, "Shell": 1})
        data, _ = repository_command("repo-languages", SimpleNamespace(), client, TARGET)
        self.assertEqual(data["total_bytes"], 4)
        self.assertEqual(data["languages"][0]["percent"], 75.0)

    def test_issue_body_file_is_used_in_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "issue.md"
            path.write_text("# Body\n", encoding="utf-8")
            args = SimpleNamespace(
                title="Title", body=None, body_file=str(path), assignees=None, labels=None,
                milestone=None, dry_run=True, confirm_write=False,
            )
            data, _ = issue_command("issue-create", args, FakeClient(), TARGET)
        self.assertEqual(data["payload"]["body"], "# Body\n")

    def test_normalize_pr_keeps_head_and_base(self) -> None:
        data = normalize_pr({
            "number": 3, "user": {"login": "octo"}, "head": {"ref": "feature", "sha": "a"},
            "base": {"ref": "main", "sha": "b"}, "labels": [], "assignees": [],
        })
        self.assertEqual(data["head"]["ref"], "feature")
        self.assertEqual(data["base"]["ref"], "main")

    def test_project_list_uses_selected_owner_type(self) -> None:
        client = FakeClient(graphql_data={
            "organization": {"projectsV2": {"nodes": [{"id": "PVT_1", "number": 1, "title": "Roadmap"}]}}
        })
        args = SimpleNamespace(owner="octo-org", owner_type="organization", limit=20)
        projects, _ = project_command("project-list", args, client, TARGET)
        self.assertEqual(projects[0]["title"], "Roadmap")
        self.assertIn("organization", client.calls[0][1])

    def test_project_count_forwards_native_filter_as_a_variable(self) -> None:
        client = FakeClient(graphql_data={
            "user": {"projectV2": {"items": {"totalCount": 14, "nodes": [], "pageInfo": {}}}}
        })
        args = SimpleNamespace(
            project="https://github.com/users/octo/projects/4/views/1",
            owner=None,
            owner_type=None,
            project_number=None,
            view_number=None,
            query='status:"In review" is:open',
            host="github.com",
        )
        result, _ = project_command("project-count", args, client, None)
        self.assertEqual(result["count"], 14)
        self.assertEqual(client.calls[0][2]["query"], args.query)

    def test_own_pull_request_approval_is_rejected_before_mutation(self) -> None:
        class OwnPullClient(FakeClient):
            def request(self, method, path, **kwargs):
                self.calls.append((method, path, kwargs))
                if path == "/user":
                    data = {"login": "octo"}
                else:
                    data = {"head": {"sha": "abc"}, "user": {"login": "octo"}}
                return Response(data, 200, {}, "https://api.github.com/test")

        args = SimpleNamespace(
            number=7,
            event="approve",
            expected_head_sha="abc",
            body=None,
            body_file=None,
            dry_run=True,
            confirm_write=False,
        )
        client = OwnPullClient()
        with self.assertRaises(GitHubError) as caught:
            pr_command("pr-review-submit", args, client, TARGET)
        self.assertIn("own pull request", caught.exception.message)
        self.assertFalse(any(call[0] == "POST" for call in client.calls))

    def test_review_context_bounds_aggregate_patch_bytes(self) -> None:
        files, budget = _bounded_review_files([
            {"filename": "one.py", "patch": "абвг"},
            {"filename": "two.py", "patch": "second"},
        ], 5)
        self.assertLessEqual(len(files[0]["patch"].encode("utf-8")), 5)
        self.assertTrue(files[0]["patch_truncated"])
        self.assertIsNone(files[1]["patch"])
        self.assertTrue(budget["truncated"])
        self.assertEqual(budget["returned_patch_bytes"], 4)

    def test_actions_mutation_dry_runs_do_not_read_unrelated_ids(self) -> None:
        cases = [
            ("run-rerun", {"run_id": 1}, "/actions/runs/1/rerun"),
            ("run-rerun-failed", {"run_id": 2}, "/actions/runs/2/rerun-failed-jobs"),
            ("job-rerun", {"job_id": 3}, "/actions/jobs/3/rerun"),
            ("run-cancel", {"run_id": 4}, "/actions/runs/4/cancel"),
        ]
        for command, identifiers, endpoint in cases:
            with self.subTest(command=command):
                args = SimpleNamespace(
                    dry_run=True,
                    confirm_write=False,
                    confirm_destructive=False,
                    confirm_target=None,
                    **identifiers,
                )
                data, response = actions_command(command, args, FakeClient(), TARGET)
                self.assertEqual(data["endpoint"], "/repos/octo/repo" + endpoint)
                self.assertIsNone(response)


if __name__ == "__main__":
    unittest.main()
