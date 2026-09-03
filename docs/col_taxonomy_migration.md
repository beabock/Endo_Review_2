# Migrating taxonomic resolution to the Catalogue of Life

Status 2026-09-03. The loader in `taxa_synonym_resolution.py` now supports a `col_dwca`
profile (tested on synthetic data). This note is (1) what COL actually gives us and
whether the loader's column names are right, (2) new fields worth using, (3) the
verification + run plan.

Decision (Bea, 2026-09-03): switch fully to COL. **No** GBIF-2023-vs-COL sensitivity
comparison — COL is the current authoritative standard, we cite it and move on.

---

## 0. Download record (for the Methods / SI)

**Taxonomy reference used:** Catalogue of Life **(2026-08-26 XR)** — the Extended Release,
which GBIF now uses as its occurrence backbone.
- ChecklistBank dataset key **316165**, DOI **`10.48580/dgyy9`**
- Citation: Bánki, O., Roskov, Y., Döring, M., *et al.* (2026). *Catalogue of Life
  (2026-08-26 XR).* Catalogue of Life Foundation, Amsterdam. https://doi.org/10.48580/dgyy9
- Downloaded 2026-09-03 by B. Bock, two kingdom-scoped DwC-A exports from ChecklistBank:

| kingdom | job key | zip | `Taxon.tsv` rows |
|---|---|---|---|
| Fungi | `a7847b0a-a6ab-4a00-862b-d04eee6da3ba` | 37.0 MB | 955,107 |
| Plantae | `c80a81c3-5f3e-4707-a806-70e821c54193` | 122.4 MB | 1,927,747 |

- Export parameters (both): `format=dwca, extended=true, classification=true,
  synonyms=true, bareNames=false, tabFormat=tsv, taxGroups=true`, minimum rank = species.
- Archive contents: `Taxon.tsv` (core, 34 DwC-prefixed columns) + `Distribution.tsv`,
  `SpeciesProfile.tsv`, `VernacularName.tsv`, `MeasurementOrFact.tsv`, `Multimedia.tsv`
  extensions + `eml.xml`, `meta.xml`.
- Local: `data/col26_8_XR_fungi/`, `data/cols26_8_XR_plantae/` (gitignored).

## 1. What COL is, and which download to get

- A new COL **base** release each month; the **Extended Release (XR)** adds ~62k
  programmatically-integrated sources on top. Pin the edition (done: 2026-08-26 XR) and
  cite the DOI — just as frozen as "GBIF Backbone 2023", but current.
- **DwC-A format, not ColDP.** DwC-A flattens everything into one `Taxon.tsv` core +
  extension files, which is what the loader expects. Partial downloads by taxon are
  allowed — Fungi and Plantae separately, then concatenate the `Taxon.tsv` files keeping
  one header.

## 2. Column names — VERIFIED against COL26.8 XR (2026-09-03)

The real `Taxon.tsv` header (from `meta.xml`) is 34 columns, **all prefixed**
(`dwc:` / `col:` / `dcterms:` / `clb:`):

```
dwc:taxonID  dwc:parentNameUsageID  dwc:acceptedNameUsageID  dwc:originalNameUsageID
dwc:scientificNameID  dwc:datasetID  dwc:taxonomicStatus  dwc:taxonRank
dwc:scientificName  dwc:scientificNameAuthorship  col:notho  dwc:genericName
dwc:infragenericEpithet  dwc:specificEpithet  dwc:infraspecificEpithet  dwc:cultivarEpithet
dwc:nameAccordingTo  dwc:namePublishedIn  dwc:nomenclaturalCode  dwc:nomenclaturalStatus
dwc:kingdom  dwc:phylum  dwc:class  dwc:order  dwc:superfamily  dwc:family  dwc:subfamily
dwc:tribe  dwc:subtribe  dwc:genus  dwc:subgenus  dwc:taxonRemarks  dcterms:references
clb:merged
```

Loader status (`_fields_col_dwca`, reconciled + tested on the full Fungi file):
- reads all the `dwc:`-prefixed names ✓
- `dwc:scientificName` carries authorship → canonical is rebuilt from
  `genericName`+`specificEpithet`(+`infraspecificEpithet`) for species ranks, else
  authorship is stripped ✓
- **no year column** — `described_year` is parsed from `dwc:namePublishedIn`
  (`"... Mycologia 106(6): 1091 (2014)."`) with an authorship-string fallback ✓
- higher-classification columns (`kingdom`…`genus`) are **often blank on species rows**
  (only kingdom + genus reliably filled); the parent-chain backfill covers the gap ✓
- `taxonomicStatus` seen: `accepted`, `provisionally accepted`, `synonym`,
  `ambiguous synonym` (and `misapplied`, which is excluded) ✓

## 2b. Original column-name notes (superseded by §2)

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

**DONE (branch `nph-col-taxonomy`):** the loader now carries the accepted name's
`namePublishedInYear` (with a fallback to the year inside `scientificNameAuthorship`)
and `nomenclaturalStatus` through to `Ollama_cleaned_synresolved.csv` as
`fungal_taxon_described_year` / `fungal_taxon_nom_status` /
`plant_host_described_year` / `plant_host_nom_status`. Zero cost to the resolution
logic; blank for GBIF-backbone runs. Tested on a synthetic *Xylona heveae*
(Xylonomycetes, 2012) record — resolves and carries the year.
(`nom_status` currently reflects the *accepted* name's status only; flagging a raw
input string that is itself a `nom. nud.` would need the synonym map to carry it —
not built, low value.)

## 4. What Bea needs to do

