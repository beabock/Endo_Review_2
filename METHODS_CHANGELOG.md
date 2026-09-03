# Methods changelog — NPH-MS-2026-57711 resubmission

A running, plain-language record of every pipeline / methods change made for the
resubmission, so the Methods section and the point-by-point "Response to referees" can be
written from a single source. Newest first. Each entry: what changed, which files, which
referee point it answers, and what still has to happen (re-run, manuscript text, figure).

Scope decisions live in `NPH_resubmission_checklist.md`; per-task plans in `NPH_task*_*.md`
(local, gitignored). This file is committed and tracks the *code*.

---

## 2026-09-02 — Corpus dedup: DOI normalisation + auditable stages
`combine_dedupe_abstracts.R` (renamed from `Combo_abstracts_pull2.R` — it combines and
deduplicates, it does not pull).

**Why.** Reviewing the dedup for the resubmission (the Methods needs the exact search
string, databases, dedup sequence, and a stage-count table — flagged in `manuscript.md`).

**Changed.**
- DOIs are normalised (case, `doi.org/` prefix, trailing punctuation) **before** the
  DOI-dedup, so `10.x/ABC` / `10.x/abc` / `https://doi.org/10.x/abc` collapse to one
  record instead of three.
- Within a DOI (and every later stage) the WoS > Scopus > PubMed record is kept,
  tie-broken by the longest abstract (most complete copy).
- Document-type filter matches any *article*-flavoured type (`Article`,
  `Article; Proceedings Paper`, `Article in Press`) + NA, not the literal string
  `"Article"`; the full `Document.Type` breakdown is printed before and after.
- Every stage writes rows-in / rows-out / removed to
  `results/outputs/dedup_stage_counts.csv` (the Methods table), and the records removed
  at the abstract / doc-type / title stages are saved to `data/processed/` for review.
- Both canonical outputs (`All_abstracts_deduped.csv` + the slim `Abstracts_for_Monsoon.csv`)
  are now written by the script to `data/Abstracts/` — the slim file used to appear with
  no script that made it.

**Search string — DISCREPANCY FOUND (needs a decision).** `search_string.txt` (the
WoS/Scopus string) is **not** equivalent to `base_search` in `api_pull_abstracts.R` (the
PubMed string):

| term | PubMed (`base_search`) | WoS/Scopus (`search_string.txt`) |
|---|---|---|
| bare `endophyte*` + fungal word | yes | no (exact phrases only) |
| `symptomless / asymptomatic / quiescent fung*` | yes | no |
| `DSE fungi` | no | yes |
| `lichen* / cyanobacteria / photobiont* / cyanobiont*` | no | yes |
| `angiosperm* / gymnosperm* / monocot* / dicot*` | yes | (relies on `plant*`) |

Plant-side differences mostly wash out (`plant*` covers the taxon words); the
endophyte-side and lichen/photobiont differences are substantive.

**Resolved by `docs/SEARCH_STRATEGY.md`** (found in the old project repo, now copied into
`Endo_Review_2/docs/`): the **authoritative** string is the Phase-2 / `search_string.txt`
one (exact endophyte phrases × host terms incl. lichen/photobiont), run across all three
databases on 2025-07-31. `base_search` in `api_pull_abstracts.R` was an earlier **draft**
— it is now renamed `base_search_DRAFT` (provenance only) and the script uses the Phase-2
string.

**RESOLVED — the PubMed pull used the draft string; it needs a re-pull.** Forensics:
- `pubmed_pull_8-14-25.csv` (10,631 PMIDs) = `rentrez` API pull, **draft** string. Used by the dedup.
- `abstract-endophyteA-set.txt` (9,222 recs, website export, 2025-08-14) = **Phase 2**
  string (has lichen/photobiont/DSE). Never used.
