# Taxa Synonym Resolution (Python CLI)

This step resolves names in `fungal_taxon` and `plant_host` from `data/Ollama_cleaned.csv` to modern accepted names using GBIF backbone data.

## Inputs
- `data/Ollama_cleaned.csv`
- `data/Reference_datasets/gbif_backbone/Taxon.tsv`

## Outputs
- `data/Ollama_cleaned_synresolved.csv`
- `results/manual_validation/taxa_unresolved_review.csv`
- `results/logs/taxa_synonym_resolution_checkpoint.json`

## What the script does
- Preserves one output row per input row.
- Adds stable IDs:
  - `paper_id`: DOI first, fallback to `source_file`
  - `interaction_id`: deterministic hash for each original row
- Splits multi-name cells in `fungal_taxon` and `plant_host`.
- Resolves names in this order:
  1. exact accepted match
  2. synonym to accepted mapping
  3. abbreviation expansion (`A. niger` style) with context-first fallback
- Writes unresolved or ambiguous tokens to review CSV.
- Supports checkpointing and resume.

## Local run
```bash
python scripts/02_taxa_resolution/taxa_synonym_resolution.py \
  --input-csv data/Ollama_cleaned.csv \
  --taxon-tsv data/Reference_datasets/gbif_backbone/Taxon.tsv \
  --output-csv data/Ollama_cleaned_synresolved.csv \
  --unresolved-csv results/manual_validation/taxa_unresolved_review.csv \
  --checkpoint-json results/logs/taxa_synonym_resolution_checkpoint.json \
  --checkpoint-interval 1000 \
  --log-interval 1000 \
  --resume
```

## Monsoon run (SLURM)
Use:
- `scripts/02_taxa_resolution/slurm/run_taxa_synonym_resolution.sbatch`

Submit from repo root:
```bash
sbatch scripts/02_taxa_resolution/slurm/run_taxa_synonym_resolution.sbatch
```

## Smoke test option
For quick validation before full run:
```bash
python scripts/02_taxa_resolution/taxa_synonym_resolution.py --max-rows 200
```
