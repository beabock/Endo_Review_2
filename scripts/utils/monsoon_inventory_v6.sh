#!/usr/bin/env bash
# BMB 2026-11-05 (Thread B, extraction v6). READ-ONLY inventory of what Monsoon already has for
# the v6 model bake-off: staged Ollama models, HF-format weights, vLLM / containers / python
# packages, GPU partitions and limits, network reach, disk space.
#
# Safe on a LOGIN node: no GPU, no downloads, no writes except the report file. Every command is
# wrapped in `timeout` so one slow filesystem cannot hang the whole thing (a missing section
# says "TIMED OUT" - tell Claude which one).
#
# Run (from anywhere):
#   bash ~/endo_review/scripts/utils/monsoon_inventory_v6.sh
# It prints to the screen AND saves ~/v6_inventory_<date>.txt - paste that file back
# (it is plain text; if it is very long, paste sections 1, 2, 3 and 4 first).

set -u
OUT="$HOME/v6_inventory_$(date +%Y%m%d_%H%M).txt"
exec > >(tee "$OUT") 2>&1

T() { timeout "${T_SEC:-40}" "$@" || echo "  (command failed or TIMED OUT: $*)"; }
H() { echo; echo "=================================================================="; echo "== $*"; echo "=================================================================="; }

H "0. who / where"
echo "date: $(date)"; echo "host: $(hostname)"; echo "user: $USER"; echo "shell: $SHELL"
echo "repo (if checked out at ~/endo_review): $(cd ~/endo_review 2>/dev/null && git rev-parse --short HEAD && git branch --show-current)"

H "1. GPU partitions, GPU types, time limits"
T sinfo -h -o "%P | gres=%G | mem=%m | cpus=%c | nodes=%D | maxtime=%l | state=%a"
echo "--- GPU model per node type (one line per distinct node config):"
T bash -c "scontrol show node 2>/dev/null | grep -E 'NodeName=|Gres=|CfgTRES=|AvailableFeatures=' | paste - - - - | sed 's/  */ /g' | awk '{print}' | sort -u -k2 | head -60"
echo "--- my accounts / QOS:"
T sacctmgr -nP show assoc user="$USER" format=account,partition,qos,grptres
T bash -c "scontrol show partition 2>/dev/null | grep -E 'PartitionName|MaxTime|DefaultTime|AllowAccounts|AllowQos|TRES=' | paste - - - - - | head -40"

H "2. Ollama: binary, modules, staged model stores"
T bash -c "module avail ollama 2>&1 | tail -5"
echo "which ollama: $(command -v ollama || echo 'not on PATH (needs: module load ollama)')"
echo "OLLAMA_MODELS env: ${OLLAMA_MODELS:-<unset>}"
echo "--- ~/.ollama/models:"; T ls -la ~/.ollama/ 2>&1 | head; T readlink -f ~/.ollama/models
echo "--- /common/contrib/ollama_models:"; T ls -la /common/contrib/ollama_models/
echo "--- ~/ollama_tags.json / ollama_model_locations.txt (if present):"
T bash -c "cat ~/ollama_model_locations.txt 2>/dev/null | head -20; ls -la ~/ollama_tags.json 2>/dev/null"

# one python helper: for every Ollama store found, list model:tag, size, quantization, params, digest
STORES=()
for d in /common/contrib/ollama_models/* /scratch/$USER/ollama_models /scratch/bmb646/ollama_models "$HOME/.ollama/models"; do
  [ -d "$d/manifests" ] && STORES+=("$d")
done
echo "--- Ollama stores with manifests: ${STORES[*]:-none}"
T_SEC=120 python3 - "${STORES[@]}" <<'PY'
import json, os, sys
seen = set()
for store in sys.argv[1:]:
    real = os.path.realpath(store)
    if real in seen:
        print(f"[{store}] same as an earlier store ({real}) - skipped"); continue
    seen.add(real)
    print(f"\n[{store}]")
    rows = []
    for root, _, files in os.walk(os.path.join(store, "manifests")):
        for f in files:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, os.path.join(store, "manifests")).split(os.sep)
            name = "/".join(rel[1:-1]) + ":" + rel[-1] if len(rel) > 2 else "/".join(rel)
            name = name.replace("library/", "")
            try:
                m = json.load(open(p))
                size = sum(l.get("size", 0) for l in m.get("layers", [])) / 1e9
                model_layer = next((l for l in m["layers"] if l["mediaType"].endswith("image.model")), {})
                cfg = m.get("config", {}).get("digest", "").replace(":", "-")
                info = {}
                cp = os.path.join(store, "blobs", cfg)
                if os.path.exists(cp):
                    info = json.load(open(cp))
                rows.append((name, round(size, 1), info.get("file_type", "?"), info.get("model_type", "?"),
                             info.get("model_family", "?"), model_layer.get("digest", "")[:19]))
            except Exception as e:
                rows.append((name, "?", "?", "?", "?", repr(e)[:30]))
    for r in sorted(rows):
        print("  %-38s %6s GB  quant=%-8s params=%-6s family=%-10s blob=%s" % r)
    if not rows:
        print("  (no manifests)")
PY

H "3. Hugging Face / safetensors weights already on disk (needed by vLLM; GGUF/Ollama blobs are NOT enough)"
echo "HF_HOME=${HF_HOME:-<unset>}  HF_HUB_CACHE=${HF_HUB_CACHE:-<unset>}  TRANSFORMERS_CACHE=${TRANSFORMERS_CACHE:-<unset>}  XDG_CACHE_HOME=${XDG_CACHE_HOME:-<unset>}"
for d in ~/.cache/huggingface/hub /scratch/$USER/.cache/huggingface/hub /scratch/$USER/huggingface /scratch/$USER/hf_cache \
         /common/contrib/huggingface /common/contrib/hf /common/contrib/models /common/contrib/llm "${HF_HOME:-/nonexistent}/hub" "${HF_HUB_CACHE:-/nonexistent}"; do
  [ -d "$d" ] && { echo "--- $d"; T ls -d "$d"/models--* 2>/dev/null | sed 's#.*/models--##' | head -80; }
