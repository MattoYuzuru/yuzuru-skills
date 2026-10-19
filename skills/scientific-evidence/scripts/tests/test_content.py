"""Credential-free fixtures for bounded article content extraction."""

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _content import extract_arxiv_html, extract_jats  # noqa: E402


JATS = b'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Archiving and Interchange DTD v1.3 20210610//EN" "JATS-archivearticle1-3.dtd">
<article xmlns:xlink="http://www.w3.org/1999/xlink">
 <front><article-meta><title-group><article-title>Trial of <italic>bounded</italic> extraction</article-title></title-group>
 <permissions><license xlink:href="https://creativecommons.org/licenses/by/4.0/"><license-p>CC BY 4.0</license-p></license></permissions>
 <abstract><p>A registered trial &amp; its outcome.</p></abstract></article-meta></front>
 <body><sec id="S1"><title>Methods</title><p>We randomized <italic>two</italic> arms.</p>
  <sec id="S1.1"><title>Participants</title><p>Forty participants were enrolled.</p></sec>
  <table-wrap id="T1"><label>Table 1</label><caption><title>Baseline characteristics</title></caption>
   <table><thead><tr><th>Arm</th><th>N</th></tr></thead><tbody><tr><td>Active</td><td>20</td></tr><tr><td>Control</td><td>20</td></tr></tbody></table>
   <table-wrap-foot><p>N means participant count.</p></table-wrap-foot></table-wrap>
 </sec><sec id="S2"><title>Results</title><p>The primary outcome was unchanged.</p></sec>
 <sec id="S3"><title>Discussion</title><p>This small trial has uncertainty.</p><ref-list><ref>NOISE REFERENCE</ref></ref-list></sec></body>
 <back><ref-list><ref>NOISE BACK</ref></ref-list></back>
</article>'''


ARXIV = '''<!doctype html><html><head><title>Ignore browser title</title><script>HEAD NOISE</script></head>
<body><nav>NAVIGATION NOISE</nav><a rel="license" href="https://creativecommons.org/licenses/by/4.0/">License</a>
<article class="ltx_document" id="doc"><h1 class="ltx_title ltx_title_document">A model &amp; its limits</h1>
<div class="ltx_authors">AUTHOR NOISE</div><div class="ltx_dates">DATE NOISE</div>
<div class="ltx_abstract" id="abs"><h6 class="ltx_title ltx_title_abstract">Abstract</h6><p>We study small models.</p></div>
<section class="ltx_section" id="S1"><h2 class="ltx_title ltx_title_section">1 Methods</h2><div class="ltx_para"><p>We trained with <math alttext="x &lt; y"><semantics><mi>x</mi><annotation>LATEX NOISE</annotation></semantics></math>.</p></div>
 <section class="ltx_subsection" id="S1.SS1"><h3 class="ltx_title ltx_title_subsection">1.1 Data</h3><p>We used an open corpus.</p></section>
 <figure class="ltx_table" id="S1.T1"><figcaption><span class="ltx_tag">Table 1:</span> Model scores</figcaption>
  <table class="ltx_tabular"><tr><th>Model</th><th>Score</th></tr><tr><td>Small</td><td>0.5</td></tr></table></figure>
 <script>SCRIPT NOISE</script><style>STYLE NOISE</style><span hidden>HIDDEN NOISE</span>
