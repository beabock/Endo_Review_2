# Global Audit of Fungal Endophyte Literature

This repository contains the data and code for our upcoming paper auditing the global fungal endophyte literature. We're looking at geographic, taxonomic, and economic biases across ~18,750 publications to test the claim that fungal endophytes are ubiquitous.

## Folder Structure

- `data/`: Raw and processed datasets, including publication metadata, GBIF taxonomic data, and country-level GDP information.
- `scripts/`: Python and R scripts that make up the analysis pipeline.
- `results/`: Output tables, statistical summaries, and figures.

## Dependencies

You will need **Python 3** and **R** installed. Key R packages include `tidyverse`, `sf`, `leaflet`, and `rnaturalearth`. Key Python packages are listed in `.venv/` (create with `python -m venv .venv && pip install pandas requests`).

### GBIF backbone (required for taxa resolution and taxonomy analysis)

The GBIF taxonomic backbone is not included in this repository due to its size (~1 GB). Download it before running the pipeline:

1. Go to https://www.gbif.org/dataset/d7dddbf4-2cf0-4f39-9b2a-bb099caae36c
2. Download the **DwC-A** (Darwin Core Archive) format
3. Unzip and place the contents in `data/Reference_datasets/gbif_backbone/` so that `data/Reference_datasets/gbif_backbone/Taxon.tsv` exists

The taxonomy analysis scripts will cache a processed version of the backbone in `results/taxonomy_analysis/cache/` on first run, which speeds up subsequent runs considerably.

## Running the analysis

To reproduce the full analysis, run the central runner script from the root of the repository:

```bash
python scripts/central_run_everything.py
```

This script will sequentially run:
1. Data cleanup (`scripts/01_data_preproccessing/02_ollama_cleanup.R`)
2. Taxa synonym resolution against GBIF (`scripts/02_taxa_resolution`)
3. Metadata standardization (`scripts/03_standardize_metadata`)
4. Statistical analyses (`scripts/04_analyses`)
5. Plot generation (`scripts/05_plotting`)

*Note: The initial literature API pulls and data consolidation steps in `01_data_preproccessing` are intentionally kept manual and aren't executed by the automated runner.*
