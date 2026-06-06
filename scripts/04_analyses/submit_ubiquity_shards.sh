#!/usr/bin/env bash
# Generate and optionally submit 4-shard sbatch jobs for ubiquity claims detection
# Usage:
#   bash scripts/04_analyses/submit_ubiquity_shards.sh [submit]
# 
# Without "submit" arg, just prints the commands (dry-run).
# With "submit" arg, actually submits the jobs.

set -euo pipefail

DRY_RUN=true
if [[ "${1:-}" == "submit" ]]; then
  DRY_RUN=false
fi

N_SHARDS=4
OLLAMA_MODEL="mistral"
SBATCH_SCRIPT="scripts/04_analyses/run_06_ubiquity_claims_ollama.sbatch"

echo "=== Ubiquity Claims Detection: 4-Shard Submission ==="
echo "Model: $OLLAMA_MODEL"
echo "Shards: $N_SHARDS"
echo "Sbatch script: $SBATCH_SCRIPT"
echo ""

if [ ! -f "$SBATCH_SCRIPT" ]; then
  echo "ERROR: sbatch script not found: $SBATCH_SCRIPT"
  exit 1
fi

echo "Commands to run:"
echo ""

JOB_IDS=()
for SHARD_ID in $(seq 0 $((N_SHARDS-1))); do
  CMD="sbatch --export=SHARD_ID=${SHARD_ID},N_SHARDS=${N_SHARDS},OLLAMA_MODEL=${OLLAMA_MODEL} ${SBATCH_SCRIPT}"
  
  echo "# Shard $SHARD_ID / $N_SHARDS"
  echo "$CMD"
  echo ""
  
  if [ "$DRY_RUN" = false ]; then
    echo "  → Submitting shard $SHARD_ID..."
    JOB_ID=$(eval "$CMD" | grep -oE '[0-9]+' | head -1)
    JOB_IDS+=("$JOB_ID")
    echo "  ✓ Job ID: $JOB_ID"
  fi
done

if [ "$DRY_RUN" = false ]; then
  echo ""
  echo "=== Jobs Submitted ==="
  for i in "${!JOB_IDS[@]}"; do
    echo "Shard $i: ${JOB_IDS[$i]}"
  done
  
  echo ""
  echo "Monitor progress:"
  echo "  squeue -u bmb646"
  echo ""
  echo "After jobs complete, merge outputs:"
  echo "  python scripts/04_analyses/merge_ubiquity_shards.py"
else
  echo "=== DRY RUN (no jobs submitted) ==="
  echo "To actually submit, run:"
  echo "  bash scripts/04_analyses/submit_ubiquity_shards.sh submit"
fi
