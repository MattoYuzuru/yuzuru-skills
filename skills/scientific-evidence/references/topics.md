# Topic routing beyond computing

Checked on 2026-10-19. Treat these topic groups as product hypotheses for useful everyday
questions; no audience popularity ranking was measured. Start with the row matching the claim,
then retrieve the specific assessment, review, study, or dataset that can answer it.

| Topic group and example question | Evidence to seek | Starting points |
|---|---|---|
| Sleep, nutrition, exercise: does caffeine timing affect sleep, or training affect strength? | Relevant systematic review, then controlled studies matching age, dose, duration, and outcome. | PubMed, Europe PMC, Cochrane. |
| Psychology and learning: does retrieval practice improve retained learning, or a school intervention improve wellbeing? | Education/psychology reviews, preregistered experiments, replications; distinguish test scores from long-term learning. | ERIC, Campbell; PsyArXiv for discovery of newer work. |
| Social, economic, and media questions: do employment programmes or media-literacy interventions change outcomes? | Campbell synthesis and underlying evaluations for effects; official indicators for descriptive country/time comparisons. | Campbell; World Bank Indicators for statistics; relevant OSF community preprints for discovery. |
| Climate and energy: what supports a warming claim, or what assumptions drive an energy projection? | IPCC assessment with its cited literature and uncertainty; IEA historical series or explicitly identified scenarios. | IPCC reports; IEA data and reports. |
| Biodiversity and environment: what drives biodiversity loss or supports a conservation intervention? | IPBES assessment and underlying studies; match ecosystem, region, species, and measurement method. | IPBES assessments; Campbell for intervention syntheses when covered. |
| Space and astronomy: what observation supports a discovery, or where are a mission's measurements? | Original paper plus mission/instrument documentation and the relevant archive product. | NASA's science-data entry points; follow the selected mission archive and paper links. |

## Source access and scope

- **PubMed / Europe PMC:** [PubMed](https://pubmed.ncbi.nlm.nih.gov/about/) is a citation/abstract
  index; a full-text link is a separate access level. [Europe PMC REST](https://europepmc.org/RestfulWebService)
  provides metadata/abstracts and eligible OA full-text XML without a key. Use the core source
  guidance for retrieval. [NCBI E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25497/) allows
  3 requests/second without a key, 10/second with a free optional key; valid `tool`/`email` identity
  is recommended. No numeric Europe PMC service quota was confirmed in the checked documentation.
- **Cochrane:** [abstracts and plain-language summaries](https://help.cochrane.org/kb/article/27-how-can-i-access-cochrane-evidence/)
  are free; full reviews can require institutional, regional, or individual access. Check the
  actual review version, search date, certainty, and availability before summarizing it.
- **ERIC:** [public education search](https://eric.ed.gov/) distinguishes peer-reviewed records
  and full text available on ERIC. Index inclusion alone does not establish either property.
  The [metadata API documentation](https://eric.ed.gov/?api) timed out during this check; current
  authentication and numeric limits were not verified. Use web discovery and verify the API
  contract before adding automation; follow record links for accessible full text.
- **Campbell:** [the evidence catalogue](https://www.campbellcollaboration.org/evidence/) covers
  social-policy reviews, protocols, and evidence-and-gap maps. Follow each record's journal link
  to the open-access review; the [journal](https://journals.sagepub.com/home/cama) was transitioning
  from Wiley to Sage at the check date. A protocol or gap map does not establish an effect.
- **OSF / PsyArXiv:** [community preprints](https://help.osf.io/article/691-preprint-moderation-policies)
  are discovery leads. [PsyArXiv moderation is not peer review](https://blog.psyarxiv.com/about-psyarxiv/).
  Check version, withdrawal, linked publication, preregistration, and available data. The
  [OSF generalist server's new submissions remain suspended](https://www.cos.io/blog/update-on-future-of-osf-preprints);
  this decision does not suspend PsyArXiv or other community servers. No API quota is asserted here.
- **IPCC:** [official reports](https://www.ipcc.ch/reports/) provide assessment chapters, summaries,
  and references. Retrieve the appropriate chapter and its errata; preserve calibrated confidence,
  likelihood, scenario, region, and time horizon. Public reading does not grant unrestricted reuse.
- **IEA:** [data and statistics](https://www.iea.org/data-and-statistics) mix free and paid products;
  some report downloads use a free account. Check the individual product's access and licence.
  Distinguish observed historical data, model estimates, and conditional scenarios.
- **IPBES:** [official assessments](https://www.ipbes.net/assessment-reports) cover biodiversity,
  ecosystem services, and related policy evidence. Public report materials include full chapters
  and summaries; select the final version and its references. Direct site access returned 403
  during this check; report availability was confirmed through official indexed pages. No
  general-purpose public literature API or quota was verified.
- **NASA:** [science-data entry points](https://science.nasa.gov/learn/entry-points-to-nasa-data/)
  route to astrophysics, planetary, heliophysics, and Earth archives. Access rules are specific
  to the archive/product: for example, [Earthdata downloads can require a free login](https://www.earthdata.nasa.gov/s3fs-public/2024-08/Getting_Started_with_Earthdata_Search.pdf).
  Verify the selected archive's API, permissions, embargo, version, and quotas separately.
- **World Bank:** the [V2 Indicators API](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation)
  requires no API key or other authentication. Retrieve indicator definitions, units, source,
  geography, observation dates, revisions, and missing values with the series. No numeric rate
  quota was confirmed in that documentation; paginate and keep reads bounded.

## Interpretation checks

- Match age group, baseline condition, country, setting, and follow-up to the requested population.
  An adult/student convenience sample does not automatically represent adolescents or all people.
- Separate association, experimental effect, natural experiment, model projection, and expert
  assessment. Record confounders, selection, comparison group, effect size, and uncertainty.
- Check review search dates and study quality; a meta-analysis cannot repair biased inputs.
  Preserve null results and harms as carefully as positive results.
- A dataset, preregistration, protocol, press release, or preprint is a different evidence type
  from a completed peer-reviewed study. Identify that type and the text actually retrieved.
- Use official summaries to locate evidence, then cite the relevant chapter/table, original study,
  or documented data product. A single chart or dataset does not establish a causal explanation.
