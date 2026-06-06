# Global Audit of Fungal Endophyte Literature

This repository contains the data and code for our upcoming paper auditing the global fungal endophyte literature. We're looking at geographic, taxonomic, and economic biases across ~18,750 publications to test the claim that fungal endophytes are ubiquitous.

## Folder Structure

- `data/`: Raw and processed datasets, including publication metadata, GBIF taxonomic data, and country-level GDP information.
- `scripts/`: Python and R scripts that make up the analysis pipeline.
- `results/`: Output tables, statistical summaries, and figures. (Check out `ANALYSIS_SUMMARY.md` for a quick breakdown of what the output files contain).
- `manuscript/`: Working drafts and review files for the paper.

## Running the analysis

To run the code, you'll need Python 3 and R installed on your machine. 

To reproduce the full analysis, you can just run the central runner script from the root of the repository:

```bash
python scripts/central_run_everything.py
```

This script will sequentially run:
1. Data cleanup (`scripts/01_data_preproccessing/ollama_cleanup.R`)
2. Taxa synonym resolution against GBIF (`scripts/02_taxa_resolution`)
3. Metadata standardization (`scripts/03_standardize_metadata`)
4. Statistical analyses (`scripts/04_analyses`)
5. Plot generation (`scripts/05_plotting`)

*Note: The initial literature API pulls and data consolidation steps in `01_data_preproccessing` are intentionaly kept manual and aren't executed by the automated runner.*
