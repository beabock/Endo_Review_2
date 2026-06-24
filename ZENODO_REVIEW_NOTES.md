# Zenodo Pre-Upload Review Notes

## What I fixed (no questions needed)

1. **Critical pipeline bug**: `central_run_everything.py` referenced `ollama_cleanup.R` but the
   actual file is `02_ollama_cleanup.R` — the runner would have crashed immediately on launch.
   Fixed in both the runner and the README.

2. **Removed `__pycache__` from git**: Compiled Python bytecode (`.pyc` files) was tracked in git
   and would have gone to Zenodo. Removed from tracking and added to `.gitignore`.

3. **Removed temp debug files from git**: `temp.R` (1 line: reads an RDS) and `temp_count.R`
   (1 line: counts world countries) were tracked. Removed from tracking and added `temp*.R` to
   `.gitignore`.

4. **Removed `manuscript/.Rhistory` from git**: R session history added to `.gitignore`.

---

## Questions for you

### Q1 — README says "upcoming paper"
`README.md` line 3: *"...our upcoming paper auditing the global fungal endophyte literature."*
The manuscript appears to be at revision stage (v8, R2R). What should this say instead?
e.g.: *"...a paper auditing..."* or *"...our paper (in review at Nature Plants)..."* or
*"...our paper (Bock et al., 202X)..."*

### Q2 — Manuscript version files need git staging
Three files were deleted from the folder but not yet staged:
- `manuscript/Bock et al NP R2R.docx` (gone from disk)
- `manuscript/Bock_v6_NM.ncj.docx` (gone)
- `manuscript/Bocketal_NP_v7.docx` (gone)

And five new/moved files are untracked:
- `manuscript/Bocketal_NP_v8.docx` ← new final version
- `manuscript/Bock et al NP R2R v8.docx` ← new review response
- `manuscript/archive/Bock et al NP R2R.docx`
- `manuscript/archive/Bock_v6_NM.ncj.docx`
- `manuscript/archive/Bocketal_NP_v7.docx`

**Do you want me to stage and commit all of these** (deletions + new tracked files), or would you
prefer to keep the archive folder out of the deposit entirely and just track the v8 files?

### Q3 — Manuscript drafts in the deposit
The repo currently tracks several working-draft files:
- `manuscript/draft_manuscript.md` — an earlier draft with in-progress sections
- `manuscript/old_manuscript.md` — an older version
- `manuscript/reviews.md` — your notes on the review comments

These are useful for your own records but probably not what readers of the Zenodo deposit need.
**Keep them in the repo or remove from tracking?**

### Q4 — SLURM logs (42 `.out`/`.err` files in `results/logs/`)
These are tracked and will go to Zenodo. They document that the pipeline ran on Monsoon HPC and
show the outputs of each stage. Pros: confirms reproducibility. Cons: bulky, hard to read, and
tied to NAU HPC specifics.
**Keep them in the deposit, or add `results/logs/*.out` and `results/logs/*.err` to `.gitignore`?**

### Q5 — Placeholder email in CrossRef API call
[`scripts/03_standardize_metadata/01a_enrich_publication_year.py:53`](scripts/03_standardize_metadata/01a_enrich_publication_year.py)
uses `mailto:endo-research@example.com` in the `User-Agent` header when calling the CrossRef API.
CrossRef's polite pool works better with a real contact email.
**Should this be updated to a real email before archiving?**

### Q6 — Python `country_mapping.py` duplicate dict keys (possible data loss)
[`scripts/utils/country_mapping.py`](scripts/utils/country_mapping.py) has many biome→country
entries with duplicate keys, e.g.:
```python
"great plains": "USA",
"great plains": "CAN",   # <-- silently overwrites, only CAN is kept
"pampas": "ARG",
"pampas": "URY",
"pampas": "BRA",          # <-- only BRA is kept
```
In Python, the last duplicate wins. The R version (`country_mapping.R`) uses a `tribble` (data
frame), so duplicates work correctly there. This Python dict is part of `COUNTRY_TO_ISO` — 
**was the intent for these biomes to map to one country (the last listed), or to both/all?**
If both countries are intended, the dict needs to be restructured as a list-of-tuples or similar.
This doesn't affect already-generated results but will matter if anyone re-runs the pipeline.

### Q7 — `results/temp/` files in the deposit
Five files in `results/temp/` are tracked:
- `bryophyta_counts_by_country.csv`
- `bryophyta_zero_study_countries.csv`
- `geographic_plotting_validation.log`
- `undersampled_unique_fungi.csv`
- `undersampled_unique_plants.csv`

These are outputs from `bryophyta_check.R` and `example_searching.R`.
**Are these intermediate/exploratory files you want to keep in the deposit, or can they be removed?**

---

## Minor observations (no action needed, just FYI)

- `scripts/01_data_preproccessing/api_pull_abstracts.R` has placeholder credentials
  (`set_api_key("")`, `"YOUR_USERNAME"`) — this is correct and intentional for a public repo.
- `data/Training_labeled_abs_6.csv` contains some synthetically generated abstracts (noted in
  `old_manuscript.md`). Including it is appropriate for reproducibility.
- LLM fingerprint check: All mentions of "LLM", "AI", "Ollama", etc. in code comments are
  legitimate technical descriptions of the data extraction pipeline — nothing to remove.
- `results/taxonomy_analysis/cache/*.rds` (6 GBIF cache files) are tracked. They're large but
  useful for anyone re-running the taxonomy analysis without re-downloading GBIF.
- `scripts/04_analyses/example_searching.R` and `bryophyta_check.R` are exploratory scripts.
  They work fine but aren't called by the main pipeline runner.
