#!/bin/bash
#SBATCH --job-name=taxa_syn_resolve
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16    # Increase from 8 to 16 to speed up dictionary indexing
#SBATCH --mem=128G            # Double the RAM to prevent swapping/freezing
#SBATCH --time=12:00:00       # Extend time just in case it's slow
#SBATCH --output=results/logs/taxa_synonym_resolution_%j.out
#SBATCH --error=results/logs/taxa_synonym_resolution_%j.err

set -euo pipefail

# Submit from the repository root:
# sbatch scripts/02_taxa_resolution/slurm/run_taxa_synonym_resolution.sbatch

cd "${SLURM_SUBMIT_DIR:-$(pwd)}"
mkdir -p results/logs results/manual_validation

if command -v module >/dev/null 2>&1; then module purge || true; fi
# use the conda env you submit from (Monsoon has no python/3.11 module)
PY="$(command -v python3 || command -v python)"

# Taxonomy source. Default: Catalogue of Life Extended Release DwC-A (COL26.x XR)
# from ChecklistBank - download the Fungi + Plantae subsets, unzip, and point
# TAXON_TSV at the Taxon.tsv. Override with the legacy GBIF backbone if needed:
#   sbatch --export=TAXON_TSV=/path/gbif_backbone/Taxon.tsv,TAXONOMY_SOURCE=gbif_backbone ...
TAXON_TSV="${TAXON_TSV:-data/Reference_datasets/col_xr/Taxon.tsv}"
TAXONOMY_SOURCE="${TAXONOMY_SOURCE:-auto}"
INPUT_CSV="${INPUT_CSV:-data/Ollama_cleaned.csv}"

echo "taxonomy: $TAXON_TSV (source=$TAXONOMY_SOURCE)"

"$PY" scripts/02_taxa_resolution/taxa_synonym_resolution.py \
  --input-csv "$INPUT_CSV" \
  --taxon-tsv "$TAXON_TSV" \
  --taxonomy-source "$TAXONOMY_SOURCE" \
  --output-csv data/Ollama_cleaned_synresolved.csv \
  --log-interval 100 \
  --checkpoint-interval 500