</section><section id="S2"><h2>2 Results</h2><p>Accuracy was 50&#37;.</p></section>
<section class="ltx_bibliography" id="bib"><h2>References</h2><p>REFERENCE NOISE</p></section>
<footer>FOOTER NOISE</footer></article></body></html>'''.encode()


class ContentTests(unittest.TestCase):
    def test_jats_sections_are_locatable_and_not_duplicated(self):
        result = extract_jats(JATS, None, 6000)
        self.assertEqual(result["title"], "Trial of bounded extraction")
        self.assertIn("https://creativecommons.org/licenses/by/4.0/", result["license"])
        self.assertEqual(result["access_level"], "full-text-excerpt")
        self.assertFalse(result["truncated"])
        by_id = {part["locator"]: part for part in result["sections"]}
        self.assertEqual(by_id["S1"]["text"], "We randomized two arms.")
        self.assertEqual(by_id["S1.1"]["text"], "Forty participants were enrolled.")
        self.assertIn("Arm\tN\nActive\t20\nControl\t20", by_id["T1"]["text"])
        self.assertIn("N means participant count.", by_id["T1"]["text"])
        combined = " ".join(part["text"] for part in result["sections"])
        self.assertEqual(combined.count("Forty participants"), 1)
        self.assertNotIn("NOISE", combined)

    def test_jats_parent_selection_includes_descendants_and_table(self):
        result = extract_jats(JATS, "METHOD", 6000)
        self.assertEqual([part["locator"] for part in result["sections"]], ["S1", "S1.1", "T1"])
        table = extract_jats(JATS, "T1", 6000)
        self.assertEqual([part["locator"] for part in table["sections"]], ["T1"])
        self.assertIn("Table 1", table["sections"][0]["title"])
        by_label = extract_jats(JATS, "Baseline characteristics", 6000)
        self.assertEqual(by_label["sections"], table["sections"])

    def test_arxiv_sections_tables_math_and_noise(self):
        result = extract_arxiv_html(ARXIV, None, 6000)
        self.assertEqual(result["title"], "A model & its limits")
        self.assertEqual(result["license"], "https://creativecommons.org/licenses/by/4.0/")
        self.assertFalse(result["truncated"])
        by_id = {part["locator"]: part for part in result["sections"]}
        self.assertEqual(by_id["S1"]["text"], "We trained with x < y.")
        self.assertEqual(by_id["S1.SS1"]["text"], "We used an open corpus.")
        self.assertEqual(by_id["S2"]["text"], "Accuracy was 50%.")
        self.assertIn("Model\tScore\nSmall\t0.5", by_id["S1.T1"]["text"])
        combined = " ".join(part["text"] for part in result["sections"])
        self.assertNotIn("NOISE", combined)
        self.assertEqual(combined.count("We used an open corpus."), 1)
        methods = extract_arxiv_html(ARXIV, "methods", 6000)
        self.assertEqual([part["locator"] for part in methods["sections"]], ["S1", "S1.SS1", "S1.T1"])
        table = extract_arxiv_html(ARXIV, "Table 1", 6000)
        self.assertEqual([part["locator"] for part in table["sections"]], ["S1.T1"])

    def test_global_cap_discloses_partial_text_and_omissions(self):
        for extractor, fixture in [(extract_jats, JATS), (extract_arxiv_html, ARXIV)]:
            with self.subTest(extractor=extractor.__name__):
                result = extractor(fixture, None, 55)
                self.assertEqual(sum(len(part["text"]) for part in result["sections"]), 55)
                self.assertTrue(result["truncated"])
                self.assertTrue(result["sections"][-1]["truncated"])
                self.assertGreater(result["sections_omitted"], 0)
                full = extractor(fixture, None, 6000)
                self.assertEqual(result["sections_omitted"], len(full["sections"]) - len(result["sections"]))
                first_size = len(full["sections"][0]["text"])
                exact = extractor(fixture, None, first_size)
                self.assertFalse(exact["sections"][0]["truncated"])
                self.assertTrue(exact["truncated"])

    def test_section_not_found_is_an_error(self):
        for extractor, fixture in [(extract_jats, JATS), (extract_arxiv_html, ARXIV)]:
            with self.subTest(extractor=extractor.__name__):
                with self.assertRaisesRegex(ValueError, "^section_not_found$"):
                    extractor(fixture, "nonexistent section", 6000)
                with self.assertRaisesRegex(ValueError, "^section_not_found$"):
                    extractor(fixture, " ", 6000)

    def test_grouping_section_with_no_own_text_selects_children(self):
        fixture = JATS.replace(b"<p>We randomized <italic>two</italic> arms.</p>", b"")
        result = extract_jats(fixture, "S1", 6000)
        self.assertEqual([part["locator"] for part in result["sections"]], ["S1.1", "T1"])

    def test_available_section_catalog_is_bounded_and_truthful(self):
        sections = b"".join(f'<sec id="s{i}"><title>Topic {i}</title><p>Text {i}.</p></sec>'.encode()
                            for i in range(65))
        fixture = b"<article><front><article-meta><article-title>Many sections</article-title></article-meta></front><body>" + sections + b"</body></article>"
        result = extract_jats(fixture, "s64", 6000)
        self.assertEqual(len(result["available_sections"]), 50)
        self.assertEqual(result["available_sections_total"], 66)
        self.assertEqual(result["sections"][0]["locator"], "s64")
        self.assertEqual(result["sections_omitted"], 0)
        self.assertTrue(result["catalog_truncated"])
        self.assertFalse(result["truncated"])

    def test_only_returned_abstract_is_not_labeled_full_text(self):
        for extractor, fixture in [(extract_jats, JATS), (extract_arxiv_html, ARXIV)]:
            result = extractor(fixture, "Abstract", 500)
            self.assertEqual(result["access_level"], "abstract")
            result = extractor(fixture, None, 20)
            self.assertEqual(result["access_level"], "abstract")
            self.assertTrue(result["truncated"])

    def test_namespace_and_missing_license(self):
        fixture = b'<article xmlns="urn:jats"><front><article-meta><article-title>A title</article-title></article-meta></front><body><sec id="s"><title>Results</title><p>Some text.</p></sec></body></article>'
        result = extract_jats(fixture, "s", 500)
        self.assertIsNone(result["license"])
        self.assertEqual(result["sections"][0]["text"], "Some text.")
        result = extract_arxiv_html(ARXIV.replace(b'rel="license"', b'rel="other"').replace(b'creativecommons.org', b'example.org'), None, 500)
        self.assertIsNone(result["license"])

    def test_no_title_or_empty_body_is_not_full_text_evidence(self):
        fixtures = [b"<article><body><p>Text</p></body></article>",
                    b"<article><front><article-meta><article-title>Title</article-title></article-meta></front><body/></article>",
                    b"<article><front><article-meta><article-title>Title</article-title><abstract><p>Only an abstract.</p></abstract></article-meta></front><body/></article>"]
        for fixture in fixtures:
            with self.assertRaises(ValueError):
                extract_jats(fixture, None, 500)
        with self.assertRaises(ValueError):
            extract_arxiv_html(b'<article class="ltx_document"><h1>Title</h1></article>', None, 500)
        with self.assertRaises(ValueError):
            extract_arxiv_html(b'<article class="ltx_document"><h1>Title</h1><div class="ltx_abstract"><p>Only an abstract.</p></div></article>', None, 500)

    def test_empty_table_cells_retain_boundaries(self):
        fixture = JATS.replace(b"<td>Active</td><td>20</td>", b"<td></td><td>20</td>")
        result = extract_jats(fixture, "T1", 6000)
        self.assertIn("Arm\tN\n\t20\nControl\t20", result["sections"][0]["text"])
        fixture = ARXIV.replace(b"<td>Small</td><td>0.5</td>", b"<td>Small</td><td></td>")
        result = extract_arxiv_html(fixture, "S1.T1", 6000)
        self.assertIn("Model\tScore\nSmall\t", result["sections"][0]["text"])

    def test_not_articles_malformed_input_and_entities_are_rejected(self):
        for fixture in [b"<html><body>Service unavailable</body></html>", b"<article>", b"not XML"]:
            with self.subTest(fixture=fixture), self.assertRaises(ValueError):
                extract_jats(fixture, None, 500)
        for fixture in [b"<html><h1>Checking your browser</h1></html>",
                        b'<article><h1>Generic article</h1><p>Text</p></article>',
                        b'<article class="ltx_document"><h1>Title</h1><p>truncated', b"\xff"]:
            with self.subTest(fixture=fixture), self.assertRaises(ValueError):
                extract_arxiv_html(fixture, None, 500)
        entity = b'<!DOCTYPE article [<!ENTITY malicious "expanded">]>' + JATS[JATS.index(b"<article "):]
        with self.assertRaisesRegex(ValueError, "xml_entities_not_allowed"):
            extract_jats(entity, None, 500)

    def test_caps_are_checked_even_for_direct_parser_use(self):
        for extractor, fixture in [(extract_jats, JATS), (extract_arxiv_html, ARXIV)]:
            for max_chars in [0, -1, 12001, True, "500"]:
                with self.subTest(extractor=extractor.__name__, cap=max_chars), self.assertRaises(ValueError):
                    extractor(fixture, None, max_chars)
            with self.assertRaisesRegex(ValueError, "invalid_article_size"):
                extractor(b"x" * (12 * 1024 * 1024 + 1), None, 500)


if __name__ == "__main__":
    unittest.main()
