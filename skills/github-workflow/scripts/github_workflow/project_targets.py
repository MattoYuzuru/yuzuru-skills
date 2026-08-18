"""Parse unambiguous GitHub Projects V2 owner, project, and view targets."""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass

from .errors import GitHubError


PROJECT_URL_RE = re.compile(
    r"^/(users|orgs)/([^/]+)/projects/(\d+)(?:/views/(\d+))?/?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ProjectTarget:
    owner: str
    owner_type: str
    number: int
    view_number: int | None = None

    @property
    def label(self) -> str:
        view = f"/views/{self.view_number}" if self.view_number is not None else ""
        namespace = "orgs" if self.owner_type == "organization" else "users"
        return f"https://github.com/{namespace}/{self.owner}/projects/{self.number}{view}"


def parse_project_url(value: str, *, expected_host: str = "github.com") -> ProjectTarget:
    parsed = urllib.parse.urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise GitHubError("--project must be a GitHub Projects V2 URL", kind="validation")
    if parsed.hostname.casefold() != expected_host.casefold():
        raise GitHubError(
            f"project host {parsed.hostname} differs from --host {expected_host}",
            kind="validation",
        )
    match = PROJECT_URL_RE.fullmatch(parsed.path)
    if not match:
        raise GitHubError(
            "--project must look like /users/OWNER/projects/NUMBER[/views/NUMBER] "
            "or /orgs/OWNER/projects/NUMBER[/views/NUMBER]",
            kind="validation",
        )
    namespace, owner, number, view = match.groups()
    return ProjectTarget(
        owner=urllib.parse.unquote(owner),
        owner_type="organization" if namespace.casefold() == "orgs" else "user",
        number=int(number),
        view_number=int(view) if view else None,
    )


def resolve_project_target(args: object, *, expected_host: str = "github.com") -> ProjectTarget:
    project_url = getattr(args, "project", None)
    if project_url:
        parsed = parse_project_url(project_url, expected_host=expected_host)
        supplied = {
            "owner": getattr(args, "owner", None),
            "owner_type": getattr(args, "owner_type", None),
            "number": getattr(args, "project_number", None),
            "view": getattr(args, "view_number", None),
        }
        conflicts = [
            key for key, value in supplied.items()
            if value is not None and value != getattr(parsed, "view_number" if key == "view" else key)
        ]
        if conflicts:
            raise GitHubError(
                f"--project conflicts with explicit {', '.join(conflicts)} argument(s)",
                kind="validation",
            )
        return parsed
    owner = getattr(args, "owner", None)
    number = getattr(args, "project_number", None)
    if not owner or number is None:
        raise GitHubError(
            "provide --project URL or both --owner and --project-number",
            kind="validation",
        )
    return ProjectTarget(
        owner=owner,
        owner_type=getattr(args, "owner_type", None) or "user",
        number=number,
        view_number=getattr(args, "view_number", None),
    )
