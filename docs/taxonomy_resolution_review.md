# Taxonomic name resolution — review for Referee 3

Referee 3 (round 2) asked two things about `taxa_synonym_resolution.py`:
1. How were cases handled where historical name usage and current taxonomic concepts
   could not be reconciled by simple synonym matching against the GBIF backbone?
2. Why the 2023 GBIF dataset — was it the most recent available at the time?

Review done 2026-09-03. Nothing changed in the code yet; this is the findings + a
recommendation + draft response text.

---

## 1. What the script actually does

`resolve_token()` tries, in order, and stops at the first hit:

| method | what it matches | status | conf |
|---|---|---|---|
| `exact_accepted` | normalised name == an accepted GBIF canonical name | ACCEPTED | 1.00 |
| `synonym_map` | name is a GBIF synonym → its accepted id | SYNONYM | 0.95 |
| `abbreviation_context_first` | `A. niger` → expanded using genera seen in the same paper first, then globally; ambiguous expansions flagged | ACCEPTED | 0.75 / 0.55 |
| `genus_exact` | binomial fails but the genus alone is an accepted name | ACCEPTED (genus rank) | 0.70 |
| `no_match` | none of the above | UNRESOLVED | 0.00 |

Plus: an alias table (`utils/taxon_mapping.py`) rewrites known problem tokens before
matching; NA-token and non-taxon-phrase filters drop obvious junk ("various fungi",
"powdery mildew"); rank is restricted to `ALLOWED_TAXON_RANKS`; higher-taxon protection
keeps e.g. phylum names from being demoted. Every UNRESOLVED or ambiguous token is
written to `results/manual_validation/taxa_unresolved_review.csv` for human review.

### The concept-drift answer

Simple synonym matching (`synonym_map`) handles 1:1 objective synonyms. It does **not**
handle genus splits (one old name → several current taxa) or circumscription changes.
The script's mitigation for those is the **`genus_exact` fallback**: when a binomial
can't be placed but its genus is unambiguous, the record is retained at genus rank. Since
the headline taxonomic analyses are at **family and order** level (Fig. 3, understudied-
lineage counts), a name resolved only to genus still lands in the right family/order in
almost all cases. Names that can't be placed at any rank are excluded and listed in the
review file.

### What the unresolved list looks like (from the last run)

`taxa_unresolved_review.csv`: **13,526 distinct tokens**, of which 13,133 `no_match` and
393 ambiguous abbreviations. Spot-checking, the overwhelming majority are **not**
taxonomic-concept failures — they are LLM extraction noise:

- fungicides / chemicals (`benomyl`), insects (`aphis gossypii`, "…is not a fungus"),
  cultivar names (`Golden Delicious`, `cv. tioga`), informal names ("powdery mildews",
  "vesicular-arbuscular mycorrhizas"), non-English ("schimmels" = Dutch for moulds),
  misspellings (`gloesporium musarum` for *Gloeosporium musarum*).
- A minority are real names the backbone missed or that need a synonym the map lacks
  (e.g. `Glomus fasciculatus` → *Funneliformis fasciculatus*) — but these are arbuscular
  mycorrhizal, and AMF are removed by `02_dataset_filtering.py` regardless.

So the pipeline is mostly **correctly rejecting junk**, not silently losing endophytes.
This is a good story for the response — but we should back it with numbers:
report the count and % of interaction tokens resolved by each method, and a
classified breakdown of the unresolved list (chemical / animal / cultivar / informal /
misspelling / genuine-taxon).

**TODO (small):** a script that reads `taxa_unresolved_review.csv` + the resolved output
and produces `results/taxonomy_analysis/resolution_method_summary.csv` and a rough
auto-classification of the unresolved tokens.

---

## 2. The 2023 GBIF backbone — and why there is no newer one

