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

module purge
module load python/3.11

# Optional: activate your Monsoon env if needed
# source ~/miniconda3/etc/profile.d/conda.sh
# conda activate endo-review

python scripts/02_taxa_resolution/taxa_synonym_resolution.py \
  --input-csv data/Ollama_cleaned.csv \
  --taxon-tsv /scratch/bmb646/Endo-Review/data/Reference_datasets/gbif_backbone/Taxon.tsv \
  --output-csv data/Ollama_cleaned_synresolved.csv \
  --log-interval 100 \
  --checkpoint-interval 500