#!/usr/bin/env python3
"""Summarize local Codex/Claude skill load requests without exporting conversations."""

from __future__ import annotations

import argparse
import ast
import json
import re
import shlex
import warnings
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JS_CALL = re.compile(r'''tools\.exec_command\s*\(\s*\{((?:[^{}'"`]|'(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*")*)\}\s*\)''')
SKILL_PATH = re.compile(r'(?:^|/)skills/([a-z0-9-]+)/(SKILL\.md|scripts/[^/]+)$')
READERS = {"cat", "head", "tail", "sed", "bat"}
PYTHON = re.compile(r"^(?:python(?:3(?:\.\d+)?)?|py)$")


def catalog(root: Path) -> set[str]:
    return {p.parent.name for pattern in ("skills/*/SKILL.md", "plugins/*/skills/*/SKILL.md")
            for p in root.glob(pattern)}


def timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result
    except ValueError:
        return None


def path_evidence(value: str, cwd: str, names: set[str]) -> tuple[str, str] | None:
    path = value.replace("\\", "/")
    if not path.startswith("/") and cwd:
        path = str(Path(cwd) / path)
    match = SKILL_PATH.search(path)
    if match and match.group(1) in names:
        return match.group(1), "load_request" if match.group(2) == "SKILL.md" else "helper_request"
    return None


def exec_arguments(source: str):
    """Recognize literal exec_command calls outside JS strings/comments, without evaluating JS."""
    index = 0
    while index < len(source):
        if source.startswith("//", index):
            newline = source.find("\n", index)
            index = newline if newline >= 0 else len(source)
        elif source.startswith("/*", index):
            end = source.find("*/", index + 2)
            index = end + 2 if end >= 0 else len(source)
        elif source[index] in "\"'`":
            quote = source[index]
            index += 1
            while index < len(source):
                if source[index] == "\\":
                    index += 2
                elif source[index] == quote:
                    index += 1
                    break
                else:
                    index += 1
        elif source.startswith("tools.exec_command", index):
            match = JS_CALL.match(source, index)
            if not match:
                index += len("tools.exec_command")
                continue
            fields = {}
            body = match.group(1)
            segments = []
            start = cursor = 0
            while cursor < len(body):
                if body[cursor] in "\"'":
                    quote = body[cursor]
                    cursor += 1
                    while cursor < len(body):
                        if body[cursor] == "\\":
                            cursor += 2
                        elif body[cursor] == quote:
                            cursor += 1
                            break
                        else:
                            cursor += 1
                elif body[cursor] == ",":
                    segments.append(body[start:cursor])
                    cursor += 1
                    start = cursor
                else:
                    cursor += 1
            segments.append(body[start:])
            for segment in segments:
                field = re.fullmatch(r'''\s*(cmd|workdir|"cmd"|"workdir"|'cmd'|'workdir')\s*:\s*("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')\s*''', segment)
                if field:
                    try:
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore", SyntaxWarning)
                            fields[field.group(1).strip("\"'")] = ast.literal_eval(field.group(2))
                    except (ValueError, SyntaxError):
                        pass
            if "cmd" in fields:
                yield fields
            index = match.end()
        else:
            index += 1


def shell_evidence(command: str, cwd: str, names: set[str]) -> set[tuple[str, str]]:
    # Shell source is data: never execute it. Ignore heredocs, substitutions, and writes.
    if any(marker in command for marker in ("<<", "$(", "`")):
        return set()
    try:
        tokens = list(shlex.shlex(command, posix=True, punctuation_chars=";&|<>"))
    except ValueError:
        return set()
    groups: list[list[str]] = [[]]
    for token in tokens:
        if token in {";", "&&", "||", "|", "&"}:
            groups.append([])
        else:
            groups[-1].append(token)
    found: set[tuple[str, str]] = set()
    for group in groups:
        if not group or any("<" in t or ">" in t for t in group):
            continue
        executable = Path(group[0]).name
        if executable == "cd" and len(group) == 2:
            cwd = str(Path(cwd) / group[1])
            continue
        if executable in READERS:
            for token in group[1:]:
                evidence = path_evidence(token, cwd, names)
                if evidence and evidence[1] == "load_request":
                    found.add(evidence)
        elif PYTHON.fullmatch(executable):
            # Only the script operand; a path in --query or a Python string is not execution.
            operands = group[1:]
            if operands[:1] == ["-3"]:
                operands = operands[1:]
            if operands and not operands[0].startswith("-"):
                evidence = path_evidence(operands[0], cwd, names)
                if evidence and evidence[1] == "helper_request":
                    found.add(evidence)
        elif executable == "google-ai-search" and executable in names:
            found.add((executable, "helper_request"))
    return found


