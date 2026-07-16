#!/usr/bin/env python3
"""Google Sheets / Drive REST helper for Google Sheets Workflow.

Every command signs its own access token headlessly via a service account (see
sheets_config.get_access_token) — no browser, no consent screen. Run scripts/bootstrap.py
first and use its 'python' for this script.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from sheets_config import SheetsConfigError, get_access_token, load_user_email

SHEETS_BASE = "https://sheets.googleapis.com/v4/spreadsheets"
DRIVE_BASE = "https://www.googleapis.com/drive/v3"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SPREADSHEET_MIME = "application/vnd.google-apps.spreadsheet"


class SheetsApiError(RuntimeError):
    pass


def encode_range(range_: str) -> str:
    return urllib.parse.quote(range_, safe="")


def request_json(token: str, method: str, url: str, body: dict[str, Any] | None = None) -> Any:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise
        message = exc.read().decode("utf-8", errors="replace")
        raise SheetsApiError(f"API error {exc.code}: {message}") from exc
    except urllib.error.URLError as exc:
        raise SheetsApiError(f"Connection error: {exc.reason}") from exc

    return json.loads(raw) if raw else {}


def request_json_bounded_retry(token: str, method: str, url: str, body: dict[str, Any] | None = None) -> Any:
    try:
        return request_json(token, method, url, body)
    except urllib.error.HTTPError as exc:
        if exc.code != 429:
            raise
        time.sleep(2.0)
        try:
            return request_json(token, method, url, body)
        except urllib.error.HTTPError as retry_exc:
            message = retry_exc.read().decode("utf-8", errors="replace")
            raise SheetsApiError(f"API error {retry_exc.code} (after one retry): {message}") from retry_exc


def pretty(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def dry_run_preview(method: str, url: str, body: dict[str, Any] | None) -> None:
    pretty({"dry_run": True, "method": method, "url": url, "body": body})


# --- read commands ---------------------------------------------------------------------


def cmd_list(token: str, args: argparse.Namespace) -> None:
    query = f"mimeType='{SPREADSHEET_MIME}' and trashed=false"
    params = {
        "q": query,
        "fields": "files(id,name,modifiedTime,webViewLink)",
        "pageSize": str(args.max_results),
    }
    url = f"{DRIVE_BASE}/files?{urllib.parse.urlencode(params)}"
    result = request_json_bounded_retry(token, "GET", url)
    pretty({"note": "spreadsheets shared with the service account, not the user's whole Drive", "files": result.get("files", [])})


def cmd_info(token: str, args: argparse.Namespace) -> None:
    params = {"fields": "spreadsheetId,properties.title,sheets.properties"}
    url = f"{SHEETS_BASE}/{args.spreadsheet_id}?{urllib.parse.urlencode(params)}"
    pretty(request_json_bounded_retry(token, "GET", url))


def cmd_read(token: str, args: argparse.Namespace) -> None:
    params = {"valueRenderOption": args.value_render}
    url = f"{SHEETS_BASE}/{args.spreadsheet_id}/values/{encode_range(args.range)}?{urllib.parse.urlencode(params)}"
    pretty(request_json_bounded_retry(token, "GET", url))


def cmd_read_batch(token: str, args: argparse.Namespace) -> None:
    ranges = args.ranges.split(",")
    params = urllib.parse.urlencode({"ranges": ranges, "valueRenderOption": args.value_render}, doseq=True)
    url = f"{SHEETS_BASE}/{args.spreadsheet_id}/values:batchGet?{params}"
    pretty(request_json_bounded_retry(token, "GET", url))


# --- write commands ---------------------------------------------------------------------


def cmd_create(token: str, args: argparse.Namespace) -> None:
    sheets = [{"properties": {"title": title}} for title in (args.sheet_titles.split(",") if args.sheet_titles else [])]
    body: dict[str, Any] = {"properties": {"title": args.title}}
    if sheets:
        body["sheets"] = sheets

    if args.dry_run:
        dry_run_preview("POST", SHEETS_BASE, body)
        return

    created = request_json_bounded_retry(token, "POST", SHEETS_BASE, body)
    spreadsheet_id = created["spreadsheetId"]
    result: dict[str, Any] = {"spreadsheetId": spreadsheet_id, "webViewLink": created.get("spreadsheetUrl")}

    user_email = load_user_email()
    if user_email:
        share_url = f"{DRIVE_BASE}/files/{spreadsheet_id}/permissions?sendNotificationEmail=false"
        share_body = {"type": "user", "role": "writer", "emailAddress": user_email}
        request_json_bounded_retry(token, "POST", share_url, share_body)
        result["shared_with"] = user_email
    else:
        result["warning"] = "No user email configured; the new spreadsheet is only visible to the service account."
    pretty(result)


def cmd_write(token: str, args: argparse.Namespace) -> None:
    values = json.loads(args.values)
    body = {"range": args.range, "values": values}
    params = {"valueInputOption": args.value_input}
    url = f"{SHEETS_BASE}/{args.spreadsheet_id}/values/{encode_range(args.range)}?{urllib.parse.urlencode(params)}"

    if args.dry_run:
        dry_run_preview("PUT", url, body)
        return
    pretty(request_json_bounded_retry(token, "PUT", url, body))


def cmd_append(token: str, args: argparse.Namespace) -> None:
    values = json.loads(args.values)
    body = {"range": args.range, "values": values}
    params = {"valueInputOption": args.value_input, "insertDataOption": "INSERT_ROWS"}
    url = f"{SHEETS_BASE}/{args.spreadsheet_id}/values/{encode_range(args.range)}:append?{urllib.parse.urlencode(params)}"

    if args.dry_run:
        dry_run_preview("POST", url, body)
        return
    pretty(request_json_bounded_retry(token, "POST", url, body))


def cmd_add_sheet(token: str, args: argparse.Namespace) -> None:
    body = {"requests": [{"addSheet": {"properties": {"title": args.title}}}]}
    url = f"{SHEETS_BASE}/{args.spreadsheet_id}:batchUpdate"

    if args.dry_run:
        dry_run_preview("POST", url, body)
        return
    pretty(request_json_bounded_retry(token, "POST", url, body))


def cmd_batch_update(token: str, args: argparse.Namespace) -> None:
    requests_payload = json.loads(args.requests)
    body = {"requests": requests_payload}
    url = f"{SHEETS_BASE}/{args.spreadsheet_id}:batchUpdate"

    if args.dry_run:
        dry_run_preview("POST", url, body)
        return
    pretty(request_json_bounded_retry(token, "POST", url, body))


# --- destructive commands ----------------------------------------------------------------


def cmd_clear(token: str, args: argparse.Namespace) -> None:
    url = f"{SHEETS_BASE}/{args.spreadsheet_id}/values/{encode_range(args.range)}:clear"

    if args.dry_run:
        dry_run_preview("POST", url, {})
        return
    pretty(request_json_bounded_retry(token, "POST", url, {}))


def cmd_delete_sheet(token: str, args: argparse.Namespace) -> None:
    body = {"requests": [{"deleteSheet": {"sheetId": args.sheet_id}}]}
    url = f"{SHEETS_BASE}/{args.spreadsheet_id}:batchUpdate"

    if args.dry_run:
        dry_run_preview("POST", url, body)
        return
    pretty(request_json_bounded_retry(token, "POST", url, body))


def cmd_trash(token: str, args: argparse.Namespace) -> None:
    params = {"fields": "id,trashed"}
    url = f"{DRIVE_BASE}/files/{args.spreadsheet_id}?{urllib.parse.urlencode(params)}"
    body = {"trashed": True}

    if args.dry_run:
        dry_run_preview("PATCH", url, body)
        return
    pretty(request_json_bounded_retry(token, "PATCH", url, body))


# --- CLI wiring ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Google Sheets / Drive REST helper")
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="List spreadsheets shared with the service account. [read]")
    list_parser.add_argument("--max-results", type=int, default=50)

    info_parser = sub.add_parser("info", help="Get spreadsheet title and sheet metadata. [read]")
    info_parser.add_argument("spreadsheet_id")

    read_parser = sub.add_parser("read", help="Read one A1 range. [read]")
    read_parser.add_argument("spreadsheet_id")
    read_parser.add_argument("--range", required=True)
    read_parser.add_argument("--value-render", default="FORMATTED_VALUE", choices=["FORMATTED_VALUE", "UNFORMATTED_VALUE", "FORMULA"])

    read_batch_parser = sub.add_parser("read-batch", help="Read multiple A1 ranges at once. [read]")
    read_batch_parser.add_argument("spreadsheet_id")
    read_batch_parser.add_argument("--ranges", required=True, help="Comma-separated A1 ranges")
    read_batch_parser.add_argument("--value-render", default="FORMATTED_VALUE", choices=["FORMATTED_VALUE", "UNFORMATTED_VALUE", "FORMULA"])

    create_parser = sub.add_parser("create", help="Create a spreadsheet, auto-shared with the configured user email. [write]")
    create_parser.add_argument("--title", required=True)
    create_parser.add_argument("--sheet-titles", help="Comma-separated sheet titles beyond the default first sheet")
    create_parser.add_argument("--dry-run", action="store_true")

    write_parser = sub.add_parser("write", help="Overwrite one A1 range with values/formulas. [write]")
    write_parser.add_argument("spreadsheet_id")
    write_parser.add_argument("--range", required=True)
    write_parser.add_argument("--values", required=True, help="JSON 2D array, e.g. '[[1,2],[3,\"=SUM(A1:A2)\"]]'")
    write_parser.add_argument("--value-input", default="USER_ENTERED", choices=["USER_ENTERED", "RAW"])
    write_parser.add_argument("--dry-run", action="store_true")

    append_parser = sub.add_parser("append", help="Append rows after an A1 range's table. [write]")
    append_parser.add_argument("spreadsheet_id")
    append_parser.add_argument("--range", required=True)
    append_parser.add_argument("--values", required=True, help="JSON 2D array")
    append_parser.add_argument("--value-input", default="USER_ENTERED", choices=["USER_ENTERED", "RAW"])
    append_parser.add_argument("--dry-run", action="store_true")

    add_sheet_parser = sub.add_parser("add-sheet", help="Add a new sheet tab. [write]")
    add_sheet_parser.add_argument("spreadsheet_id")
    add_sheet_parser.add_argument("--title", required=True)
    add_sheet_parser.add_argument("--dry-run", action="store_true")

    batch_update_parser = sub.add_parser(
        "batch-update",
        help="Generic escape hatch: raw batchUpdate requests array (formatting, pivot tables, freeze panes, merges...). [write]",
    )
    batch_update_parser.add_argument("spreadsheet_id")
    batch_update_parser.add_argument("--requests", required=True, help="JSON array of batchUpdate request objects")
    batch_update_parser.add_argument("--dry-run", action="store_true")

    clear_parser = sub.add_parser("clear", help="Clear all values in an A1 range. [destructive]")
    clear_parser.add_argument("spreadsheet_id")
    clear_parser.add_argument("--range", required=True)
    clear_parser.add_argument("--dry-run", action="store_true")

    delete_sheet_parser = sub.add_parser("delete-sheet", help="Delete one sheet tab by numeric sheetId. [destructive]")
    delete_sheet_parser.add_argument("spreadsheet_id")
    delete_sheet_parser.add_argument("--sheet-id", type=int, required=True)
    delete_sheet_parser.add_argument("--dry-run", action="store_true")

    trash_parser = sub.add_parser("trash", help="Move a spreadsheet to Drive trash (recoverable). [destructive]")
    trash_parser.add_argument("spreadsheet_id")
    trash_parser.add_argument("--dry-run", action="store_true")

    return parser


COMMANDS = {
    "list": cmd_list,
    "info": cmd_info,
    "read": cmd_read,
    "read-batch": cmd_read_batch,
    "create": cmd_create,
    "write": cmd_write,
    "append": cmd_append,
    "add-sheet": cmd_add_sheet,
    "batch-update": cmd_batch_update,
    "clear": cmd_clear,
    "delete-sheet": cmd_delete_sheet,
    "trash": cmd_trash,
}


def main() -> int:
    args = build_parser().parse_args()
    try:
        if getattr(args, "dry_run", False):
            COMMANDS[args.command](None, args)
        else:
            token = get_access_token(SCOPES)
            COMMANDS[args.command](token, args)
    except (SheetsConfigError, SheetsApiError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