- ~1,487 records are only in the draft CSV; **~723 have no "endophyte" term at all** —
  clinical antifungal + plant-pathology papers matched via `"latent/systemic fungi"` +
  generic host words. The draft PubMed component is contaminated with clinical mycology.

**Fixed (2026-09-02).** `abstract-endophyteA-set.txt` (9,222 recs) IS the Phase 2 PubMed
website export from 2025-08-14. `parse_pubmed_textfile.py` (new) parses it →
`pubmed_pull_phase2.csv` (9,141 recs with an abstract; correction/erratum/retraction
notices dropped). `combine_dedupe_abstracts.R` picks it up automatically.

**Corpus re-run with Phase 2 PubMed:** 39,114 combined → DOI 22,212 → abstract 21,982 →
doc-type 21,982 → title **21,414** (19,586 with DOI). Contribution after dedup: WoS 14,624
/ Scopus 4,229 / PubMed 2,561. vs the pre-resubmission 21,891 — smaller mainly because
~1,500 clinical-mycology / plant-pathology papers the draft string caught are gone.

`pull_pubmed_phase2.R` (rentrez) kept for the eventual date-extension only (it needs its
count validated against the 9,141 first).

**Search date = 2025-08-14** (resolved). Every WoS/Scopus/PubMed export file is timestamped
09:16–10:01 on 2025-08-14; `old_manuscript.md` agrees. The 2025-07-31 in the old
SEARCH_STRATEGY.md / `docs/METHODS.md` was the planning date. `docs/METHODS.md` (old repo)
still needs the fix.

**Dedup re-run (2026-09-02), improved script, real data:**
40,776 combined → DOI 23,100 → abstract 22,830 → doc-type 22,830 → title **22,268**
(20,411 with a DOI, 1,857 without). Old pipeline was 21,891; the +377 is mostly
`Article; Proceedings Paper` / `Book Chapter` / `Early Access` the old exact-`"Article"`
filter dropped. 3 rows had a volume number in the year field → set to NA. Year span
1926–2025. Table: `results/outputs/dedup_stage_counts.csv`.

**Still to do.**
- Resolve the search-string discrepancy (above).
- Copy the fresh `All_abstracts_deduped.csv` (22,268 rows) to Monsoon for the dry-run.
- Add the search string(s) + `dedup_stage_counts.csv` table to Methods / SI.
- Add an explicit corpus-scope paragraph (self-identified endophyte research; fungi
  published under mycorrhizal / pathology / microbiome frames are out of scope by design).
- Before final submission only: extend the search to the current year (mechanical,
  reshuffles every number — do it last).

---

## 2026-09-02 — Task 1 Phase 0: full-text retrieval + extraction rewrite (code only)
Branch `nph-task1-fulltext-revalidation`. Nothing run at scale yet.

**Why.** Referee 3: the abstract-vs-full-text "sensitivity analysis" compared two
different pools of papers, not the abstract and full text of the *same* records. And the
old `monsoon_extract.py` only read the first 12 PDF pages then truncated to 8,000
characters, so the "full-text" dataset was really an extended-abstract dataset.

**Changed.**
- `scripts/01_data_preproccessing/extract_schema.py` (new) — one definition of the
  extraction schema: the JSON schema for schema-constrained decoding, the controlled
  vocabularies, the prompt, and a map from every Task 2 human-annotation label to the
  same machine token (so model output and the human ground truth score on one axis).
  Fields locked to the Task 2 workbook: per interaction `fungus`, `host_plant`,
  `tissue`, `fungal_lifestyle`, `effect_on_host`, `evidence_basis`; per paper the
  Q1–Q11 equivalents + 6 detection-method flags + a metabarcoding community summary.
- `scripts/01_data_preproccessing/pdf_segment.py` (new) — structure-aware PDF parse
  (pymupdf4llm), keep Methods/Results/Discussion/Taxonomy + table captions + paragraphs
  naming a binomial or country, drop References/Acknowledgements/Funding, chunk into
  context-sized windows with `[DOI | section]` headers. Scanned / image-only PDFs are
  OCR'd with `ocrmypdf` (Tesseract) and cached — **not** skipped, because skipping scans
  would bias against exactly the older and non-English papers the study is about.
