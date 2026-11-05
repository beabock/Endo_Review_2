# Methods draft — literature search & corpus assembly

Drafting text for the resubmission. Numbers are from the 2026-09-02 corpus rebuild
(`combine_dedupe_abstracts.R`, `results/outputs/dedup_stage_counts.csv`). Prose is written
to drop into the manuscript Methods; the verbatim strings and the stage table go in the SI.
Square-bracketed notes are for us, not the manuscript.

---

## Methods — "Literature search" (main text)

We searched Web of Science Core Collection, Scopus, and PubMed on 14 August 2025 for
primary research reporting fungal endophytes of photosynthetic hosts. The search paired a
fungal-endophyte concept block with a host concept block (full strings in Table S1). The
endophyte block used exact phrases rather than a truncated `endophyt*` wildcard
("fungal endophyte", "endophytic fungi", "dark septate endophyte", "seed-borne fungi",
etc.) to keep precision high and exclude bacterial-endophyte and non-fungal uses of the
term. The host block covered vascular plants, bryophytes, pteridophytes, algae, and
photosynthetic-symbiont systems including lichens. Results were restricted to
journal articles (including the "article; proceedings paper", "article; early access", and
"article; book chapter" document types) and to English-language records; we return to the
language restriction in the Discussion. No lower date bound was set; the earliest record
retained is from 1926.

The three exports were combined (Web of Science *n* = 14,855; Scopus *n* = 15,426; PubMed
*n* = 9,141) and deduplicated in four stages, preferring the Web of Science record where a
paper appeared in more than one database and, within a database, the copy with the longest
abstract: (i) exact match on the normalised DOI (lower-cased, `doi.org/` prefix and
trailing punctuation removed); (ii) exact match on normalised abstract text (lower-cased,
whitespace collapsed, punctuation removed); (iii) removal of records whose document type
was not an article variant; (iv) exact match on normalised title (titles of at least 15
characters). Records without an abstract were removed before deduplication. Three records
whose year field contained a volume number were set to missing year. This yielded a corpus
of **21,414 records** (19,586 with a DOI), spanning 1926–2025, that entered the extraction
pipeline. Per-stage counts are in Table S2.

[We-note: stage (iii) removed 0 records this run because the Web of Science and Scopus web
exports were already limited to article types at download; it is retained as an explicit,
reproducible filter. Say this in the SI, not the main text.]

## Methods — corpus scope (main text, ~1 short paragraph)

Our corpus is the body of research that explicitly frames its subject in fungal-endophyte
terms. Fungi that can occupy plant tissue asymptomatically but are typically studied and
published under other framings — arbuscular and ectomycorrhizal symbioses, plant
pathology, or bulk plant-microbiome surveys — are therefore largely outside it by design.
This is a deliberate scoping choice: our aim is to map the geographic, taxonomic, and
methodological structure of *endophyte research as a field*, and the biases that structure
imposes on what is known, not to enumerate every fungus that is ever endophytic. Where the
distinction matters for interpretation — for example in the functional-guild analysis
(Section X) — we address it directly.

[We-note: this paragraph is the honest answer to Referee 2's "endophytes are frequently
classified as mycorrhizal / other groups" and Referee 3's "relies on the spread and
interpretation of the term endophyte". It concedes the point and reframes it as scope, not
error. Pair it with the guild-circularity fix (independent validation, Task 2).]

## Discussion — language limitation (fold into existing limitations text)

The search was restricted to English-language records. Because publication language
correlates with the geography of research effort, this restriction is expected to
compound rather than offset the geographic biases we report: literature from countries
where endophyte research is more often published in other languages is under-represented
here, so our estimates of geographic unevenness are conservative in that direction and
inflated in others (e.g. relative to regions whose work appears predominantly in
English). [cite the ~X% non-English figure once we have it from the Q4 ground-truth field.]

---

## Table S1 — search strings (verbatim)

**Concept and platform-independent form** (as designed; the same logic was entered in
each database's advanced search, adjusted only for that platform's phrase and wildcard
syntax):

```
("fungal endophyte" OR "fungal endophytes" OR "endophytic fungus" OR "endophytic fungi" OR
 "latent fungus" OR "latent fungi" OR "systemic fungus" OR "systemic fungi" OR
 "internal fungi" OR "resident fungi" OR "seed-borne fungi" OR "seed-transmitted fungi" OR
 "dark septate endophyte" OR "dark septate fungi" OR "DSE fungi")
AND
(plant* OR moss* OR bryophyte* OR liverwort* OR hornwort* OR fern* OR lycophyte* OR
 pteridophyte* OR tree* OR shrub* OR grass* OR graminoid* OR herb* OR crop* OR
 seedling* OR sapling* OR seed* OR root* OR leaf* OR foliage OR shoot* OR stem* OR
 twig* OR rhizome* OR thallus OR frond* OR algae OR "green alga*" OR macroalga* OR
 cyanobacteria OR cyanobiont* OR photobiont* OR lichen*)
```

[TODO — paste the exact platform-formatted strings actually run in each of Web of Science
Advanced Search, Scopus Advanced Search, and PubMed, with the field tags used (TS= / TITLE-
ABS-KEY() / [tiab] etc.) and the date/document-type limits as applied in each interface.
`data/Abstracts/All_abstracts_8-14-25/search_string.txt` holds the WoS/Scopus logic;
the PubMed Phase 2 result is `abstract-endophyteA-set.txt`.]

## Table S2 — deduplication stages

| Stage | Records in | Records out | Removed | Basis |
|---|---:|---:|---:|---|
| Combined (with abstract) | — | 39,114 | — | WoS 14,855 + Scopus 15,426 + PubMed 9,141, minus records lacking an abstract |
| 1. DOI | 39,114 | 22,212 | 16,902 | exact match on normalised DOI (36,772 records had a DOI; 2,342 did not) |
| 2. Abstract text | 22,212 | 21,982 | 230 | exact match on normalised abstract (62 removed had a DOI, 168 did not) |
| 3. Document type | 21,982 | 21,982 | 0 | non-article document types (0 this run; WoS/Scopus pre-filtered at download) |
| 4. Title | 21,982 | 21,414 | 568 | exact match on normalised title (≥ 15 characters) |
| **Final corpus** | | **21,414** | | 19,586 with a DOI, 1,828 without; years 1926–2025 |

[Regenerate this table from `results/outputs/dedup_stage_counts.csv` if the corpus is
rebuilt.]

---

## Checklist — what still has to happen before this is submission-ready

- [ ] Paste the three exact platform-formatted strings into Table S1 (Bea has the search
      history / can re-open the saved searches).
- [ ] Fill the non-English `%` in the language-limitation paragraph from the Task 2 Q4 field.
- [ ] Cross-check the final *n* against whatever the analysis scripts report after the
      corpus rebuild propagates (currently the pipeline still points at the old file).
- [ ] Decide whether to extend the search to the current year before final submission
      (mechanical; shifts every number; do it last).
- [ ] Reconcile `docs/METHODS.md` (old repo) — it still says the search date was 31 July
      2025 (the planning date; the search ran 14 August 2025).
