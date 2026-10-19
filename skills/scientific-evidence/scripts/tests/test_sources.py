"""Credential/network-free regressions for record identity and evidence boundaries."""

import json
import unittest

import _sources as sources


class FakeClient:
    def __init__(self, payload):
        self.payload = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.calls = []

    def get(self, provider, path, params=None):
        self.calls.append((provider, path, params))
        return self.payload


def epmc(record=None):
    return {"resultList": {"result": [record or {
        "source": "MED", "id": "9500320", "title": "A trial", "doi": "10.1234/ABC",
        "pmcid": "PMC123", "firstPublicationDate": "2001-02-03",
        "pubTypeList": {"pubType": ["Journal Article"]},
    }]}}


def crossref(**fields):
    record = {"DOI": "10.1234/ABC", "title": ["A study"], "type": "journal-article",
              "published": {"date-parts": [[2020, 2, 3]]}}
    record.update(fields)
    return {"status": "ok", "message": record}


def arxiv(identifier="2501.12948v2", extra="", abstract="A summary"):
    return f'''<?xml version="1.0"?>
      <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry><id>http://arxiv.org/abs/{identifier}</id><title>A model</title>
      <published>2025-01-22T00:00:00Z</published><updated>2025-03-01T00:00:00Z</updated>
      <summary>{abstract}</summary>{extra}</entry></feed>'''.encode()


