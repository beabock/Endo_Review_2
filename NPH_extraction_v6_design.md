# Extraction v6 — staged architecture, serving, and a pre-specified model bake-off

Status: **design for review (Thread B), 2026-11-05.** Nothing has been run on Monsoon. Local
models only (vLLM / Ollama); no Claude or hosted API anywhere in the pipeline.
Companion files: `NPH_v6_monsoon_inventory.md` (commands for Bea), `NPH_v6_poc_plan.md`
(≤25-paper proof of concept), `scripts/04_analyses/draw_dev_set.py`,
`scripts/01_data_preproccessing/{extract_v6_poc.py, v6_bench.py, run_v6_poc.sbatch}`,
`scripts/utils/monsoon_inventory_v6.sh`.

---

## 0. Summary — and where I disagree with the brief

I keep the four-stage skeleton (paper card → entities → classification → verification) and the
DEV/TEST split. I changed eight things; the reasons are in §3.

| # | Brief | Change | Why (short) |
|---|---|---|---|
| 1 | Stage 1 reads abstract + methods | Abstract + **intro start** + methods + captions + **keyword windows**; regex *proposes*, LLM *decides*, quote *verifies* | Ubiquity claims live in the intro, coordinates in tables, hosts in Results |
| 2 | Stage 2 per chunk, union + dedup | Same, but each chunk call gets the Stage-1 **study hosts**; name-finder is a **recall audit**, not a generator | Results chunks name the fungus but not the plant; gnfinder-style hits would add noise as entities |
| 3 | Stage 3 per interaction | Per **group of ≤5 pairs**, plus the paper card | ~100k extra calls otherwise; humans use paper-level context (fungus source, methods) for `evidence_basis` |
| 4 | Stage 4 mandatory quote + substring check | Keep, but (a) absence labels are exempt, (b) add quote-only **re-derivation**, (c) never use quote-support rate alone to rank models | A model that says "not reported" everywhere has 100% support; verbatim ≠ entailment |
| 5 | Country/biome deterministic from coordinates | **Two columns each**: `*_named` (scored against the human) and `*_resolved` (analysis) | Human Q6a/Q8 are "what the text says", not "where the point falls"; most papers will have no coordinates |
| 6 | vLLM from HF weights | Agreed; **selection must be done on the engine that will run production** | Q4 GGUF on Ollama ≠ bf16/FP8 on vLLM; "the model" = weights + quantisation + engine + version |
| 7 | Staging everywhere | Staging for full text; **abstracts get an A/B arm** (1 call vs staged) | Staging solves long-document problems; abstracts may not need it |
| 8 | DEV ≈ 40 papers | Keep, but be explicit: **underpowered for small differences** → margins fixed in advance, ≤3 prompt revisions | n≈40 papers / ~150 pairs gives ±0.07 on F1 |

**Four schema/vocabulary mismatches I found and did NOT fix (need Bea, §2):** the workbooks split
`evidence_basis` in two; `extract_schema.py` has one; the scorer reads whichever column comes
last. Q11 (ubiquity), the 4-level inoculation answer and yes/no/not-stated methods exist in the
workbooks but not in `extract_schema.py`. And v5 never writes `sampling_country`,
`coordinates_given` or `fungus_source` to its CSV.

---

## 1. Why a redesign (what v5 actually does)

`monsoon_extract.py` (v5): one schema-constrained call per ~20k-char chunk asks for ~17 paper-level
fields **and** the interaction list at once, then `merge_chunk_objs()` reconciles with "first
informative value wins". Consequences:

* interpretive fields (`effect_on_host`, `evidence_basis`, `fungal_lifestyle`) are decided from a
  chunk that may not contain the evidence (the inoculation experiment is two chunks away);
* paper-level fields are chosen by chunk order, not by evidence;
* biome/country are model guesses; nothing checks that any label is grounded in the text.

Bugs found while reading (v5 is superseded, so these are recorded, not patched):
`merge_chunk_objs()` and `to_rows()` never carry `sampling_country`, `coordinates_given`,
`fungus_source` — those columns are blank in every v5 output although `score_groundtruth.py`
scores them; the legacy `country` alias is filled from `sampling_location`;
`extract_schema.py`'s question numbers (Q10 = n pairs, Q11 = sterilisation) are one off from the
workbook (Q9, Q10).

---

## 2. Schema lock and the mismatches I found (decisions needed)

