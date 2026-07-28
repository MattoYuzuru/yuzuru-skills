#!/usr/bin/env python3
"""Synchronize dual plugin manifests from each canonical plugin-version.json."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?$")


def atomic_json(path: Path, value: object) -> None:
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report drift without modifying files")
    parser.add_argument("plugins", nargs="*", help="plugin IDs (default: all)")
    args = parser.parse_args()

    selected = set(args.plugins)
    failures: list[dict[str, str]] = []
    changed: list[str] = []
    for plugin in sorted((ROOT / "plugins").iterdir()):
        if not (plugin / ".codex-plugin" / "plugin.json").is_file():
            continue
        if selected and plugin.name not in selected:
            continue
        try:
            version_doc = json.loads((plugin / "plugin-version.json").read_text(encoding="utf-8"))
            version = version_doc["version"]
        except (OSError, KeyError, json.JSONDecodeError) as exc:
            failures.append({"plugin": plugin.name, "error": f"invalid canonical version: {exc}"})
            continue
        if not isinstance(version, str) or not SEMVER_RE.fullmatch(version):
            failures.append({"plugin": plugin.name, "error": f"invalid semantic version: {version!r}"})
            continue
        for relative in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
            path = plugin / relative
            try:
                manifest = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                failures.append({"plugin": plugin.name, "error": f"{relative}: {exc}"})
                continue
            if manifest.get("version") == version:
                continue
            if args.check:
                failures.append(
                    {
                        "plugin": plugin.name,
                        "error": f"{relative} version {manifest.get('version')!r} != {version}",
                    }
                )
            else:
                manifest["version"] = version
                atomic_json(path, manifest)
                changed.append(str(path.relative_to(ROOT)))
    print(
        json.dumps(
            {"ok": not failures, "check": args.check, "changed": changed, "failures": failures},
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