**The GBIF Backbone Taxonomy (DOI 10.15468/39omei) was last built in 2023 and will not
be rebuilt.** GBIF discontinued the backbone build in favour of the **Catalogue of Life
Extended Release (COL XR)**, which is now GBIF.org's default taxonomy for organising
occurrence records and is updated roughly monthly. The legacy backbone stays available
for backwards compatibility and its identifiers are preserved.

So Bea's choice was correct for what it was — the last stable, versioned, DOI-citable
release of that dataset — and it now has a *better* justification than "newest I could
find": it is the **final** release. But a reviewer who knows the GBIF/COL transition may
still ask why we didn't use the successor.

### Options

| | effort | strength of the response |
|---|---|---|
| **A. Keep the 2023 backbone, sharpen the justification** | ~0 | fine — "final stable release, DOI-citable, frozen for reproducibility" |
| **B. A + a COL XR sensitivity check** | moderate | strong — re-resolve the names against current COL XR (or the GBIF species-match API) and report that family/order-level counts are unchanged (or by how much) |
| **C. Switch the pipeline to COL XR** | high | not worth it — reshuffles every number, and the taxon archive schema differs from the backbone `Taxon.tsv` the script expects |

**Recommended: B.** The species-match API route is the least code: send the ~unique
resolved names (a few thousand) to `https://api.gbif.org/v1/species/match` (now backed by
COL XR) and compare accepted name + family + order to what the 2023 backbone gave. One
script, one table, and it directly answers "was this the most recent dataset available".

**TODO (moderate):** `scripts/02_taxa_resolution/col_xr_sensitivity.py` — batch the
distinct resolved fungal + plant names through the GBIF match API, join to the 2023
resolution, output `results/taxonomy_analysis/col_xr_vs_backbone_2023.csv` with a summary
(n names, % same accepted name, % same family, % same order, examples of differences).

---

## 3. Draft text

### Methods (replace the current one-liner)

> Extracted fungal and plant names were resolved to accepted taxa against the GBIF
> Backbone Taxonomy (GBIF Secretariat 2023; DOI 10.15468/39omei), the final release of
> that dataset. Resolution proceeded deterministically: exact match to an accepted
> canonical name; mapping of nomenclatural synonyms to their accepted name; expansion of
> abbreviated genus names using genera named elsewhere in the same article; and, where a
> binomial could not be placed, retention at genus rank when the genus was unambiguous.
> Names that could not be placed at any rank (predominantly non-taxonomic strings —
> fungicides, host cultivars, informal group names — rather than unreconciled taxonomy)
> were excluded and are listed in Table S<n>. Because the taxonomic analyses are
> conducted at family and order level, names resolved only to genus still contribute to
> the correct higher lineage. [If we do the sensitivity check:] Re-resolving the accepted
> names against the current Catalogue of Life Extended Release changed the family
> assignment of <x>% and the order assignment of <y>% of names (Table S<n>).

### Response to referees (Referee 3)

> *Historical vs current concepts:* our matching resolves objective synonyms but, as the
> referee notes, cannot by itself resolve genus splits or circumscription changes. We
> handle these by retaining such names at genus rank, which is sufficient for the
> family/order-level analyses we report; names not placeable at any rank were excluded
> (n = <n>, Table S<n>), and are overwhelmingly non-taxonomic extraction artefacts rather
> than genuine taxonomic ambiguity. *Dataset version:* the 2023 release is the final
> build of the GBIF Backbone Taxonomy — GBIF has since moved to the Catalogue of Life
> Extended Release. We used the last stable, DOI-citable version for reproducibility and
> [have confirmed / confirm] that resolving against the current Catalogue of Life leaves
> the lineage-level results essentially unchanged.

---

## Sources

- GBIF Backbone Taxonomy dataset page: https://www.gbif.org/dataset/d7dddbf4-2cf0-4f39-9b2a-bb099caae36c
- Migrating from the legacy backbone to Catalogue of Life Extended Release: https://data-blog.gbif.org/post/catalogue-of-life-taxonomic-backbone/
- GBIF taxonomy interpretation (techdocs): https://techdocs.gbif.org/en/data-processing/taxonomy-interpretation
