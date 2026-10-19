"""Bounded metadata adapters. Network policy and credentials belong to the client.

Metadata, including an abstract, never constitutes a read of the article's full text.
Notice checks inspect the named record fields, not the complete scholarly record.
"""

import html
from html.parser import HTMLParser
import json
import re
from urllib.parse import quote, urlsplit
import xml.etree.ElementTree as ET


MAX_RESULTS = 10
MAX_QUERY = 500
MAX_ABSTRACT = 1800
MAX_NOTICES = 6
_DOI = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)
_ARXIV = re.compile(r"(?:\d{4}\.\d{4,5}|[a-z][a-z-]*(?:\.[A-Z]{2})?/\d{7})(?:v[1-9]\d{0,3})?")
_ATOM = "{http://www.w3.org/2005/Atom}"
_AX = "{http://arxiv.org/schemas/atom}"


class _PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag.lower() in ("p", "br", "div", "title", "jats:p", "jats:title"):
            self.parts.append(" ")

    def handle_endtag(self, tag):
        self.parts.append(" ")


def _text(value, cap=600):
    if not isinstance(value, str):
        return ""
    parser = _PlainText()
    parser.feed(value)
    return " ".join(html.unescape("".join(parser.parts)).split())[:cap]


def _abstract(value):
    text = _text(value, 2_000_000)
    return {"text": text[:MAX_ABSTRACT], "truncated": len(text) > MAX_ABSTRACT}


def _mapping(value):
    return value if isinstance(value, dict) else {}


def _items(value):
    return value if isinstance(value, list) else []


def _json(data):
    try:
        result = json.loads(data)
    except (ValueError, TypeError, UnicodeError):
        raise ValueError("invalid-source-response") from None
    if not isinstance(result, dict):
        raise ValueError("invalid-source-response")
    return result


def parse_identifier(identifier):
    """Accept explicit identifier formats, never arbitrary input URLs."""
    if not isinstance(identifier, str) or len(identifier) > 256:
        raise ValueError("invalid-identifier")
    identifier = identifier.strip()
    if identifier.lower().startswith("doi:"):
        identifier = identifier[4:]
    if _DOI.fullmatch(identifier):
        return "doi", identifier.lower()
    for prefix, pattern in (("pmid", r"[1-9]\d{0,11}"),
                            ("pmcid", r"PMC[1-9]\d{0,11}"),
                            ("openalex", r"W[1-9]\d{0,15}")):
        if identifier.lower().startswith(prefix + ":"):
            value = identifier[len(prefix) + 1:]
            if re.fullmatch(pattern, value, re.I):
                return prefix, value.upper() if prefix != "pmid" else value
            raise ValueError("invalid-identifier")
    value = identifier[6:] if identifier.lower().startswith("arxiv:") else identifier
    if _ARXIV.fullmatch(value):
        month = value.split("/")[-1][2:4] if "/" in value else value[2:4]
        if 1 <= int(month) <= 12:
            return "arxiv", value
    raise ValueError("invalid-identifier")


def _doi(value):
    if not isinstance(value, str) or len(value) > 300:
        return None
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.I)
    return value.lower() if len(value) <= 256 and _DOI.fullmatch(value) else None


def _url(value):
    if not isinstance(value, str) or len(value) > 1500 or any(ord(c) < 32 for c in value):
        return None
    try:
        parts = urlsplit(value)
    except ValueError:
        return None
    return value if parts.scheme in ("https", "http") and parts.hostname and not parts.username and not parts.password else None


def _notice_priority(notice):
    kind = notice["type"].lower()
    for priority, word in enumerate(("retract", "withdraw", "concern", "correct", "errat")):
        if word in kind:
            return priority
    return 10