- `scripts/01_data_preproccessing/fetch_fulltext_pdfs.py` (new, replaces
  `download_pdfs.py`) — six open-access resolvers in order (Unpaywall → OpenAlex →
  Europe PMC → Semantic Scholar → CORE → publisher `citation_pdf_url`) until a validated
  PDF is obtained (magic bytes + PyMuPDF open + ≥1 page). Resumable, shardable, per-DOI
  manifest + miss log. `--dry-run` produces a coverage report grouped by
  publisher/journal.
- `scripts/01_data_preproccessing/monsoon_extract.py` (rewritten; v4 → `scripts/archive/`)
  — per paper: segment → one schema-constrained Ollama call per chunk → union + dedup
  interactions on `(fungus, host, tissue-set)` → `global_endo_extraction_v5.csv`.
  `--mode abstract|fulltext` (same schema both ways so the paired comparison joins on
  `paper_id`), `--model` for the bake-off, explicit `num_ctx` + `temperature=0`.
- `scripts/04_analyses/06_detect_ubiquity_claims_ollama.py` — `collect_snippets` now
  takes keyword-centred windows instead of `text[:8000]` (a ubiquity claim in the
  Discussion of a long paper was previously invisible); `num_ctx` and `temperature` are
  now set explicitly on the Ollama call (the default 2048-token window silently
  truncated even the 8k it was handed).

**Answers.** Referee 3 (paired validation, detection-method QC, guild criteria);
Referee 2 (precision/recall against a curated set, English-only question, strain-level
variation, author-assigned vs demonstrated function); Referee 1 (commensalism as a
first-class category).

**Corpus denominator (2026-09-02).** The full-text coverage check and the re-extraction
are seeded from `data/Abstracts/All_abstracts_deduped.csv` — the **deduplicated original
search export**, before any LLM touched it (20,228 records with a DOI + 1,630 without).
Not from the old pipeline's cleaned/filtered output, which would inherit the old model's
relevance and guild-classification decisions — the exact thing the re-extraction exists
to redo. Relevance + guild filtering is re-applied afterwards with the new schema and
validated against the Task 2 ground truth.

**Still to do.**
- Decide the pre-registered agreement threshold (proposed: interaction F1 ≥ 0.75, taxon
  counts not systematically lower for abstracts, country/biome κ ≥ 0.6).
- Run: Phase 0a dry-run → real PDF pull → 25-paper Phase 1 POC (model sanity check) →
  scaled re-extraction (whole corpus, new schema, bake-off winner).
- **Re-run the ubiquity detector** — the snippet + `num_ctx` fix changes the Prediction-1
  "2.7% of the corpus states ubiquity" number. Manuscript figure + text need updating.
- Working decision (2026-09-02): headline taxonomic/geographic claims will rest on the
  **full-text corpus only**; abstract extraction is run anyway to quantify what abstracts
  omit (supplement). Revisit only if paired agreement is exceptional (>90%).

---

## 2026-09-02 — Task 2: ground-truth validation sample + annotation workbooks
Branch `nph-task2-ground-truth`, commit 54cd8e5. Infrastructure built; workbooks are
filled after Task 1 provides the re-extraction to score against.

**Why.** Referee 2 asked for precision, recall, false-positive/negative rates, and
inter-annotator agreement against a manually curated set — not a model confidence score.

**Changed.**
- `scripts/04_analyses/build_groundtruth_sample.py` (new) — draws a stratified random
  sample (fixed seed), writes one Excel workbook per annotator with warning-style
  dropdown validation. A shared 50-paper κ block (15 calibration + 35 measurement) for
  all five annotators (Bea, Nancy, Kitty, Ian, Jack) plus solo blocks. Full-text papers
  get a paired `abstract` row and `full text` row so the human abstract-vs-full-text gap
  is measured the same way as the machine one.