I read the vocabularies from `extract_schema.py` (imported, not copied — `extract_v6_poc.py`
cannot drift from it) and compared them with the Review headers and Lists sheet of
`groundtruth_kappa_MASTER.xlsx` (read-only), `reviewer_guide.md/.docx` and `score_groundtruth.py`.

| # | Finding | Evidence | Needs |
|---|---|---|---|
| S1 | **`evidence_basis` is two columns in every workbook** (`evidence_basis_n (how the EFFECT was shown)` and `… (how the LIFESTYLE was shown)`), but `extract_schema.py` has one field, `reviewer_guide.md/.docx` still describe one field with the rule "effect, else lifestyle", and `score_groundtruth.py`'s `SLOT_RE` keeps the **last** matching column per slot → it silently scores the LIFESTYLE column as `evidence_basis`. | all 7 workbooks have 5 `LIFESTYLE was` columns | **Bea: which is canonical?** v6 PoC emits both (`evidence_basis_effect`, `evidence_basis_lifestyle`) plus the legacy single field computed by the guide's rule. The scorer needs the matching fix (not made here). |
| S2 | Workbook has **Q11 ubiquity** (`all or nearly all plants`), a **4-level inoculation** answer (confirmed / not confirmed / no / not stated) and **methods as yes/no/unclear/not stated**. `extract_schema.py` v5.4 has none of Q11/inoculation levels, and `detection_methods` is a *set* (cannot say "no" vs "not stated"). | Lists sheet: `inoculation`, `method_status` | **Approve adding** `ubiquity_claim`, `inoculation`, per-method yes/no/not_stated to the extraction schema (additions, no existing vocab changed). PoC already emits them as proposed fields. |
| S3 | Lifestyle/effect/evidence lists now end with **"other (type over this cell…)"**; the extractor has no `other`. | Lists sheet | Scorer already passes typed values through; the model's enums stay closed. Disagreement on typed "other" counts as a miss — acceptable, but know it. |
| S4 | v5 drops three scored fields (§1). | `monsoon_extract.py` | v6 fixes by construction. |
| S5 | `extract_schema.py` still emits `sampling_approach`, `n_distinct_pairs`, `is_fungus_in_plant_study`; the workbook dropped Q1/sampling approach/n pairs is now Q9. | headers | Harmless extras; v6 derives `n_distinct_pairs` from the entity list instead of asking the model. |

I have **not** changed any field name or value in `extract_schema.py`, the workbooks, the guide or
the scorer. `extract_v6_poc.py` only *adds* clearly-labelled columns.

---

## 3. Architecture

```
PDF / abstract
   │
   ├─ Stage 0  (CPU, deterministic)  parse → sections; regex proposals: coordinates, country
   │           names, sterilisation/ubiquity/inoculation keyword windows; language guess;
   │           capitalised-binomial candidates (+ COL genus whitelist when available)
   │
   ├─ Stage 1  PAPER CARD  (1 call)   input: title + abstract + intro start + methods + table/
   │           figure captions + keyword windows.  Output (quote BEFORE label for every judgment):
   │           text_status, primary_aim, fungus_source, sampling_approach, uncultured_taxa,
   │           strain_variation, country_named, coordinates_text, location_status, habitat_text,
   │           biome_text, sterilisation_checked, methods ×4, inoculation, ubiquity_claim,
   │           study_hosts[], community_summary
   │
   ├─ Stage 2  ENTITIES  (1 call per chunk, N chunks)  input: chunk + study_hosts.
   │           Output: {evidence_quote, fungus, host_plant, tissue[]}.  Union + dedup on
   │           (name_key(fungus), host_key).  Every entity must quote the sentence/table row that
   │           names it.  Then RECALL AUDIT: binomials in the text that no entity covers are
   │           listed (never auto-added) → counted as a recall-risk metric, optionally a 2b pass.
   │
   ├─ Stage 3  CLASSIFY  (1 call per ≤5 ranked pairs)  input: paper card + each pair's retrieved
   │           evidence windows (sentences naming the fungus / abbreviation / host + effect-
   │           trigger sentences).  Output per pair: lifestyle_quote, fungal_lifestyle,
   │           effect_quote, effect_on_host, evidence_basis_effect, evidence_basis_lifestyle.
   │
   ├─ Stage 4  VERIFY  (mostly CPU)  (a) normalised-substring check of every quote against the text
   │           the model saw (exact / rapidfuzz ≥92 / none);  (b) consistency rules (effect set but
   │           basis not_stated; "experimental" but inoculation = no);  (c) optional quote-only
   │           re-derivation of the label (small call);  (d) flagged items → optional second model /
   │           k=3 self-consistency (budget ≤10 % of items).  Nothing is silently overwritten:
   │           raw label + `verification_flags` are both kept; analysis uses a policy fixed in advance.
   │
   └─ Geography (CPU)  coordinates → country / WWF biome by polygon lookup (`*_resolved`);
               `country_named` / `biome_text` stay the text-derived values scored against humans.
```

