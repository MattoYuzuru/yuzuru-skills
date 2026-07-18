#!/usr/bin/env python3
"""Central University LMS read/export helper and safe write-discovery tool."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from lms_core import (
    API_BASE,
    LmsError,
    is_unfinished,
    redacted_shape,
    resolve_lms_url,
    sanitized_request_url,
    validate_submission_manifest,
    write_private_json,
)


DEFAULT_URL = "https://my.centraluniversity.ru/learn/courses/view/actual/all"
DEFAULT_STATE = Path("~/.config/yuzuru-codex-skills/central-university-lms/storage-state.json").expanduser()
DEADLINE_RE = re.compile(
    r"(?i)(дедлайн|deadline|домаш|homework|assignment|задани|сдать|до\s+\d{1,2}[./]\d{1,2}|"
    r"\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?)"
)


def ensure_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is not installed. Run: python3 -m pip install playwright && python3 -m playwright install chromium"
        ) from exc
    return sync_playwright


def state_path(value: str | None) -> Path:
    return Path(value).expanduser() if value else DEFAULT_STATE


def print_json(data: object, *, stream: Any = sys.stdout) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2), file=stream)


def login(args: argparse.Namespace) -> int:
    sync_playwright = ensure_playwright()
    storage = state_path(args.storage_state)
    storage.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(args.url, wait_until="domcontentloaded", timeout=args.timeout)
        print("Log in to Central University LMS in the opened browser window.")
        print("After the courses page is visible, return here and press Enter.")
        input()
        context.storage_state(path=str(storage))
        browser.close()

    os.chmod(storage, 0o600)
    print_json({"status": "saved", "storage_state": str(storage)})
    return 0


def context_with_state(p: Any, args: argparse.Namespace):
    storage = state_path(args.storage_state)
    if not storage.exists():
        raise LmsError("reauth_required", f"Storage state not found: {storage}. Run login first.")
    browser = p.chromium.launch(headless=args.headless)
    context = browser.new_context(storage_state=str(storage))
    return browser, context


def api_request(
    context: Any,
    path: str,
    params: dict[str, object] | None = None,
    *,
    timeout: int = 30000,
) -> Any:
    """GET a micro-lms/hub JSON endpoint using the authenticated context.

    Requires NODE_EXTRA_CA_CERTS to point at a PEM bundle containing the
    corporate TLS-inspection root CA, or context.request.get raises
    "self-signed certificate in certificate chain". See references/discovery.md.
    """
    url = resolve_lms_url(path, require_api=True)
    response = context.request.get(url, params=params or {}, timeout=timeout)
    response_url = response.url
    if response_url and not response_url.startswith(f"{API_BASE}/api/"):
        raise LmsError("reauth_required", "LMS session expired or redirected. Run login again.")
    if response.status >= 400:
        code = "reauth_required" if response.status in {401, 403} else "api_error"
        raise LmsError(code, f"GET {url} -> {response.status}: {response.text()[:500]}")
    try:
        return response.json()
    except Exception as exc:
        raise LmsError("invalid_response", f"GET {url} did not return JSON.") from exc


def course_longread_url(course_id: object, theme_id: object, longread_id: object) -> str:
    return f"{API_BASE}/learn/courses/view/actual/{course_id}/themes/{theme_id}/longreads/{longread_id}"


class DescriptionParser(HTMLParser):
    """Extract readable text and links from an LMS rich-text description."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.links: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

    def text(self) -> str:
        return " ".join(" ".join(self.parts).split())


def description_fields(view_content: object) -> dict[str, object]:
    """Return text and links from the JSON-encoded rich-text exercise description."""
    try:
        payload = json.loads(view_content) if isinstance(view_content, str) else view_content
    except json.JSONDecodeError:
        payload = {}
    html = payload.get("description", "") if isinstance(payload, dict) else ""
    parser = DescriptionParser()
    if isinstance(html, str):
        parser.feed(html)
    links = list(dict.fromkeys(parser.links))
    return {"text": parser.text(), "links": links}


