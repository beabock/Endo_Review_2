# v6 proof of concept — plan (≤25 papers, 2–3 models). **Nothing submitted; waiting for Bea's OK.**

2026-11-05, Thread B. Companion to `NPH_extraction_v6_design.md`.

## 1. Purpose (and what it is not)

Not a model comparison — 25 papers cannot rank models. It answers four **go/no-go** questions
before the DEV bake-off and before the reviewer vocabulary is frozen any further:

1. **Is the locked schema feasible for local models?** (Phase 0 notes: "check that the schema isn't too hard" — a failure here means the workbook vocab must be simplified *now*, while reviewers are mid-annotation.) Metrics: unrecoverable-call rate, truncated outputs, fields stuck on one value.
2. **Does staging help at all?** Same model (`mistral`), v5 single-call vs v6 staged, eyeballed on the same papers.
3. **How fast is each engine/model?** Measured tokens/s, papers/hour, GPU-s/paper — replaces the guesses in design §8.
4. **Does quote verification work mechanically?** Quote-support rate, flag rate, and what a "unsupported" flag looks like in practice (are they real hallucinations or PDF-text mismatches?).

## 2. Papers

The **first 25 rows of the DEV draw** (`dev_set_selected.csv`, `poc_prefix_25`). They are
balanced on their own (era × design × doc type), contain both abstract-only and full-text papers,
exclude the 230 TEST papers and the 2 MOCK papers, and are the first 25 Bea annotates — so the PoC
can be scored the moment she finishes them. Each PoC paper is run as an abstract; the ~10 with PDFs
are also run as full text (paired abstract/full-text, as in TEST).

Prerequisite (CPU, no GPU, minutes): run the DEV draw on Monsoon so table-heaviness is balanced and
the PDFs are staged:

```bash
cd ~/endo_review
python scripts/04_analyses/draw_dev_set.py --stage draw \
    --pdf-manifest /scratch/bmb646/full_corpus/pdf_manifest.csv --pdf-dir /scratch/bmb646/full_corpus
bash results/manual_validation/dev_set/copy_dev_pdfs.sh        # -> ~/dev_pdfs/D002b.pdf ...
```

then copy `results/manual_validation/dev_set/` back to the laptop and run `--stage sheet` (needs only
`dev_set_selected.csv` and the reviewer template) to produce `devset_bea.xlsx`.
(The local test draw already works: 40 papers, 24 abstract-only + 16 full-text, no reviewer file
touched.)

## 3. Arms

| arm | engine | model | pipeline | why |
|---|---|---|---|---|
| 0 | Ollama | `mistral:latest` | **v5** `monsoon_extract.py` (unchanged) | baseline = what the manuscript numbers came from (modulo the full-text fix) |
| 1 | Ollama | `mistral:latest` | **v6 staged** | same model as arm 0 ⇒ isolates the *architecture* effect |
| 2 | Ollama | `qwen2.5:32b` | v6 staged | already staged; the mid-tier point; also the "Ollama is too slow for 32B" measurement |
| 3 | vLLM *(if available)* | a 32B in HF format (same family as arm 2) **or** a ~8B of a second family | v6 staged | engine effect on speed and accuracy; second-family check |

Arm 3 is conditional on the inventory (vLLM + weights). If it is missing, the PoC runs arms 0–2 and
the vLLM question stays open — I would then propose Part 3 downloads before the DEV bake-off.
Arms 0–2 need nothing that is not already staged (per the Phase 0 notes — the inventory confirms).

## 4. Jobs (one per arm; 1 GPU each; ≈ 1–3 h wall including model load)

Written in `scripts/01_data_preproccessing/run_v6_poc.sbatch` (`bash -n` checked, not run):
starts the server, logs `nvidia-smi` and a compute-node network check, runs the throughput bench and
then abstract + full-text PoC runs, optionally the v5 baseline, and prints a summary. Resumable
(`papers.jsonl`), writes a run manifest. Partition and GPU come from the command line.

```bash
# arm 0 + 1  (7B, Ollama; v5 baseline + v6 staged in the same job)
sbatch --partition=<PARTITION> --time=02:00:00 \
  --export=ALL,STEP=both,ENGINE=ollama,MODEL=mistral:latest,RUN_BASELINE_V5=1 \
  scripts/01_data_preproccessing/run_v6_poc.sbatch

# arm 2  (32B, Ollama)
sbatch --partition=<PARTITION> --time=03:00:00 \
  --export=ALL,STEP=both,ENGINE=ollama,MODEL=qwen2.5:32b,NUM_PARALLEL=4 \
  scripts/01_data_preproccessing/run_v6_poc.sbatch

# arm 3  (vLLM; fill in after the inventory)
sbatch --partition=<PARTITION> --time=03:00:00 \
  --export=ALL,STEP=both,ENGINE=vllm,MODEL=<served-name>,MODEL_PATH=<hf-dir>,VLLM_SETUP="<activate env>" \
  scripts/01_data_preproccessing/run_v6_poc.sbatch
```

GPU choice: 7B fits anything; Q4 32B (~20 GB + KV cache for `NUM_PARALLEL × NUM_CTX` tokens) fits an
A100-40 at `NUM_PARALLEL=2–4`, comfortably an A100-80/H200; bf16 32B (~66 GB) needs an H200 or
A100-80. Whichever partition is chosen, **ask first** — I will not submit.

## 5. What I will report back (from `run_stats.json`, `bench.md`, `v6_rows.csv`)

* per arm: papers/hour, GPU-s/paper, prompt/completion tokens, tokens/s, per-stage malformed/timeout/
  truncation counts;
* quote-support rate (exact/fuzzy/none) for entity quotes and for lifestyle/effect quotes, share of
  pairs flagged, and a hand-read of 10 flagged items (real hallucination vs PDF text mismatch);
* arm 0 vs arm 1 on the same papers: pairs found, side-by-side for 3–5 papers (recovered/missed);
* field distributions per arm (a field stuck on one value = infeasible vocab);
* uncovered-name candidates per paper (the recall-risk proxy);
* once Bea has annotated the first 25: P/R/F1 and per-field AC1 via `score_groundtruth.py` on
  `devset_bea.xlsx` (needs the S1 decision first — the scorer currently reads the LIFESTYLE column as
  `evidence_basis`), reported as *descriptive*, not as a ranking.

## 6. Acceptance for moving on to the DEV bake-off

* ≤ 2 % unrecoverable calls on at least one arm (else the schema/decoder combination needs work);
* no judgment field collapses to a single value in every arm;
* staged ≥ v5 on pairs found for the same model (otherwise the redesign is not earning its cost);
* a measured throughput for at least one production-viable engine/model, so gate G4 can be computed.

## 7. Risks I already know about

* `extract_v6_poc.py` is **unit-tested with a mock backend only**; the first real run may need
  small client fixes (Ollama vs vLLM schema dialects: `anyOf`-free schemas are used on purpose;
  vLLM's structured-output option names changed between versions — `VLLM_EXTRA_ARGS` is the escape
  hatch).
* Full-text mode needs `pymupdf`/`pymupdf4llm` on the compute node (installed into `.venv_v6` — needs
  internet once, or create the venv on the login node first).
* Ollama + `NUM_PARALLEL` multiplies KV-cache memory; if the 32B arm OOMs, lower `NUM_PARALLEL`.
* OCR is off in the PoC (scans are skipped and logged); production keeps `ocrmypdf`.