### 3.1 Stage 1 — what goes in, and "regex proposes, LLM decides, quote verifies"

* The brief's "abstract + methods" misses: the **ubiquity claim** (usually intro paragraph 1; this
  is workbook Q11 and Thread F's detector), **coordinates in tables**, **host named only in
  Results**. Context = title, abstract, first ~2.5k chars of the Introduction, Methods (capped),
  table/figure captions, plus ±350-char windows around keyword hits (`geo`, `steril`, `ubiq`,
  `inoc`). If heading detection fails the Methods slot falls back to a whole-text prefix.
* Numbers are where LLMs mis-transcribe, so **coordinates are found by regex** (decimal degrees,
  DMS with hemisphere) and handed to the model only as candidates; the model chooses whether one is
  the *sampling* site and copies it. Language (Q3) is a detector, not a prompt.
* One call vs two (card vs geography) is an ablation, not a decision: start with one.
* `study_hosts[]` is new and exists for Stage 2.

### 3.2 Stage 2 — recall

* Chunks come from `pdf_segment.chunk_segments`. Each call gets `STUDY HOSTS (from the methods)`.
* Prompt rules are transcribed from the reviewer guide §7 (verbatim names, drop strain codes, group
  words and OTU codes are not names, fungi only, aerial_parts). Strain-code stripping is *also*
  done deterministically in `name_key()` so dedup does not depend on the model obeying.
* **Ranking for the 5-block cap.** Humans fill at most 5 blocks "title → abstract → most common".
  The pipeline keeps *all* entities and writes `listed_rank` from the same rule (title mention ×3,
  abstract ×2, then text frequency) so top-5 recall is comparable and `score_groundtruth.py`'s
  "partial list ⇒ recall only" rule applies (human total > 5 ⇒ extra model pairs are not FPs).
* **Name finder.** I recommend *not* adding gnfinder as a dependency: it needs a Go binary, and its
  main value (verification against sources) needs the network. A capitalised-binomial regex checked
  against the local COL fungal genus list gives most of the audit value. The audit interface is
  pluggable; `which gnfinder` is in the inventory script in case it is already there.
  Fungal-genus whitelisting also gives a cheap **bacteria/plant filter** (the guide excludes
  bacteria; 7B models list *Bacillus* and host plants as fungi).
* Metabarcoding: a table can name 100+ genera. Cap 40 per chunk; `community_summary` carries the
  rest (as the humans do).

### 3.3 Stage 3 — grouped, with the paper card

Per-pair calls would add ~10⁵ calls and, more importantly, remove the paper-level context humans
use: the guide's three "most common cases" for `evidence_basis` are decided by `fungus_source`
(from study plants vs called-an-endophyte-in-passing vs cited). So Stage 3 gets the card, groups ≤5
pairs per call (same size as the human block count), and each pair carries its own retrieved
evidence (cap 3.5k chars; fallback = title + abstract for single-fungus papers). Property order is
quote → label, so the constrained decoder must *write the evidence before committing* — a cheap
form of reasoning that also makes Stage 4 possible.

### 3.4 Stage 4 — what verification can and cannot do

* **Can:** catch labels with no support in the text the model saw (precision of *positive*
  judgments), invented names (entity quote not found), quote–label incoherence (re-derivation).
* **Cannot:** detect a *missed* positive. Absence labels (`not_reported`, `not_stated`, `no`,
  `unclear`) cannot have a quote, so a model that abstains scores perfect "support". That is why
  quote-support is a **gate**, never a ranking criterion (§6), and why recall of positives is read
  off the human comparison.
* Policy fixed now: an unsupported positive label is *kept* in the output with
  `verification_flags`, and analyses report results both with and without flagged labels (a
  sensitivity analysis), rather than silently downgrading to `not_reported`.