def compact_attachments(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    attachments = []
    for item in value:
        if not isinstance(item, dict):
            continue
        attachments.append(
            {
                key: item[key]
                for key in ("id", "name", "url", "downloadUrl", "size")
                if key in item and item[key] is not None
            }
        )
    return attachments


def event_summary(event: object) -> dict[str, object]:
    if not isinstance(event, dict):
        return {"type": "unknown"}
    content = event.get("content") if isinstance(event.get("content"), dict) else {}
    summary = {
        key: content[key]
        for key in ("state", "score", "deadline", "maxScore", "startDate", "solutionUrl")
        if key in content and content[key] is not None
    }
    return {
        "at": event.get("occurredOn"),
        "type": event.get("type"),
        "actor": event.get("actorName") or None,
        "details": summary,
    }


def comment_summary(comment: object) -> dict[str, object]:
    if not isinstance(comment, dict):
        return {"message": str(comment)}
    return {
        "id": comment.get("id"),
        "at": comment.get("createdAt") or comment.get("createdOn") or comment.get("date"),
        "author": comment.get("authorName") or comment.get("actorName") or comment.get("author"),
        "message": comment.get("content") or comment.get("message") or comment.get("text"),
        "attachments": compact_attachments(comment.get("attachments")),
    }


def longread_task(context: Any, longread_id: str, exercise_id: str | None) -> dict[str, object]:
    materials = api_request(context, f"/api/micro-lms/longreads/{longread_id}/materials", {"limit": 100, "offset": 0})
    items = materials.get("items", [])
    candidates = [item for item in items if isinstance(item, dict) and item.get("taskId")]
    if exercise_id:
        candidates = [item for item in candidates if str(item.get("id")) == exercise_id]
    if len(candidates) != 1:
        available = [
            {"exerciseId": item.get("id"), "name": item.get("name"), "taskId": item.get("taskId")}
            for item in candidates
        ]
        hint = "Provide --exercise-id." if candidates else "No assigned task was found in this longread."
        raise RuntimeError(f"Expected exactly one task. {hint} Available: {available}")
    return candidates[0]


def extract_snapshot(page: Any) -> dict[str, object]:
    return page.evaluate(
        """() => {
            const clean = s => (s || '').replace(/\\s+/g, ' ').trim();
            const links = [...document.querySelectorAll('a[href]')]
                .map(a => ({ text: clean(a.innerText), href: a.href }))
                .filter(x => x.text.length > 0)
                .slice(0, 300);
            const blocks = [...document.querySelectorAll('article, li, tr, section, div')]
                .map((el, index) => ({ index, text: clean(el.innerText), href: el.querySelector('a[href]')?.href || '' }))
                .filter(x => x.text.length >= 8 && x.text.length <= 1500)
                .slice(0, 500);
            return {
                title: document.title,
                url: location.href,
                links,
                blocks
            };
        }"""
    )


def snapshot(args: argparse.Namespace) -> int:
    sync_playwright = ensure_playwright()
    with sync_playwright() as p:
        browser, context = context_with_state(p, args)
        page = context.new_page()
        page.goto(args.url, wait_until="networkidle", timeout=args.timeout)
        data = extract_snapshot(page)
        browser.close()
    print_json(data)
    return 0


def deadlines_dom(args: argparse.Namespace) -> int:
    sync_playwright = ensure_playwright()
    with sync_playwright() as p:
        browser, context = context_with_state(p, args)
        page = context.new_page()
        page.goto(args.url, wait_until="networkidle", timeout=args.timeout)
        data = extract_snapshot(page)
        browser.close()

    matches = []
    seen = set()
    for block in data.get("blocks", []):
        text = block.get("text", "")
        if not DEADLINE_RE.search(text):
            continue
        key = text[:240]
        if key in seen:
            continue
        seen.add(key)
        matches.append(
            {
                "text": text,
                "url": block.get("href") or data.get("url"),
                "inferred": True,
            }
        )
        if len(matches) >= args.limit:
            break

    print_json({"url": data.get("url"), "matches": matches})
    return 0


def list_courses(args: argparse.Namespace) -> int:
    """List the student's courses via /api/micro-lms/courses/student.

    Without --limit, auto-paginates until paging.totalCount items are collected.
    """
    sync_playwright = ensure_playwright()
    page_size = args.limit or 50
    items: list[dict[str, object]] = []
    offset = args.offset
    total_count: int | None = None

    with sync_playwright() as p:
        browser, context = context_with_state(p, args)
        while True:
            params: dict[str, object] = {"limit": page_size, "offset": offset}
            if args.state:
                params["state"] = args.state
            body = api_request(context, "/api/micro-lms/courses/student", params)
            page_items = body.get("items", [])
            items.extend(page_items)
            paging = body.get("paging", {})
            total_count = paging.get("totalCount", len(items))
            offset += page_size
            if args.limit or not page_items or len(items) >= total_count:
                break
        browser.close()

    print_json({"totalCount": total_count, "count": len(items), "items": items})
    return 0


def course_overview(args: argparse.Namespace) -> int:
    """Fetch /api/micro-lms/courses/{id}/overview: themes -> longreads -> exercises."""
    sync_playwright = ensure_playwright()
    with sync_playwright() as p:
        browser, context = context_with_state(p, args)
        body = api_request(context, f"/api/micro-lms/courses/{args.course_id}/overview")
        browser.close()
    print_json(body)
    return 0


def course_progress(args: argparse.Namespace) -> int:
    """Fetch /api/micro-lms/courses/{id}/student/progress: earned/left/max score."""
    sync_playwright = ensure_playwright()
    with sync_playwright() as p:
        browser, context = context_with_state(p, args)
        body = api_request(context, f"/api/micro-lms/courses/{args.course_id}/student/progress")
        browser.close()
    print_json(body)
    return 0


def task_details(args: argparse.Namespace) -> int:
    """Fetch assignment description, solution, events, comments, and information via the LMS task API."""
    sync_playwright = ensure_playwright()
    with sync_playwright() as p:
        browser, context = context_with_state(p, args)
        try:
            material = longread_task(context, args.longread_id, args.exercise_id)
            task_id = material["taskId"]
            task = api_request(context, f"/api/micro-lms/tasks/{task_id}")
            events = api_request(context, f"/api/micro-lms/tasks/{task_id}/events")
            comments = api_request(context, f"/api/micro-lms/tasks/{task_id}/comments")
        finally:
            browser.close()

    if not isinstance(task, dict):
        raise RuntimeError(f"Unexpected task response for task {task_id}")
    exercise = task.get("exercise") if isinstance(task.get("exercise"), dict) else {}
    course = task.get("course") if isinstance(task.get("course"), dict) else {}
    theme = task.get("theme") if isinstance(task.get("theme"), dict) else {}
    longread = task.get("longread") if isinstance(task.get("longread"), dict) else {}
    solution = task.get("solution") if isinstance(task.get("solution"), dict) else {}
    description = description_fields(exercise.get("viewContent"))
    exercise_url = exercise.get("exerciseUrl")
    if exercise_url and exercise_url not in description["links"]:
        description["links"].append(exercise_url)

    information = {
        "deadline": task.get("deadline") or exercise.get("deadline"),
        "status": task.get("state"),
        "activity": (exercise.get("activity") or {}).get("name"),
        "score": task.get("score"),
        "maxScore": exercise.get("maxScore"),
        "extraScore": task.get("extraScore"),
        "course": {"id": course.get("id"), "name": course.get("name")},
        "theme": {"id": theme.get("id"), "name": theme.get("name")},
    }
    output = {
        "url": course_longread_url(course.get("id"), theme.get("id"), longread.get("id")),
        "task": {
            "id": task.get("id"),
            "exerciseId": exercise.get("id"),
            "name": exercise.get("name") or longread.get("name"),
            "type": task.get("type"),
            "state": task.get("state"),
            "createdAt": task.get("createdAt"),
            "startedAt": task.get("startedAt"),
            "submittedAt": task.get("submitAt"),
            "evaluatedAt": task.get("evaluateAt"),
        },
        "description": description,
        "solution": {
            "type": solution.get("type"),
            "url": solution.get("solutionUrl"),
            "attachments": compact_attachments(solution.get("attachments")),
        },
        "information": information,
        "events": [event_summary(event) for event in events] if isinstance(events, list) else [],
        "comments": [comment_summary(comment) for comment in comments] if isinstance(comments, list) else [],
    }
    print_json(output)
    return 0


def session_check(args: argparse.Namespace) -> int:
    """Verify that saved auth works without returning private course data."""
    sync_playwright = ensure_playwright()
    with sync_playwright() as p:
        browser, context = context_with_state(p, args)
        try:
            body = api_request(
                context,
                "/api/micro-lms/courses/student",
                {"limit": 1, "offset": 0, "state": "published"},
                timeout=args.timeout,
            )
        finally:
            browser.close()
    print_json(
        {
            "status": "ready",
            "headless": args.headless,
            "publishedCourseCount": (body.get("paging") or {}).get("totalCount"),
        }
    )
    return 0


def pending_manifest_item(
    course: dict[str, Any],
    theme: dict[str, Any],
    longread: dict[str, Any],
    material: dict[str, Any],
    task: dict[str, Any],
) -> dict[str, Any]:
    exercise = task.get("exercise") if isinstance(task.get("exercise"), dict) else {}
    solution = task.get("solution") if isinstance(task.get("solution"), dict) else {}
    description = description_fields(exercise.get("viewContent"))
    exercise_url = exercise.get("exerciseUrl")
    if exercise_url and exercise_url not in description["links"]:
        description["links"].append(exercise_url)
    return {
        "taskId": str(task.get("id") or material.get("taskId")),
        "exerciseId": str(exercise.get("id") or material.get("id") or ""),
        "longreadId": str(longread.get("id") or ""),
        "course": {"id": course.get("id"), "name": course.get("name")},
        "theme": {"id": theme.get("id"), "name": theme.get("name")},
        "title": exercise.get("name") or material.get("name") or longread.get("name"),
        "taskUrl": course_longread_url(course.get("id"), theme.get("id"), longread.get("id")),
        "condition": description,
        "deadline": task.get("deadline") or exercise.get("deadline"),
        "currentState": task.get("state"),
        "solution": {
            "type": solution.get("type"),
            "url": solution.get("solutionUrl"),
        },
        "snapshot": {
            "state": task.get("state"),
            "submittedAt": task.get("submitAt"),
            "evaluatedAt": task.get("evaluateAt"),
        },
    }


def export_pending(args: argparse.Namespace) -> int:
    """Export a bounded, resumable input manifest for unfinished homework."""
    sync_playwright = ensure_playwright()
    items: list[dict[str, Any]] = []
    scanned_tasks = 0
    truncated = False
    with sync_playwright() as p:
        browser, context = context_with_state(p, args)
        try:
            courses_body = api_request(
                context,
                "/api/micro-lms/courses/student",
                {"limit": args.course_limit, "offset": 0, "state": "published"},
                timeout=args.timeout,
            )
            courses = courses_body.get("items", [])[: args.course_limit]
            if (courses_body.get("paging") or {}).get("totalCount", len(courses)) > len(courses):
                truncated = True
            for course in courses:
                overview = api_request(
                    context,
                    f"/api/micro-lms/courses/{course['id']}/overview",
                    timeout=args.timeout,
                )
                for theme in overview.get("themes", []):
                    for longread in theme.get("longreads", []):
                        if not longread.get("exercises"):
                            continue
                        materials = api_request(
                            context,
                            f"/api/micro-lms/longreads/{longread['id']}/materials",
                            {"limit": 100, "offset": 0},
                            timeout=args.timeout,
                        )
                        for material in materials.get("items", []):
                            if not isinstance(material, dict) or not material.get("taskId"):
                                continue
                            scanned_tasks += 1
                            task = api_request(
                                context,
                                f"/api/micro-lms/tasks/{material['taskId']}",
                                timeout=args.timeout,
                            )
                            if not isinstance(task, dict) or not is_unfinished(task):
                                continue
                            items.append(pending_manifest_item(course, theme, longread, material, task))
                            if len(items) >= args.limit:
                                truncated = True
                                break
                        if len(items) >= args.limit:
                            break
                    if len(items) >= args.limit:
                        break
                if len(items) >= args.limit:
                    break
        finally:
            browser.close()

    items.sort(key=lambda item: (item.get("deadline") or "9999", item.get("title") or ""))
    payload = {
        "schemaVersion": 1,
        "kind": "central-university-pending-homework",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": API_BASE,
        "scannedTasks": scanned_tasks,
        "count": len(items),
        "truncated": truncated,
        "items": items,
    }
    if args.output:
        output = Path(args.output)
        write_private_json(output, payload)
        print_json({"status": "saved", "output": str(output.expanduser().resolve()), "count": len(items), "truncated": truncated})
    else:
        print_json(payload)
    return 0


def validate_submissions(args: argparse.Namespace) -> int:
    path = Path(args.manifest).expanduser()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LmsError("invalid_manifest", f"Submission manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LmsError("invalid_manifest", f"Submission manifest is not valid JSON: {exc}") from exc
    submissions = validate_submission_manifest(payload)
    print_json(
        {
            "status": "valid",
            "effect": "local-validation-only",
            "count": len(submissions),
            "submissions": submissions,
            "next": "Observe and document the real LMS write endpoint before enabling submit-manifest.",
        }
    )
    return 0


def api_health(args: argparse.Namespace) -> int:
    """Verify the supported API route chain for one longread without scraping the UI."""
    sync_playwright = ensure_playwright()
    checks = []
    with sync_playwright() as p:
        browser, context = context_with_state(p, args)
        try:
            overview = api_request(context, f"/api/micro-lms/courses/{args.course_id}/overview")
            checks.append({"endpoint": "course-overview", "ok": isinstance(overview, dict)})
            material = longread_task(context, args.longread_id, args.exercise_id)
            checks.append({"endpoint": "longread-materials", "ok": True})
            task_id = material["taskId"]
            task = api_request(context, f"/api/micro-lms/tasks/{task_id}")
            checks.append({"endpoint": "task", "ok": isinstance(task, dict)})
            events = api_request(context, f"/api/micro-lms/tasks/{task_id}/events")
            checks.append({"endpoint": "task-events", "ok": isinstance(events, list)})
            comments = api_request(context, f"/api/micro-lms/tasks/{task_id}/comments")
            checks.append({"endpoint": "task-comments", "ok": isinstance(comments, list)})
        finally:
            browser.close()

    print_json(
        {
            "status": "ok" if all(check["ok"] for check in checks) else "unexpected-response",
            "courseId": args.course_id,
            "longreadId": args.longread_id,
            "taskId": task_id,
            "checks": checks,
        }
    )
    return 0


def deadlines_api(args: argparse.Namespace) -> int:
    """Walk published courses' overview and flatten exercises that carry a deadline.

    This is the preferred deadline extractor: it reads the LMS's own deadline
    field per exercise instead of regexing rendered DOM text.
    """
    sync_playwright = ensure_playwright()
    matches: list[dict[str, object]] = []

    with sync_playwright() as p:
        browser, context = context_with_state(p, args)
        courses_body = api_request(
            context, "/api/micro-lms/courses/student", {"limit": 100, "offset": 0, "state": "published"}
        )
        for course in courses_body.get("items", []):
            course_id = course["id"]
            overview = api_request(context, f"/api/micro-lms/courses/{course_id}/overview")
            for theme in overview.get("themes", []):
                for longread in theme.get("longreads", []):
                    for exercise in longread.get("exercises", []):
                        deadline = exercise.get("deadline")
                        if not deadline:
                            continue
                        matches.append(
                            {
                                "courseId": course_id,
                                "courseName": course.get("name"),
                                "theme": theme.get("name"),
                                "longread": longread.get("name"),
                                "exercise": exercise.get("name"),
                                "maxScore": exercise.get("maxScore"),
                                "activity": (exercise.get("activity") or {}).get("name"),
                                "deadline": deadline,
                            }
                        )
        browser.close()

    if not args.include_past:
        now = datetime.now(timezone.utc).isoformat()
        matches = [m for m in matches if m["deadline"] >= now]

    matches.sort(key=lambda m: m["deadline"])
    print_json({"count": len(matches), "matches": matches[: args.limit]})
    return 0


def discover_api(args: argparse.Namespace) -> int:
    """Observe bounded LMS API traffic without recording query values or bodies."""
    sync_playwright = ensure_playwright()
    observed: list[dict[str, object]] = []

    with sync_playwright() as p:
        browser, context = context_with_state(p, args)
        page = context.new_page()

        def on_request(request: Any) -> None:
            if request.resource_type in {"xhr", "fetch"}:
                url = sanitized_request_url(request.url)
                if url:
                    observed.append({"method": request.method, "url": url, "type": request.resource_type})

        page.on("request", on_request)
        page.goto(resolve_lms_url(args.url), wait_until="domcontentloaded", timeout=args.timeout)
        page.wait_for_timeout(args.seconds * 1000)
        browser.close()

    deduped = []
    seen = set()
    for item in observed:
        key = (item["method"], item["url"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= args.limit:
            break
    print_json({"url": resolve_lms_url(args.url), "requests": deduped, "truncated": len(observed) > len(deduped)})
    return 0


def request_body_shape(request: Any) -> Any:
    try:
        return redacted_shape(request.post_data_json) if request.post_data else None
    except Exception:
        return "<non-json-body>" if request.post_data else None


def observe_action(args: argparse.Namespace) -> int:
    """Observe a user-performed LMS write without clicking or replaying it."""
    if not args.confirm_write_observation:
        raise LmsError(
            "confirmation_required",
            "observe-action requires --confirm-write-observation because the user's manual UI action may mutate LMS state.",
        )
    sync_playwright = ensure_playwright()
    observed: list[dict[str, Any]] = []
    by_request: dict[int, dict[str, Any]] = {}

    with sync_playwright() as p:
        browser, context = context_with_state(p, args)
        page = context.new_page()

        def on_request(request: Any) -> None:
            if request.resource_type not in {"xhr", "fetch"} or request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
                return
            url = sanitized_request_url(request.url)
            if not url:
                return
            item = {
                "method": request.method,
                "url": url,
                "type": request.resource_type,
                "headerNames": sorted(
                    key.casefold()
                    for key in request.headers
                    if key.casefold() not in {"authorization", "cookie", "x-csrf-token", "x-xsrf-token"}
                ),
                "bodyShape": request_body_shape(request),
                "status": None,
            }
            observed.append(item)
            by_request[id(request)] = item

        def on_response(response: Any) -> None:
            item = by_request.get(id(response.request))
            if item is not None:
                item["status"] = response.status

        page.on("request", on_request)
        page.on("response", on_response)
        page.goto(resolve_lms_url(args.url), wait_until="networkidle", timeout=args.timeout)
        page.wait_for_timeout(args.seconds * 1000)
        browser.close()

    payload = {
        "schemaVersion": 1,
        "kind": "central-university-write-observation",
        "effect": "user-performed-write-observation",
        "requests": observed[: args.limit],
        "truncated": len(observed) > args.limit,
        "note": "Values and sensitive headers are redacted. This command never clicks or replays requests.",
    }
    if args.output:
        write_private_json(Path(args.output), payload)
        print_json(
            {
                "status": "saved",
                "output": str(Path(args.output).expanduser().resolve()),
                "count": len(payload["requests"]),
            }
        )
    else:
        print_json(payload)
    return 0


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def add_common(parser: argparse.ArgumentParser, *, default_headless: bool = True) -> None:
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--storage-state")
    parser.add_argument("--timeout", type=positive_int, default=30000)
    browser_mode = parser.add_mutually_exclusive_group()
    browser_mode.add_argument("--headless", dest="headless", action="store_true")
    browser_mode.add_argument("--headed", dest="headless", action="store_false")
    parser.set_defaults(headless=default_headless)


def main() -> int:
    parser = argparse.ArgumentParser(description="Central University LMS automation helper")
    sub = parser.add_subparsers(dest="command", required=True)

    login_parser = sub.add_parser("login")
    add_common(login_parser, default_headless=False)

    session_parser = sub.add_parser("session-check")
    add_common(session_parser)

    snapshot_parser = sub.add_parser("snapshot")
    add_common(snapshot_parser)

    list_courses_parser = sub.add_parser("list-courses")
    add_common(list_courses_parser)
    list_courses_parser.add_argument("--state", default="published")
    list_courses_parser.add_argument("--limit", type=int)
    list_courses_parser.add_argument("--offset", type=int, default=0)

    course_overview_parser = sub.add_parser("course-overview")
    add_common(course_overview_parser)
    course_overview_parser.add_argument("course_id")

    course_progress_parser = sub.add_parser("course-progress")
    add_common(course_progress_parser)
    course_progress_parser.add_argument("course_id")

    task_details_parser = sub.add_parser("task-details")
    add_common(task_details_parser)
    task_details_parser.add_argument("longread_id")
    task_details_parser.add_argument("--exercise-id")

    health_parser = sub.add_parser("api-health")
    add_common(health_parser)
    health_parser.add_argument("course_id")
    health_parser.add_argument("longread_id")
    health_parser.add_argument("--exercise-id")

    deadlines_parser = sub.add_parser("deadlines")
    add_common(deadlines_parser)
    deadlines_parser.add_argument("--limit", type=positive_int, default=50)
    deadlines_parser.add_argument("--include-past", action="store_true")

    export_parser = sub.add_parser("export-pending")
    add_common(export_parser)
    export_parser.add_argument("--limit", type=positive_int, default=100)
    export_parser.add_argument("--course-limit", type=positive_int, default=50)
    export_parser.add_argument("--output", help="Write a private JSON manifest instead of stdout.")

    validate_parser = sub.add_parser("validate-submissions")
    validate_parser.add_argument("manifest")

    deadlines_dom_parser = sub.add_parser("deadlines-dom")
    add_common(deadlines_dom_parser)
    deadlines_dom_parser.add_argument("--limit", type=positive_int, default=50)

    discover_parser = sub.add_parser("discover-api")
    add_common(discover_parser, default_headless=False)
    discover_parser.add_argument("--seconds", type=positive_int, default=20)
    discover_parser.add_argument("--limit", type=positive_int, default=100)

    observe_parser = sub.add_parser("observe-action")
    add_common(observe_parser, default_headless=False)
    observe_parser.add_argument("--seconds", type=positive_int, default=60)
    observe_parser.add_argument("--limit", type=positive_int, default=20)
    observe_parser.add_argument("--output")
    observe_parser.add_argument("--confirm-write-observation", action="store_true")

    args = parser.parse_args()
    try:
        if args.command == "login":
            return login(args)
        if args.command == "session-check":
            return session_check(args)
        if args.command == "snapshot":
            return snapshot(args)
        if args.command == "list-courses":
            return list_courses(args)
        if args.command == "course-overview":
            return course_overview(args)
        if args.command == "course-progress":
            return course_progress(args)
        if args.command == "task-details":
            return task_details(args)
        if args.command == "api-health":
            return api_health(args)
        if args.command == "deadlines":
            return deadlines_api(args)
        if args.command == "export-pending":
            return export_pending(args)
        if args.command == "validate-submissions":
            return validate_submissions(args)
        if args.command == "deadlines-dom":
            return deadlines_dom(args)
        if args.command == "discover-api":
            return discover_api(args)
        if args.command == "observe-action":
            return observe_action(args)
    except LmsError as exc:
        print_json({"error": str(exc), "code": exc.code}, stream=sys.stderr)
        return 1
    except Exception as exc:
        print_json({"error": str(exc), "code": "unexpected_error"}, stream=sys.stderr)
        return 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
