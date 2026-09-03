# Migrating taxonomic resolution to the Catalogue of Life

Status 2026-09-03. The loader in `taxa_synonym_resolution.py` now supports a `col_dwca`
profile (tested on synthetic data). This note is (1) what COL actually gives us and
whether the loader's column names are right, (2) new fields worth using, (3) the
verification + run plan.

Decision (Bea, 2026-09-03): switch fully to COL. **No** GBIF-2023-vs-COL sensitivity
comparison — COL is the current authoritative standard, we cite it and move on.

---

## 1. What COL is, and which download to get

- **Current release: COL26.8** (2026-08-20), ChecklistBank dataset key `316115`, DOI
  `10.48580/dgywk`. A new base release each month; the **Extended Release (XR)** adds
  ~62k programmatically-integrated sources on top and is what GBIF.org now uses as its
  occurrence backbone.
- Pin one edition (whatever's current when we run — e.g. **COL26.8 XR**) and cite it in
  Methods with its DOI. Just as frozen as "GBIF Backbone 2023", but current.
- **Download the DwC-A format, not ColDP.** COL's native format (ColDP) splits names and
  usages across several files; the DwC-A export flattens everything into one `Taxon.tsv`
  core + extension files, which is what the loader expects. On ChecklistBank:
  Datasets → COL Releases → the XR edition → Download → **Darwin Core Archive**. Partial
  downloads by taxon are allowed — grab `Fungi` and `Plantae` separately (smaller), then
  concatenate the two `Taxon.tsv` files keeping one header.

## 2. Column names — what the loader assumes vs what COL emits

COL fungal/plant names are under the **botanical code (ICN)** — the API record for
*Colletotrichum* shows `code: "botanical"` on every classification level.

The COL DwC-A `Taxon.tsv` core columns the loader reads (`_fields_col_dwca`):

| loader expects | COL DwC-A column | confidence |
|---|---|---|
| `taxonID` | `dwc:taxonID` (short code, e.g. `3SC5`) | high |
| `parentNameUsageID` | `dwc:parentNameUsageID` | high |
| `acceptedNameUsageID` | `dwc:acceptedNameUsageID` (synonyms only) | high |
| `scientificName` | `dwc:scientificName` (with authorship) | high |
| `scientificNameAuthorship` | `dwc:scientificNameAuthorship` | high |
| `genericName` / `specificEpithet` / `infraspecificEpithet` | same DwC terms | high |
| `taxonRank` | `dwc:taxonRank` (lowercase) | high |
| `taxonomicStatus` | `dwc:taxonomicStatus` — `accepted` / `provisionally accepted` / `synonym` / `ambiguous synonym` / `misapplied` | high |
| `kingdom`/`phylum`/`class`/`order`/`family`/`genus` | denormalised higher-classification columns | **VERIFY** — present in the DwC-A Taxon core, but may be sparse for non-accepted rows; the loader's parent-chain backfill covers gaps |

**One thing to confirm on a real file:** whether the higher-classification columns
(`kingdom`..`genus`) are populated on the DwC-A `Taxon.tsv`, or only reachable via
`parentNameUsageID`. The loader handles both (it backfills phylum/class/order/family from
the parent chain), but knowing which saves a debugging round.

## 3. New fields COL has that the GBIF backbone did not — and whether they help us

| COL field / extension | useful? |
|---|---|
| **`namePublishedInYear`** (year the name was described) | **YES — worth adding.** Directly supports Referee 1's "endophyte research drives fungal discovery" point: we can report the description-year distribution of the fungal taxa recovered as endophytes (e.g. "% described post-2000"), and cross-tab by region/host to show under-studied regions yield more recently-described taxa. This is a real analysis, not just QC. |
| **`nomenclaturalStatus`** (`nom. nud.`, `nom. inval.`, `nom. illeg.`) | **Minor yes.** Flag corpus names that are not validly published — a concrete data-quality point for Referee 3. |
| `Distribution.tsv` extension (native/introduced range, `countryCode`, `establishmentMeans`) | **Maybe.** An independent signal of where a fungus is *known to occur* vs where it was *studied* — could sharpen the geographic-bias story. But fungal distribution coverage in COL is patchy. Assess coverage after the download before committing. |
| `scientificNameID` (Index Fungorum / IPNI LSIDs) | provenance only; nice for the SI, not analysis. |
| `SpeciesProfile.tsv` (`isMarine` / `isFreshwater` / `isTerrestrial`) | low value here. |
| `group` (coarse tag, e.g. "ascomycetes") | redundant with phylum/class. |
| `VernacularName`, `Multimedia`, `TypeMaterial` | not relevant. |

**Proposed loader change:** carry `namePublishedInYear` (and `nomenclaturalStatus`) through
to `Ollama_cleaned_synresolved.csv` as `fungal_taxon_described_year` /
`plant_host_described_year` (+ a `*_nom_status` flag). Zero cost to the resolution logic;
enables the discovery-driver analysis. GBIF-backbone runs just leave these blank.

## 4. Verification + run plan

1. **Bea downloads** the COL26.x XR DwC-A (Fungi + Plantae partials) to
   `data/Reference_datasets/col_xr/Taxon.tsv`.
2. **Check the real header** and paste it here:
   ```bash
   head -1 data/Reference_datasets/col_xr/Taxon.tsv | tr '\t' '\n' | nl
   wc -l data/Reference_datasets/col_xr/Taxon.tsv
   ```
   I reconcile `_fields_col_dwca` against the actual column names (adjust any that differ
   — DwC-A exports sometimes prefix with `dwc:` or use `col:` for the ID).
3. **Smoke test** (200 rows) locally or on Monsoon:
   ```bash
   python scripts/02_taxa_resolution/taxa_synonym_resolution.py \
     --taxon-tsv data/Reference_datasets/col_xr/Taxon.tsv --max-rows 200
   ```
   Confirm: "taxonomy source: col_dwca" prints, resolved names look right, the
   unresolved list isn't suddenly huge.
4. If I add the `namePublishedInYear` passthrough, re-smoke-test.
5. **Full run on Monsoon** — folds into the big post-Task-1 pipeline regeneration.
6. **Methods text**: "...resolved against the Catalogue of Life Extended Release
   (COL26.x, DOI ...), the taxonomic reference now used by GBIF."

## Sources
- COL release COL26.8: https://api.checklistbank.org/dataset/316115 (DOI 10.48580/dgywk)
- COL downloads: https://www.catalogueoflife.org/data/download
- GBIF → COL backbone migration: https://data-blog.gbif.org/post/catalogue-of-life-taxonomic-backbone/
