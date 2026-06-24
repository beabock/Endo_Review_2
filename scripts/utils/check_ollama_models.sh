#!/usr/bin/env bash
# BMB 2026-06-05
# Quick helper to find Ollama model files and check what's available on Monsoon.
set -euo pipefail

echo "== Environment summary =="
echo "USER: ${USER:-$(whoami)}"
echo "PWD: $(pwd)"
echo "which ollama: $(command -v ollama || echo 'ollama not in PATH')"

echo "\n== ollama list (if available) =="
if command -v ollama >/dev/null 2>&1; then
  ollama list || true
else
  echo "ollama CLI not found in PATH"
fi

echo "\n== OLLAMA_MODELS env var =="
echo "${OLLAMA_MODELS:-<not set>}"

echo "\n== Checking common model directories =="
common_dirs=("$HOME/.ollama/models" "/scratch/$USER/ollama_models" "/scratch/ollama_models" "/scratch/bmb646/ollama_models" "/opt/ollama/models" "/var/lib/ollama" "/srv/ollama/models" "/usr/local/share/ollama/models")
for d in "${common_dirs[@]}"; do
  if [ -d "$d" ]; then
    echo "FOUND: $d"
    ls -lah -- "$d" | sed -n '1,40p'
    echo ""
  fi
done

echo "\n== Fast targeted search for known model names (qwen, mistral, llama, vicuna) under /scratch and /opt (limited depth) =="
# limited-depth find to avoid scanning whole filesystem
for base in /scratch /opt /srv; do
  if [ -d "$base" ]; then
    echo "Searching in $base..."
    find "$base" -maxdepth 4 -type d \( -iname '*qwen*' -o -iname '*mistral*' -o -iname '*llama*' -o -iname '*vicuna*' -o -iname '*ollama*' \) -print 2>/dev/null | sed -n '1,200p'
  fi
done

echo "\n== Search for Ollama blobs/archives under /scratch (may still take time) =="
if [ -d /scratch ]; then
  find /scratch -maxdepth 3 -type f -iname '*blobs*' -o -iname '*.gguf' -o -iname '*.bin' 2>/dev/null | sed -n '1,200p' || true
fi

echo ""
echo "Done. Run on a Monsoon login or compute node with Ollama access."