### 3.5 Deterministic geography — two columns each

Workbook Q6a is "the country the **text names** (never look one up; coordinates-only ⇒ not
stated)", Q8 is "habitat words in the **text**, never guess from plant or country", and its value
list includes agriculture / urban / greenhouse / marine, which are not WWF biomes. A
coordinates→WWF lookup is therefore a *different construct*. So:

| column | source | scored against human? | used for |
|---|---|---|---|
| `country_named` / `sampling_country` | model + quote check | yes (Q6a) | agreement |
| `country_resolved` | polygon lookup of coordinates; else `country_named`; else null | no | analysis |
| `biome_text` / `biome` | model mapping of the text's habitat words (guide table) | yes (Q8) | agreement |
| `wwf_biome_coords` | WWF/Olson polygon lookup | no (diagnostic where both exist) | Task-4 realm/biome analyses |

Coverage reality: the share of papers with coordinates is the human Q6b "yes" rate — unknown until
annotation finishes; I expect a minority. Papers without coordinates fall back to the existing
`country → realm` table (`scripts/utils/country_biogeographic_realm.csv`). The WWF terrestrial
ecoregion shapefile (Olson et al. 2001 / Dinerstein et al. 2017) needs a one-time download and
`geopandas`/`shapely`; plan, not done. Optional offline GeoNames locality lookup is a later
extension (flag `geocode_confidence`), not part of the first build.

### 3.6 Abstracts

Abstracts are ~60 % of the call count but short. Two arms on DEV: **A** = v5-style single call with
the quote fields; **B** = the staged pipeline on the abstract. Pick on DEV with the same rule (§6).

---

## 4. Data flow and outputs

Per run directory: `run_manifest.json`, `raw_calls.jsonl.gz` (every call: stage, paper, prompt hash,
status, latency, tokens, response), `papers.jsonl` (full structured record; **resume key**),
`v6_rows.csv` (flat, `extract_schema.CSV_COLUMNS` + extra columns so `score_groundtruth.py` can read
it), `run_stats.json` (calls, malformed, tokens, quote-support, flags, s/paper).

`data_source` is `abstract-reextract-v6` / `fulltext-reextract-v6` (the scorer decides the stage by
the substring "full"). Output rows carry `run_id`, `arm`, `model`, `pipeline_version`.

### Reproducibility manifest (every run)

`run_id`, git commit + dirty flag, SHA-256 of the script, `extract_schema.py` and the input file,
**prompt hashes per stage**, schema version, seed, sampling parameters, host / SLURM job / GPU,
Python version, and the **server's own answer**: vLLM `/version` + `/v1/models` (HF snapshot path =
revision hash) or Ollama `/api/version` + model digest + quantisation. The SI table of "which model"
is generated from these, not typed.

---

## 5. Serving

| | Ollama | vLLM |
|---|---|---|
| batching | effectively sequential per model; `OLLAMA_NUM_PARALLEL` adds slots (KV memory = slots × num_ctx) | continuous batching, prefix caching (Stage 3/4 share the card prefix), JSON-schema guided decoding |
| weights | the staged GGUF Q4 blobs | **HF-format** (safetensors) — Ollama blobs are not directly usable; vLLM's GGUF loader is experimental, single-file, architecture-limited → fallback only |
| status here | installed (module `ollama`, 0.20.5 per Phase 0 notes), 2 models staged in my notes | **unknown** — the inventory answers it |

Decision tree after the inventory (§ in `NPH_v6_monsoon_inventory.md`):
1. vLLM module/container present **and** HF weights for ≥2 candidates present → use as is.
2. vLLM absent: conda env with the `vllm` wheel (needs login-node internet and a driver new
   enough for its CUDA build) **or** an Apptainer image from the vLLM OpenAI-server container
   (needs Docker Hub reach + ~10 GB); weights from Hugging Face are 16 GB (8B bf16), ~30 GB (14B),
   ~66 GB (32B), ~140 GB (70B; ~70 GB in FP8). **Any download > ~50 GB total needs Bea's OK.**
3. Neither: several Ollama instances (one per GPU) + `OLLAMA_NUM_PARALLEL=8`; or llama.cpp
   `llama-server --parallel N --cont-batching` on the *same* GGUF blobs (Ollama blobs are plain
   GGUF) if a CUDA build can be made. Measure; do not assume.