def _finish(source, identifier, title, identifiers, url, published=None, updated=None,
            publication_types=None, publication_status="unknown", abstract=None,
            notices=None, scope="record metadata", checked=True, license=None, version=None):
    title = _text(title)
    if not title:
        raise ValueError("invalid-source-record")
    notices = notices or []
    notices.sort(key=_notice_priority)
    result = {
        "source": source, "id": identifier, "title": title,
        "identifiers": {k: v for k, v in identifiers.items() if v}, "url": url,
        "published": _text(published, 40) or None, "updated": _text(updated, 40) or None,
        "publication_types": [_text(t, 100) for t in (publication_types or [])[:12] if _text(t, 100)],
        "publication_status": publication_status, "abstract": _abstract(abstract),
        "notices": notices[:MAX_NOTICES], "notice_count": len(notices),
        "notices_truncated": len(notices) > MAX_NOTICES,
        "notice_check": {"scope": scope, "status": "notice-found" if notices else ("none-in-record" if checked else "not-checked")},
        "license": _text(license, 300) or None,
    }
    result["access_level"] = "abstract" if result["abstract"]["text"] else "metadata"
    if version is not None:
        result["version"] = version
    return result


def _epmc_record(record):
    record = _mapping(record)
    source, identifier = record.get("source"), record.get("id")
    if not isinstance(source, str) or not re.fullmatch(r"[A-Z]{2,12}", source) or not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", identifier):
        raise ValueError("invalid-source-record")
    ids = {"doi": _doi(record.get("doi"))}
    if source == "MED" and re.fullmatch(r"[1-9]\d{0,11}", identifier):
        ids["pmid"] = identifier
    pmcid = record.get("pmcid") or (identifier if source == "PMC" else None)
    if isinstance(pmcid, str) and re.fullmatch(r"PMC[1-9]\d{0,11}", pmcid):
        ids["pmcid"] = pmcid
    types = _items(_mapping(record.get("pubTypeList")).get("pubType"))
    notices = []
    for kind in types:
        if isinstance(kind, str) and re.search(r"retract|withdraw|concern|correct|errat", kind, re.I):
            notices.append({"type": _text(kind, 120), "direction": "publication-type"})
    comments = _mapping(record.get("commentCorrectionList")).get("commentCorrection")
    for item in _items(comments):
        item = _mapping(item)
        kind = _text(item.get("type"), 120)
        if not re.search(r"retract|withdraw|concern|correct|errat", kind, re.I):
            continue
        notice = {"type": kind or "unspecified", "direction": "record-relation", "reference": _text(item.get("reference"), 300)}
        notice_id, notice_source = item.get("id"), item.get("source")
        if isinstance(notice_id, str) and re.fullmatch(r"[A-Za-z0-9._-]{1,80}", notice_id) and isinstance(notice_source, str) and re.fullmatch(r"[A-Z]{2,12}", notice_source):
            notice["id"] = f"{notice_source}:{notice_id}"
            notice["url"] = f"https://europepmc.org/article/{notice_source}/{notice_id}"
        notices.append(notice)
    is_preprint = source == "PPR" or any("preprint" in str(t).lower() for t in types)
    status = "preprint" if is_preprint else ("journal-reference-present" if "Journal Article" in types else "unknown")
    return _finish("epmc", f"{source}:{identifier}", record.get("title"), ids,
                   f"https://europepmc.org/article/{source}/{identifier}",
                   record.get("firstPublicationDate") or record.get("pubYear"), record.get("dateOfRevision"),
                   types, status, record.get("abstractText"), notices,
                   "Europe PMC core publication types and screened retraction/withdrawal/concern/correction/erratum commentCorrectionList types; not an exhaustive retraction search",
                   license=record.get("license"))


def _date(value):
    value = _mapping(value)
    if isinstance(value.get("date-time"), str):
        return value["date-time"]
    parts = _items(value.get("date-parts"))
    if parts and isinstance(parts[0], list) and 1 <= len(parts[0]) <= 3 and all(isinstance(n, int) and 0 < n <= 9999 for n in parts[0]):
        return "-".join(str(n).zfill(4 if i == 0 else 2) for i, n in enumerate(parts[0]))
    return None


