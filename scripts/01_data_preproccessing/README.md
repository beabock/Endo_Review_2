# Stage 01: data acquisition & preprocessing

Scripts for building the abstract corpus and running the LLM extraction. Most are
**manual / cluster steps** — the automated runner (`scripts/central_run_everything.py`)
picks up later, from `02_ollama_cleanup.R`.

## Corpus construction (run once, in order)

| script | what it does | where it runs |
|---|---|---|
| `api_pull_abstracts.R` | Pulls abstracts from PubMed (API) with the boolean search string. WoS and Scopus were run through their web interfaces with the same string reformatted per platform; those exports go in `data/raw/`. | local, needs API keys |
| `combine_dedupe_abstracts.R` | Combines the three source exports, normalises DOIs, deduplicates (DOI → normalized abstract → document-type filter → normalized title), and writes `data/Abstracts/All_abstracts_deduped.csv` + the slim `Abstracts_for_Monsoon.csv`. Emits a stage-count table (`results/outputs/dedup_stage_counts.csv`) and per-stage removed-record audits. | local |

## LLM extraction (Task 1 rebuild — branch `nph-task1-fulltext-revalidation`)

| script | what it does | where it runs |
|---|---|---|
| `extract_schema.py` | Single source of truth: the JSON schema for schema-constrained decoding, the controlled vocabularies, the prompt, and the map from Task 2 human-annotation labels to the same tokens. Imported by the two below. | — |
| `pdf_segment.py` | Structure-aware PDF parse (`pymupdf4llm`) → targeted section/paragraph selection → context-sized chunks. OCRs scanned PDFs (`ocrmypdf`). | Monsoon |
| `fetch_fulltext_pdfs.py` | Multi-resolver OA PDF retriever (Unpaywall → OpenAlex → Europe PMC → Semantic Scholar → CORE → publisher meta). Resumable, shardable, validated. `--dry-run` writes a coverage report. Run via `run_fetch_pdfs.sbatch` (Slurm array). | Monsoon |
| `merge_pdf_manifests.py` | Combines the per-shard manifests and regenerates the coverage report. | Monsoon |
| `monsoon_extract.py` | Per paper: segment → one schema-constrained Ollama call per chunk → union/dedup → `global_endo_extraction_v5.csv`. `--mode abstract\|fulltext`, `--model` for the bake-off. | Monsoon (GPU) |
| `run_fetch_pdfs.sbatch` | Slurm array wrapper for `fetch_fulltext_pdfs.py`. | Monsoon |

## Post-extraction

| script | what it does |
|---|---|
| `01_csv_cleanup.py` | Heals malformed rows in the raw Ollama CSV, locks the column schema. |
| `02_ollama_cleanup.R` | Cleans taxon strings, drops clinical/human hosts, standardises categoricals. First step of the automated runner. |
| `merge_final_data.py` | Merges the per-task extraction shards into one file. |

## Deprecated / archived

- `download_pdfs.py` — stub; replaced by `fetch_fulltext_pdfs.py`. Original in
  `scripts/archive/download_pdfs_v4.py`.
- `scripts/archive/monsoon_extract_v4.py` — the pre-Task-1 extraction script (first 12
  pages / 8k-char truncation bug).

## Dependencies

- **R**: `rentrez`, `rscopus`, `wosr` (pull); `tidyverse`, `stringr` (dedup)
- **Python**: `pandas`, `requests`, `pymupdf` + `pymupdf4llm`, `ocrmypdf`, `ollama`
- API keys for Scopus and Web of Science (pull step only)
- Monsoon: `module load ollama`; models staged in `/scratch/bmb646/ollama_models`