- `scripts/04_analyses/score_groundtruth.py` (new, skeleton) — interaction-level
  P/R/F1 per reading stage, Fleiss' κ per field, false-positive/negative rates. Wired to
  `extract_schema.HUMAN_TO_TOKEN`; field-accuracy + κ finished once the re-extraction
  schema lands.
- `results/manual_validation/groundtruth/` — `guild_rubric.md` (Methods-citable rubric,
  FungalTraits `primary_lifestyle` cited), `data_dictionary.md`, `annotator_instructions.md`,
  `stratification_report.md`.

**Design notes worth keeping for Methods.**
- `fungal_lifestyle` (trophic mode) and `effect_on_host` (net host outcome) are separate
  axes — a plant pathogen can be present with no symptoms. This decoupling is the study's
  central claim, so the instrument enforces it.
- `evidence_basis` (experimental / observational / inferred-from-taxon / asserted) is the
  anti-circularity field — it quantifies how often a functional label was actually tested.
- Fungal + host names are recorded **verbatim as the authors wrote them**, even
  known-outdated names; synonym resolution stays programmatic.
- κ unit: 1 item = 1 paper for paper-level fields (~35 measurement papers × 5 raters),
  1 item = 1 matched interaction for interaction-level fields.

**Answers.** Referee 2 (extraction validation, strain variation, author-assigned labels);
Referee 3 (guild circularity, endophytism-method QC, "human in the loop" definition);
Referee 1 (commensalism).

---

## 2026-08-2x — Task 3: remove GDP / Prediction 4
Branch `nph-tasks-3-4-gdp-biogeographic`, commit c75a8c2. Implemented; awaiting merge +
Monsoon regeneration.

**Why.** All three referees + the editor converged on the country-level GDP analysis:
it conflates population with research capacity and the positive relationship is
unsurprising as stated.

**Changed.** GDP analysis + Prediction 4 removed from the pipeline (archived, not
deleted): `scripts/archive/01_country_gdp_latitude_analysis.R`; `01_country_latitude_analysis.R`
(new, GDP-free); `04_country_enrichment.R` gains a `--with-gdp` opt-in flag; GDP
references stripped from 8 consumer scripts (`03_geographic_bias_mapping.R`,
`09_biodiversity_priority_robustness.py`, `08_biodiversity_priority_overlap.R`,
`make_supplementary_tables.py`, `compare_abs_fulltexts.R`, plotting scripts, sbatch).

**Still to do.** Manuscript: drop "socioeconomic" from the title, rewrite the Summary
close, cut Prediction 4 + Figure 5, renumber predictions, re-anchor the Discussion
examples to "under-sampled regions" generally.

---

## 2026-08-2x — Task 4: biogeographic realms replace political categories
Branch `nph-tasks-3-4-gdp-biogeographic`, commit 8ee155e. Implemented; awaiting merge +
Monsoon regeneration.

**Why.** Referee 3: "European Union" and "Global South" are political categories with
geographically inconsistent membership; biogeographic regions would be more meaningful.

**Changed.** EU / Global North–South grouping replaced with Olson et al. (2001) WWF
biogeographic realms (8) and biomes (14): `scripts/utils/build_biogeographic_realm_table.py`
(new), `country_biogeographic_realm.csv` (new, 250 rows), `biogeographic_mapping.R` (new),
`country_mapping.py` gains `get_realm()`; `03c_biogeographic_bias_mapping.R` (new) replaces
the `*_eu_grouped` scripts (archived); `biome_plots_by_realm.R` (new) adds a realm × biome
heatmap.

**Still to do.** Manuscript: replace "Global North/South" and "EU" language throughout
Introduction / Results / Discussion with biogeographic framing.
