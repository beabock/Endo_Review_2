#!/bin/bash
#SBATCH --job-name=endo_fetch_pdfs
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=08:00:00
#SBATCH --output=results/logs/fetch_pdfs_%A_%a.out
#SBATCH --error=results/logs/fetch_pdfs_%A_%a.out
#
# Multi-resolver full-text PDF retrieval (Task 1 Phase 0a). No GPU, no Ollama - this is
# just HTTP requests to OA resolvers. Runs as a Slurm array (one task per shard).
#
# Usage:
#   # coverage dry-run (no downloads), 4 shards:
#   sbatch --array=0-3 --export=NSHARDS=4,DRY_RUN=1 \
#       scripts/01_data_preproccessing/run_fetch_pdfs.sbatch
#   # real download, 8 shards:
#   sbatch --array=0-7 --export=NSHARDS=8 \
#       scripts/01_data_preproccessing/run_fetch_pdfs.sbatch
#
# Then merge the per-shard manifests:
#   python scripts/01_data_preproccessing/merge_pdf_manifests.py --out-dir <OUT_DIR>

set -euo pipefail
trap 'rc=$?; echo "ERROR: line ${LINENO}: ${BASH_COMMAND} (exit ${rc})"; exit ${rc}' ERR

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [ -n "${SLURM_SUBMIT_DIR:-}" ] && [ -d "${SLURM_SUBMIT_DIR}/scripts/01_data_preproccessing" ]; then
    PROJECT_ROOT="${SLURM_SUBMIT_DIR}"
fi
cd "$PROJECT_ROOT"
mkdir -p results/logs

# default: the deduplicated analysis paper set (tracked in the repo, has a `doi` column).
# Override with INPUT=data/Abstracts/Abstracts_for_Monsoon.csv to use the raw abstract list.
INPUT="${INPUT:-data/Ollama_cleaned_synresolved_standardized_year.csv}"
OUT_DIR="${OUT_DIR:-/scratch/bmb646/full_corpus}"
EMAIL="${EMAIL:-bmb646@nau.edu}"
NSHARDS="${NSHARDS:-1}"
DRY_RUN="${DRY_RUN:-0}"
SLEEP="${SLEEP:-0.3}"
SHARD="${SLURM_ARRAY_TASK_ID:-0}"

# Python env
if [ -x ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
else
    if ! type module >/dev/null 2>&1 && [ -f /etc/profile.d/modules.sh ]; then
        source /etc/profile.d/modules.sh
    fi
    module purge || true
    module load python/3.11
    python -m venv .venv
    PYTHON_BIN=".venv/bin/python"
fi
"$PYTHON_BIN" -m pip install --upgrade pip >/dev/null
# dry-run needs only requests+pandas; real download also needs pymupdf for validation
"$PYTHON_BIN" -m pip install requests pandas pymupdf >/dev/null
export PYTHONUNBUFFERED=1

DRY_FLAG=""
[ "$DRY_RUN" = "1" ] && DRY_FLAG="--dry-run"

echo "--- fetch_fulltext_pdfs (shard ${SHARD}/${NSHARDS}, dry_run=${DRY_RUN}) ---"
echo "input=$INPUT  out_dir=$OUT_DIR"

"$PYTHON_BIN" scripts/01_data_preproccessing/fetch_fulltext_pdfs.py \
    --input "$INPUT" \
    --out-dir "$OUT_DIR" \
    --manifest "${OUT_DIR}/pdf_manifest_shard${SHARD}.csv" \
    --email "$EMAIL" \
    --shard "$SHARD" --nshards "$NSHARDS" \
    --sleep "$SLEEP" \
    $DRY_FLAG

echo "shard ${SHARD} done"
