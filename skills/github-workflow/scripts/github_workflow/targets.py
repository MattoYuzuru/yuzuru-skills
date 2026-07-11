"""Resolve and sanitize GitHub repository targets."""

from __future__ import annotations

import re
import subprocess
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .errors import GitHubError


PART_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
SCP_RE = re.compile(r"^(?:[^@\s]+@)?(?P<host>[^:/\s]+):(?P<path>[^\s]+)$")


@dataclass(frozen=True)
class RepositoryTarget:
    host: str
    owner: str
    repo: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repo}"

    def as_dict(self) -> dict[str, str]:
        return {"host": self.host, "repository": self.full_name}


def redact_url(value: str) -> str:
    value = re.sub(r"(https?://)[^/@\s]+@", r"\1***@", value)
    value = re.sub(r"(https?://)[^/:@\s]+:[^/@\s]+@", r"\1***:***@", value)
    return value


def _from_parts(host: str, path: str) -> RepositoryTarget:
    clean_path = path.strip().strip("/")
    if clean_path.endswith(".git"):
        clean_path = clean_path[:-4]
    parts = clean_path.split("/")
    if len(parts) != 2 or not all(PART_RE.fullmatch(part) for part in parts):
        raise GitHubError("repository must be owner/repo or a GitHub repository URL", kind="validation")
    normalized_host = host.strip().lower().rstrip(".")
    if not normalized_host or any(char.isspace() for char in normalized_host):
        raise GitHubError("invalid GitHub host", kind="validation")
    return RepositoryTarget(normalized_host, parts[0], parts[1])


def parse_repository(value: str, default_host: str = "github.com") -> RepositoryTarget:
    candidate = value.strip()
    if not candidate:
        raise GitHubError("repository target is empty", kind="validation")

    parsed = urllib.parse.urlparse(candidate)
    if parsed.scheme in {"http", "https", "ssh", "git"} and parsed.hostname:
        return _from_parts(parsed.hostname, parsed.path)

    scp = SCP_RE.fullmatch(candidate)
    if scp and "/" in scp.group("path"):
        return _from_parts(scp.group("host"), scp.group("path"))

    if "://" in candidate or candidate.count("/") != 1:
        raise GitHubError("unsupported repository target", kind="validation")
    return _from_parts(default_host, candidate)


def git_remote_urls(
    cwd: str | Path = ".",
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, str]:
    try:
        names = runner(
            ["git", "remote"], cwd=str(cwd), capture_output=True, text=True, timeout=10, check=False
        )
    except (FileNotFoundError, subprocess.SubprocessError, OSError) as exc:
        raise GitHubError(f"cannot inspect Git remotes: {exc}", kind="validation") from exc
    if names.returncode != 0:
        raise GitHubError("current directory is not a readable Git checkout", kind="validation")

    remotes: dict[str, str] = {}
    for name in names.stdout.splitlines():
        name = name.strip()
        if not name:
            continue
        result = runner(
            ["git", "remote", "get-url", name],
            cwd=str(cwd), capture_output=True, text=True, timeout=10, check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            remotes[name] = result.stdout.strip()
    return remotes


def resolve_repository(
    explicit: str | None,
    *,
    cwd: str | Path = ".",
    default_host: str = "github.com",
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> RepositoryTarget:
    if explicit:
        return parse_repository(explicit, default_host)

    remotes = git_remote_urls(cwd, runner=runner)
    preferred = [(name, remotes[name]) for name in ("upstream", "origin") if name in remotes]
    if not preferred:
        raise GitHubError("no upstream or origin remote; pass --repo owner/repo", kind="validation")

    parsed: list[tuple[str, RepositoryTarget]] = []
    for name, url in preferred:
        try:
            parsed.append((name, parse_repository(url, default_host)))
        except GitHubError:
            continue
    if not parsed:
        raise GitHubError("no GitHub repository remote; pass --repo owner/repo", kind="validation")

    unique = {(item.host, item.owner, item.repo) for _, item in parsed}
    if len(unique) > 1:
        summary = ", ".join(f"{name}={target.full_name}" for name, target in parsed)
        raise GitHubError(f"ambiguous remotes ({summary}); pass --repo explicitly", kind="validation")
    return parsed[0][1]