### Step 0 — DONE (2026-09-03): downloaded COL26.8 XR Fungi + Plantae (see §0).

### Step 1 — concatenate the two Taxon.tsv files

```bash
cd "C:/Users/beabo/NAU/Endo-Review/Endo_Review_Ollama"
mkdir -p data/Reference_datasets/col_xr
cp data/col26_8_XR_fungi/meta.xml data/Reference_datasets/col_xr/meta.xml
cat data/col26_8_XR_fungi/Taxon.tsv                > data/Reference_datasets/col_xr/Taxon.tsv
tail -n +2 data/cols26_8_XR_plantae/Taxon.tsv     >> data/Reference_datasets/col_xr/Taxon.tsv
grep -c "" data/Reference_datasets/col_xr/Taxon.tsv   # expect ~2,882,853
# also keep the Distribution extensions for the possible geographic check:
cat data/col26_8_XR_fungi/Distribution.tsv            > data/Reference_datasets/col_xr/Distribution.tsv
tail -n +2 data/cols26_8_XR_plantae/Distribution.tsv >> data/Reference_datasets/col_xr/Distribution.tsv
```

### Step 2 — smoke test

The combined index is ~2.9M rows. Building it takes a couple of minutes and a few GB of
RAM the first time (then it's cached). **Better to run this on Monsoon than your laptop.**

```bash
python scripts/02_taxa_resolution/taxa_synonym_resolution.py \
  --input-csv data/Ollama_cleaned.csv \
  --taxon-tsv data/Reference_datasets/col_xr/Taxon.tsv \
  --taxonomy-cache results/logs/col_xr_index.pkl \
  --max-rows 500
head -3 data/Ollama_cleaned_synresolved.csv | tr ',' '\n' | grep -n year   # columns exist?
grep -c "" results/manual_validation/taxa_unresolved_review.csv            # unresolved count
```
Check: prints `taxonomy source: col_dwca`; `fungal_taxon_described_year` populated for
resolved fungi; unresolved count roughly in line with the old GBIF-backbone run
(~13.5k over the full corpus, so ~200–400 in a 500-row sample).

### Step 3 — full run

Folds into the big post-Task-1 Monsoon pipeline regeneration. The sbatch
(`run_taxa_synonym_resolution.sbatch`) already defaults `TAXON_TSV` to
`data/Reference_datasets/col_xr/Taxon.tsv` and `TAXONOMY_SOURCE=auto`.

### (old, more detailed download walkthrough kept below for reference)

### Step 1 — download the COL Extended Release DwC-A

1. Go to <https://www.checklistbank.org> and **sign in with your GBIF account** (top right).
2. Left menu → **Datasets**. In the search box type `COL` and open the entry titled
   **"Catalogue of Life"** (the project, key `3`). On its page, open the **Releases** tab.
3. Find the newest **Extended Release** — the alias looks like `COL26.8 XR` (the plain
   `COL26.8` without "XR" is the smaller Base Release; we want **XR**). Click it.
   **Write down the exact version + DOI** shown on that page — that's what goes in Methods.
4. On the release page → **Download** (or the ⋯ menu) → choose **Darwin Core Archive**
   as the format. If it offers a taxon filter, enter **Fungi**, download, then repeat for
   **Plantae**. (If there's no filter, download the whole XR DwC-A — bigger but fine.)
   These come as `.zip` files, each containing `Taxon.tsv`, `meta.xml`, and extension
   `.tsv` files.
5. Put the unzipped result at `data/Reference_datasets/col_xr/`. If you downloaded Fungi
   and Plantae separately:
   ```bash
   mkdir -p data/Reference_datasets/col_xr
   # unzip both zips into two temp folders, then:
   cat fungi/Taxon.tsv > data/Reference_datasets/col_xr/Taxon.tsv
   tail -n +2 plantae/Taxon.tsv >> data/Reference_datasets/col_xr/Taxon.tsv   # skip the 2nd header
   cp fungi/meta.xml data/Reference_datasets/col_xr/meta.xml
   ```

### Step 2 — send me the real column names

```bash
head -1 data/Reference_datasets/col_xr/Taxon.tsv | tr '\t' '\n' | nl
grep -c "" data/Reference_datasets/col_xr/Taxon.tsv
cat data/Reference_datasets/col_xr/meta.xml
```
Paste all three outputs. I reconcile `_fields_col_dwca` against the actual headers
(DwC-A exports sometimes prefix columns with `dwc:` / `col:`, or split the archive
differently — the `meta.xml` is the authoritative field map).

### Step 3 — smoke test (I'll confirm the exact command after step 2)

```bash
python scripts/02_taxa_resolution/taxa_synonym_resolution.py \
  --taxon-tsv data/Reference_datasets/col_xr/Taxon.tsv --max-rows 300
head -3 data/Ollama_cleaned_synresolved.csv
```
Check: prints `taxonomy source: col_dwca`; `*_described_year` columns are populated for
resolved fungi; the unresolved count isn't wildly higher than before.

### Step 4 — full run

Folds into the big post-Task-1 Monsoon pipeline regeneration (with `--taxonomy-source`
defaulting to `auto`, or explicit `col_dwca`).

### Methods text
"...names were resolved against the Catalogue of Life Extended Release (COL26.x,
DOI 10.xxxxx/xxxxx), the taxonomic reference now used by GBIF for organising occurrence
records."

## Sources
- COL release COL26.8: https://api.checklistbank.org/dataset/316115 (DOI 10.48580/dgywk)
- COL downloads: https://www.catalogueoflife.org/data/download
- GBIF → COL backbone migration: https://data-blog.gbif.org/post/catalogue-of-life-taxonomic-backbone/
