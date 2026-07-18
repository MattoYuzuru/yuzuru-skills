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
from pathlib import Path
from typing import Any

from sheets_config import SheetsConfigError, get_access_token, load_user_email, remember_spreadsheet

SHEETS_BASE = "https://sheets.googleapis.com/v4/spreadsheets"
DRIVE_BASE = "https://www.googleapis.com/drive/v3"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SPREADSHEET_MIME = "application/vnd.google-apps.spreadsheet"
WRITE_COMMANDS = {"create", "write", "append", "add-sheet", "batch-update"}
DESTRUCTIVE_COMMANDS = {"clear", "delete-sheet", "trash"}
DESTRUCTIVE_BATCH_KEYS = {
    "deleteBanding",
    "deleteConditionalFormatRule",
    "deleteDeveloperMetadata",
    "deleteDimension",
    "deleteDimensionGroup",
    "deleteEmbeddedObject",
    "deleteFilterView",
    "deleteNamedRange",
    "deleteProtectedRange",
    "deleteRange",
    "deleteSheet",
}


class SheetsApiError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


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
        message = exc.read().decode("utf-8", errors="replace")
        raise SheetsApiError(f"API error {exc.code}: {message}", status=exc.code) from exc
    except urllib.error.URLError as exc:
        raise SheetsApiError(f"Connection error: {exc.reason}") from exc

    return json.loads(raw) if raw else {}


def request_json_bounded_retry(token: str, method: str, url: str, body: dict[str, Any] | None = None) -> Any:
    if method != "GET":
        return request_json(token, method, url, body)
    try:
        return request_json(token, method, url, body)
    except SheetsApiError as exc:
        if exc.status != 429:
            raise
        time.sleep(2.0)
        try:
            return request_json(token, method, url, body)
        except SheetsApiError as retry_exc:
            raise SheetsApiError(
                f"{retry_exc} (after one retry)", status=retry_exc.status
            ) from retry_exc


