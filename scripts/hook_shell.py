"""Bounded shell-command inspection for accidental-operation guards, never execution.

Vendored into each hook package by sync_hook_runtime.py. This is a POSIX-shell
subset, not a sandbox: aliases, sourced files and computed commands are opaque.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

MAX_BYTES = 262144
MAX_DEPTH = 8
SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "fish", "pwsh", "powershell"}
SEPARATORS = {";", ";;", "&&", "||", "|", "&", "\n", "(", ")"}
REDIRECTIONS = {"<", ">", ">>", "<<", "<<-", "<<<", ">&", "<&", ">|", "<>"}
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")


class AnalysisLimit(ValueError):
    """The command cannot be inspected within the hook's bounded subset."""


@dataclass
class Token:
    value: str
    operator: bool = False
    quoted: bool = False


def basename(value: str) -> str:
    return value.rsplit("/", 1)[-1].lower()


def unwrap(words: list[str]) -> list[str]:
    """Recognize common transparent wrappers without searching arbitrary arguments."""
    words = list(words)
    while words:
        name = basename(words[0])
        if ASSIGNMENT.match(words[0]) or name in {"if", "then", "elif", "else", "do", "!", "time", "{"}:
            words.pop(0)
        elif name in {"command", "builtin", "exec", "nohup"}:
            words.pop(0)
            while words and words[0] in {"--", "-p"}:
                words.pop(0)
        elif name == "env":
            words.pop(0)
            while words and (ASSIGNMENT.match(words[0]) or words[0] in {"-i", "--ignore-environment", "--"}):
                words.pop(0)
        elif name == "sudo":
            words.pop(0)
            while words and words[0].startswith("-"):
                option = words.pop(0)
                if option in {"-u", "-g", "-h", "-p", "-C", "--user", "--group", "--host"} and words:
                    words.pop(0)
        else:
            break
    return words


def simple_commands(tokens: list[Token]) -> list[list[str]]:
    result: list[list[str]] = []
    current: list[str] = []
    redirect = False
    for token in tokens + [Token("\n", True)]:
        if token.operator and token.value in SEPARATORS:
            if current:
                result.append(unwrap(current))
            current = []
            redirect = False
        elif token.operator and token.value in REDIRECTIONS:
            if current and current[-1].isdigit():
                current.pop()
            redirect = True
        elif redirect:
            redirect = False
        else:
            current.append(token.value)
    return [words for words in result if words]


def shell_input(tokens: list[Token], position: int) -> bool:
    """A heredoc/here-string can reach any shell in its own pipeline only."""
    boundaries = {";", ";;", "&&", "||", "&", "\n"}
    start = position
    end = position + 1
    while start and not (tokens[start - 1].operator and tokens[start - 1].value in boundaries):
        start -= 1
    while end < len(tokens) and not (tokens[end].operator and tokens[end].value in boundaries):
        end += 1
    return any(basename(words[0]) in SHELLS or basename(words[0]) == "eval" for words in simple_commands(tokens[start:end]))