Measured-throughput test plan: `v6_bench.py` (no PDFs; stage-2 prompt + real schema over DEV
abstracts at 0.4k / 3k / 11k tokens, concurrency 1–32, distinct prompts so caching cannot flatter it,
plus a shared-prefix series). Output: req/s, prompt-tok/s, completion-tok/s, p50/p95, malformed,
truncated. Run per engine × model via `run_v6_poc.sbatch STEP=bench`.

Licences to record (publication): Qwen2.5 ≤ 32B and Qwen3 — Apache-2.0; Qwen2.5-72B — Qwen licence;
Llama 3.x — Llama community licence; Gemma — Gemma terms; Mistral-Small 3.x — Apache-2.0;
Mistral-7B — Apache-2.0. (Check the exact model card at download time.)

---

## 6. DEV / TEST protocol and model selection (pre-specified)

**TEST** = the 230-paper ground-truth sample (310 annotation rows) + nothing else. **DEV** = ~40
papers drawn by `draw_dev_set.py`, annotated by Bea only, blind, same workbook layout.

### 6.1 The DEV draw (`draw_dev_set.py`)

* Excludes 232 papers: the 230 in `sample_selected.csv`, the 2 MOCK papers, and (belt and braces)
  every paper_id found in any `groundtruth_*.xlsx` (read-only).
* 24 abstract-only + 16 full-text (≈ 8.5 h of annotation; `--n-abstract/--n-fulltext` to change).
  One row per paper — the paired abstract row is a TEST measure.
* Marginal-quota sampling on **era** (sqrt-proportional: over-weights pre-2000), **design hint**
  (30 % metabarcoding / 40 % isolate-culture / 30 % other, from title+abstract regex; bacteria-only
  papers excluded from "metabarcoding"), and — full text only, needs the PDFs, so run on Monsoon —
  **table-heavy vs prose** (≥4 distinct "Table N" captions, or 3 + digit fraction ≥ 0.10).
  Not proportional on purpose: DEV exists to find where models break.
* **Prefix-balanced order**: row ids `D001a…` (a = abstract, b = full text) are in an order where
  any prefix is balanced; the first 25 are the PoC set, so Bea can annotate those first.
* Frame facts (local test draw): after exclusions 5,672 full-text-eligible and 13,428 abstract-only
  papers; design hint classes in the frame ≈ 10 % metabarcoding / 21 % isolate / 69 % other. The
  hint is a heuristic (the draw report prints the cross-tab) — it stratifies, it does not label.
* Corpus reality check: the draw includes papers that are *not* fungus-in-plant studies (bacterial
  16S, etc.), as the corpus does. That is intended — the pipeline must say so.
* **The local test draw has no table-heaviness**; the real draw is the same command on Monsoon with
  `--pdf-dir` and the latest manifest (it will change as Thread C adds OA coverage — DEV papers must
  be re-checked to still have a PDF; the script only draws papers that have one at draw time).

### 6.2 Rules fixed before any DEV result exists

* **Gates** (must pass to be eligible): G1 unrecoverable call rate (malformed + timeout after one
  retry) ≤ 2 %; G2 no paper silently dropped (every paper has a record or an explicit failure);
  G3 quote-support ≥ 90 % among *non-empty* judgment quotes; G4 projected full-corpus GPU-hours ≤
  budget B (**Bea to set; I suggest 60**), projected from *measured* production-engine throughput.
* **Ranking among eligible models**, in this order: (R1) pair **recall and F1**, genus-level key,
  partial-list rule, abstract and full-text rows macro-averaged; (R2) macro-AC1 over the
  interaction judgments on matched pairs (fungal_lifestyle, effect_on_host, evidence_basis[×2],
  tissue); (R3) macro-AC1 over paper-level fields (primary_aim, fungus_source,
  location_status, country_named, biome_text, sterilisation, uncultured, strain, ubiquity,
  inoculation). AC1 (Gwet) is primary, κ reported (κ is unstable at these prevalences).
* **Decision**: the best R1 model, unless a cheaper model is within **δ₁ = 0.03 F1 and δ₂ = 0.05
  macro-AC1** on *point estimates* — then take the cheaper one. Paired bootstrap-over-papers 90 % CIs
  are reported but are **not** used to declare ties: with ~40 papers / ~150 pairs the CI half-width
  on an F1 difference is ≈ 0.06–0.08 (my estimate, to be replaced by the bootstrap), so DEV can
  separate model *families and sizes*, not fine prompt variants.
