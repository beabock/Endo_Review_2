# Monsoon inventory + throughput-test plan (Thread B, v6 extraction)

2026-11-05. Everything in **Part 1 is read-only and safe on a login node** (no GPU, no download,
no writes except one report file). Part 2 (GPU) and Part 3 (downloads) wait for your OK.

## Part 1 — what Bea runs now (about 2–5 minutes)

Make sure the repo on Monsoon has the new script (the files are in the working tree on the laptop;
copy them or `git pull` once Thread A's branch is pushed):

```bash
scp scripts/utils/monsoon_inventory_v6.sh <monsoon>:~/endo_review/scripts/utils/
```

On Monsoon:

```bash
bash ~/endo_review/scripts/utils/monsoon_inventory_v6.sh
```

It prints to the screen and saves `~/v6_inventory_<date>_<time>.txt`. **Paste that file back to
me** (if it is very long, sections 1–4 first). If a section says `TIMED OUT`, tell me which one — I
will give a narrower command.

What each section answers:

| section | question | what I do with it |
|---|---|---|
| 1 GPU partitions | which partitions have H200 / A100-80 / A100-40 / V100, time limits, my account/QOS | choose partition, decide which model sizes fit one GPU |
| 2 Ollama stores | which models are already staged in `/common/contrib/ollama_models/*`, `/scratch/bmb646/ollama_models`, `~/.ollama/models` (name, size, quantisation, params, blob digest) | candidate list for the incumbent/staged arms; digests go in the run manifest |
| 3 HF weights | are any safetensors (HF-format) weights already on disk — **vLLM cannot use Ollama blobs** | decides whether vLLM arms need a download |
| 4 vLLM & envs | is vLLM installed (module / conda / container), CUDA, torch, `pymupdf`, `rapidfuzz`, `geopandas`, `gnfinder` | decision tree in design doc §5 |
| 5 network | can the login node reach Hugging Face, Ollama registry, PyPI, GitHub, Docker Hub | decides whether we can fetch weights/envs at all (and from where) |
| 6 disk | space on `$HOME`, `/scratch/bmb646`, quota | weights are 16–140 GB each |
| 7 project inputs | `full_corpus` PDFs + manifest present, repo commit | DEV draw prerequisites |

### Optional extra, if section 2 shows no 7B/32B/70B you want

(only listing — not pulling anything):

```bash
module load ollama && ollama list
```

## Part 2 — measured-throughput test plan (GPU; **ask first**)

Goal: replace the guessed tokens/s in the design doc (§8) with measurements, per **engine × model**.

* Tool: `scripts/01_data_preproccessing/v6_bench.py`, driven by `run_v6_poc.sbatch STEP=bench`.
* Load: the real stage-2 prompt + real JSON schema over DEV abstracts at three prompt lengths
  (≈0.4k, 3k, 11k tokens) and client concurrency 1/4/8/16/32; every prompt distinct (so prefix
  caching cannot flatter it) plus one shared-prefix series.
* Reported per cell: requests/s, prompt-tok/s, completion-tok/s, p50/p95 latency, malformed,
  timeouts, truncated.
* Cells (each ≈ 10–25 min including model load; one job each):

| job | engine | model | needs |
|---|---|---|---|
| T1 | Ollama `NUM_PARALLEL=1` | `mistral:latest` | staged ✔ (per Phase 0 notes) |
| T2 | Ollama `NUM_PARALLEL=8` | `mistral:latest` | staged ✔ — shows what Ollama parallelism buys |
| T3 | Ollama `NUM_PARALLEL=8` | `qwen2.5:32b` | staged ✔ |
| T4 | vLLM | same family as T3 in HF format (e.g. Qwen2.5-32B-Instruct) | vLLM + HF weights (Part 3) |
| T5 | vLLM | a ~8B HF model | vLLM + weights |
| T6 *(optional)* | vLLM FP8 | a ~70B | H200 + ~70 GB weights |

Command pattern (partition from the inventory; **not submitted — waiting for OK**):

```bash
sbatch --partition=<PARTITION> --export=ALL,STEP=bench,ENGINE=ollama,MODEL=mistral:latest,NUM_PARALLEL=1 \
       scripts/01_data_preproccessing/run_v6_poc.sbatch
```

Output lands in `results/v6_poc/<arm>_<jobid>/bench/bench.md` (paste it back).

## Part 3 — only if Part 1 shows gaps (**needs your OK before anything is downloaded**)

| gap | action | size |
|---|---|---|
| no vLLM | conda env with the `vllm` wheel on a login node, or an Apptainer image of the vLLM OpenAI server | ≈ 10 GB |
| no HF weights for a candidate | `huggingface-cli download <repo> --local-dir /scratch/bmb646/hf/<name>` | 8B ≈ 16 GB · 14B ≈ 30 GB · 32B ≈ 66 GB · 70B ≈ 140 GB (≈ 70 GB FP8) |
| network blocked on login node | stage via your laptop + `scp`/Globus; or only Ollama arms | — |

I will write the exact download commands (repo ids, `--local-dir`, revision pinning so the manifest
records the commit) once I see the inventory.