def _crossref_record(record):
    record = _mapping(record)
    doi = _doi(record.get("DOI"))
    titles = _items(record.get("title"))
    if not doi or not titles:
        raise ValueError("invalid-source-record")
    notices = []
    for field, direction in (("updated-by", "notice-about-this-work"), ("update-to", "this-work-updates-target")):
        for item in _items(record.get(field)):
            item = _mapping(item)
            notice = {"type": _text(item.get("type") or item.get("label"), 120) or "unspecified", "direction": direction}
            target = _doi(item.get("DOI"))
            if target:
                notice.update({"doi": target, "url": "https://doi.org/" + target})
            notices.append(notice)
    kind = _text(record.get("type"), 100)
    status = "preprint" if record.get("subtype") == "preprint" or kind == "preprint" else ("journal-reference-present" if kind == "journal-article" else "unknown")
    licenses = _items(record.get("license"))
    license_url = _url(_mapping(licenses[0]).get("URL")) if licenses else None
    published = next((_date(record.get(k)) for k in ("published", "published-print", "published-online", "issued") if _date(record.get(k))), None)
    return _finish("crossref", "doi:" + doi, titles[0], {"doi": doi}, "https://doi.org/" + doi,
                   published, _date(record.get("deposited")), [kind] if kind else [], status,
                   record.get("abstract"), notices,
                   "Crossref deposited updated-by/update-to fields, including supplied Retraction Watch data; not exhaustive",
                   license=license_url)


def _arxiv_records(data):
    if not isinstance(data, bytes) or b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("invalid-source-response")
    try:
        root = ET.fromstring(data)
    except (ET.ParseError, ValueError):
        raise ValueError("invalid-source-response") from None
    if root.tag != _ATOM + "feed":
        raise ValueError("invalid-source-response")
    records = []
    for entry in root.findall(_ATOM + "entry")[:MAX_RESULTS]:
        raw_id = entry.findtext(_ATOM + "id", "")
        match = re.fullmatch(r"https?://arxiv\.org/abs/(.+)", raw_id)
        if not match:
            raise ValueError("invalid-source-record")
        try:
            _, identifier = parse_identifier("arxiv:" + match.group(1))
        except ValueError:
            raise ValueError("invalid-source-record") from None
        version_match = re.search(r"v([1-9]\d*)$", identifier)
        journal = entry.findtext(_AX + "journal_ref", "")
        comment = entry.findtext(_AX + "comment", "")
        title = entry.findtext(_ATOM + "title", "")
        abstract = entry.findtext(_ATOM + "summary", "")
        notices = []
        for field, value in (("title", title), ("comment", comment), ("summary", abstract)):
            if re.search(r"\b(withdrawn|retracted|retraction|expression of concern)\b", value, re.I):
                notices.append({"type": "withdrawal/retraction language (candidate, verify)", "field": field, "reference": _text(value, 300)})
        records.append(_finish("arxiv", "arxiv:" + identifier, title,
                               {"arxiv": identifier, "doi": _doi(entry.findtext(_AX + "doi"))},
                               "https://arxiv.org/abs/" + identifier,
                               entry.findtext(_ATOM + "published"), entry.findtext(_ATOM + "updated"),
                               ["preprint"], "journal-reference-present" if journal.strip() else "preprint",
                               abstract, notices, "arXiv title/comment/summary language only; no external notice registry",
                               version=int(version_match.group(1)) if version_match else None))
    return records


def _openalex_abstract(index):
    if not isinstance(index, dict) or not index:
        return None, False
    positions = {}
    omitted = len(index) > 20_000
    # Reconstruct only a bounded prefix; never allocate a list at attacker-provided positions.
    for word, occurrences in list(index.items())[:20_000]:
        if not isinstance(word, str) or not isinstance(occurrences, list):
            raise ValueError("invalid-source-record")
        omitted = omitted or len(occurrences) > 20_000 or len(word) > MAX_ABSTRACT + 1
        for position in occurrences[:20_000]:
            if not isinstance(position, int) or isinstance(position, bool) or position < 0:
                raise ValueError("invalid-source-record")
            if position < 20_000:
                if position in positions and positions[position] != word:
                    raise ValueError("invalid-source-record")
                positions[position] = word[:MAX_ABSTRACT + 1]
            else:
                omitted = True
    return " ".join(positions[p] for p in sorted(positions)), omitted