class SourceTests(unittest.TestCase):
    def test_arbitrary_urls_and_malformed_ids_never_make_network_calls(self):
        client = FakeClient({})
        for identifier in ("https://doi.org/10.1234/abc", "https://127.0.0.1/",
                           "doi:10.12/x", "doi:10.1234/abc?secret=x", "pmid:0",
                           "pmcid:../../etc", "arxiv:2513.12345", "arxiv:2501.12345v0",
                           "12345", "openalex:W1/../secret"):
            with self.subTest(identifier=identifier), self.assertRaisesRegex(ValueError, "^invalid-identifier$"):
                sources.resolve(identifier, client)
        self.assertEqual(client.calls, [])

    def test_crossref_doi_is_case_normalized_and_path_encoded(self):
        client = FakeClient(crossref())
        result = sources.resolve("DOI:10.1234/ABC", client)
        self.assertEqual(result["identifiers"]["doi"], "10.1234/abc")
        self.assertEqual(client.calls[0], ("crossref", "/v1/works/10.1234%2Fabc", None))
        self.assertEqual(result["published"], "2020-02-03")
        self.assertEqual(result["access_level"], "metadata")

    def test_crossref_wrong_doi_is_not_silently_accepted(self):
        client = FakeClient(crossref(DOI="10.1234/WRONG"))
        with self.assertRaisesRegex(ValueError, "^identifier-mismatch$"):
            sources.resolve("10.1234/abc", client)

    def test_crossref_notice_direction_preserves_target_meaning(self):
        client = FakeClient(crossref(**{
            "updated-by": [{"DOI": "10.1234/retraction", "type": "retraction"}],
            "update-to": [{"DOI": "10.1234/original", "type": "correction"}],
        }))
        result = sources.resolve("10.1234/abc", client)
        self.assertEqual(result["notices"][0]["direction"], "notice-about-this-work")
        self.assertEqual(result["notices"][1]["direction"], "this-work-updates-target")
        self.assertEqual(result["notice_check"]["status"], "notice-found")

    def test_buried_retraction_survives_notice_cap(self):
        record = epmc()["resultList"]["result"][0]
        comments = [{"type": "Comment in", "source": "MED", "id": str(100 + n)} for n in range(20)]
        comments.extend([{"type": "Retraction in", "source": "MED", "id": "20137807"},
                         {"type": "Expression of concern in", "source": "MED", "id": "21971344"}])
        comments.extend([{"type": "Erratum in", "source": "MED", "id": str(200 + n)} for n in range(10)])
        record["commentCorrectionList"] = {"commentCorrection": comments}
        result = sources.resolve("pmid:9500320", FakeClient(epmc(record)))
        self.assertEqual(result["notices"][0]["type"], "Retraction in")
        self.assertEqual(result["notices"][1]["type"], "Expression of concern in")
        self.assertEqual(result["notice_count"], 12)
        self.assertEqual(len(result["notices"]), sources.MAX_NOTICES)
        self.assertTrue(result["notices_truncated"])

    def test_ordinary_epmc_comments_do_not_become_notices(self):
        record = epmc()["resultList"]["result"][0]
        record["commentCorrectionList"] = {"commentCorrection": [{"type": "Comment in", "id": "123", "source": "MED"}]}
        result = sources.resolve("pmid:9500320", FakeClient(epmc(record)))
        self.assertEqual(result["notices"], [])
        self.assertEqual(result["notice_count"], 0)
        self.assertEqual(result["notice_check"]["status"], "none-in-record")

    def test_epmc_pub_type_alone_detects_retracted_publication(self):
        record = epmc()["resultList"]["result"][0]
        record["pubTypeList"]["pubType"].append("Retracted Publication")
        result = sources.resolve("pmcid:PMC123", FakeClient(epmc(record)))
        self.assertEqual(result["notice_check"]["status"], "notice-found")
        self.assertEqual(result["notices"][0]["direction"], "publication-type")

    def test_epmc_pmc_source_can_supply_identifier_without_redundant_pmcid_field(self):
        record = {"source": "PMC", "id": "PMC123", "title": "A work"}
        result = sources.resolve("pmcid:PMC123", FakeClient(epmc(record)))
        self.assertEqual(result["identifiers"]["pmcid"], "PMC123")

    def test_epmc_search_asks_for_core_metadata(self):
        client = FakeClient(epmc())
        result = sources.search("epmc", "sleep AND adolescent", 2, client)
        self.assertEqual(client.calls[0][2]["resultType"], "core")
        self.assertEqual(client.calls[0][2]["pageSize"], 2)
        self.assertEqual(result[0]["notice_check"]["status"], "none-in-record")
        self.assertIn("not an exhaustive", result[0]["notice_check"]["scope"])

    def test_metadata_does_not_claim_full_text_even_with_open_access_flag(self):
        record = epmc()["resultList"]["result"][0]
        record["isOpenAccess"] = "Y"
        result = sources.resolve("pmid:9500320", FakeClient(epmc(record)))
        self.assertEqual(result["access_level"], "metadata")
        self.assertEqual(result["abstract"], {"text": "", "truncated": False})

    def test_abstract_is_plain_bounded_and_marked_truncated(self):
        client = FakeClient(crossref(abstract="<jats:p>" + "evidence " * 1000 + "</jats:p>"))
        result = sources.resolve("10.1234/abc", client)
        self.assertEqual(result["access_level"], "abstract")
        self.assertTrue(result["abstract"]["truncated"])
        self.assertEqual(len(result["abstract"]["text"]), sources.MAX_ABSTRACT)
        self.assertNotIn("<jats:p>", result["abstract"]["text"])

    def test_api_doi_cannot_make_normalized_output_unbounded(self):
        payload = crossref(DOI="10.1234/" + "a" * 5000)
        payload["message"] = {"items": [payload["message"]]}
        with self.assertRaisesRegex(ValueError, "^invalid-source-record$"):
            sources.search("crossref", "x", 1, FakeClient(payload))

    def test_latest_arxiv_returns_explicit_version_and_date(self):
        client = FakeClient(arxiv())
        result = sources.resolve("2501.12948", client)
        self.assertEqual(client.calls[0][2]["id_list"], "2501.12948")
        self.assertEqual(result["version"], 2)
        self.assertEqual(result["url"], "https://arxiv.org/abs/2501.12948v2")
        self.assertEqual(result["publication_status"], "preprint")

    def test_arxiv_pinned_version_cannot_be_substituted(self):
        client = FakeClient(arxiv())
        with self.assertRaisesRegex(ValueError, "^identifier-mismatch$"):
            sources.resolve("arxiv:2501.12948v1", client)
        self.assertEqual(client.calls[0][2]["id_list"], "2501.12948v1")

    def test_arxiv_legacy_id_and_native_namespace_journal_reference(self):
        extra = "<arxiv:journal_ref>A Journal 2020</arxiv:journal_ref><arxiv:doi>10.1234/ABC</arxiv:doi>"
        result = sources.resolve("arxiv:hep-th/9901001v1", FakeClient(arxiv("hep-th/9901001v1", extra)))
        self.assertEqual(result["version"], 1)
        self.assertEqual(result["identifiers"]["doi"], "10.1234/abc")
        self.assertEqual(result["publication_status"], "journal-reference-present")
        self.assertNotIn("peer-reviewed", json.dumps(result))

    def test_arxiv_withdrawal_language_retained(self):
        result = sources.resolve("2501.12948", FakeClient(arxiv(extra="<arxiv:comment>This paper has been withdrawn.</arxiv:comment>")))
        self.assertEqual(result["notices"][0]["field"], "comment")
        self.assertIn("candidate, verify", result["notices"][0]["type"])
        self.assertEqual(result["notice_check"]["status"], "notice-found")

    def test_arxiv_errors_and_xml_entity_declarations_fail_closed(self):
        for body in (b"not xml", b"<feed/>", arxiv("api/errors"),
                     b'<!DOCTYPE feed [<!ENTITY x "test">]><feed/>'):
            with self.subTest(body=body[:30]), self.assertRaises(ValueError):
                sources.search("arxiv", "all:ai", 1, FakeClient(body))

    def test_openalex_reconstructs_abstract_without_large_sparse_allocation(self):
        record = {"id": "https://openalex.org/W123", "display_name": "A work", "type": "preprint",
                  "doi": "https://doi.org/10.1234/ABC", "is_retracted": False,
                  "ids": {"pmid": "https://pubmed.ncbi.nlm.nih.gov/1234", "pmcid": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5678/"},
                  "abstract_inverted_index": {"First": [0], "then": [1], "next": [2, 999999999999]}}
        result = sources.resolve("openalex:W123", FakeClient(record))
        self.assertEqual(result["abstract"]["text"], "First then next")
        self.assertTrue(result["abstract"]["truncated"])
        self.assertEqual(result["identifiers"]["doi"], "10.1234/abc")
        self.assertEqual(result["identifiers"]["pmid"], "1234")
        self.assertEqual(result["identifiers"]["pmcid"], "PMC5678")
        self.assertEqual(result["notice_check"]["status"], "none-in-record")

    def test_openalex_missing_notice_flag_is_not_checked(self):
        record = {"id": "https://openalex.org/W123", "title": "A work"}
        result = sources.resolve("openalex:W123", FakeClient(record))
        self.assertEqual(result["notice_check"]["status"], "not-checked")
        record["is_retracted"] = True
        self.assertEqual(sources.resolve("openalex:W123", FakeClient(record))["notice_check"]["status"], "notice-found")

    def test_invalid_source_records_do_not_look_like_empty_success(self):
        for source, payload in (("epmc", {}), ("crossref", {"status": "error", "message": {"items": []}}),
                                ("openalex", {"results": [{"id": "file:///tmp/x", "title": "x"}]}),
                                ("openalex", {"results": [{"id": 123, "title": "x"}]}),
                                ("epmc", {"resultList": {"result": [{"source": "MED", "id": "1"}]}})):
            with self.subTest(source=source), self.assertRaises(ValueError):
                sources.search(source, "a query", 1, FakeClient(payload))

    def test_invalid_search_arguments_are_rejected_before_network(self):
        client = FakeClient({})
        for args in (("epmc", "", 1), ("epmc", "a" * 501, 1), ("epmc", "x", True),
                     ("epmc", "x", 11), ("unknown", "x", 1)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                sources.search(*args, client)
        self.assertEqual(client.calls, [])

    def test_empty_resolve_result_is_not_found(self):
        client = FakeClient({"resultList": {"result": []}})
        with self.assertRaisesRegex(ValueError, "^record-not-found$"):
            sources.resolve("pmid:123", client)


if __name__ == "__main__":
    unittest.main()
