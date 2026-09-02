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

# default: the deduplicated ORIGINAL search export (pre-LLM), so full-text coverage is
# measured for every record the search returned - not just the ~18.7k that survived the
# old LLM relevance/guild filtering (which we are about to redo). This file is gitignored
# (~164 MB); copy it onto Monsoon:
#   scp data/Abstracts/All_abstracts_deduped.csv <monsoon>:.../data/Abstracts/
# It carries Publisher / Source.title / Open.Access / Document.Type, used in the report.
INPUT="${INPUT:-data/Abstracts/All_abstracts_deduped.csv}"
OUT_DIR="${OUT_DIR:-/scratch/bmb646/full_corpus}"
EMAIL="${EMAIL:-bmb646@nau.edu}"
NSHARDS="${NSHARDS:-1}"
DRY_RUN="${DRY_RUN:-0}"
SLEEP="${SLEEP:-0.3}"
SHARD="${SLURM_ARRAY_TASK_ID:-0}"

# Python env. This job needs no GPU and no Ollama - just a Python with requests +
# pandas (+ pymupdf for the real-download PDF validation). We use whatever `python`
# is on PATH (the conda env you submit from is inherited by the job) and layer the
# few extra packages into a lightweight venv that also sees the conda site-packages,
# so pandas/numpy come for free. No `module load` - Monsoon has no `python/3.11`.
BASE_PY="$(command -v python3 || command -v python)"
if [ -z "$BASE_PY" ]; then
    echo "ERROR: no python on PATH. Submit this job from your (base) conda env."
    exit 1
fi
echo "base python: $BASE_PY ($("$BASE_PY" --version 2>&1))"

# one venv per array task - no cross-task races
VENV="$PROJECT_ROOT/.venv_fetch_${SHARD}"
if [ ! -x "$VENV/bin/python" ]; then
    "$BASE_PY" -m venv --system-site-packages "$VENV" \
        || { echo "venv creation failed - falling back to base python"; VENV=""; }
fi
if [ -n "$VENV" ] && [ -x "$VENV/bin/python" ]; then
    PYTHON_BIN="$VENV/bin/python"
else
    PYTHON_BIN="$BASE_PY"
fi
"$PYTHON_BIN" -m pip install --quiet --upgrade pip requests pandas pymupdf || true
export PYTHONUNBUFFERED=1

# hard check - fail loudly now, not 4700 DOIs in
"$PYTHON_BIN" - <<'PY' || { echo "ERROR: missing Python deps (need requests, pandas)"; exit 1; }
import requests, pandas  # noqa
print("deps ok: requests", requests.__version__, "| pandas", pandas.__version__)
PY

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
