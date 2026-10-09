#!/usr/bin/env python3
"""PreToolUse guard for dotenv secrets.

Agents may run commands that pass a dotenv file to a program (launchers, docker compose
--env-file, `test -f`, `shasum`), but must not print its values. Blocks:
  * Read/Grep/Glob/Edit/Write/NotebookEdit on a dotenv file (examples/templates allowed);
  * Bash commands that reference a dotenv file together with a program that would show,
    copy or ship its content (cat, grep, sed, cp, curl, python -c, echo, ...);
  * Bash commands that dump the environment or echo a secret-looking variable.
Masked inspection: ~/.claude/bin/envpeek FILE [KEY...] or envpeek --env KEY.

This is a guardrail against accidental disclosure, not a sandbox: a program the agent
runs can still read the file itself.
"""
import json
import os
import re
import sys
import shlex
from pathlib import Path

ALLOWED_SUFFIXES = (".example", ".sample", ".template", ".dist", ".defaults")
ENV_PATH = re.compile(r"(?:^|[^A-Za-z0-9_.-])(\.env(?:\.[A-Za-z0-9_-]+)?)(?=$|[^A-Za-z0-9_.-])")
# A dotenv path in these positions is loaded or checked, never shown: `source F`, `. F`, `--env-file F`,
# `VAR=F` (handed to a launcher), `test -f F`, `[ -f F ]`, `ls`/`stat`/`shasum F`.
SAFE_CONTEXT = re.compile(r"(?:\bsource|(?:^|[;&|(]\s*)\.|--env-file[= ]|[A-Za-z_][A-Za-z0-9_]*=|\s-[efsr]|\b(?:ls|stat|shasum|sha256sum|md5)(?:\s+-\S+)*)\s*['\"]?$")
READERS = {
    "cat", "tac", "less", "more", "head", "tail", "bat", "nl", "od", "xxd", "hexdump", "strings",
    "grep", "egrep", "fgrep", "rg", "ag", "ack", "awk", "gawk", "sed", "cut", "sort", "uniq",
    "paste", "column", "tr", "fold", "fmt", "jq", "yq", "diff", "cmp", "comm", "cp", "mv", "ln",
    "rsync", "scp", "tee", "dd", "base64", "base32", "openssl", "gpg", "zip", "tar", "gzip",
    "curl", "wget", "nc", "pbcopy", "open", "code", "vim", "vi", "nano", "emacs",
    "printenv", "env", "declare", "compgen", "python", "python3", "node", "deno",
    "bun", "git", "ruby", "perl", "php", "lua", "osascript", "sqlite3", "xargs", "eval", "read",
}
SECRET_NAME = r"[A-Za-z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD|PASSWD|PASS|CREDENTIAL|PRIVATE|AUTH)[A-Za-z0-9_]*"
SECRET_ECHO = re.compile(r"\b(?:echo|printf)\b[^|;&\n]*\$\{?" + SECRET_NAME + r"\b", re.IGNORECASE)
ENV_DUMP = re.compile(r"(?:^|[|;&(`]\s*|\$\(\s*)(?:printenv|env|export\s+-p|declare\s+-[px]+|set|compgen\s+-v)\s*(?:$|[|;&)>`])")
HINT = "Use ~/.claude/bin/envpeek FILE [KEY...] (or envpeek --env KEY) to see masked values."


def executable_text(command: str) -> str:
    """Ignore only quoted literal cat data; executable/unquoted heredocs stay checked."""
    lines = command.splitlines(keepends=True)
    result = []
    index = 0
    while index < len(lines):
        line = lines[index]
        result.append(line)
        # Restrict this exception to a whole cat command, not arbitrary shell or Python code.
        match = re.fullmatch(r"\s*cat(?:\s+>\s*(?:'[^']+'|\"[^\"]+\"|[^\s;&|<>]+))?\s+<<(['\"])([A-Za-z_][A-Za-z0-9_]*)\1\s*\n?", line)
        index += 1
        if match:
            end = next((j for j in range(index, len(lines)) if lines[j].rstrip("\r\n") == match[2]), None)
            if end is not None:
                result.append("\n" * (end - index + 1))
                index = end + 1
    return "".join(result)


