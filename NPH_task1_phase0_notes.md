# Task 1 — Phase 0 code drop (review gate)

Status: **code written, nothing run at scale.** Branch `nph-task1-fulltext-revalidation`
(off `master`). 2026-09-02.

Phase 0 = "code only, no scaled compute" from `NPH_task1_paired_validation_plan.md` §3.

## The models do NOT run next — the reviewers come first

Corrected sequencing (Bea, 2026-09-02). The manual reviewers open papers by DOI; they
never see pipeline output. So the models are **not** on the critical path right now. What
unblocks the reviewers:

1. **`fetch_fulltext_pdfs.py --dry-run`** on all ~19k DOIs → coverage report. No models,
   ~30–60 min. Tells us the real full-text / abstract split.
2. **`fetch_fulltext_pdfs.py`** real pull for the DOIs we can get → validated PDF corpus
   (+ OCR pass on scans). No models. This is the "re-download the papers" step.
3. **Re-draw the Task 2 sample** against the final full-text set (the current sample's
   full-text picks are based on the old, mostly-gone corpus) → send workbooks to
   Nancy / Kitty / Ian / Jack.

The bake-off (Phase 1) and the scaled re-extraction (Phase 2) run **in parallel with the
reviewers**, on their own clock — they only need to be finished before the reviewers hand
their annotations back (weeks out). The one reason to run the 25-paper Phase 1 POC
*sooner* rather than later: it's the check that the locked schema isn't too hard for the
models. If it is, we'd want to simplify it — and the Task 2 workbook vocab is tied to the
schema, so better to catch that before the workbooks go out. Low risk (the schema only
asks what we're already asking humans), but worth a day.

This note is still the review gate for the code: sanity-check the four files, answer the
two remaining questions, then step 1 runs.

---

## What changed

### New: `scripts/01_data_preproccessing/extract_schema.py`
Single source of truth for the re-extraction:
- the JSON schema handed to Ollama for **schema-constrained decoding** (`format=<schema>`,
  not free-form `format="json"` — measurably fewer malformed rows);
- the controlled vocabularies as short machine tokens;
- the prompt text;
- **`HUMAN_TO_TOKEN`** — maps every Task 2 workbook dropdown label to the same token, so
  `score_groundtruth.py` compares model output and human annotation on one axis.

Field names + value sets are **locked to the Task 2 workbook** (`build_groundtruth_sample.py`
VOCAB / `guild_rubric.md`). Per interaction: `fungus`, `host_plant`, `tissue`,
`fungal_lifestyle`, `effect_on_host`, `evidence_basis`. Per paper: Q1–Q11 equivalents +
the 6 detection-method flags + a metabarcoding `community_summary`.
`primary_guild` is still emitted (derived from `fungal_lifestyle`) so the current
`02_ollama_cleanup.R` keeps working unchanged.

### New: `scripts/01_data_preproccessing/pdf_segment.py`
Structure-aware parse → targeted segmentation → chunking (plan §2b):
1. parse with `pymupdf4llm` (markdown, sections + tables) when installed, else a plain
   PyMuPDF page dump;
2. keep Abstract / Intro / Methods / Results / Discussion / Taxonomy sections + table
   captions + any paragraph naming a genus-looking binomial or a country; drop
   References / Acknowledgements / Funding / Supplementary;
3. chunk what's left into context-sized windows (`--max-chars`, sized per model),
   ~1.5k-char overlap, each prefixed `[DOI | section]`;
4. scanned / no-text-layer PDFs are detected and skipped with a logged reason (OCR is
   **out of scope** — open question 2 below).

### Rewrite: `scripts/01_data_preproccessing/monsoon_extract.py` (v4 archived)
Orchestrates: for each paper → segment (or take the abstract) → one schema-constrained
call per chunk → **union + dedup** interactions on `(fungus, host, tissue-set)`, union
biome/method lists, reconcile paper-level fields → write `global_endo_extraction_v5.csv`.
- `--mode abstract | fulltext` (same schema both ways → Phase 3 joins on `paper_id`);
- `--model` for the bake-off; explicit `num_ctx` + `temperature=0` per model;
- resumable, `--shard/--nshards`, per-call timeout.

### Rewrite: `scripts/01_data_preproccessing/fetch_fulltext_pdfs.py` (v4 archived)
Six resolvers in order — Unpaywall → OpenAlex → Europe PMC → Semantic Scholar → CORE →
publisher `<meta citation_pdf_url>` — until a **validated** PDF lands (magic bytes +
PyMuPDF open + ≥1 page; rejects HTML error pages saved as `.pdf`). Resumable, shardable,
per-DOI manifest + structured miss log. `--dry-run` does lookups only and writes
`coverage_report.csv` (missing PDFs grouped by publisher/journal → Referee 2's
"are abstract-only papers concentrated in particular publishers?").

### OCR for scanned PDFs — `pdf_segment.ocr_pdf` (Bea: OCR when needed, don't skew against old papers)
`parse_pdf` detects an image-only PDF (≈no text layer on the first pages) and runs
`ocrmypdf` (Tesseract, `eng+fra+spa+deu+por` by default, `skip_text=True`), caching the
OCR'd copy in `<pdf-dir>/_ocr/`. Falls back to "skip + log" only if `ocrmypdf` isn't
installed. `monsoon_extract.py --no-ocr` turns it off. Adds a dependency
(`ocrmypdf` + tesseract lang packs on Monsoon) and ~5–30 s/scanned-paper, one-time.

### Fix (plan §1b, "handle it whenever makes sense"): `06_detect_ubiquity_claims_ollama.py`
- `collect_snippets` no longer returns `text[:8000]`. It now takes ±`snippet_window`
  windows around each ubiquity keyword (mericterm list already in the file), merged,
  capped at `--max-context-chars`; prefix fallback only when there is no keyword hit.
  A claim in the Discussion of a 12-page paper is no longer invisible.
- `ollama_generate_json` sets `num_ctx` (new `--num-ctx`, default 8192) and
  `temperature` explicitly — the old call inherited Ollama's 2048-token default and
  silently truncated even the 8k it was handed.
- **This changes the Prediction-1 / 2.7%-ubiquity number.** Needs a re-run (cheap,
  abstracts + the ~280 local PDFs) and the manuscript figure updated. Flag for the
  response-to-referees.

---

## Decisions taken (were open questions in the plan)

| # | question | decision | reversible? |
|---|---|---|---|
| §4.4 | GROBID vs pymupdf4llm/docling | **pymupdf4llm** — pip-only, no service to stand up on Monsoon, resumable. | yes — `pdf_segment.parse_pdf` is the only touch-point |
| §4.2 | OCR scanned PDFs? | **yes, OCR them** (ocrmypdf/Tesseract) — skipping scans biases against exactly the old / non-English papers the study is about. Implemented. | — |
| schema §5.1 | 4-field split vs lighter | **use the Task 2 workbook's 3 interaction fields** — already the negotiated set, keeps human + model directly comparable | — |
| schema §5.3 | split `mutualist_*` | no — folded into `effect_on_host = beneficial` + `interaction_notes` | yes |
| §3.4 | re-extraction scope | **whole corpus, new schema, bake-off winner.** The new fields (`effect_on_host`, `evidence_basis`, Q2–Q11) don't exist in v4 at all, and the guild-circularity / commensalism results are corpus-level, so all ~18.7k abstracts + ~3k full texts get re-extracted regardless of which model wins. | — |

## Still open — 2 questions, neither blocks the PDF download

1. **P/R/F1 bar** (plan §4.3) — the pre-registered rule for "abstracts are good enough,
   keep the combined corpus for the headline claims" vs "abstracts miss too much, demote
   them to a supplementary lower-confidence layer." Setting it *before* seeing results is
   what makes it defensible to referees. **Proposed rule (approve / adjust):**
   > abstract→fulltext agreement is "adequate" if, on the paired set, interaction-level
   > F1 ≥ 0.75 **and** the fungal-taxon-per-paper count is not systematically lower for
   > abstracts (paired Wilcoxon p > 0.05 or median difference ≤ 1) **and** country/biome
   > Cohen's κ ≥ 0.6. Otherwise headline taxonomic + geographic claims are restricted to
   > the full-text subset.

   0.75 / 0.6 are mid-range for LLM extraction of standardised ecological fields (the
   ~55–75% P/R literature in the plan). Not needed until Phase 2 — but good to lock now.
2. **Bake-off shortlist.** See the next section — pick from there, or say "those + pull
   the rest." Not needed until Phase 1.

## Bake-off — model options

Decided downstream of the Task 2 ground truth (score every candidate on the same
sample, pick on F1-per-GPU-second + malformed-rate). Monsoon GPUs: h200 (≈140 GB, runs
70B q4 easily), a100 (40–80 GB, up to ≈32B). Ollama 0.20.5 supports schema-constrained
`format`.

| model | size | why include |
|---|---|---|
| `mistral` 7B | 7B | incumbent (v4) — the baseline everything is compared against |
| `qwen2.5:7b` | 7B | modern small model, strong at structured extraction, cheap |
| `qwen2.5:32b` | 32B | already staged; the mid-tier quality point |
| `llama3.1:8b` | 8B | cross-family check (is Qwen's edge real or task-fit?) |
| `llama3.3:70b` *or* `qwen2.5:72b` | 70B | h200 ceiling — is a big model worth the GPU cost? |
| *(optional)* `gemma2:27b`, `mistral-small` (24B), `qwen3` if available | — | only if the above don't separate cleanly |

Action before Phase 1: `ls /common/contrib/ollama_models/2025-12/manifests/registry.ollama.ai/library/`
to see what's already staged, then `ollama pull` the 2–3 gaps from a login node.

## Run order on Monsoon

### Step 1 (now) — coverage dry-run, no downloads, no GPU
```bash
cd ~/endo_review          # repo checkout, on branch nph-task1-fulltext-revalidation
git pull
mkdir -p results/logs
sbatch --array=0-3 --export=NSHARDS=4,DRY_RUN=1 \
    scripts/01_data_preproccessing/run_fetch_pdfs.sbatch
# ~30-60 min. when all 4 array tasks finish:
python scripts/01_data_preproccessing/merge_pdf_manifests.py \
    --out-dir /scratch/bmb646/full_corpus
```
Look at: `resolvable` % (expected ~55-75%), `coverage_report.csv` (which publishers /
journals we can't reach — the Referee 2 point), `oa_status` breakdown. Decide whether an
OCR dependency install is worth it based on how the real pull goes.

### Step 2 — real PDF pull (after we look at step 1)
```bash
sbatch --array=0-7 --export=NSHARDS=8 \
    scripts/01_data_preproccessing/run_fetch_pdfs.sbatch
python scripts/01_data_preproccessing/merge_pdf_manifests.py --out-dir /scratch/bmb646/full_corpus
```
Then re-draw the Task 2 sample against the real full-text set → workbooks to reviewers.

### Step 3 — 25-paper model POC (parallel track, needs a GPU + Ollama)
```bash
# pick 25 DOIs spanning short/long, table-heavy/prose, taxon-rich/poor -> poc_25.csv
python scripts/01_data_preproccessing/monsoon_extract.py --mode fulltext \
    --manifest /scratch/bmb646/full_corpus/pdf_manifest.csv --pdf-dir /scratch/bmb646/full_corpus \
    --model mistral --out /scratch/bmb646/poc_mistral.csv --limit 25
python scripts/01_data_preproccessing/monsoon_extract.py --mode fulltext ... --model qwen2.5:32b ...
python scripts/01_data_preproccessing/monsoon_extract.py --mode abstract \
    --input poc_25.csv --model mistral --out /scratch/bmb646/poc_abstract.csv
```
(An sbatch wrapper for step 3, modelled on `run_06_ubiquity_claims_ollama.sbatch`, comes
once step 1's numbers are in.)

## Dependencies to add on Monsoon
`pymupdf4llm` (pulls `pymupdf`), `requests`, `ocrmypdf` (+ system `tesseract-ocr` and
language packs `tesseract-ocr-fra/spa/deu/por` — via conda/module or a container).
`ollama` already present. `pypdf` already used by script 06.
