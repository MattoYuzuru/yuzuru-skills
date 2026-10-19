#!/usr/bin/env python3
"""Search, resolve and read bounded scientific evidence through public source APIs."""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True

import argparse
from datetime import datetime, timezone
import json
import re
import xml.etree.ElementTree as ET
from _runtime import EvidenceError, HttpClient, emit
import _sources
from _content import extract_arxiv_html, extract_jats


def read(identifier: str, section: str | None, max_chars: int, client: HttpClient) -> dict:
    if re.fullmatch(r"PMC[1-9][0-9]{0,11}", identifier, re.IGNORECASE):
        identifier = "pmcid:" + identifier
    kind, raw_id = _sources.parse_identifier(identifier)
    if kind == "pmcid":
        identity = raw_id.upper()
        data = client.get("epmc", "/" + identity + "/fullTextXML")
        result = extract_jats(data, section, max_chars)
        result.update({"id": "pmcid:" + identity, "url": "https://europepmc.org/articles/" + identity,
                       "notice_check": {"status": "not-checked", "scope": "Use resolve for linked publication notices."}})
        return result
    if kind == "arxiv" and re.fullmatch(r"[0-9]{4}\.[0-9]{4,5}(?:v[1-9][0-9]*)?", raw_id):
        record = None
        if not re.search(r"v[1-9][0-9]*$", raw_id):
            record = _sources.resolve("arxiv:" + raw_id, client)
            pinned = record.get("identifiers", {}).get("arxiv", "")
            # Adapters may expose an explicit version separately from the base identifier.
            if not re.search(r"v[1-9][0-9]*$", pinned) and record.get("version"):
                pinned = raw_id + "v" + str(record["version"]).removeprefix("v")
            if not re.fullmatch(re.escape(raw_id) + r"v[1-9][0-9]*", pinned):
                raise EvidenceError("arxiv_version_not_resolved")
            raw_id = pinned
        data = client.get("arxiv-html", "/html/" + raw_id)
        result = extract_arxiv_html(data, section, max_chars)
        result.update({"id": "arxiv:" + raw_id, "url": "https://arxiv.org/html/" + raw_id,
                       "notice_check": {"status": "not-checked", "scope": "Article extraction is not publication-status certification."}})
        if record:
            result["resolved_from"] = record["id"]
        return result
    raise EvidenceError("read_requires_pmcid_or_modern_arxiv_id_resolve_other_identifiers_first")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=20, help="Per-request seconds (1..60).")
    sub = parser.add_subparsers(dest="command", required=True)
    search = sub.add_parser("search", help="Return bounded metadata candidates; not full-text verification.")
    search.add_argument("--source", required=True, choices=["epmc", "arxiv", "crossref", "openalex"])
    search.add_argument("--query", required=True, help="Text or provider-native query, up to 500 characters.")
    search.add_argument("--limit", type=int, choices=range(1, 11), default=3, metavar="1..10")
    resolve = sub.add_parser("resolve", help="Resolve DOI, pmid:, pmcid:, arxiv: or openalex: identity and notices.")
    resolve.add_argument("identifier")
    content = sub.add_parser("read", help="Read a bounded section/table from OA JATS or arXiv HTML.")
    content.add_argument("identifier", help="pmcid:PMC... or arxiv:ID[vN]; latest arXiv IDs are pinned first.")
    content.add_argument("--section", help="Section/table ID or title substring; a missing match fails visibly.")
    content.add_argument("--max-chars", type=int, default=6000, help="Total excerpt text budget, 500..12000.")
    args = parser.parse_args()
    if not 1 <= args.timeout <= 60:
        parser.error("--timeout must be 1..60")
    if args.command == "search" and not 1 <= len(args.query.strip()) <= 500:
        parser.error("--query must contain 1..500 characters")
    if args.command in {"resolve", "read"} and not 1 <= len(args.identifier) <= 220:
        parser.error("identifier must contain 1..220 characters")
    if args.command == "read":
        if not 500 <= args.max_chars <= 12000:
            parser.error("--max-chars must be 500..12000")
        if args.section is not None and not 1 <= len(args.section.strip()) <= 200:
            parser.error("--section must contain 1..200 characters")
    client = HttpClient(timeout=args.timeout)
    if args.command == "search":
        payload = {"records": _sources.search(args.source, args.query, args.limit, client)}
    elif args.command == "resolve":
        payload = {"record": _sources.resolve(args.identifier, client)}
    else:
        payload = {"content": read(args.identifier, args.section, args.max_chars, client)}
    emit({"version": 1, "operation": args.command, "retrieved_at": datetime.now(timezone.utc).isoformat(),
          **payload, "requests": client.requests,
          "limitation": "Retrieval identifies evidence; it does not establish that the evidence proves a claim."})
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EvidenceError as exc:
        emit(exc.result(), stream=sys.stderr)
        raise SystemExit(1)
    except ValueError as exc:
        kind = str(exc)
        emit({"error": kind if re.fullmatch(r"[a-z][a-z0-9_-]{0,99}", kind) else "invalid_upstream_record"}, stream=sys.stderr)
        raise SystemExit(1)
    except (KeyError, TypeError, ET.ParseError, UnicodeError):
        emit({"error": "invalid_identifier_section_or_upstream_record"}, stream=sys.stderr)
        raise SystemExit(1)
    except OSError:
        emit({"error": "local_state_unavailable"}, stream=sys.stderr)
        raise SystemExit(1)
