# scripts/archive/

Retired scripts kept for reference / possible future reuse. **Not run by the pipeline**
(`central_run_everything.py` only walks `03_*`, `04_analyses/`, `05_plotting/`).

## Superseded extraction / download scripts (Task 1, 2026-09-02)

Superseded scripts, kept for provenance. Not part of the active pipeline.

| file | replaced by | when / why |
|---|---|---|
| `monsoon_extract_v4.py` | `scripts/01_data_preproccessing/monsoon_extract.py` | 2026-09-02, Task 1 Phase 0b. v4 read only the first 12 PDF pages and truncated the prompt to 8,000 chars, so the "full-text" dataset was effectively an extended-abstract dataset. The rewrite does a structure-aware parse → targeted segmentation → context-sized chunks → schema-constrained JSON, with fields locked to the Task 2 ground-truth workbook. |
| `download_pdfs_v4.py` | `scripts/01_data_preproccessing/fetch_fulltext_pdfs.py` | 2026-09-02, Task 1 Phase 0a. v4 was Unpaywall-only, unvalidated, non-resumable. The replacement chains six OA resolvers, validates each download, is resumable + shardable, and has a `--dry-run` coverage report. |

See `NPH_task1_paired_validation_plan.md` (local planning doc) for the full rationale.

## Retired analyses (Tasks 3 & 4, 2026-08-27)

### `01_country_gdp_latitude_analysis.R`
Archived 2026-08-27 during the NPH-MS-2026-57711 resubmission. GDP / "Prediction 4" was
cut from the manuscript (all three referees + editor converged on this — see
`NPH_resubmission_checklist.md` item B). The script computed Pearson/Spearman correlations
of per-country study count vs `log10(GDP)` and vs latitude.

- The **latitude** analysis (still cited for the geographic-bias framing) was moved to
  `scripts/04_analyses/01_country_latitude_analysis.R`.
- The **GDP** analysis is preserved here only. To run it, first regenerate the enriched
  country table with GDP columns (the default pipeline omits them):
  `Rscript scripts/03_standardize_metadata/04_country_enrichment.R --with-gdp`
### `03b_geographic_bias_mapping_eu_grouped.R` and `biome_plots_eu_grouped.R`
Archived 2026-08-27. These collapsed the 27 EU member states into one "European Union"
unit - a political grouping Referee 3 flagged (`NPH_resubmission_checklist.md` item D).
Replaced by a biogeographic-realm grouping (Olson et al. 2001 / WWF):
- `scripts/04_analyses/03c_biogeographic_bias_mapping.R`
- `scripts/05_plotting/biome_plots_by_realm.R`
- `scripts/utils/biogeographic_mapping.R` + `data/Reference_datasets/country_biogeographic_realm.csv`