def commands(text: str, depth: int = 0, *, expansions_only: bool = False) -> list[list[str]]:
    """Return command positions and explicit nested shell payloads, excluding data."""
    if depth > MAX_DEPTH or len(text.encode()) > MAX_BYTES:
        raise AnalysisLimit("command analysis limit exceeded; use a small script file")
    if expansions_only:
        nested = []
        index = 0
        while index < len(text):
            if text[index] == "\\":
                index += 2
                continue
            if text.startswith("$(", index) or text[index] == "`":
                start = index + (2 if text[index] == "$" else 1)
                end = _substitution_end(text, start, ")" if text[index] == "$" else "`")
                nested.extend(commands(text[start:end], depth + 1))
                index = end
            index += 1
        return nested
    tokens: list[Token] = []
    nested: list[list[str]] = []
    word = ""
    quoted = False
    quote = ""
    pending: list[tuple[str, bool, bool, int]] = []
    here_strings: list[tuple[str, int]] = []
    index = 0

    def flush() -> None:
        nonlocal word, quoted
        if word or quoted:
            if tokens and tokens[-1].operator and tokens[-1].value in {"<<", "<<-"}:
                pending.append((word, quoted, tokens[-1].value == "<<-", len(tokens) - 1))
            elif tokens and tokens[-1].operator and tokens[-1].value == "<<<":
                here_strings.append((word, len(tokens) - 1))
            tokens.append(Token(word, quoted=quoted))
            word = ""
            quoted = False

    while index < len(text):
        char = text[index]
        if char == "\\" and quote != "'" and index + 1 < len(text):
            following = text[index + 1]
            if following == "\n":
                index += 2
                continue
            if not quote or following in {'"', "\\", "$", "`"}:
                word += following
                index += 2
                continue
        if char == quote:
            quote = ""
            quoted = True
        elif not quote and char in {"'", '"'}:
            quote = char
            quoted = True
        elif quote != "'" and (text.startswith("$(", index) or char == "`"):
            start = index + (2 if char == "$" else 1)
            end = _substitution_end(text, start, ")" if char == "$" else "`")
            nested.extend(commands(text[start:end], depth + 1))
            word += "__shell_expansion__"
            index = end
        elif quote:
            word += char
        elif char == "#" and not word:
            end = text.find("\n", index)
            index = len(text) if end < 0 else end
            continue
        elif char in " \t\r":
            flush()
        elif char in ";&|()<>\n":
            flush()
            operator = char
            if index + 1 < len(text) and text[index:index + 2] in {"&&", "||", ";;", "<<", ">>", ">&", "<&", ">|", "<>"}:
                operator = text[index:index + 2]
                index += 1
                if operator == "<<" and index + 1 < len(text) and text[index + 1] in {"-", "<"}:
                    index += 1
                    operator += text[index]
            if char == "\n" and pending:
                for delimiter, literal, strip_tabs, position in pending:
                    start = index + 1
                    end = start
                    while end < len(text):
                        next_line = text.find("\n", end)
                        next_line = len(text) if next_line < 0 else next_line
                        line = text[end:next_line]
                        if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                            break
                        end = next_line + 1
                    if end >= len(text):
                        raise AnalysisLimit("unterminated here-document")
                    body = text[start:end]
                    if shell_input(tokens, position):
                        nested.extend(commands(body, depth + 1))
                    elif not literal:
                        nested.extend(commands(body, depth + 1, expansions_only=True))
                    index = next_line
                pending = []
            tokens.append(Token(operator, True))
        else:
            word += char
        index += 1
    if quote:
        raise AnalysisLimit("unterminated shell quote")
    flush()
    if pending:
        raise AnalysisLimit("unterminated here-document")
    for body, position in here_strings:
        if shell_input(tokens, position):
            nested.extend(commands(body, depth + 1))
    direct = simple_commands(tokens)
    for words in direct:
        name = basename(words[0])
        if name in SHELLS:
            for i, argument in enumerate(words[1:], 1):
                if (argument.startswith("-") and "c" in argument[1:]) or argument.lower() in {"-command", "-c"}:
                    if i + 1 < len(words):
                        nested.extend(commands(words[i + 1], depth + 1))
                    break
        elif name == "eval" and len(words) > 1:
            nested.extend(commands(" ".join(words[1:]), depth + 1))
    return direct + nested


def _substitution_end(text: str, start: int, closer: str) -> int:
    quote = ""
    level = 0
    index = start
    while index < len(text):
        char = text[index]
        if char == "\\" and quote != "'":
            index += 2
            continue
        if char == quote:
            quote = ""
        elif not quote and char in {"'", '"'}:
            quote = char
        elif not quote:
            if char == closer and level == 0:
                return index
            if char == "(":
                level += 1
            elif char == ")":
                level -= 1
        index += 1
    raise AnalysisLimit("unterminated command substitution")
