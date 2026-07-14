#!/usr/bin/env python3
"""Read-only Central University LMS helper."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


DEFAULT_URL = "https://my.centraluniversity.ru/learn/courses/view/actual/all"
DEFAULT_STATE = Path("~/.config/yuzuru-codex-skills/central-university-lms/storage-state.json").expanduser()
API_BASE = "https://my.centraluniversity.ru"
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


def print_json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


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
        raise RuntimeError(f"Storage state not found: {storage}. Run login first.")
    browser = p.chromium.launch(headless=args.headless)
    context = browser.new_context(storage_state=str(storage))
    return browser, context


def api_request(context: Any, path: str, params: dict[str, object] | None = None) -> Any:
    """GET a micro-lms/hub JSON endpoint using the authenticated context.

    Requires NODE_EXTRA_CA_CERTS to point at a PEM bundle containing the
    corporate TLS-inspection root CA, or context.request.get raises
    "self-signed certificate in certificate chain". See references/discovery.md.
    """
    url = path if path.startswith("http") else f"{API_BASE}{path}"
    response = context.request.get(url, params=params or {})
    if response.status >= 400:
        raise RuntimeError(f"GET {url} -> {response.status}: {response.text()[:500]}")
    return response.json()


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
    sync_playwright = ensure_playwright()
    observed: list[dict[str, object]] = []

    with sync_playwright() as p:
        browser, context = context_with_state(p, args)
        page = context.new_page()

        def on_request(request: Any) -> None:
            if request.resource_type in {"xhr", "fetch"}:
                observed.append({"method": request.method, "url": request.url, "type": request.resource_type})

        page.on("request", on_request)
        page.goto(args.url, wait_until="domcontentloaded", timeout=args.timeout)
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
    print_json({"url": args.url, "requests": deduped})
    return 0


def api_get(args: argparse.Namespace) -> int:
    sync_playwright = ensure_playwright()
    url = args.endpoint
    if url.startswith("/"):
        url = f"https://my.centraluniversity.ru{url}"

    with sync_playwright() as p:
        browser, context = context_with_state(p, args)
        response = context.request.get(url, timeout=args.timeout)
        status = response.status
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            body: object = response.json()
        else:
            body = response.text()
        browser.close()

    print_json({"status": status, "url": url, "body": body})
    return 0


def click_text_discover(args: argparse.Namespace) -> int:
    sync_playwright = ensure_playwright()
    observed: list[dict[str, object]] = []

    with sync_playwright() as p:
        browser, context = context_with_state(p, args)
        page = context.new_page()

        def on_request(request: Any) -> None:
            if request.resource_type in {"xhr", "fetch"}:
                observed.append({"method": request.method, "url": request.url, "type": request.resource_type})

        page.on("request", on_request)
        page.goto(args.url, wait_until="networkidle", timeout=args.timeout)
        click_result = page.evaluate(
            """text => {
                const clean = s => (s || '').replace(/\\s+/g, ' ').trim();
                const candidates = [...document.querySelectorAll('a, button, [role="button"], [tabindex], div, span')]
                    .filter(el => clean(el.innerText || el.textContent).includes(text));
                if (!candidates.length) {
                    return { clicked: false, reason: 'text not found' };
                }
                let el = candidates.sort((a, b) => clean(a.innerText || a.textContent).length - clean(b.innerText || b.textContent).length)[0];
                let target = el;
                for (let i = 0; i < 6 && target; i += 1) {
                    const role = target.getAttribute('role');
                    const tabIndex = target.getAttribute('tabindex');
                    if (target.tagName === 'A' || target.tagName === 'BUTTON' || role === 'button' || tabIndex !== null || target.onclick) {
                        break;
                    }
                    target = target.parentElement;
                }
                (target || el).click();
                return {
                    clicked: true,
                    tag: (target || el).tagName,
                    text: clean((target || el).innerText || (target || el).textContent).slice(0, 300),
                    href: (target || el).href || ''
                };
            }""",
            args.text,
        )
        page.wait_for_timeout(args.seconds * 1000)
        data = extract_snapshot(page)
        browser.close()

    deduped = []
    seen = set()
    for item in observed:
        key = (item["method"], item["url"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    print_json({"click": click_result, "final_url": data.get("url"), "requests": deduped, "snapshot": data})
    return 0


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--storage-state")
    parser.add_argument("--timeout", type=int, default=30000)
    parser.add_argument("--headless", action="store_true")


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Central University LMS helper")
    sub = parser.add_subparsers(dest="command", required=True)

    login_parser = sub.add_parser("login")
    add_common(login_parser)

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
    deadlines_parser.add_argument("--limit", type=int, default=50)
    deadlines_parser.add_argument("--include-past", action="store_true")

    deadlines_dom_parser = sub.add_parser("deadlines-dom")
    add_common(deadlines_dom_parser)
    deadlines_dom_parser.add_argument("--limit", type=int, default=50)

    discover_parser = sub.add_parser("discover-api")
    add_common(discover_parser)
    discover_parser.add_argument("--seconds", type=int, default=20)

    api_parser = sub.add_parser("api-get")
    add_common(api_parser)
    api_parser.add_argument("endpoint")

    click_parser = sub.add_parser("click-text-discover")
    add_common(click_parser)
    click_parser.add_argument("text")
    click_parser.add_argument("--seconds", type=int, default=10)

    args = parser.parse_args()
    try:
        if args.command == "login":
            return login(args)
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
        if args.command == "deadlines-dom":
            return deadlines_dom(args)
        if args.command == "discover-api":
            return discover_api(args)
        if args.command == "api-get":
            return api_get(args)
        if args.command == "click-text-discover":
            return click_text_discover(args)
    except Exception as exc:
        print_json({"error": str(exc)})
        return 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
