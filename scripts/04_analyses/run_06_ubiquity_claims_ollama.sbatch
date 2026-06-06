#!/bin/bash
#SBATCH --job-name=endo_ubiquity_claims
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --gres=gpu:1
#SBATCH --time=10:00:00
#SBATCH --output=results/logs/ubiquity_claims_%j.out
#SBATCH --error=results/logs/ubiquity_claims_%j.out
#
# Ollama-based ubiquity claims detection for endophyte abstracts and full texts.
# Requires Monsoon module system: module load ollama
# Models pre-staged at: /scratch/bmb646/ollama_models
#
# Usage:
#   sbatch run_06_ubiquity_claims_ollama.sbatch
#   sbatch --export=OLLAMA_MODEL=mistral run_06_ubiquity_claims_ollama.sbatch
#   sbatch --export=SOURCE_MODE=fulltext run_06_ubiquity_claims_ollama.sbatch

set -euo pipefail
trap 'rc=$?; echo "ERROR: line ${LINENO}: ${BASH_COMMAND} (exit ${rc})"; exit ${rc}' ERR

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ -n "${SLURM_SUBMIT_DIR:-}" ] && [ -d "${SLURM_SUBMIT_DIR}/scripts/04_analyses" ]; then
    PROJECT_ROOT="${SLURM_SUBMIT_DIR}"
fi

cd "$PROJECT_ROOT"
mkdir -p results/logs

# Load Ollama module from Monsoon HPC
echo "Loading Ollama module..."
if ! type module >/dev/null 2>&1; then
    if [ -f /etc/profile ]; then
        # shellcheck source=/etc/profile
        source /etc/profile
    fi
fi

if ! type module >/dev/null 2>&1; then
    # Non-login batch shells may not preload the modules function.
    if [ -f /etc/profile.d/modules.sh ]; then
        # shellcheck source=/etc/profile.d/modules.sh
        source /etc/profile.d/modules.sh
    elif [ -f /usr/share/Modules/init/bash ]; then
        # shellcheck source=/usr/share/Modules/init/bash
        source /usr/share/Modules/init/bash
    fi
fi

if ! type module >/dev/null 2>&1; then
    echo "ERROR: environment modules system is not initialized; 'module' command unavailable."
    echo "Checked: /etc/profile, /etc/profile.d/modules.sh, /usr/share/Modules/init/bash"
    exit 1
fi

if ! module purge; then
    echo "Warning: module purge returned non-zero; continuing"
fi
if ! module load ollama; then
    echo "ERROR: failed to load ollama module"
    exit 1
fi
echo "Ollama version: $(ollama --version)"

# Defaults can be overridden via sbatch --export
INPUT_DIR="${INPUT_DIR:-/scratch/bmb646/Bea_Nick_papers_endoreview}"
OUTPUT_DIR="${OUTPUT_DIR:-results/ubiquity_claims}"
OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-mistral}"
MAX_FILES="${MAX_FILES:-0}"
SOURCE_MODE="${SOURCE_MODE:-paired}"
ABSTRACT_CSV="${ABSTRACT_CSV:-/scratch/bmb646/Abstracts_for_Monsoon.csv}"
ABSTRACT_TEXT_COL="${ABSTRACT_TEXT_COL:-}"
ABSTRACT_ID_COL="${ABSTRACT_ID_COL:-}"
AUTO_START_OLLAMA="${AUTO_START_OLLAMA:-1}"
OLLAMA_SERVE_LOG="${OLLAMA_SERVE_LOG:-results/logs/ollama_serve_${SLURM_JOB_ID:-manual}.log}"
OLLAMA_MODELS="${OLLAMA_MODELS:-/scratch/bmb646/ollama_models}"
SHARD_ID="${SHARD_ID:-0}"
N_SHARDS="${N_SHARDS:-1}"