def _openalex_record(record):
    record = _mapping(record)
    raw_id = record.get("id")
    match = re.fullmatch(r"https://openalex\.org/(W[1-9]\d{0,15})", raw_id) if isinstance(raw_id, str) else None
    if not match:
        raise ValueError("invalid-source-record")
    identifier = match.group(1)
    ids = {"openalex": identifier, "doi": _doi(record.get("doi"))}
    external = _mapping(record.get("ids"))
    for name, pattern in (("pmid", r"https?://(?:(?:www\.)?ncbi\.nlm\.nih\.gov/pubmed|pubmed\.ncbi\.nlm\.nih\.gov)/([1-9]\d{0,11})/?"),
                          ("pmcid", r"https?://(?:(?:www\.)?ncbi\.nlm\.nih\.gov/pmc/articles|pmc\.ncbi\.nlm\.nih\.gov/articles)/(PMC[1-9]\d{0,11})/?")):
        candidate = external.get(name)
        match = re.fullmatch(pattern, candidate) if isinstance(candidate, str) else None
        if match:
            ids[name] = match.group(1)
    kind = _text(record.get("type"), 100)
    notices = [{"type": "retraction flag", "direction": "record-flag"}] if record.get("is_retracted") is True else []
    location = _mapping(record.get("best_oa_location")) or _mapping(record.get("primary_location"))
    abstract, omitted = _openalex_abstract(record.get("abstract_inverted_index"))
    result = _finish("openalex", "openalex:" + identifier, record.get("title") or record.get("display_name"), ids,
                   raw_id, record.get("publication_date"), record.get("updated_date"), [kind] if kind else [],
                   "preprint" if kind == "preprint" else "unknown", abstract,
                   notices, "OpenAlex is_retracted flag only; false or missing is not proof of no notices",
                   checked=isinstance(record.get("is_retracted"), bool), license=location.get("license"))
    result["abstract"]["truncated"] = result["abstract"]["truncated"] or omitted
    return result


def search(source, query, limit, client):
    if source not in ("epmc", "crossref", "arxiv", "openalex"):
        raise ValueError("invalid-source")
    if not isinstance(query, str) or not query.strip() or len(query) > MAX_QUERY or any(ord(c) < 32 for c in query):
        raise ValueError("invalid-query")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_RESULTS:
        raise ValueError("invalid-limit")
    if source == "epmc":
        payload = _json(client.get("epmc", "/search", {"query": query, "format": "json", "resultType": "core", "pageSize": limit}))
        container = _mapping(payload.get("resultList"))
        if not isinstance(container.get("result"), list):
            raise ValueError("invalid-source-response")
        return [_epmc_record(r) for r in container["result"][:limit]]
    if source == "crossref":
        payload = _json(client.get("crossref", "/v1/works", {"query": query, "rows": limit}))
        items = _mapping(payload.get("message")).get("items")
        if not isinstance(items, list) or payload.get("status") != "ok":
            raise ValueError("invalid-source-response")
        return [_crossref_record(r) for r in items[:limit]]
    if source == "arxiv":
        return _arxiv_records(client.get("arxiv", "/api/query", {"search_query": query, "start": 0, "max_results": limit}))[:limit]
    payload = _json(client.get("openalex", "/works", {"search": query, "per-page": limit}))
    if not isinstance(payload.get("results"), list):
        raise ValueError("invalid-source-response")
    return [_openalex_record(r) for r in payload["results"][:limit]]


def resolve(identifier, client):
    kind, value = parse_identifier(identifier)
    if kind == "doi":
        payload = _json(client.get("crossref", "/v1/works/" + quote(value, safe="")))
        if payload.get("status") != "ok":
            raise ValueError("invalid-source-response")
        record = _crossref_record(payload.get("message"))
        if record["identifiers"]["doi"] != value:
            raise ValueError("identifier-mismatch")
        return record
    if kind in ("pmid", "pmcid"):
        query = f"EXT_ID:{value} AND SRC:MED" if kind == "pmid" else "PMCID:" + value
        records = search("epmc", query, 1, client)
    elif kind == "arxiv":
        records = _arxiv_records(client.get("arxiv", "/api/query", {"id_list": value, "max_results": 1}))
    else:
        record = _openalex_record(_json(client.get("openalex", "/works/" + value)))
        records = [record]
    if not records:
        raise ValueError("record-not-found")
    record = records[0]
    found = record["identifiers"].get(kind)
    if kind == "arxiv" and "v" not in value.rsplit("/", 1)[-1]:
        found = re.sub(r"v\d+$", "", found or "")
    if found != value:
        raise ValueError("identifier-mismatch")
    return record
