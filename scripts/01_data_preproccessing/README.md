# Stage 01: Data Preprocessing

Manual steps for acquiring and consolidating abstracts. These scripts are **not** run by the automated pipeline - they were run once to build the initial dataset.

## Scripts

- `api_pull_abstracts.R` - Pulls abstracts from PubMed, Scopus, and Web of Science. Requires API credentials.
- `Combo_abstracts_pull2.R` - Combines and deduplicates the three source exports.
- `01_csv_cleanup.py` - Fixes malformed rows in the raw Ollama extraction CSV.
- `merge_final_data.py` - Merges abstract metadata with Ollama extraction output.
- `monsoon_extract.py` - Submits extraction jobs to the Monsoon HPC cluster.
- `download_pdfs.py` - Downloads PDFs for full-text extraction.

## Dependencies

- R packages: `rentrez`, `dplyr`, `readr`
- Python: standard library only
- API keys required for Scopus and Web of Science