def pretty(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def dry_run_preview(method: str, url: str, body: dict[str, Any] | None) -> None:
    pretty({"dry_run": True, "method": method, "url": url, "body": body})


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def parse_json_array(value: str, *, label: str) -> list[Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise SheetsApiError(f"{label} must be a JSON array.")
    return parsed


def load_requests(args: argparse.Namespace) -> list[dict[str, Any]]:
    try:
        payload = json.loads(args.requests_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SheetsApiError(f"batchUpdate requests file not found: {args.requests_file}") from exc
    if not isinstance(payload, list) or not payload:
        raise SheetsApiError("batchUpdate requests file must contain a non-empty JSON array.")
    if len(payload) > 100:
        raise SheetsApiError("batchUpdate is limited to 100 requests per command.")
    normalized: list[dict[str, Any]] = []
    for index, request in enumerate(payload):
        if not isinstance(request, dict) or len(request) != 1:
            raise SheetsApiError(f"batchUpdate request {index} must be an object with exactly one operation.")
        operation = next(iter(request))
        if operation in DESTRUCTIVE_BATCH_KEYS:
            raise SheetsApiError(
                f"Destructive batchUpdate operation '{operation}' is not allowed through batch-update; "
                "use a dedicated destructive command."
            )
        normalized.append(request)
    return normalized


def bound_values(result: Any, max_cells: int) -> Any:
    remaining = max_cells
    truncated = False

    def bound_range(value_range: Any) -> Any:
        nonlocal remaining, truncated
        if not isinstance(value_range, dict):
            return value_range
        output = dict(value_range)
        rows = value_range.get("values")
        if not isinstance(rows, list):
            return output
        kept = []
        for row in rows:
            width = len(row) if isinstance(row, list) else 1
            if width > remaining:
                truncated = True
                break
            kept.append(row)
            remaining -= width
        if len(kept) < len(rows):
            truncated = True
        output["values"] = kept
        return output

    if isinstance(result, dict) and isinstance(result.get("valueRanges"), list):
        output = dict(result)
        bounded_ranges = []
        for value_range in result["valueRanges"]:
            if remaining <= 0:
                truncated = True
                break
            bounded_ranges.append(bound_range(value_range))
        output["valueRanges"] = bounded_ranges
    else:
        output = bound_range(result)
    if isinstance(output, dict):
        output["truncated"] = truncated
        output["maxCells"] = max_cells
    return output


def require_confirmation(args: argparse.Namespace) -> None:
    if args.command in WRITE_COMMANDS and not args.dry_run and not args.confirm_write:
        raise SheetsApiError("Write requires --confirm-write after the user approves the exact dry-run preview.")
    if args.command in DESTRUCTIVE_COMMANDS and not args.dry_run and not args.confirm_destructive:
        raise SheetsApiError(
            "Destructive operation requires --confirm-destructive after exact target confirmation."
        )


# --- read commands ---------------------------------------------------------------------


def cmd_list(token: str, args: argparse.Namespace) -> None:
    if args.max_results > 1000:
        raise SheetsApiError("--max-results cannot exceed the Drive API page size limit of 1000.")
    query = f"mimeType='{SPREADSHEET_MIME}' and trashed=false"
    params = {
        "q": query,
        "fields": "files(id,name,modifiedTime,webViewLink)",
        "pageSize": str(args.max_results),
    }
    url = f"{DRIVE_BASE}/files?{urllib.parse.urlencode(params)}"
    result = request_json_bounded_retry(token, "GET", url)
    files = result.get("files", [])
    for file in files:
        remember_spreadsheet(file["id"], title=file.get("name"), url=file.get("webViewLink"))
    pretty({"note": "spreadsheets shared with the service account, not the user's whole Drive", "files": files})


def cmd_info(token: str, args: argparse.Namespace) -> None:
    params = {"fields": "spreadsheetId,properties.title,spreadsheetUrl,sheets.properties"}
    url = f"{SHEETS_BASE}/{args.spreadsheet_id}?{urllib.parse.urlencode(params)}"
    result = request_json_bounded_retry(token, "GET", url)
    remember_spreadsheet(
        args.spreadsheet_id,
        title=result.get("properties", {}).get("title"),
        url=result.get("spreadsheetUrl"),
    )
    pretty(result)


def cmd_read(token: str, args: argparse.Namespace) -> None:
    params = {"valueRenderOption": args.value_render}
    url = f"{SHEETS_BASE}/{args.spreadsheet_id}/values/{encode_range(args.range)}?{urllib.parse.urlencode(params)}"
    pretty(bound_values(request_json_bounded_retry(token, "GET", url), args.max_cells))


def cmd_read_batch(token: str, args: argparse.Namespace) -> None:
    ranges = [value.strip() for value in args.ranges.split(",") if value.strip()]
    if not ranges or len(ranges) > 20:
        raise SheetsApiError("read-batch requires between 1 and 20 ranges.")
    params = urllib.parse.urlencode({"ranges": ranges, "valueRenderOption": args.value_render}, doseq=True)
    url = f"{SHEETS_BASE}/{args.spreadsheet_id}/values:batchGet?{params}"
    pretty(bound_values(request_json_bounded_retry(token, "GET", url), args.max_cells))


# --- write commands ---------------------------------------------------------------------


def cmd_create(token: str, args: argparse.Namespace) -> None:
    sheets = [{"properties": {"title": title}} for title in (args.sheet_titles.split(",") if args.sheet_titles else [])]
    body: dict[str, Any] = {"properties": {"title": args.title}}
    if sheets:
        body["sheets"] = sheets

    if args.dry_run:
        dry_run_preview("POST", SHEETS_BASE, body)
        return

    created = request_json(token, "POST", SHEETS_BASE, body)
    spreadsheet_id = created["spreadsheetId"]
    result: dict[str, Any] = {"spreadsheetId": spreadsheet_id, "webViewLink": created.get("spreadsheetUrl")}
    remember_spreadsheet(spreadsheet_id, title=args.title, url=created.get("spreadsheetUrl"))

    user_email = load_user_email()
    if user_email:
        share_url = f"{DRIVE_BASE}/files/{spreadsheet_id}/permissions?sendNotificationEmail=false"
        share_body = {"type": "user", "role": "writer", "emailAddress": user_email}
        try:
            request_json(token, "POST", share_url, share_body)
            result["shared_with"] = user_email
            result["status"] = "created-and-shared"
        except SheetsApiError as exc:
            result["status"] = "created-not-shared"
            result["warning"] = str(exc)
            result["next"] = "Share the returned spreadsheetId manually; do not retry create."
    else:
        result["status"] = "created-only"
        result["warning"] = "No user email configured; the new spreadsheet is only visible to the service account."
    pretty(result)


def cmd_write(token: str, args: argparse.Namespace) -> None:
    values = parse_json_array(args.values, label="--values")
    body = {"range": args.range, "values": values}
    params = {"valueInputOption": args.value_input}
    url = f"{SHEETS_BASE}/{args.spreadsheet_id}/values/{encode_range(args.range)}?{urllib.parse.urlencode(params)}"

    if args.dry_run:
        dry_run_preview("PUT", url, body)
        return
    pretty(request_json_bounded_retry(token, "PUT", url, body))


def cmd_append(token: str, args: argparse.Namespace) -> None:
    values = parse_json_array(args.values, label="--values")
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
    requests_payload = load_requests(args)
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
    list_parser.add_argument("--max-results", type=positive_int, default=50)

    info_parser = sub.add_parser("info", help="Get spreadsheet title and sheet metadata. [read]")
    info_parser.add_argument("spreadsheet_id")

    read_parser = sub.add_parser("read", help="Read one A1 range. [read]")
    read_parser.add_argument("spreadsheet_id")
    read_parser.add_argument("--range", required=True)
    read_parser.add_argument("--max-cells", type=positive_int, default=10000)
    read_parser.add_argument("--value-render", default="FORMATTED_VALUE", choices=["FORMATTED_VALUE", "UNFORMATTED_VALUE", "FORMULA"])

    read_batch_parser = sub.add_parser("read-batch", help="Read multiple A1 ranges at once. [read]")
    read_batch_parser.add_argument("spreadsheet_id")
    read_batch_parser.add_argument("--ranges", required=True, help="Comma-separated A1 ranges")
    read_batch_parser.add_argument("--max-cells", type=positive_int, default=10000)
    read_batch_parser.add_argument("--value-render", default="FORMATTED_VALUE", choices=["FORMATTED_VALUE", "UNFORMATTED_VALUE", "FORMULA"])

    create_parser = sub.add_parser("create", help="Create a spreadsheet, auto-shared with the configured user email. [write]")
    create_parser.add_argument("--title", required=True)
    create_parser.add_argument("--sheet-titles", help="Comma-separated sheet titles beyond the default first sheet")
    create_parser.add_argument("--dry-run", action="store_true")
    create_parser.add_argument("--confirm-write", action="store_true")

    write_parser = sub.add_parser("write", help="Overwrite one A1 range with values/formulas. [write]")
    write_parser.add_argument("spreadsheet_id")
    write_parser.add_argument("--range", required=True)
    write_parser.add_argument("--values", required=True, help="JSON 2D array, e.g. '[[1,2],[3,\"=SUM(A1:A2)\"]]'")
    write_parser.add_argument("--value-input", default="USER_ENTERED", choices=["USER_ENTERED", "RAW"])
    write_parser.add_argument("--dry-run", action="store_true")
    write_parser.add_argument("--confirm-write", action="store_true")

    append_parser = sub.add_parser("append", help="Append rows after an A1 range's table. [write]")
    append_parser.add_argument("spreadsheet_id")
    append_parser.add_argument("--range", required=True)
    append_parser.add_argument("--values", required=True, help="JSON 2D array")
    append_parser.add_argument("--value-input", default="USER_ENTERED", choices=["USER_ENTERED", "RAW"])
    append_parser.add_argument("--dry-run", action="store_true")
    append_parser.add_argument("--confirm-write", action="store_true")

    add_sheet_parser = sub.add_parser("add-sheet", help="Add a new sheet tab. [write]")
    add_sheet_parser.add_argument("spreadsheet_id")
    add_sheet_parser.add_argument("--title", required=True)
    add_sheet_parser.add_argument("--dry-run", action="store_true")
    add_sheet_parser.add_argument("--confirm-write", action="store_true")

    batch_update_parser = sub.add_parser(
        "batch-update",
        help="Apply a validated non-destructive batchUpdate requests file. [write]",
    )
    batch_update_parser.add_argument("spreadsheet_id")
    batch_update_parser.add_argument("--requests-file", required=True, type=Path, help="Path to a JSON requests array")
    batch_update_parser.add_argument("--dry-run", action="store_true")
    batch_update_parser.add_argument("--confirm-write", action="store_true")

    clear_parser = sub.add_parser("clear", help="Clear all values in an A1 range. [destructive]")
    clear_parser.add_argument("spreadsheet_id")
    clear_parser.add_argument("--range", required=True)
    clear_parser.add_argument("--dry-run", action="store_true")
    clear_parser.add_argument("--confirm-destructive", action="store_true")

    delete_sheet_parser = sub.add_parser("delete-sheet", help="Delete one sheet tab by numeric sheetId. [destructive]")
    delete_sheet_parser.add_argument("spreadsheet_id")
    delete_sheet_parser.add_argument("--sheet-id", type=int, required=True)
    delete_sheet_parser.add_argument("--dry-run", action="store_true")
    delete_sheet_parser.add_argument("--confirm-destructive", action="store_true")

    trash_parser = sub.add_parser("trash", help="Move a spreadsheet to Drive trash (recoverable). [destructive]")
    trash_parser.add_argument("spreadsheet_id")
    trash_parser.add_argument("--dry-run", action="store_true")
    trash_parser.add_argument("--confirm-destructive", action="store_true")

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
        require_confirmation(args)
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
