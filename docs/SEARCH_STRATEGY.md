# Search strategy — fungal endophyte literature audit (NPH-MS-2026-57711)

**PI:** B. Bock, Northern Arizona University
**Brought into `Endo_Review_2` 2026-09-02** from the original project repo, and updated with
the resubmission dedup. This is the authoritative record of how the corpus was assembled.

---

## The search string (Phase 2 — current for all analyses)

The **same** boolean string was run in **Web of Science Core Collection, Scopus, and
PubMed**, reformatted only for each platform's phrase/wildcard syntax. Verbatim copy in
`data/Abstracts/All_abstracts_8-14-25/search_string.txt`; coded form in
`scripts/01_data_preproccessing/api_pull_abstracts.R` (`base_search`).

```
("fungal endophyte" OR "fungal endophytes" OR "endophytic fungus" OR "endophytic fungi" OR
 "latent fungus" OR "latent fungi" OR "systemic fungus" OR "systemic fungi" OR
 "internal fungi" OR "resident fungi" OR "seed-borne fungi" OR "seed-transmitted fungi" OR
 "dark septate endophyte" OR "dark septate fungi" OR "DSE fungi")
AND
(plant* OR moss* OR bryophyte* OR liverwort* OR hornwort* OR fern* OR lycophyte* OR
 pteridophyte* OR tree* OR shrub* OR grass* OR "graminoid*" OR herb* OR crop* OR
 seedling* OR sapling* OR seed* OR root* OR leaf* OR foliage OR shoot* OR stem* OR
 twig* OR rhizome* OR thallus OR frond* OR algae OR "green alga*" OR macroalga* OR
 cyanobacteria OR cyanobiont* OR photobiont* OR lichen*)
```

- **Concept 1 (fungal endophytes):** exact phrases only — precision over recall, excludes
  bacterial-endophyte and non-fungal "endophyte" contexts.
- **Concept 2 (hosts):** vascular plants, bryophytes, pteridophytes, algae, and
  photosynthetic-symbiont systems (lichens, cyanobionts, photobionts).
- **Document types:** journal articles (incl. proceedings papers / book chapters /
  early-access that carry the "Article" type); reviews and editorials excluded — they
  carry no primary occurrence records.
- **Language:** English (acknowledged as a bias in the manuscript).
- **Date span:** all years to the search date.
- **Search date:** searches run 2025-07-31; full-record exports downloaded 2025-08-14
  (folder `All_abstracts_8-14-25/`). *(reconcile which single date to cite in Methods.)*
- **Searcher:** B. Bock, via each platform's Advanced Search.

### ⚠️ open item — PubMed string verification
`api_pull_abstracts.R` originally carried a **different, earlier** string
(`base_search_DRAFT`: bare `endophyte*`, `symptomless/asymptomatic/quiescent fung*`, no
lichen/photobiont terms). It is unclear from the data alone whether
`pubmed_pull_8-14-25.csv` was produced with the Phase 2 string or that draft (only 48 % of
PubMed rows contain an exact endophyte phrase in title+abstract, though MeSH indexing can
explain the rest). **Action:** re-pull PubMed with the Phase 2 string (cheap, one database)
so all three sources are provably consistent, or recover the exact PubMed query used. The
script now defaults to the Phase 2 string (`pubmed_search`).

---

## Deduplication

`scripts/01_data_preproccessing/combine_dedupe_abstracts.R`. Records with no abstract are
dropped first; then, keeping the WoS > Scopus > PubMed copy (tie-broken by the longest
abstract):

1. **DOI** — normalized (case, `doi.org/` prefix, trailing punctuation) then exact match.
2. **Normalized abstract text** — lowercase, whitespace collapsed, punctuation stripped.
3. **Document-type filter** — keep any `*article*`-flavoured type + records with no type
   (PubMed, already article-limited at search).
4. **Normalized title** — same normalization; titles < 15 chars left alone.

Per-stage counts are written to `results/outputs/dedup_stage_counts.csv` (the Methods
table); the records removed at stages 2–4 are saved under `data/processed/` for audit.

### Current corpus (2026-09-02 re-run)

| stage | in | out | removed |
|---|---:|---:|---:|
| combined, usable abstract | — | 40,776 | — |
| DOI dedup | 40,776 | 23,100 | 17,676 |
| abstract-text dedup | 23,100 | 22,830 | 270 |
| document-type filter | 22,830 | 22,830 | 0 |
| title dedup | 22,830 | **22,268** | 562 |

**22,268 records** (20,411 with a DOI, 1,857 without). WoS 14,855 / Scopus 15,426 /
PubMed 10,873 before combining. Publication years 1926–2025 (3 rows had a volume number in
the year field → set to missing).

*(The pre-resubmission pipeline produced 21,891; the +377 is mostly `Article; Proceedings
Paper` / `Book Chapter` / `Early Access` types the old exact-`"Article"` filter dropped,
plus a few extra DOI-variant duplicates now collapsed.)*

Outputs (both gitignored — too large for the repo):
- `data/Abstracts/All_abstracts_deduped.csv` — full bibliographic record
- `data/Abstracts/Abstracts_for_Monsoon.csv` — 6-column slim projection for the LLM / PDF retrieval

---

## Search evolution (provenance)

| phase | date | string | use |
|---|---|---|---|
| 1 — exploratory | 2024-11-18 | `("fungal endophyte" OR … "endophytic fungus") AND plant` (WoS, Scopus) | scope check + model training data |
| 2 — comprehensive | 2025-07-31 | the string above (WoS, Scopus, PubMed) | **all current analyses** |

---

## Known limitations (carried into the manuscript)

- **English-language only** — interacts with the geographic-bias findings; stated explicitly.
- **Self-identified endophyte research** — fungi that function as endophytes but are
  published under mycorrhizal / plant-pathology / general-microbiome framings are out of
  scope by design; the study maps the *field* of endophyte research and its biases, not
  every fungus that is ever endophytic.
- **Terminology evolution** — exact-phrase matching may miss older work using other terms.
- **Gray literature** (theses, reports) excluded.

## To finalise for submission

- [ ] Resolve the PubMed-string question (re-pull, or document the exact query used).
- [ ] Reconcile the search date (2025-07-31 vs 2025-08-14) to one value in Methods.
- [ ] Paste the exact WoS- and Scopus-formatted strings into the SI.
- [ ] Add the dedup stage table (above) to Methods / SI.
- [ ] Decide whether to extend the search to the current year before final submission
      (mechanical, but reshuffles every downstream number — do it last).