* **Prompt iteration budget**: at most **3** prompt revisions after seeing DEV results, each applied
  to *all* candidates and logged by prompt hash. Then **freeze** model + prompt hashes + schema +
  code (git tag `v6-frozen`) and run TEST **once**.
* **No leakage into TEST**: few-shot examples (if any) come only from the 2 MOCK papers or
  synthetic text, never from the 230 or DEV; the guide's worked examples are synthetic and fine.
* **TEST reporting**: P/R/F1 with bootstrap CIs; per-field AC1/κ **against the human–human AC1 on the
  20-paper kappa block** (the noise ceiling — a model is "as good as a reviewer" only relative to
  that); the abstract-vs-full-text paired rule from Phase 0 is unchanged
  (interaction F1 ≥ 0.75 **and** fungal-taxa-per-paper not systematically lower **and**
  country/biome κ ≥ 0.6) and is evaluated with the frozen model on the paired rows. A bug found
  after TEST may be fixed only as a documented bugfix with both numbers reported.
* Reported alongside: malformed rate, quote-support, flags, **GPU-seconds/paper on the production
  engine**, determinism check (same 25 papers twice: label-flip rate — vLLM batching is not
  bit-reproducible even at temperature 0).

### 6.3 Candidate models

Whatever the inventory shows is actually available, in this order of preference. Three size tiers so
the DEV result answers "is size worth the GPU-hours":

| tier | candidates (use what is staged / obtainable) | role |
|---|---|---|
| ~7–9 B | `mistral` 7B (**incumbent**), Qwen2.5-7B / Qwen3-8B, Llama-3.1-8B | cost floor; continuity with v4/v5 |
| ~24–32 B | `qwen2.5:32b` (**already staged**), Qwen3-32B or 30B-A3B (MoE), Gemma-3-27B, Mistral-Small 24B | likely sweet spot |
| ~70 B | Llama-3.3-70B or Qwen2.5-72B (FP8 on one H200) | ceiling; is it worth 3× the GPU-hours? |

Include the *same family at two engines/quantisations* (e.g. `qwen2.5:32b` Q4 GGUF on Ollama vs
Qwen2.5-32B bf16/FP8 on vLLM) once, to measure how much the engine/quantisation changes accuracy.

---

## 7. Failure modes and mitigations

| failure | where | mitigation |
|---|---|---|
| two-column PDFs interleave, tables flatten to prose, hyphenation | parse | `pymupdf4llm` markdown; `norm_text()` joins line-break hyphens and strips markdown pipes before quote checks; table-heavy DEV stratum measures it |
| heading splitter finds no Methods | Stage 1 | whole-text prefix fallback; `note` records it; count of fallbacks reported |
| OCR garbage on scans | parse | `ocr=False` in the PoC; production uses the existing ocrmypdf cache; fuzzy quote match tolerates OCR noise |
| entity explosion (metabarcoding tables) | Stage 2 | cap 40/chunk, `max_tokens`, `community_summary` |
| host not in the chunk | Stage 2 | study-hosts header; host-less duplicate dropped when the same fungus has a host |
| name drift ("F. oxysporum", authorities, strain codes) | dedup | `name_key()` (genus + epithet, codes/authorities stripped); abbreviation expansion is a production TODO |
| bacteria / plants listed as fungi | Stage 2 | prompt rule + COL fungal-genus whitelist flag |
| degenerate loops under constrained decoding (whitespace, endless list) | all | `max_tokens` cap, `finish_reason == length` counted as truncated, one retry |
| quote hallucination | Stage 4 | substring/fuzzy check, flag; re-derivation |
| abstention gaming | selection | quote-support is a gate only; agreement decides |
| positive judgment missed | all | not detectable by verification — measured against humans (recall) |
| host × fungus pairing wrong across chunks | Stage 2/3 | evidence windows are pair-specific; pair-level F1 on DEV shows it |
| engine/quant mismatch between bake-off and production | process | select on the production engine; manifest records both |
| nondeterminism across runs | process | seed + determinism test; `raw_calls` stored |
| preemption / time limit | process | `papers.jsonl` is append-only, resume skips done papers; production = 4-shard pattern |
| number mis-transcription (coordinates) | Stage 1 | regex finds them; model only selects; quote check |
| corpus not in English (≈ 3 % Chinese etc.) | all | language detector; the DEV draw does not force non-English (Bea reads English/Spanish) — report non-English performance from TEST instead |
| TEST contamination | process | §6.2 |

