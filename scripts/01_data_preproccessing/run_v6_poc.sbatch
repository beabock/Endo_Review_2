#!/bin/bash
#SBATCH --job-name=endo_v6
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=03:00:00
#SBATCH --output=results/logs/v6_%x_%j.out
#SBATCH --error=results/logs/v6_%x_%j.out
#
# BMB 2026-11-05 (Thread B). v6 extraction: serving-throughput benchmark + <=25-paper proof of
# concept, ONE engine + ONE model per job. NOT submitted yet - Bea has to OK the GPU request
# first (NPH_v6_poc_plan.md). Local models only; no hosted API anywhere.
#
# Choose partition / GPU on the command line (decide from the inventory output), e.g.
#   --partition=<h200 or a100 partition> --gres=gpu:1
#
# Environment variables (sbatch --export=ALL,KEY=VAL,...):
#   STEP          bench | poc | both                        (default both)
#   ENGINE        ollama | vllm                             (default ollama)
#   MODEL         ollama tag (mistral:latest, qwen2.5:32b)  or the vLLM --served-model-name
#   MODEL_PATH    vllm only: local HF-format model dir (or a hub id if the node has internet)
#   ARM           label written into every output row       (default = MODEL with : -> _)
#   OLLAMA_MODELS ollama store                              (default /scratch/bmb646/ollama_models)
#   NUM_PARALLEL  OLLAMA_NUM_PARALLEL                       (default 8; KV memory = this x NUM_CTX)
#   NUM_CTX       ollama num_ctx                            (default 16384)
#   MAX_LEN       vllm --max-model-len                      (default 20480)
#   VLLM_SETUP    shell snippet that activates the vLLM env (e.g. "source activate vllm")
#   VLLM_EXTRA_ARGS extra flags for `vllm serve` (quantisation etc.; flags differ by vLLM version)
#   DEV_CSV       default results/manual_validation/dev_set/dev_set_selected.csv
#   PDF_DIR       default $HOME/dev_pdfs   (staged by copy_dev_pdfs.sh; files are D007b.pdf etc.)
#   PREFIX        papers from the balanced DEV prefix       (default 25)
#   CONC          client concurrency for the PoC run        (default 16)
#   BENCH_CONC    concurrency sweep for the bench           (default 1,4,8,16,32)
#   RUN_BASELINE_V5=1   also run the existing v5 monsoon_extract.py with the same model (ollama only)
#   OUT_ROOT      default results/v6_poc
#
# Examples (after the inventory tells us what is available):
#   # arm 1: incumbent 7B on Ollama (v6 staged + v5 baseline for the same model)
#   sbatch --partition=<p> --export=ALL,ENGINE=ollama,MODEL=mistral:latest,RUN_BASELINE_V5=1 \
#          scripts/01_data_preproccessing/run_v6_poc.sbatch
#   # arm 2: qwen2.5:32b (already staged) on Ollama
#   sbatch --partition=<p> --export=ALL,ENGINE=ollama,MODEL=qwen2.5:32b ...
#   # arm 3 / engine comparison: same family under vLLM from HF weights
#   sbatch --partition=<p> --export=ALL,ENGINE=vllm,MODEL=qwen2.5-32b,MODEL_PATH=/scratch/bmb646/hf/Qwen2.5-32B-Instruct,VLLM_SETUP="source activate vllm" ...

set -uo pipefail
trap 'rc=$?; echo "ERROR: line ${LINENO}: ${BASH_COMMAND} (exit ${rc})"; cleanup; exit ${rc}' ERR

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [ -n "${SLURM_SUBMIT_DIR:-}" ] && [ -d "${SLURM_SUBMIT_DIR}/scripts/01_data_preproccessing" ]; then
    PROJECT_ROOT="${SLURM_SUBMIT_DIR}"
fi
cd "$PROJECT_ROOT"; mkdir -p results/logs

