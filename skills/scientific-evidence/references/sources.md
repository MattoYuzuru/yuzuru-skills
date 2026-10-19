# Source selection and helper boundaries

Checked 2026-10-19. Use this reference for papers, medicine and computing; use topics.md for
everyday/social/environment/space questions. Recheck provider documentation before changing APIs.

| Need | Source and use | Helper support |
|---|---|---|
| Biomedical discovery and notices | [Europe PMC REST](https://europepmc.org/RestfulWebService): core metadata, abstracts, eligible OA XML | `search --source epmc`, `resolve pmid:ID`, `resolve pmcid:PMC…`, `read pmcid:PMC…` |
| Medical index and subject terms | [PubMed/MEDLINE](https://pubmed.ncbi.nlm.nih.gov/about/): citations/abstracts, MeSH and linked notices | Use Europe PMC adapter for covered records or native public search; no direct E-utilities adapter is bundled. |
| Trial registration | [ClinicalTrials.gov API v2](https://clinicaltrials.gov/data-api/api) for planned outcomes, dates and posted results | Public API/native tools; preserve registry update dates separately from publication dates. |
| Reviews | [Cochrane](https://help.cochrane.org/kb/article/27-how-can-i-access-cochrane-evidence/) | Free abstracts/summaries; full reviews may need access. No universal full-text adapter is bundled. |
| DOI/title matching and updates | [Crossref](https://www.crossref.org/documentation/retrieve-metadata/rest-api/), [versioned API](https://www.crossref.org/documentation/retrieve-metadata/api-versioning/) | `search --source crossref`, `resolve doi:…`; updated-by notices describe this work, update-to may describe a notice's target. |
| LLM/ML, physics and quantitative reports | [arXiv API](https://info.arxiv.org/help/api/user-manual.html) | `search --source arxiv`, `resolve arxiv:ID[vN]`; `read` supports modern IDs with HTML available. |
| Broad discovery graph | [OpenAlex](https://help.openalex.org/api/authentication/) | Keyless `search --source openalex` / `resolve openalex:W…`; optional free key for quota/pagination. |
| Related papers/citations | [Semantic Scholar](https://api.semanticscholar.org/api-docs/) | Optional native discovery; no adapter or key requirement in this package. |
| Reviewed ML/NLP publications | [OpenReview](https://docs.openreview.net/getting-started/using-the-api), [ACL Anthology](https://aclanthology.org/), [PMLR](https://proceedings.mlr.press/), [NeurIPS](https://papers.nips.cc/) | Native tools for published text, reviews and decisions; submission, acceptance and publication are separate states. |
| CS bibliography and systems research | [DBLP](https://dblp.org/faq/How%2Bto%2Buse%2Bthe%2Bdblp%2Bsearch%2BAPI.html), [ACM](https://dl.acm.org/), [USENIX](https://www.usenix.org/publications/proceedings) | Resolve the actual paper and requested version. Bibliographic inclusion is not substantive verification. |
| Software behavior | Official versioned docs, specification, source/changelog | Prefer the requested release and section. A research paper does not establish current API behavior. |
| Historical web page | [Wayback availability API](https://archive.org/help/wayback_api.php) | Native tools for a known URL and dated capture; archive.org is separate from arxiv.org. |

## Original AI reports

Follow the official organisation to the report, checkpoint and eval configuration:
[DeepSeek](https://github.com/deepseek-ai), [MoonshotAI/Kimi](https://github.com/MoonshotAI),
[Qwen](https://github.com/QwenLM). Pin a commit/model revision when it changes the claim.
Developer-reported benchmarks do not by themselves establish independent replication or universal
superiority. A linked journal DOI may refer to a different revision from the original report.

## Read exactly what is needed

- `resolve` checks source identity, version and available notice fields. Crossref/Europe PMC flags
  may be incomplete; `none-in-record` is not a clean bill. arXiv keyword notices are candidates to
  verify, not an authoritative retraction registry. Follow the notice before interpreting it.
- `read` extracts eligible Europe PMC JATS or arXiv HTML sections/tables with locators. For an
  unversioned arXiv ID it first resolves and pins the current version. Old-style IDs and reports
  without HTML still need the host's PDF/browser tools; a failed fetch must remain a visible gap.
- Section filtering accepts an exact locator or title substring. Inspect `available_sections`
  when a heading differs. `truncated` and `sections_omitted` disclose excerpt cuts;
  `catalog_truncated` separately marks an abbreviated heading list. Fetch a
  narrower section rather than treating the first excerpt as the whole paper.
- For DOI/PMID text, use the resolved PMCID/arXiv identifier if present. The helper does not bypass
  publisher restrictions or automatically follow arbitrary metadata URLs.
  For a biomedical DOI without a PMCID, search Europe PMC with `DOI:the-resolved-doi` and verify
  the returned identity; do not guess a PMCID from memory.
- Tables, abstracts and methods have different roles: retain units, denominators, population,
  comparator, time window and uncertainty when reporting an effect. Never subtract unlike outcomes
  into an invented net benefit. Do not infer no independent evidence anywhere from a failed search.

## Access constraints

The helper needs Python 3.10+ and its standard library. Core sources need no registration.
Requests have size/time limits, at most three GET attempts, conservative serial provider gates and
an arXiv interval of at least 3.1 seconds held through retrieval. These are local client limits,
not new claims about provider quotas; other clients still share upstream limits.
Nonsecret request timestamps use a private per-user directory under the host's platform temp
directory, which remains writable in common agent sandboxes. Clients with different temp roots
have separate gates; do not assume coordination across different hosts or sandbox temp roots.

[arXiv API terms](https://info.arxiv.org/help/api/tou.html) require one connection and no more than
one request per three seconds. [PMC automated content rules](https://pmc.ncbi.nlm.nih.gov/tools/oai/)
restrict retrieval interfaces and reuse by article rights; the old
[PMC OA service closed in August 2026](https://pmc.ncbi.nlm.nih.gov/tools/oa-service/).
Europe PMC's OA XML service is a distinct documented route; unavailable text is not an empty success.

[Google Scholar](https://scholar.google.com/intl/en/scholar/help.html) is optional discovery subject
to robots.txt; no bulk-access or CAPTCHA bypass client is provided. Free reading, automated access
and permission to redistribute a text are separate questions.