---

## 8. Compute estimate (assumptions — replace with `v6_bench.py` numbers)

Corpus per Sep 17 manifest: 19,586 DOIs, 5,957 full texts (Thread C may raise this; scale linearly).
All 19.6k get an abstract extraction (the paired comparison needs abstracts for the full-text papers
too).

| item | calls | prompt tok | completion tok |
|---|---|---|---|
| abstract, staged (3 calls: 1.6k+1.3k+1.8k in; 0.45k+0.15k+0.2k out) × 19.6k | 59k | ~92 M | ~16 M |
| abstract, single call (1.5k in, 0.5k out) × 19.6k *(arm A)* | 20k | ~29 M | ~10 M |
| full text, staged: S1 ~9k in; S2 ~2.5 chunks × 5k; S3 ~2 calls × 3k; S4 ~1k → ~28k in, ~1.5k out × 6k | ~39k | ~168 M | ~9 M |
| **staged total (abstract + full text)** | **~100k** | **~260 M** | **~25 M** |

Assumed sustained throughput (**guesses, factor-2 error bars; the bench replaces them**):

| setup | prefill | decode (aggregate) | ⇒ full-corpus GPU-h |
|---|---|---|---|
| 7–8B, vLLM, 1×A100-80 | ~12k tok/s | ~2k tok/s | **~10** |
| 32B, vLLM, 1×H200 (bf16) | ~5k | ~1k | **~21** |
| 70B, vLLM FP8, 1×H200 | ~2k | ~0.5k | **~50** |
| 7B, Ollama sequential | ~2.5k | ~70 | **~130** |
| 32B Q4, Ollama sequential | ~0.8k | ~30 | **~320** |
| Ollama, `NUM_PARALLEL=8` | 2.5–4× better than sequential | | 7B ~40, 32B ~100 |

Take-aways: (i) Ollama-sequential is not viable beyond a 7B; vLLM (or measured parallel Ollama) is
what makes ≥ 32B affordable; (ii) the **bake-off itself is cheap** — a DEV model-run is ≈ 0.6 M prompt
tokens (minutes), TEST ≈ 4 M (minutes on vLLM, 1–2 h on sequential 32B); the cost that matters is
the full-corpus run, which differs by ~5× across tiers; (iii) the budget gate G4 therefore has real
teeth only when throughput is measured on the production engine.

---

## 9. Sequence

| step | what | who / gate |
|---|---|---|
| B0 | inventory (login node, read-only) | **Bea runs, pastes back** |
| B1 | `draw_dev_set.py --stage draw` on Monsoon (CPU) + `copy_dev_pdfs.sh`; `--stage sheet` locally → Bea annotates DEV, first 25 first | Bea; no GPU |
| B2 | throughput bench per engine × model; PoC ≤25 papers, 2–3 models | **GPU — Bea's go/no-go** (`NPH_v6_poc_plan.md`) |
| B3 | full DEV grid (all candidates, arms A/B for abstracts), apply §6.2, ≤3 prompt revisions | after B1 annotation + B2 |
| B4 | freeze (`v6-frozen`), TEST once | Bea OK |
| B5 | full-corpus plan (4-shard, resumable) | separate plan + Bea OK |

Thread F (ubiquity) should reuse the Stage-1 `ubiquity_claim` field and the chosen model; its
benchmark against human Q11 is already covered by TEST.

---

## 10. Decisions I need from Bea

1. **S1** — one `evidence_basis` or two (effect / lifestyle)? (Workbooks have two; guide, schema and scorer assume one; scorer currently reads the wrong one.)
2. **S2** — OK to *add* `ubiquity_claim`, `inoculation` (4-level) and per-method yes/no/not_stated to the extraction schema, to match the workbook?
3. **DEV size/load** — 40 papers ≈ 8.5 h annotation, or 30 (≈ 6.5 h, wider CIs)?
4. **GPU budget B** for gate G4 (suggest 60 GPU-h for the full corpus) and which partition(s) to use.
5. **Downloads** — after the inventory: OK to pull HF weights (≈ 66 GB for a 32B; ≈ 100–150 GB for a full three-tier grid) and, if vLLM is missing, ≈ 10 GB for a container/env?
6. **Geography** — OK with two columns (`*_named` scored vs human, `*_resolved` for analysis)?