STEP="${STEP:-both}"; ENGINE="${ENGINE:-ollama}"
MODEL="${MODEL:?set MODEL (ollama tag or vLLM served name)}"
ARM="${ARM:-${MODEL//[:\/]/_}_${ENGINE}}"
OUT_ROOT="${OUT_ROOT:-results/v6_poc}"; OUT="$OUT_ROOT/${ARM}_${SLURM_JOB_ID:-manual}"
DEV_CSV="${DEV_CSV:-results/manual_validation/dev_set/dev_set_selected.csv}"
PDF_DIR="${PDF_DIR:-$HOME/dev_pdfs}"
PREFIX="${PREFIX:-25}"; CONC="${CONC:-16}"; BENCH_CONC="${BENCH_CONC:-1,4,8,16,32}"
NUM_PARALLEL="${NUM_PARALLEL:-8}"; NUM_CTX="${NUM_CTX:-16384}"; MAX_LEN="${MAX_LEN:-20480}"
OLLAMA_MODELS="${OLLAMA_MODELS:-/scratch/bmb646/ollama_models}"
mkdir -p "$OUT"
SERVER_PID=""
cleanup() { [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null && echo "stopped server $SERVER_PID"; return 0; }
trap cleanup EXIT

echo "=== v6 job $SLURM_JOB_ID on $(hostname) | step=$STEP engine=$ENGINE model=$MODEL arm=$ARM ==="
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv || true
echo "compute-node network check (informational; the run itself needs no internet):"
for u in https://huggingface.co https://registry.ollama.ai https://pypi.org; do
  printf '  %-30s ' "$u"; timeout 10 curl -s -o /dev/null -m 8 -w '%{http_code}\n' -I "$u" || echo "no response"
done
echo "git: $(git rev-parse --short HEAD 2>/dev/null) dirty=$(git status --porcelain 2>/dev/null | wc -l) files"

[ -f "$DEV_CSV" ] || { echo "ERROR: $DEV_CSV missing - run draw_dev_set.py --stage draw first"; exit 1; }

# ---- python client env: whatever python is on PATH + a small venv that also sees its site-packages
BASE_PY="$(command -v python3 || command -v python)"
VENV="${V6_VENV:-$PROJECT_ROOT/.venv_v6}"
if [ ! -x "$VENV/bin/python" ]; then
    "$BASE_PY" -m venv --system-site-packages "$VENV" || { echo "ERROR creating venv"; exit 1; }
fi
PY="$VENV/bin/python"
"$PY" -m pip install -q requests pandas pymupdf pymupdf4llm rapidfuzz ollama 2>&1 | tail -2 || \
    echo "WARNING: pip install failed (no internet on compute node?). Create $VENV on a login node first."
export PYTHONUNBUFFERED=1

# ---- start the server
if [ "$ENGINE" = "ollama" ]; then
    module purge 2>/dev/null || true
    module load ollama || { echo "ERROR: module load ollama failed"; exit 1; }
    export OLLAMA_MODELS OLLAMA_NUM_PARALLEL="$NUM_PARALLEL" OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_KEEP_ALIVE=24h
    export OLLAMA_HOST="127.0.0.1:11434"
    echo "ollama $(ollama --version 2>&1 | tail -1) | store=$OLLAMA_MODELS | NUM_PARALLEL=$NUM_PARALLEL NUM_CTX=$NUM_CTX"
    nohup ollama serve > "$OUT/server.log" 2>&1 & SERVER_PID=$!
    for i in $(seq 1 60); do curl -s http://127.0.0.1:11434/api/tags >/dev/null && break; sleep 1; done
    ollama list | tee "$OUT/ollama_list.txt"
    ollama list | grep -q "^${MODEL}" || { echo "ERROR: $MODEL is not in the Ollama store $OLLAMA_MODELS"; exit 1; }
    BACKEND=ollama; BASE_URL="http://127.0.0.1:11434"
    "$PY" - <<PY || true
import requests; r=requests.post("http://127.0.0.1:11434/api/generate", json={"model":"$MODEL","prompt":"hi","stream":False,
 "options":{"num_ctx":$NUM_CTX},"keep_alive":"24h"}, timeout=900); print("warm-up:", r.status_code)
PY
else
    : "${MODEL_PATH:?set MODEL_PATH for vllm}"
    [ -n "${VLLM_SETUP:-}" ] && eval "$VLLM_SETUP"
    command -v vllm >/dev/null || { echo "ERROR: vllm not on PATH (set VLLM_SETUP)"; exit 1; }
    echo "vllm $(python -c 'import vllm;print(vllm.__version__)' 2>/dev/null)"
    nohup vllm serve "$MODEL_PATH" --served-model-name "$MODEL" --max-model-len "$MAX_LEN" \
        --gpu-memory-utilization 0.90 --enable-prefix-caching --seed 0 --port 8000 \
        ${VLLM_EXTRA_ARGS:-} > "$OUT/server.log" 2>&1 & SERVER_PID=$!
    echo "waiting for vLLM (loading weights can take 5-15 min for 32B)..."
    for i in $(seq 1 120); do
        curl -s http://127.0.0.1:8000/health >/dev/null && { echo "vLLM up after ~$((i*10))s"; break; }
        kill -0 "$SERVER_PID" 2>/dev/null || { echo "ERROR: vllm died"; tail -40 "$OUT/server.log"; exit 1; }
        sleep 10
    done
    curl -s http://127.0.0.1:8000/health >/dev/null || { echo "ERROR: vLLM never became healthy"; tail -40 "$OUT/server.log"; exit 1; }
    BACKEND=openai; BASE_URL="http://127.0.0.1:8000/v1"
fi

COMMON=(--backend "$BACKEND" --base-url "$BASE_URL" --model "$MODEL" --num-ctx "$NUM_CTX")
S="$PROJECT_ROOT/scripts/01_data_preproccessing"

# ---- STEP bench: serving throughput (no PDFs needed)
if [ "$STEP" = "bench" ] || [ "$STEP" = "both" ]; then
    echo "=== bench ==="
    "$PY" "$S/v6_bench.py" --input "$DEV_CSV" "${COMMON[@]}" --concurrency "$BENCH_CONC" --out-dir "$OUT/bench"
fi

# ---- STEP poc: staged v6 on the balanced DEV prefix (abstract mode: all PREFIX papers; fulltext: those with PDFs)
if [ "$STEP" = "poc" ] || [ "$STEP" = "both" ]; then
    echo "=== v6 staged, abstract mode ==="
    "$PY" "$S/extract_v6_poc.py" --mode abstract --input "$DEV_CSV" --prefix "$PREFIX" \
        "${COMMON[@]}" --concurrency "$CONC" --arm "$ARM" --reverify --out-dir "$OUT/v6_abstract"
    if [ -d "$PDF_DIR" ]; then
        echo "=== v6 staged, full-text mode ==="
        "$PY" "$S/extract_v6_poc.py" --mode fulltext --input "$DEV_CSV" --pdf-dir "$PDF_DIR" --prefix "$PREFIX" \
            "${COMMON[@]}" --concurrency "$CONC" --arm "$ARM" --reverify --out-dir "$OUT/v6_fulltext"
    else
        echo "WARNING: PDF_DIR=$PDF_DIR missing - skipped full-text (run results/manual_validation/dev_set/copy_dev_pdfs.sh)"
    fi
    if [ "${RUN_BASELINE_V5:-0}" = "1" ] && [ "$ENGINE" = "ollama" ]; then
        echo "=== v5 baseline (existing monsoon_extract.py, same model) ==="
        "$PY" - <<PY
import pandas as pd
d = pd.read_csv("$DEV_CSV").sort_values("order").head($PREFIX)
ft = d[d.doc_type == "full-text"]
pd.DataFrame({"doi": ft.paper_id, "filename": ft.row_id + ".pdf", "status": "downloaded"}).to_csv("$OUT/dev_manifest.csv", index=False)
d[["paper_id", "abstract"]].to_csv("$OUT/dev_abstracts.csv", index=False)
PY
        "$PY" "$S/monsoon_extract.py" --mode abstract --input "$OUT/dev_abstracts.csv" --model "$MODEL" \
            --out "$OUT/v5_abstract.csv" --num-ctx "$NUM_CTX"
        [ -d "$PDF_DIR" ] && "$PY" "$S/monsoon_extract.py" --mode fulltext --manifest "$OUT/dev_manifest.csv" \
            --pdf-dir "$PDF_DIR" --model "$MODEL" --out "$OUT/v5_fulltext.csv" --num-ctx "$NUM_CTX" --no-ocr
    fi
fi

echo "=== summary ==="
for f in "$OUT"/bench/bench.md "$OUT"/v6_*/run_stats.json; do [ -f "$f" ] && { echo "--- $f"; cat "$f"; }; done
echo "Outputs in: $OUT   (paste bench.md and the run_stats.json files back)"
