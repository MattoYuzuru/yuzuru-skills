#!/usr/bin/env python3
"""Validate repository skills using only the Python standard library."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
RESOURCE_RE = re.compile(r"`((?:references|scripts|assets)/[^`]+)`")
ABSOLUTE_PATH_RE = re.compile(r"(?:/Users/|/home/)[^\s`]+")
RUNTIME_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", "node_modules"}
ALLOWED_TARGETS = {"codex", "claude"}
TEMPLATE_MARKERS = {
    "Describe the capability and its scope in one short paragraph.",
    "Select the relevant route and load only its required reference.",
}


@dataclass
class Result:
    skill: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def parse_frontmatter(path: Path, result: Result) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        result.errors.append("SKILL.md must start with YAML frontmatter")
        return {}, text
    closing = text.find("\n---\n", 4)
    if closing < 0:
        result.errors.append("SKILL.md frontmatter must end with ---")
        return {}, text

    values: dict[str, str] = {}
    for number, line in enumerate(text[4:closing].splitlines(), start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1].isspace() or ":" not in line:
            result.errors.append(f"frontmatter line {number} must use one-line key: value syntax")
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values, text[closing + 5 :]


def validate_resource_links(skill_dir: Path, body: str, result: Result) -> None:
    candidates = set(RESOURCE_RE.findall(body))
    for link in LINK_RE.findall(body):
        link = link.split("#", 1)[0]
        if link and not re.match(r"^[a-z]+://", link) and not link.startswith("#"):
            candidates.add(link)

    for relative in sorted(candidates):
        if any(char in relative for char in "*{}<>"):
            continue
        if not (skill_dir / relative).exists():
            result.errors.append(f"referenced path does not exist: {relative}")


def validate_python_scripts(skill_dir: Path, result: Result) -> None:
    scripts = skill_dir / "scripts"
    if not scripts.is_dir():
        return
    for path in sorted(scripts.rglob("*.py")):
        if any(part in RUNTIME_PARTS for part in path.parts):
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError) as exc:
            result.errors.append(f"invalid Python script {path.relative_to(skill_dir)}: {exc}")


def validate_openai_metadata(skill_dir: Path, name: str, result: Result) -> None:
    path = skill_dir / "agents" / "openai.yaml"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    for key in ("display_name:", "short_description:", "default_prompt:"):
        if key not in text:
            result.errors.append(f"agents/openai.yaml is missing {key[:-1]}")
    if f"${name}" not in text:
        result.errors.append(f"agents/openai.yaml default_prompt must mention ${name}")


def parse_target_list(value: str, source: str, result: Result) -> list[str]:
    if not value.startswith("[") or not value.endswith("]"):
        result.errors.append(f"{source} must use an inline list such as [codex, claude]")
        return []
    targets = [item.strip() for item in value[1:-1].split(",") if item.strip()]
    if not targets:
        result.errors.append(f"{source} must not be empty")
        return []
    unknown = sorted(set(targets) - ALLOWED_TARGETS)
    if unknown:
        result.errors.append(f"{source} has unknown targets: {', '.join(unknown)}")
    if len(targets) != len(set(targets)):
        result.errors.append(f"{source} must not contain duplicate targets")
    return targets


def validate_target_metadata(skill_dir: Path, frontmatter: dict[str, str], result: Result) -> None:
    sidecar = skill_dir / "skill.yaml"
    legacy = frontmatter.get("agents")
    if sidecar.exists() and legacy:
        result.errors.append("use skill.yaml targets or legacy agents frontmatter, not both")
        return
    if legacy:
        parse_target_list(legacy, "legacy agents frontmatter", result)
        return
    if not sidecar.exists():
        return
    try:
        lines = sidecar.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        result.errors.append(f"skill.yaml must be UTF-8: {exc}")
        return
    entries = [line for line in lines if line.strip() and not line.lstrip().startswith("#")]
    if len(entries) != 1 or not entries[0].startswith("targets:"):
        result.errors.append("skill.yaml must contain only targets: [codex, claude]")
        return
    parse_target_list(entries[0].split(":", 1)[1].strip(), "skill.yaml targets", result)


def validate_skill(skill_dir: Path) -> Result:
    result = Result(skill=skill_dir.name)
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        result.errors.append("missing SKILL.md")
        return result

    frontmatter, body = parse_frontmatter(skill_file, result)
    name = frontmatter.get("name", "")
    description = frontmatter.get("description", "")
    validate_target_metadata(skill_dir, frontmatter, result)

    if not name:
        result.errors.append("frontmatter is missing name")
    elif not NAME_RE.fullmatch(name) or len(name) > 64:
        result.errors.append("name must be kebab-case and <=64 characters")
    elif name != skill_dir.name:
        result.errors.append(f"name '{name}' must match directory '{skill_dir.name}'")

    if not description:
        result.errors.append("frontmatter is missing description")
    else:
        if len(description) < 40:
            result.errors.append("description must be at least 40 characters")
        if "use when" not in description.lower():
            result.errors.append("description must include concrete 'Use when ...' trigger conditions")

    body_lines = body.splitlines()
    if not body.strip():
        result.errors.append("SKILL.md body is empty")
    for marker in sorted(TEMPLATE_MARKERS):
        if marker in body:
            result.errors.append(f"replace scaffold placeholder: {marker}")
    if len(body_lines) > 500:
        result.errors.append(f"SKILL.md has {len(body_lines)} body lines; hard limit is 500")
    elif len(body_lines) > 200:
        result.warnings.append(f"SKILL.md has {len(body_lines)} body lines; target is <=200")

    if ABSOLUTE_PATH_RE.search(body):
        result.errors.append("SKILL.md contains a maintainer-specific absolute path")

    references = skill_dir / "references"
    if references.is_dir():
        for path in sorted(references.rglob("*")):
            if path.is_file() and path.parent != references and not any(
                part in RUNTIME_PARTS for part in path.parts
            ):
                result.errors.append(
                    f"nested reference is not allowed: {path.relative_to(skill_dir)}"
                )
            if path.is_file() and path.suffix.lower() == ".md":
                lines = path.read_text(encoding="utf-8").splitlines()
                has_contents = any(
                    line.strip().lower() in {"## contents", "## table of contents"}
                    for line in lines[:30]
                )
                if len(lines) > 100 and not has_contents:
                    result.warnings.append(
                        f"{path.relative_to(skill_dir)} has {len(lines)} lines without a contents section"
                    )

    validate_resource_links(skill_dir, body, result)
    validate_python_scripts(skill_dir, result)
    validate_openai_metadata(skill_dir, name, result)
    return result


def discover_skills(skills_dir: Path, names: list[str]) -> list[Path]:
    if not names or names == ["all"]:
        return sorted(
            path for path in skills_dir.iterdir() if path.is_dir() and (path / "SKILL.md").is_file()
        )
    paths = []
    for name in names:
        path = skills_dir / name
        if not path.is_dir():
            raise ValueError(f"unknown skill: {name}")
        paths.append(path)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Yuzuru skills")
    parser.add_argument("names", nargs="*", help="skill names or 'all' (default: all)")
    parser.add_argument("--json", action="store_true", help="emit machine-readable results")
    parser.add_argument("--skills-dir", type=Path, required=True, help=argparse.SUPPRESS)
    args = parser.parse_args()

    try:
        paths = discover_skills(args.skills_dir, args.names)
    except ValueError as exc:
        parser.error(str(exc))
    results = [validate_skill(path) for path in paths]

    if args.json:
        print(
            json.dumps(
                [
                    {"skill": item.skill, "ok": item.ok, "errors": item.errors, "warnings": item.warnings}
                    for item in results
                ],
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    else:
        for item in results:
            marker = "ok" if item.ok else "FAIL"
            print(f"{marker:4} {item.skill}")
            for warning in item.warnings:
                print(f"  warning: {warning}")
            for error in item.errors:
                print(f"  error: {error}")
        print(
            f"validated {len(results)} skill(s): "
            f"{sum(item.ok for item in results)} passed, {sum(not item.ok for item in results)} failed"
        )
    return 0 if all(item.ok for item in results) else 1


if __name__ == "__main__":
    sys.exit(main())
