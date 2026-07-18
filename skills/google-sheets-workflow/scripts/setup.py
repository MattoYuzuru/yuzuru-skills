#!/usr/bin/env python3
"""Configure and inspect the service-account credentials used by Google Sheets Workflow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sheets_config import (
    SheetsConfigError,
    config_dir,
    config_path,
    load_client_email,
    load_known_spreadsheets,
    load_user_email,
    remove_all,
    save_service_account_key,
    save_user_email,
    service_account_key_path,
)

SETUP_URL = "https://console.cloud.google.com/iam-admin/serviceaccounts"


def print_json(value: dict[str, Any], *, stream: Any = sys.stdout) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2), file=stream)


def collect_status() -> dict[str, Any]:
    key_configured = service_account_key_path().is_file()
    user_email = load_user_email()
    result: dict[str, Any] = {
        "ready": key_configured and user_email is not None,
        "service_account_key_configured": key_configured,
        "client_email": load_client_email(),
        "user_email": user_email,
        "config_dir": str(config_dir()),
    }
    if not key_configured:
        result["setup_url"] = SETUP_URL
        result["next_action"] = (
            "Create a project, enable the Google Sheets API and Google Drive API, create a "
            "Service Account, add a JSON key, download it, then run: "
            "python3 scripts/setup.py import-service-account <path-to-downloaded-key.json>"
        )
    elif user_email is None:
        result["next_action"] = (
            "python3 scripts/setup.py set-user-email <your-google-account-email>"
        )
    else:
        result["next_action"] = (
            f"Share a spreadsheet with {result['client_email']} (Editor) via Sheets' Share "
            "button, then use scripts/sheets_api.py."
        )
    return result


def import_service_account(args: argparse.Namespace) -> int:
    source = Path(args.path).expanduser()
    if not source.is_file():
        print_json({"error": f"No such file: {source}"}, stream=sys.stderr)
        return 1
    try:
        info = save_service_account_key(source)
    except (SheetsConfigError, json.JSONDecodeError) as exc:
        print_json({"error": str(exc)}, stream=sys.stderr)
        return 1
    result = collect_status()
    result["imported_client_email"] = info["client_email"]
    print_json(result)
    return 0


def set_user_email(args: argparse.Namespace) -> int:
    try:
        save_user_email(args.email)
    except SheetsConfigError as exc:
        print_json({"error": str(exc)}, stream=sys.stderr)
        return 1
    print_json(collect_status())
    return 0


def remove(args: argparse.Namespace) -> int:
    if not args.confirm_remove:
        print_json(
            {"error": "remove requires --confirm-remove because it deletes local credentials and config."},
            stream=sys.stderr,
        )
        return 1
    remove_all()
    print_json({"removed": True, "service_account_key": str(service_account_key_path()), "config": str(config_path())})
    return 0


def known_spreadsheets(_args: argparse.Namespace) -> int:
    print_json({"known_spreadsheets": load_known_spreadsheets()})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("check", help="Report whether the skill is ready to call the Sheets API.")

    import_parser = subparsers.add_parser(
        "import-service-account", help="Copy a downloaded service-account JSON key into secure storage."
    )
    import_parser.add_argument("path", help="Path to the downloaded key file (never its contents).")

    email_parser = subparsers.add_parser(
        "set-user-email", help="Store the email spreadsheets created by this skill should be auto-shared with."
    )
    email_parser.add_argument("email")

    remove_parser = subparsers.add_parser(
        "remove", help="Delete the stored key, cached token, and config (email + known spreadsheets)."
    )
    remove_parser.add_argument("--confirm-remove", action="store_true")

    subparsers.add_parser(
        "known-spreadsheets",
        help="List spreadsheets previously seen via list/info/create, cached locally with title and URL.",
    )

    args = parser.parse_args()

    if args.command == "check":
        status = collect_status()
        print_json(status)
        return 0 if status["ready"] else 2
    if args.command == "import-service-account":
        return import_service_account(args)
    if args.command == "set-user-email":
        return set_user_email(args)
    if args.command == "known-spreadsheets":
        return known_spreadsheets(args)
    return remove(args)


if __name__ == "__main__":
    raise SystemExit(main())