def tool_evidence(name: str, value: object, cwd: str, names: set[str]) -> set[tuple[str, str]]:
    if name.lower() == "skill" and isinstance(value, dict):
        skill = str(value.get("skill", "")).split(":")[-1]
        return {(skill, "native_invocation_request")} if skill in names else set()
    if name in {"Read", "read_file"} and isinstance(value, dict):
        evidence = path_evidence(str(value.get("file_path", value.get("path", ""))), cwd, names)
        return {evidence} if evidence and evidence[1] == "load_request" else set()
    if name in {"Bash", "exec_command"} and isinstance(value, dict):
        return shell_evidence(str(value.get("command", value.get("cmd", ""))),
                              str(value.get("workdir", cwd)), names)
    if name == "exec" and isinstance(value, str):
        found: set[tuple[str, str]] = set()
        for fields in exec_arguments(value):
            found.update(shell_evidence(fields["cmd"], fields.get("workdir", cwd), names))
        return {(skill, "wrapped_" + kind.replace("request", "candidate")) for skill, kind in found}
    return set()


def calls(record: dict, provider: str):
    if provider == "codex" and record.get("type") == "response_item":
        item = record.get("payload", {})
        if not isinstance(item, dict) or not isinstance(item.get("name", ""), str):
            return
        if item.get("type") not in {"function_call", "custom_tool_call"}:
            return
        value = item.get("arguments", item.get("input", ""))
        if item.get("type") == "function_call" and isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                return
        yield item.get("call_id", item.get("id")), item.get("name", ""), value
    elif provider == "claude" and record.get("type") == "assistant":
        message = record.get("message", {})
        if not isinstance(message, dict):
            return
        content = message.get("content", [])
        if not isinstance(content, list):
            return
        for item in content:
            if isinstance(item, dict) and item.get("type") == "tool_use" and isinstance(item.get("name", ""), str):
                yield item.get("id"), item.get("name", ""), item.get("input", {})