# Python environment setup
if [ -x ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
elif [ -x ".venv/Scripts/python.exe" ]; then
    PYTHON_BIN=".venv/Scripts/python.exe"
else
    if ! module purge; then
        echo "Warning: module purge returned non-zero before python setup; continuing"
    fi
    if ! module load python/3.11; then
        echo "ERROR: failed to load python/3.11 module"
        exit 1
    fi
    python -m venv .venv
    PYTHON_BIN=".venv/bin/python"
fi

# Ensure required dependencies for PDF parsing and Ollama API
"$PYTHON_BIN" -m pip install --upgrade pip >/dev/null
"$PYTHON_BIN" -m pip install pypdf ollama >/dev/null
export PYTHONUNBUFFERED=1

echo "--- Ubiquity Claim Detection Run ---"
echo "Project root: $PROJECT_ROOT"
echo "Input dir: $INPUT_DIR"
echo "Output dir: $OUTPUT_DIR"
echo "Ollama host: $OLLAMA_HOST"
echo "Ollama model: $OLLAMA_MODEL"
echo "Max files: $MAX_FILES"
echo "Source mode: $SOURCE_MODE"
echo "Abstract CSV: $ABSTRACT_CSV"
echo "Auto-start Ollama: $AUTO_START_OLLAMA"
echo "Ollama models dir: $OLLAMA_MODELS"

# Verify ollama is available from module
if ! command -v ollama >/dev/null 2>&1; then
    echo "ERROR: ollama command not found after module load."
    echo "Verify: module load ollama was successful."
    exit 1
fi

echo "Ollama binary path: $(command -v ollama)"

check_ollama_up() {
    "$PYTHON_BIN" - <<'PY'
import os
import sys
import urllib.request

host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
url = host + "/api/tags"
try:
        with urllib.request.urlopen(url, timeout=5) as resp:
                ok = resp.status == 200
except Exception:
        ok = False

sys.exit(0 if ok else 1)
PY
}

if ! check_ollama_up; then
    echo "Ollama is not reachable at $OLLAMA_HOST"
    if [ "$AUTO_START_OLLAMA" = "1" ]; then
        echo "Attempting to start Ollama server (module-provided binary)..."
        export OLLAMA_MODELS="$OLLAMA_MODELS"
        nohup ollama serve > "$OLLAMA_SERVE_LOG" 2>&1 &
        echo "Started ollama serve with PID $!"
        echo "Log file: $OLLAMA_SERVE_LOG"
        
        # Wait up to 30 seconds for server to be ready
        for i in {1..30}; do
            if check_ollama_up; then
                echo "Ollama server endpoint is ready!"
                break
            fi
            echo "Waiting for Ollama to be ready... ($i/30)"
            sleep 1
        done
        
        if ! check_ollama_up; then
            echo "ERROR: Ollama still unreachable after 30 seconds."
            echo "Check log: $OLLAMA_SERVE_LOG"
            tail -20 "$OLLAMA_SERVE_LOG"
            exit 1
        fi
        
        # Extended wait for model to fully load into VRAM (can take 3-5+ minutes)
        echo "Waiting for model to be fully loaded into VRAM (up to 300 seconds)..."
        max_attempts=300
        model_ready=0
        for i in $(seq 1 $max_attempts); do
            if "$PYTHON_BIN" - <<'PYTEST'
import os, sys, time
try:
    import ollama
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    model = os.environ.get("OLLAMA_MODEL", "mistral")
    client = ollama.Client(host=host)
    # Simple test inference - if this succeeds, model is loaded
    response = client.generate(model=model, prompt="test", stream=False, options={"temperature": 0})
    print(f"Model {model} is ready")
    sys.exit(0)
except Exception as e:
    sys.exit(1)
PYTEST
            then
                model_ready=1
                echo "Model fully loaded and responding after $i second(s)"
                break
            fi
            if [ $((i % 30)) -eq 0 ]; then
                echo "Still loading model... ($i/300 seconds elapsed)"
            fi
            sleep 1
        done

        if [ "$model_ready" -ne 1 ]; then
            echo "ERROR: model readiness check did not succeed within 300 seconds."
            echo "Check log: $OLLAMA_SERVE_LOG"
            tail -30 "$OLLAMA_SERVE_LOG"
            exit 1
        fi
        
        # Final verification
        if ! check_ollama_up; then
            echo "ERROR: Ollama not reachable after full wait cycle."
            tail -20 "$OLLAMA_SERVE_LOG"
            exit 1
        fi
    else
        echo "ERROR: AUTO_START_OLLAMA=0 and Ollama host is unreachable."
        echo "Ensure Ollama server is running: ollama serve &"
        exit 1
    fi
else
    echo "Ollama server is already running at $OLLAMA_HOST"
fi

SHARD_OUTPUT_DIR="${OUTPUT_DIR}/shard_${SHARD_ID}"
mkdir -p "$SHARD_OUTPUT_DIR"

"$PYTHON_BIN" scripts/04_analyses/06_detect_ubiquity_claims_ollama.py \
    --input-dir "$INPUT_DIR" \
    --output-dir "$SHARD_OUTPUT_DIR" \
        --source-mode "$SOURCE_MODE" \
        --abstract-csv "$ABSTRACT_CSV" \
        --abstract-text-col "$ABSTRACT_TEXT_COL" \
        --abstract-id-col "$ABSTRACT_ID_COL" \
    --model "$OLLAMA_MODEL" \
    --ollama-host "$OLLAMA_HOST" \
    --max-files "$MAX_FILES" \
    --n-shards "$N_SHARDS" \
    --shard-id "$SHARD_ID"

echo "Done. Outputs are in: $OUTPUT_DIR"
