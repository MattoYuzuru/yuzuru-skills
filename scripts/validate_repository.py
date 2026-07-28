#!/usr/bin/env python3
"""Validate repository structure, skills, plugins, schemas, docs, and catalogs."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def run_check(command: list[str]) -> dict[str, object]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    return {
        "command": " ".join(command),
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout[-8000:],
        "stderr": result.stderr[-4000:],
    }


def json_checks() -> list[str]:
    errors: list[str] = []
    for path in sorted(ROOT.rglob("*.json")):
        if any(part in {".git", "__pycache__", "node_modules"} for part in path.parts):
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
    return errors


def documentation_link_checks() -> list[str]:
    errors: list[str] = []
    for path in sorted(ROOT.rglob("*.md")):
        if any(part in {".git", "__pycache__", "node_modules"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK_RE.findall(text):
            clean = target.split("#", 1)[0].strip("<>")
            if (
                not clean
                or clean.lower() in {"url", "path", "target"}
                or re.match(r"^[a-z]+://", clean)
                or clean.startswith("mailto:")
            ):
                continue
            resolved = (path.parent / clean).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(f"{path.relative_to(ROOT)}: link escapes repository: {target}")
                continue
            if not resolved.exists():
                errors.append(f"{path.relative_to(ROOT)}: broken link: {target}")
    return errors


def readme_catalog_checks() -> list[str]:
    errors: list[str] = []
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for plugin in sorted((ROOT / "plugins").iterdir()):
        if (plugin / ".codex-plugin/plugin.json").is_file() and f"`{plugin.name}`" not in text:
            errors.append(f"README.md missing plugin {plugin.name}")
    for skill in sorted((ROOT / "skills").iterdir()):
        if (skill / "SKILL.md").is_file() and f"`{skill.name}`" not in text:
            errors.append(f"README.md missing standalone skill {skill.name}")
    return errors


def runtime_path_checks() -> list[str]:
    errors: list[str] = []
    forbidden = {
        ".venv",
        "venv",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".gradle",
        ".tox",
        ".nox",
        ".playwright",
        ".coverage",
        "coverage.xml",
        "htmlcov",
        "playwright-report",
        "test-results",
        "target",
    }
    for path in ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        if (
            path.name in forbidden
            or path.name == "__pycache__"
            or path.suffix in {".pyc", ".pyo", ".log"}
        ):
            errors.append(f"runtime artifact in repository: {path.relative_to(ROOT)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    checks = [
        run_check(
            [
                sys.executable,
                str(ROOT / "scripts" / "validate_skills.py"),
                "--skills-dir",
                str(ROOT / "skills"),
                "--evals-dir",
                str(ROOT / "evals"),
                "all",
                *(["--strict"] if args.strict else []),
            ]
        ),
        run_check(
            [
                sys.executable,
                str(ROOT / "scripts" / "validate_plugins.py"),
                "all",
                *(["--strict"] if args.strict else []),
            ]
        ),
        run_check([sys.executable, str(ROOT / "scripts" / "sync_plugin_versions.py"), "--check"]),
        run_check([sys.executable, str(ROOT / "scripts" / "run_evals.py")]),
        run_check([sys.executable, str(ROOT / "scripts" / "smoke_scripts.py")]),
    ]
    artifact_examples = {
        "artifact": "artifact-metadata.json",
        "decision": "decision-record.json",
        "work_package": "work-package.json",
        "evidence_bundle": "evidence-bundle.json",
    }
    checks.extend(
        run_check(
            [
                sys.executable,
                str(ROOT / "scripts" / "validate_artifact.py"),
                kind,
                str(ROOT / "assets" / "artifacts" / filename),
            ]
        )
        for kind, filename in artifact_examples.items()
    )
    local = {
        "json": json_checks(),
        "documentation_links": documentation_link_checks(),
        "readme_catalog": readme_catalog_checks(),
        "runtime_paths": runtime_path_checks(),
    }
    ok = all(check["ok"] for check in checks) and not any(local.values())
    payload = {"ok": ok, "checks": checks, "local": local}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    else:
        for check in checks:
            print(f"{'ok' if check['ok'] else 'FAIL':4} {check['command']}")
            if not check["ok"]:
                print(check["stdout"], end="")
                print(check["stderr"], end="", file=sys.stderr)
        for name, errors in local.items():
            print(f"{'ok' if not errors else 'FAIL':4} {name}")
            for error in errors:
                print(f"  error: {error}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