def summarize(roots: list[tuple[str, Path]], names: set[str], since: datetime | None,
              excluded: set[str], max_files: int, max_bytes: int,
              plugin_for_skill: dict[str, str] | None = None) -> dict:
    evidence = defaultdict(lambda: defaultdict(set))
    seen: set[tuple[str, str]] = set()
    sessions: set[tuple[str, str]] = set()
    coverage = {"files_scanned": 0, "files_omitted": 0, "files_truncated": 0,
                "malformed_records": 0, "unreadable_files": 0, "records_without_time": 0,
                "excluded_sessions": 0, "inherited_records": 0,
                "bytes_read": 0, "missing_roots": 0}
    for provider, root in roots:
        if not root.is_dir():
            coverage["missing_roots"] += 1
            continue
        files = sorted(root.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        coverage["files_omitted"] += max(0, len(files) - max_files)
        for path in files[:max_files]:
            session = path.stem
            cwd = ""
            created = None
            coverage["files_scanned"] += 1
            try:
                with path.open("rb") as stream:
                    consumed = 0
                    while True:
                        line = stream.readline(max_bytes - consumed + 1)
                        if not line:
                            break
                        consumed += len(line)
                        coverage["bytes_read"] += len(line)
                        if consumed > max_bytes:
                            coverage["files_truncated"] += 1
                            break
                        try:
                            record = json.loads(line)
                        except (ValueError, UnicodeDecodeError):
                            coverage["malformed_records"] += 1
                            continue
                        if not isinstance(record, dict):
                            coverage["malformed_records"] += 1
                            continue
                        if provider == "codex" and record.get("type") in {"session_meta", "response_item"} and not isinstance(record.get("payload"), dict):
                            coverage["malformed_records"] += 1
                            continue
                        if provider == "claude" and record.get("type") == "assistant" and not isinstance(record.get("message"), dict):
                            coverage["malformed_records"] += 1
                            continue
                        if provider == "codex" and record.get("type") == "session_meta":
                            meta = record.get("payload", {})
                            cwd = meta.get("cwd", "")
                            session = meta.get("id", meta.get("session_id", session))
                            created = timestamp(meta.get("timestamp", record.get("timestamp")))
                        else:
                            cwd = record.get("cwd", cwd)
                            session = record.get("sessionId", session)
                        if not isinstance(cwd, str) or not isinstance(session, str):
                            coverage["malformed_records"] += 1
                            continue
                        if cwd and (cwd in excluded or Path(cwd).name == "yuzuru-skills" and
                                    "yuzuru-skills" in excluded):
                            coverage["excluded_sessions"] += 1
                            break
                        when = timestamp(record.get("timestamp"))
                        if created and when and when < created:
                            coverage["inherited_records"] += 1
                            continue
                        if since and when is None:
                            coverage["records_without_time"] += 1
                            continue
                        if since and when < since:
                            continue
                        sessions.add((provider, session))
                        for call_id, name, value in calls(record, provider):
                            if call_id:
                                key = (provider, str(call_id))
                                if key in seen:
                                    continue
                                seen.add(key)
                            for skill, kind in tool_evidence(name, value, cwd, names):
                                evidence[skill][provider + ":" + kind].add(session)
            except OSError:
                coverage["unreadable_files"] += 1
    rows = []
    for skill in sorted(names):
        kinds = evidence[skill]
        unique = {(key.split(":")[0], session) for key, values in kinds.items() for session in values}
        if unique:
            rows.append({"skill": skill, "sessions_with_requests": len(unique),
                         "evidence": {key: len(values) for key, values in sorted(kinds.items())}})
    rows.sort(key=lambda row: (-row["sessions_with_requests"], row["skill"]))
    plugins = defaultdict(set)
    for skill, kinds in evidence.items():
        plugin = (plugin_for_skill or {}).get(skill)
        if plugin:
            for key, values in kinds.items():
                plugins[plugin].update((key.split(":")[0], session) for session in values)
    return {"version": 1, "metric": "distinct sessions with tool-request evidence or wrapped-source candidates",
            "since": since.isoformat() if since else None, "coverage": coverage,
            "sessions_in_window": len(sessions), "skills": rows,
            "plugins": [{"plugin": plugin, "sessions_with_requests": len(values)}
                        for plugin, values in sorted(plugins.items(), key=lambda p: (-len(p[1]), p[0]))],
            "limitations": ["Requests are not proof of successful loading or useful outcomes.",
                            "Catalogs, prose mentions, and user messages are excluded.",
                            "Unsupported tools and indirect/variable paths are not counted.",
                            "Wrapped exec calls are source candidates; control flow and successful execution are not proven.",
                            "Local retention and forks can bias coverage; absent evidence is not non-use."]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-root", type=Path, help="explicit directory of Codex JSONL sessions")
    parser.add_argument("--claude-root", type=Path, help="explicit directory of Claude JSONL projects")
    parser.add_argument("--since", help="inclusive ISO date/time (UTC when offset omitted)")
    parser.add_argument("--exclude-cwd", action="append", default=[],
                        help="exclude exact cwd; 'yuzuru-skills' excludes this repo and its worktrees")
    parser.add_argument("--max-files", type=int, default=500, help="per provider (default: 500)")
    parser.add_argument("--max-file-mib", type=int, default=128, help="read cap per file (default: 128 MiB)")
    parser.add_argument("--output", type=Path, help="optional aggregate JSON outside the repository")
    args = parser.parse_args()
    if not args.codex_root and not args.claude_root:
        parser.error("supply --codex-root and/or --claude-root; user data is never scanned by default")
    since = timestamp(args.since) if args.since else None
    if args.since and since is None:
        parser.error("--since must be an ISO date/time")
    if args.max_files < 1 or args.max_file_mib < 1:
        parser.error("read caps must be positive")
    if args.output and any((parent / ".git").exists() for parent in args.output.resolve().parents):
        parser.error("usage aggregates must stay outside Git repositories")
    roots = [(provider, root.expanduser()) for provider, root in
             (("codex", args.codex_root), ("claude", args.claude_root)) if root is not None]
    plugin_for_skill = {p.parent.name: p.parents[2].name for p in ROOT.glob("plugins/*/skills/*/SKILL.md")}
    result = summarize(roots, catalog(ROOT), since, set(args.exclude_cwd), args.max_files,
                       args.max_file_mib * 1024 * 1024, plugin_for_skill)
    encoded = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # Open exclusively so a summary cannot silently replace an existing file.
        try:
            with args.output.open("x", encoding="utf-8") as stream:
                args.output.chmod(0o600)
                stream.write(encoded + "\n")
        except OSError:
            print(json.dumps({"ok": False, "error_kind": "output_error",
                              "error": "Cannot create the aggregate; existing outputs are never replaced."}))
            return 1
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
