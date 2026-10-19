"""Bounded, network-free article extraction; locators identify text, not verified claims."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from html.parser import HTMLParser


_MAX_BYTES = 12 * 1024 * 1024
_MAX_NODES = 150_000
_MAX_DEPTH = 128
_MAX_UNITS = 10_000
_MAX_AVAILABLE = 50
_XML_NOISE = {"ref-list", "permissions", "back", "ack", "supplementary-material"}
_BLOCKS = {"p", "div", "sec", "section", "abstract", "title", "label", "caption",
           "figcaption", "table", "table-wrap", "table-wrap-foot", "list", "list-item",
           "disp-formula", "blockquote", "pre", "ul", "ol", "li", "dl", "dt", "dd"}


@dataclass
class _Unit:
    locator: str
    title: str
    text: str
    parent: int | None = None
    kind: str = "section"


def _check_input(data: bytes, max_chars: int) -> None:
    if not isinstance(data, bytes) or not data or len(data) > _MAX_BYTES:
        raise ValueError("invalid_article_size")
    if isinstance(max_chars, bool) or not isinstance(max_chars, int) or not 1 <= max_chars <= 12_000:
        raise ValueError("invalid_max_chars")


def _clean(text: str) -> str:
    # Keep cell separators and paragraph boundaries; collapse layout-only whitespace.
    lines = []
    for line in text.splitlines():
        cells = [re.sub(r"[^\S\t]+", " ", cell).strip() for cell in line.split("\t")]
        if len(cells) > 1 and not cells[-1]:
            cells.pop()  # The renderer terminates each cell, including the last cell.
        if any(cells):
            lines.append("\t".join(cells))
    return "\n".join(lines)


def _label(text: str, fallback: str) -> str:
    return re.sub(r"\s+", " ", text).strip()[:300] or fallback


def _locator(raw: str | None, fallback: str, used: set[str]) -> str:
    value = _label(raw or "", fallback)
    base = value
    number = 2
    while value in used:
        value = f"{base}-{number}"
        number += 1
    used.add(value)
    return value


def _result(title: str, license_text: str | None, units: list[_Unit],
            section: str | None, max_chars: int) -> dict:
    if not any(unit.text for unit in units):
        raise ValueError("article_text_unavailable")
    if section is None:
        selected = set(range(len(units)))
    else:
        query = section.strip()
        if not query:
            raise ValueError("section_not_found")
        exact = {i for i, unit in enumerate(units) if unit.locator == query}
        selected = exact or {i for i, unit in enumerate(units)
                             if query.casefold() in unit.title.casefold()}
        if not selected:
            raise ValueError("section_not_found")
        # A section heading selects its subsections and tables without duplicating text.
        for i, unit in enumerate(units):
            if unit.parent in selected:
                selected.add(i)
    selected_units = [unit for i, unit in enumerate(units) if i in selected and unit.text]
    if not selected_units:
        raise ValueError("section_text_unavailable")
    sections = []
    returned_kinds = []
    remaining = max_chars
    for unit in selected_units:
        if remaining <= 0:
            break
        text = unit.text[:remaining]
        sections.append({"locator": unit.locator, "title": unit.title,
                         "text": text, "truncated": len(text) < len(unit.text)})
        returned_kinds.append(unit.kind)
        remaining -= len(text)
    omitted = len(selected_units) - len(sections)
    return {"title": title, "license": license_text,
            "access_level": "abstract" if returned_kinds and all(k == "abstract" for k in returned_kinds) else "full-text-excerpt",
            "sections": sections,
            "available_sections": [{"locator": unit.locator, "title": unit.title}
                                   for unit in units[:_MAX_AVAILABLE]],
            "available_sections_total": len(units), "sections_omitted": omitted,
            "catalog_truncated": len(units) > _MAX_AVAILABLE,
            "truncated": bool(omitted or any(part["truncated"] for part in sections))}


def _tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1] if isinstance(element.tag, str) else ""


def _xml_text(element: ET.Element, excluded: set[str] | None = None) -> str:
    excluded = _XML_NOISE | (excluded or set())
    parts: list[str] = []
    stack = [(element, False)]
    while stack:
        node, closing = stack.pop()
        tag = _tag(node)
        if closing:
            if tag in {"td", "th"}:
                parts.append("\t")
            elif tag == "tr" or tag in _BLOCKS:
                parts.append("\n")
            if node is not element and node.tail:
                parts.append(node.tail)
        elif node is not element and tag in excluded:
            if node.tail:
                parts.append(node.tail)
        else:
            if tag in _BLOCKS or tag == "tr":
                parts.append("\n")
            if node.text:
                parts.append(node.text)
            stack.append((node, True))
            stack.extend((child, False) for child in reversed(list(node)))
    return _clean("".join(parts))


def _xml_child(element: ET.Element, name: str) -> ET.Element | None:
    return next((child for child in element if _tag(child) == name), None)


def _xml_title(element: ET.Element, fallback: str) -> str:
    names = {"label", "caption"} if _tag(element) == "table-wrap" else {"title"}
    return _label(" ".join(_xml_text(child) for child in element if _tag(child) in names), fallback)


def extract_jats(data: bytes, section: str | None, max_chars: int) -> dict:
    """Extract JATS body sections/tables and optional abstracts, with a global text cap."""
    _check_input(data, max_chars)
    # External DOCTYPE declarations are common in JATS, but entity declarations are not needed.
    if re.search(br"<!\s*ENTITY\b", data.replace(b"\x00", b""), re.IGNORECASE):
        raise ValueError("xml_entities_not_allowed")
    try:
        root = ET.fromstring(data)
    except (ET.ParseError, ValueError) as exc:
        raise ValueError("invalid_article_xml") from exc
    count = 0
    stack = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        count += 1
        if depth > _MAX_DEPTH or count > _MAX_NODES:
            raise ValueError("article_structure_too_large")
        stack.extend((child, depth + 1) for child in node)
    body = _xml_child(root, "body")
    if _tag(root) != "article" or body is None:
        raise ValueError("not_a_jats_article")
    article_meta = next((node for node in root.iter() if _tag(node) == "article-meta"), None)
    title_node = next((node for node in article_meta.iter() if _tag(node) == "article-title"), None) \
        if article_meta is not None else None
    if title_node is None:
        raise ValueError("article_title_unavailable")
    title = _label(_xml_text(title_node), "")
    if not title:
        raise ValueError("article_title_unavailable")
    license_node = next((node for node in root.iter() if _tag(node) == "license"), None)
    license_text = None
    if license_node is not None:
        href = next((value for key, value in license_node.attrib.items()
                     if key.rsplit("}", 1)[-1] == "href"), "")
        license_text = _label(" ".join(filter(None, [_xml_text(license_node), href])), "") or None
    units: list[_Unit] = []
    used: set[str] = set()
    if article_meta is not None:
        for index, abstract in enumerate((node for node in article_meta
                                          if _tag(node) == "abstract"), 1):
            units.append(_Unit(_locator(abstract.get("id"), f"abstract-{index}", used),
                               "Abstract", _xml_text(abstract, {"title"}), kind="abstract"))
            if len(units) >= _MAX_UNITS:
                raise ValueError("too_many_sections")
    body_index = len(units)
    units.append(_Unit(_locator(body.get("id"), "body", used), "Body",
                       _xml_text(body, {"sec", "table-wrap", "title"})))
    stack = [(child, len(units) - 1) for child in reversed(list(body))]
    while stack:
        node, parent = stack.pop()
        tag = _tag(node)
        if tag in _XML_NOISE:
            continue
        if tag in {"sec", "table-wrap"}:
            fallback = f"section-{len(units) + 1}" if tag == "sec" else f"table-{len(units) + 1}"
            text = _xml_text(node, {"sec", "table-wrap", "title"}) if tag == "sec" else _xml_text(node)
            units.append(_Unit(_locator(node.get("id"), fallback, used),
                               _xml_title(node, "Section" if tag == "sec" else "Table"), text, parent))
            parent = len(units) - 1
            if len(units) > _MAX_UNITS:
                raise ValueError("too_many_sections")
            if tag == "table-wrap":
                continue
        stack.extend((child, parent) for child in reversed(list(node)))
    if not any(unit.text for unit in units[body_index:]):
        raise ValueError("article_text_unavailable")
    return _result(title, license_text, units, section, max_chars)


@dataclass(eq=False)
class _HTMLNode:
    tag: str
    attrs: dict[str, str]
    children: list = field(default_factory=list)
    closed: bool = False

    @property
    def classes(self) -> set[str]:
        return set(self.attrs.get("class", "").split())


class _HTMLTree(HTMLParser):
    _VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
             "meta", "param", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _HTMLNode("document", {})
        self.stack = [self.root]
        self.nodes = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        self.nodes += 1
        if self.nodes > _MAX_NODES or len(self.stack) > _MAX_DEPTH:
            raise ValueError("article_structure_too_large")
        node = _HTMLNode(tag, {key: value or "" for key, value in attrs})
        self.stack[-1].children.append(node)
        if tag not in self._VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in self._VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                self.stack[index].closed = True
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)


_HTML_NOISE_TAGS = {"script", "style", "nav", "footer", "head", "noscript", "annotation",
                    "annotation-xml"}
_HTML_NOISE_CLASSES = {"ltx_bibliography", "ltx_biblist", "ltx_bibitem", "ltx_page_navbar", "ltx_page_footer", "ltx_authors",
                       "ltx_dates", "ltx_role_author", "ltx_role_affiliation", "ltx_note_outer"}


def _html_noise(node: _HTMLNode) -> bool:
    return (node.tag in _HTML_NOISE_TAGS or bool(node.classes & _HTML_NOISE_CLASSES)
            or node.attrs.get("role") == "doc-bibliography"
            or "hidden" in node.attrs or node.attrs.get("aria-hidden") == "true")


def _html_nodes(root: _HTMLNode):
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        stack.extend(child for child in reversed(node.children) if isinstance(child, _HTMLNode))


def _html_text(root: _HTMLNode, excluded: set[int] | None = None) -> str:
    excluded = excluded or set()
    parts: list[str] = []
    stack = [(root, False)]
    while stack:
        item, closing = stack.pop()
        if isinstance(item, str):
            parts.append(item)
            continue
        if closing:
            if item.tag in {"td", "th"}:
                parts.append("\t")
            elif item.tag == "tr" or item.tag in _BLOCKS or item.tag.startswith("h") and item.tag[1:].isdigit():
                parts.append("\n")
        elif _html_noise(item) or item is not root and id(item) in excluded:
            continue
        elif item.tag == "math" and item.attrs.get("alttext"):
            parts.append(item.attrs["alttext"])
        else:
            if item.tag in _BLOCKS or item.tag == "tr" or item.tag == "br":
                parts.append("\n")
            stack.append((item, True))
            stack.extend((child, False) for child in reversed(item.children))
    return _clean("".join(parts))


def _html_heading(node: _HTMLNode) -> _HTMLNode | None:
    # arXiv headings are direct children; tolerate a lightweight header wrapper.
    for child in node.children:
        if not isinstance(child, _HTMLNode):
            continue
        if child.tag in {"h1", "h2", "h3", "h4", "h5", "h6", "figcaption", "caption"}:
            return child
        if child.tag == "header":
            return _html_heading(child)
    return None


def extract_arxiv_html(data: bytes, section: str | None, max_chars: int) -> dict:
    """Extract an arXiv LaTeXML article, rejecting generic HTML and incomplete articles."""
    _check_input(data, max_chars)
    try:
        html = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("invalid_article_html_encoding") from exc
    parser = _HTMLTree()
    try:
        parser.feed(html)
        parser.close()
    except (RecursionError, AssertionError) as exc:
        raise ValueError("invalid_article_html") from exc
    article = next((node for node in _html_nodes(parser.root)
                    if node.tag == "article" and "ltx_document" in node.classes), None)
    if article is None or not article.closed:
        raise ValueError("not_an_arxiv_article")
    title_node = next((node for node in _html_nodes(article)
                       if "ltx_title_document" in node.classes), None) or _html_heading(article)
    if title_node is None:
        raise ValueError("article_title_unavailable")
    title = _label(_html_text(title_node), "")
    if not title:
        raise ValueError("article_title_unavailable")
    license_text = None
    for node in _html_nodes(parser.root):
        href = node.attrs.get("href", "")
        if node.tag in {"a", "link"} and ("license" in node.attrs.get("rel", "").split()
                or re.match(r"https?://(?:www\.)?creativecommons\.org/(?:licenses|publicdomain)/", href)):
            license_text = _label(href or _html_text(node), "") or None
            break
    candidates: list[tuple[_HTMLNode, int | None, str]] = [(article, None, "Body")]
    stack = [(child, 0, False) for child in reversed(article.children) if isinstance(child, _HTMLNode)]
    while stack:
        node, parent, in_table = stack.pop()
        if _html_noise(node):
            continue
        classes = node.classes
        table = "ltx_table" in classes or node.tag == "table" and not in_table
        abstract = "ltx_abstract" in classes
        is_section = node.tag == "section" or bool(classes & {"ltx_section", "ltx_subsection", "ltx_subsubsection"})
        if table or abstract or is_section:
            heading = _html_heading(node)
            fallback = "Table" if table else "Abstract" if abstract else "Section"
            heading_text = _label(_html_text(heading), fallback) if heading is not None else fallback
            candidates.append((node, parent, heading_text))
            parent = len(candidates) - 1
            if len(candidates) > _MAX_UNITS:
                raise ValueError("too_many_sections")
            if table:
                continue
        stack.extend((child, parent, in_table or table) for child in reversed(node.children)
                     if isinstance(child, _HTMLNode))
    candidate_ids = {id(node) for node, _, _ in candidates}
    headings = {id(heading) for node, _, _ in candidates
                if (heading := _html_heading(node)) is not None and node.tag != "table"
                and "ltx_table" not in node.classes}
    headings.add(id(title_node))
    units: list[_Unit] = []
    used: set[str] = set()
    excluded = candidate_ids | headings
    abstract_units: set[int] = set()
    for index, (node, parent, heading) in enumerate(candidates):
        if "ltx_abstract" in node.classes or parent in abstract_units:
            abstract_units.add(index)
        units.append(_Unit(_locator(node.attrs.get("id"), "body" if index == 0 else f"section-{index}", used),
                           heading, _html_text(node, excluded), parent,
                           "abstract" if index in abstract_units else "section"))
    if not any(unit.text for index, unit in enumerate(units) if index not in abstract_units):
        raise ValueError("article_text_unavailable")
    return _result(title, license_text, units, section, max_chars)