done
echo "--- /common/contrib top level (what else is staged?):"
T ls /common/contrib | head -150
echo "--- any directory named models--* or containing *.safetensors, depth <= 4 (limited search):"
T_SEC=90 T bash -c "find /common/contrib /scratch/$USER -maxdepth 4 \( -name 'models--*' -o -name '*.safetensors' \) 2>/dev/null | head -40"

H "4. vLLM, python envs, containers, relevant packages"
T bash -c "module avail 2>&1 | grep -i -E 'vllm|sglang|llama|ollama|cuda|python|conda|anaconda|mamba|apptainer|singularity|torch|gnfinder' | head -60"
echo "which vllm: $(command -v vllm || echo none)"
echo "python: $(command -v python3) $(python3 --version 2>&1)"
echo "--- conda envs:"; T bash -c "conda env list 2>/dev/null || echo 'conda not on PATH'"
echo "--- containers:"; echo "apptainer: $(command -v apptainer || echo none)   singularity: $(command -v singularity || echo none)"
T bash -c "find /common -maxdepth 3 \( -iname '*vllm*' -o -iname '*.sif' \) 2>/dev/null | head -20"
echo "--- pip packages in the CURRENT python:"
T bash -c "python3 -m pip list 2>/dev/null | grep -i -E '^(vllm|torch|transformers|flash.attn|xformers|xgrammar|outlines|openai|requests|pymupdf|pymupdf4llm|ocrmypdf|rapidfuzz|geopandas|shapely|pyproj|lingua|langid|openpyxl|pandas|numpy) '"
echo "--- gnfinder (optional taxonomic name finder): $(command -v gnfinder || echo none)"
echo "--- nvidia driver / CUDA (login node usually has none):"; T nvidia-smi -L

H "5. Network reach from THIS node (login). Compute nodes can differ - the bench/PoC sbatch re-checks."
for u in https://huggingface.co https://registry.ollama.ai https://pypi.org/simple/pip/ https://github.com \
         https://registry-1.docker.io/v2/ https://nvcr.io; do
  printf '%-40s ' "$u"; timeout 12 curl -s -o /dev/null -m 10 -w '%{http_code}\n' -I "$u" || echo "no response"
done
echo "--- proxy env: http_proxy=${http_proxy:-<unset>} https_proxy=${https_proxy:-<unset>}"

H "6. Disk space and quotas"
T df -h "$HOME" /scratch/"$USER" /common/contrib 2>&1
T bash -c "quota -s 2>/dev/null | head -10"
T bash -c "du -sh /scratch/$USER/* 2>/dev/null | sort -h | tail -15"

H "7. Project inputs on Monsoon"
for p in /scratch/bmb646/full_corpus /scratch/bmb646/Abstracts_for_Monsoon.csv ~/endo_review/data/Abstracts/All_abstracts_deduped.csv; do
  [ -e "$p" ] && { echo "--- $p"; T ls -la "$p" | head -8; } || echo "--- $p : MISSING"
done
T bash -c "ls /scratch/bmb646/full_corpus/*.pdf 2>/dev/null | wc -l | sed 's/^/n PDFs in full_corpus: /'"
T bash -c "head -2 /scratch/bmb646/full_corpus/pdf_manifest.csv 2>/dev/null; wc -l /scratch/bmb646/full_corpus/pdf_manifest.csv 2>/dev/null"

H "DONE"
echo "Saved to: $OUT   ($(wc -l < "$OUT") lines so far)"
