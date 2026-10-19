#!/usr/bin/env python3
"""Check keyless readiness or configure the optional OpenAlex key with hidden input."""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True

import argparse
import getpass
import os
import warnings
from _runtime import EvidenceError, HttpClient, SETUP_URL, emit, key_path, load_key, save_key, validate_key, _check_file


def check() -> dict:
    issue = None
    try:
        key, source = load_key()
    except EvidenceError as exc:
        key, source, issue = None, None, exc.kind
    return {"ready": True, "mode": "keyless-core", "keyless_sources": ["epmc", "arxiv", "crossref"],
            "openalex": {"key_configured": key is not None, "key_source": source,
                         "authentication_verified": False, "optional": True,
                         "configuration_issue": issue,
                         "benefit": "Higher budget and cursor pagination; basic queries work without a key.",
                         "setup_url": SETUP_URL},
            "next_action": None if key else "Optional: run this setup.py configure openalex in your terminal."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="Local readiness only; never contacts a provider or prints a key.")
    config = sub.add_parser("configure", help="Validate and privately store an optional API key (local write).")
    config.add_argument("provider", choices=["openalex"])
    config.add_argument("--dry-run", action="store_true")
    remove = sub.add_parser("remove-key", help="Remove only this skill's stored key (destructive local operation).")
    remove.add_argument("provider", choices=["openalex"])
    remove.add_argument("--dry-run", action="store_true")
    remove.add_argument("--confirm-remove", action="store_true")
    args = parser.parse_args()
    if args.command == "check":
        emit(check())
        return 0
    path = key_path()
    if args.dry_run:
        emit({"effect": "destructive" if args.command == "remove-key" else "local-write",
              "dry_run": True, "target": str(path), "setup_url": SETUP_URL})
        return 0
    if args.command == "remove-key":
        if not args.confirm_remove:
            raise EvidenceError("remove_requires_confirm_remove")
        if path.exists() or path.is_symlink():
            _check_file(path)
            path.unlink()
        emit({"removed": True, "target": str(path), "environment_key_unchanged": "OPENALEX_API_KEY" in os.environ})
        return 0
    if path.exists() or path.is_symlink():
        raise EvidenceError("key_already_exists_remove_exact_stored_key_first")
    if not sys.stdin.isatty():
        raise EvidenceError("hidden_terminal_input_required")
    print("Optional OpenAlex key: " + SETUP_URL, file=sys.stderr)
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            key = validate_key(getpass.getpass("OpenAlex API key (hidden): "))
        except (getpass.GetPassWarning, EOFError):
            raise EvidenceError("hidden_terminal_input_unavailable") from None
    client = HttpClient(openalex_key=key)
    client.get("openalex", "/rate-limit")
    saved = save_key(key)
    emit({"configured": True, "provider": "openalex", "authentication_verified": True,
          "config_path": str(saved)})
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EvidenceError as exc:
        emit(exc.result(), stream=sys.stderr)
        raise SystemExit(1)
    except (OSError, UnicodeError):
        emit({"error": "local_configuration_unavailable"}, stream=sys.stderr)
        raise SystemExit(1)