def presence_helper(command: str) -> bool:
    """Allow only the maintained helper's value-free env subcommand, alone."""
    if re.search(r"[|;&`]|\$\(", command):
        return False
    try:
        words = shlex.split(command)
    except ValueError:
        return False
    if not words:
        return False
    if Path(words[0]).name in {"python3", "python"}:
        words = words[1:]
        while words and words[0] in {"-B", "-I"}:
            words = words[1:]
    return (len(words) >= 4 and Path(words[0]).expanduser().resolve() == Path(__file__).resolve().with_name("dev.py")
            and words[1:3] == ["env", "--file"])


def is_secret_env(name: str) -> bool:
    base = os.path.basename(name.rstrip("/"))
    if base != ".env" and not base.startswith(".env."):
        return False
    return not base.endswith(ALLOWED_SUFFIXES)


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason + " " + HINT}}))
    sys.exit(0)


def check_bash(command: str) -> None:
    if presence_helper(command):
        return
    lines = command.splitlines()
    for index, line in enumerate(lines):
        unquoted = re.search(r"<<-?\s*([A-Za-z_][A-Za-z0-9_]*)\s*$", line)
        if unquoted:
            end = next((j for j in range(index + 1, len(lines)) if lines[j].strip() == unquoted[1]), len(lines))
            if re.search(r"\$\{?" + SECRET_NAME + r"\b", "\n".join(lines[index + 1:end]), re.I):
                deny("Blocked: an unquoted heredoc expands a secret-looking variable.")
    command = executable_text(command)
    matches = [m for m in ENV_PATH.finditer(command) if is_secret_env(m.group(1))]
    if matches:
        name = matches[0].group(1)
        if re.search(r"<\s*['\"]?[^\s'\"]*" + re.escape(name), command):
            deny(f"Blocked: reading {name} through a redirection.")
        if re.search(r"\bcompose\b", command) and re.search(r"\bconfig\b", command):
            deny("Blocked: docker compose config prints interpolated secrets.")
        envpeek_only = re.search(r"(?:^|[\s/])envpeek(?:\s|$)", command) and not re.search(r"[|;&`]|\$\(", command)
        exposed = [m for m in matches if not SAFE_CONTEXT.search(_path_prefix(command, m))]
        if exposed and not envpeek_only:
            words = {os.path.basename(w) for w in re.findall(r"[A-Za-z0-9_./+-]+", command)}
            readers = sorted(words & READERS)
            if readers:
                deny(f"Blocked: the command passes {name} to a command line that also runs {', '.join(readers)}, "
                     "which could print or copy secrets.")
    if ENV_DUMP.search(command):
        deny("Blocked: dumping the environment could reveal secrets.")
    if SECRET_ECHO.search(command):
        deny("Blocked: echoing a secret-looking variable.")


def _path_prefix(command: str, match: "re.Match") -> str:
    """The text before the whole path token that ends in the dotenv name (e.g. before `/x/Mnema/.env`)."""
    start = match.start(1)
    while start > 0 and command[start - 1] not in " \t\n=;&|()<>'\"":
        start -= 1
    return command[:start]


def main() -> None:
    if sys.argv[1:] == ["--help"]:
        print(__doc__.strip())
        return
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)
    tool = payload.get("tool_name", "")
    data = payload.get("tool_input") or {}
    if tool == "Bash":
        check_bash(str(data.get("command", "")))
        return
    keys = ("file_path", "path", "notebook_path", "glob") + (("pattern",) if tool == "Glob" else ())
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and any(is_secret_env(part) for part in re.split(r"[\s,{}]", value) if part):
            deny(f"Blocked: {tool} on a dotenv file ({value}).")


if __name__ == "__main__":
    main()
