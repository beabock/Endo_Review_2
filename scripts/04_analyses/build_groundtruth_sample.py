#!/usr/bin/env python3
# BMB 2026-08-28
# Builds the manually-curated ground-truth / validation sample for the extraction
# pipeline (NPH-MS-2026-57711 resubmission, Referee 2). See NPH_task2_ground_truth_plan.md
# and NPH_extraction_schema_design.md.
#
#   1. Builds a paper-level frame directly from the deduplicated search export (2026-09-17:
#      switched from the old LLM-extraction output - see the note below), assigning what
#      stratification variables are actually available pre-extraction (doc type, era).
#   2. Draws a stratified random sample (fixed seed), in a stratified ORDER so that any
#      prefix is itself balanced (the kappa block can be extended later).
#   3. Splits into: a kappa block (all annotators) + solo blocks (Bea + 2 extra reviewers).
#      Nancy & Kitty rate only the kappa block.
#   4. Writes one .xlsx workbook per person. One row per (paper, reading stage): a
#      full-text paper gets an abstract-only row THEN a full-text row (adjacent, same
#      reader) so we also get a human measure of what abstracts omit vs their own full
#      text. Dropdown-validated, 5 interaction slots, method tick-columns.
#
# 2026-09-17 note - why this no longer reads the old extraction file: Bea flagged that
# `Ollama_cleaned_synresolved_standardized_year.csv` (the old default) is downstream of
# the OLD LLM extraction run, on the OLD (narrower) search - 18,751 papers vs. the
# ~19,586 the current deduplicated search export actually contains, confirmed against
# `Combo_abstracts_pull2.R` (the dedup script) and its real output,
# `data/Abstracts/All_abstracts_deduped.csv`. We don't need the LLM extraction to build a
# sample for people to read - that's a separate pipeline - so this now reads the deduped
# search export directly. Tradeoff: that export is pre-LLM, so it has no guild/country/
# interaction data. Function and continent stratification are dropped until the Task 1
# re-extraction runs on this corpus (Bea, 2026-09-17: "it's fine for us not to be
# stratifying" on those). Era (from Year) is still available and used. doc_type
# (full-text vs abstract-only) now comes from an optional PDF-availability manifest
# (--pdf-manifest); without one, everything defaults to abstract-only - see main().
#
# BLIND annotation: no model output is shown (avoids anchoring). score_groundtruth.py
# merges the completed sheets with an extraction run for precision / recall / F1 / kappa.
#
# Usage:
#   python scripts/04_analyses/build_groundtruth_sample.py
#   python scripts/04_analyses/build_groundtruth_sample.py --pdf-manifest path/to/merged_manifest.csv

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rubric_sheet import (COUNTRIES, NEW_Q7_LINES, Q7A, Q7B, Q7C,  # noqa: E402
                          add_rubric_sheet, force_recalc, remove_completeness, set_rollup_formula,
                          write_instructions)

ROOT = Path(__file__).resolve().parents[2]

# 2026-09-17: the deduplicated search export (see the header note above), not the old
# LLM-extraction output. ~19,586 papers with a usable DOI as of the 2026-09-17 check.
DEFAULT_CORPUS = ROOT / "data" / "Abstracts" / "All_abstracts_deduped.csv"
OUT_DIR = ROOT / "results" / "manual_validation" / "groundtruth"

# annotator key -> display label.
ANNOTATORS = {
    "bea": "Bea",
    "nancy": "Nancy",
    "kitty": "Kitty",
    "ian": "Ian",
    "jack": "Jack",
}
# reviewers who take a solo block in addition to the kappa block (besides Bea, who
# takes the remainder). Nancy & Kitty do the kappa block only.
EXTRA_REVIEWERS = ["ian", "jack"]

# --- controlled vocabularies -------------------------------------------------------
# Kept in sync with guild_rubric.md. Written to a hidden "Lists" sheet and range-
# referenced by the dropdowns (so values may contain commas, and the lists stay
# editable). Validation is set to "warning" style, so an annotator can also type a
# value that isn't in the list (e.g. a specific language / biome).
VOCAB = {
    "yn": ["yes", "no"],
    "yn_unclear": ["yes", "no", "unclear"],
    "country": COUNTRIES,   # Q7a - warning-style, so any other name can still be typed
    # the five method columns: every cell filled on a complete row (blank = not done yet)
    "method_status": ["yes", "no", "not stated"],
    "text_reviewed": [
        "complete",
        "could not access the paper (full text needed)",
        "review or secondary compilation - no primary data of its own",
        "not a fungus-in-plant study",
    ],
    "primary_aim": [
        "endophyte ecology / diversity / community",
        "endophyte function: growth, nutrition, or stress tolerance",
        "endophyte function: disease protection / biocontrol",
        "natural products / secondary metabolites / bioprospecting",
        "plant pathology (the fungus studied as a pathogen)",
        "fungal taxonomy / systematics / new species",
        "genomics / transcriptomics / methods development",
        "other (type it)",
    ],
    "sampling_approach": [
        "one or a few isolates (named)", "culture survey (many isolates, named)",
        "community metabarcoding / NGS (OTU or ASV table)",
        "direct observation only (microscopy / histology, no isolation or sequencing)",
        "mixed methods (type which)",
        "review / synthesis / secondary compilation - no new fungi obtained here",
        "other (type it)", "unclear",
    ],
    "language": [
        "English",
        "non-English (type which)",
        "English + non-English (bilingual abstract, or English abstract + non-English body)",
        "unclear",
    ],
    "sampling_location_status": [
        "sampling location is explicitly stated",
        "sampling location is inferable from a named field site / region",
        "the main text says location details are in a supplement",
        "the main text says location details are in another cited study",
        "no sampling location - only the authors' institutional country is given",
        "no geographic information at all",
    ],
    "strain_variation": [
        "yes - noted", "no - not noted", "only one strain / isolate studied",
    ],
    "biome": [
        "tropical / subtropical moist forest", "tropical / subtropical dry forest",
        "temperate or boreal forest", "Mediterranean forest / woodland / scrub",
        "tropical grassland / savanna / shrubland",
        "temperate grassland / steppe / prairie", "montane grassland / alpine",
        "desert / xeric shrubland", "wetland / flooded grassland / bog",
        "mangrove", "tundra / polar", "marine / coastal",
        "agriculture / cultivated (crop, orchard, plantation, sown pasture)",
        "urban / garden / botanical collection", "greenhouse / growth chamber",
        "other (type it)", "not stated",
    ],
    "tissue": [
        "leaf", "root", "stem / wood / bark", "seed", "fruit",
        "flower / reproductive", "aerial parts / shoots (not separated)", "whole plant",
        "other (type it)", "not stated",
    ],
    # fungal lifestyle / trophic mode - how the fungus makes its living in this
    # interaction. Values follow FungalTraits primary_lifestyle (Polme et al. 2020);
    # the three endophyte types are grouped (the tissue column records leaf vs root).
    "fungal_lifestyle": [
        "endophyte (any plant tissue; symptomless in living tissue)",
        "latent pathogen / hemibiotroph",
        "plant pathogen",
        "wood saprotroph",
        "litter saprotroph",
        "soil saprotroph",
        "unspecified / other saprotroph",
        "arbuscular mycorrhizal",
        "ectomycorrhizal",
        "ericoid mycorrhizal",
        "orchid mycorrhizal",
        "mycoparasite / antagonist of other microbes",
        "epiphyte (surface only)",
        "lichenised",
        "context-dependent (varies by host / environment / strain)",
        "not clear from the text",
    ],
    # net outcome for THIS host plant, as the paper reports it
    "effect_on_host": [
        "not reported (fungus just isolated / detected)",
        "no visible symptoms; benefit or harm not tested",
        "neutral / commensal (plant response tested; no net effect)",
        "beneficial to the plant",
        "harmful to the plant (disease / reduced fitness)",
        "context-dependent (varies by host / environment / strain)",
        "unclear",
    ],
    "evidence_basis": [
        "experimentally tested in this study",
        "observed / measured in this study (no manipulation)",
        "inferred from what the fungus usually does (taxon reputation / database)",
        "asserted with no support",
        "not stated",
    ],
    "sterilisation_checked": [
        "yes - a control was done (final rinse plated, tissue imprints, or similar)",
        "no - standard sterilisation, no check described",
        "not a culture-based study",
        "cannot tell from the text",
    ],
}

N_SLOTS = 5
# Method columns: plain-English headers (no "m_" prefix - Kitty / Nancy found the codes
# confusing). Tick "yes" in every one that applies. Full definitions in guild_rubric.md.
METHOD_COLS = [
    "culture from sterilised tissue",
    "microscopy in tissue",
    "direct sequencing from tissue",
    "isolate ID by sequencing",
    "resynthesis / re-inoculation",
    "method not stated",
]


def norm_doi(x):
    if pd.isna(x):
        return None
    return str(x).strip().lower().lstrip("doi:").strip().replace("https://doi.org/", "")


def era_of(year):
    if pd.isna(year):
        return "unknown"
    y = int(year)
    return "pre-2000" if y < 2000 else "2000-2012" if y <= 2012 else "2013-2024"


def build_paper_frame(corpus_path: Path, pdf_manifest_path: Path | None) -> pd.DataFrame:
    """Paper-level frame straight from the deduplicated search export - no LLM
    extraction involved. See the header note for why."""
    df = pd.read_csv(corpus_path, low_memory=False)
    df["doi_n"] = df["DOI"].map(norm_doi)
    n_before = len(df)
    df = df.dropna(subset=["doi_n"]).drop_duplicates("doi_n")
    print(f"  {n_before:,} rows in corpus -> {len(df):,} with a usable DOI "
          f"(dropped {n_before - len(df):,} with no/blank DOI)")

    papers = pd.DataFrame({
        "paper_id": df["doi_n"],
        "doi_n": df["doi_n"],
        "title": df["Title"],
        "authors": df["Authors"],
        "journal": df["Source.title"],
        "abstract": df["Abstract"],
        "language_hint": df["Language.of.Original.Document"]
                          if "Language.of.Original.Document" in df.columns else "",
        "year": pd.to_numeric(df["Year"], errors="coerce"),
    }).reset_index(drop=True)
    papers["era"] = papers["year"].map(era_of)
    papers["doi_link"] = papers["doi_n"].map(lambda d: f"https://doi.org/{d}")

    if pdf_manifest_path and Path(pdf_manifest_path).exists():
        man = pd.read_csv(pdf_manifest_path, low_memory=False)
        doi_col = "doi" if "doi" in man.columns else "DOI"
        man["doi_n"] = man[doi_col].map(norm_doi)
        man = man.dropna(subset=["doi_n"]).drop_duplicates("doi_n")
        downloaded = set(man.loc[man["status"] == "downloaded", "doi_n"])
        papers["doc_type"] = np.where(papers["doi_n"].isin(downloaded),
                                      "full-text", "abstract-only")
        n_ft = int((papers.doc_type == "full-text").sum())
        print(f"  PDF manifest matched: {n_ft:,} full-text / {len(papers) - n_ft:,} "
              f"abstract-only")
    else:
        papers["doc_type"] = "abstract-only"
        print("  WARNING: no --pdf-manifest given - doc_type defaults to 'abstract-only' "
              "for every paper. The kappa block needs full-text papers; re-run with "
              "--pdf-manifest pointing at the merged PDF manifest once you have it.")
    return papers


def proportional_allocation(counts: dict, total: int, floor: int = 2) -> dict:
    keys = [k for k, v in counts.items() if v > 0]
    base = {k: min(floor, counts[k]) for k in keys}
    remaining = total - sum(base.values())
    if remaining > 0:
        wt = sum(counts[k] for k in keys)
        for k in keys:
            base[k] += int(round(remaining * counts[k] / wt))
    diff = total - sum(base.values())
    order = sorted(keys, key=lambda k: counts[k], reverse=diff > 0)
    i = 0
    while diff != 0 and order and i < 10000:
        k = order[i % len(order)]
        step = 1 if diff > 0 else -1
        if 1 <= base[k] + step <= counts[k]:
            base[k] += step
            diff -= step
        i += 1
    return base


def stratified_sample(pool: pd.DataFrame, n: int, rng, strata_cols) -> pd.DataFrame:
    if n <= 0 or pool.empty:
        return pool.iloc[0:0]
    counts = {k: v for k, v in pool.groupby(strata_cols).size().to_dict().items() if v > 0}
    alloc = proportional_allocation(counts, n)
    picks = []
    for key, k_n in alloc.items():
        key_t = key if isinstance(key, tuple) else (key,)
        cell = pool[np.logical_and.reduce([pool[c] == v for c, v in zip(strata_cols, key_t)])]
        take = min(k_n, len(cell))
        if take:
            picks.append(cell.sample(n=take, random_state=rng.integers(1 << 31)))
    return pd.concat(picks).drop_duplicates("paper_id")


def stratified_order(df: pd.DataFrame, rng, strata_cols) -> pd.DataFrame:
    """Round-robin interleave strata so any prefix of the result is balanced."""
    buckets = defaultdict(list)
    for _, r in df.sample(frac=1, random_state=rng.integers(1 << 31)).iterrows():
        buckets[tuple(r[c] for c in strata_cols)].append(r)
    keys = sorted(buckets, key=lambda k: -len(buckets[k]))
    ordered, exhausted = [], False
    while not exhausted:
        exhausted = True
        for k in keys:
            if buckets[k]:
                ordered.append(buckets[k].pop(0))
                exhausted = False
    return pd.DataFrame(ordered).reset_index(drop=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS,
                    help="deduplicated search export (2026-09-17: replaces the old "
                         "--extraction LLM-output flag - see the header note)")
    ap.add_argument("--pdf-manifest", type=Path, default=None,
                    help="merged PDF-fetch manifest (doi + status columns) used to set "
                         "doc_type. Without it, every paper defaults to abstract-only.")
    ap.add_argument("--seed", type=int, default=20260828)
    ap.add_argument("--n-core", type=int, default=230,
                    help="total sample size (2026-09-17: absorbs the old separate "
                         "rare-function-oversample tier, which required guild data we "
                         "don't have pre-extraction - see header note)")
    ap.add_argument("--full-text-frac", type=float, default=0.35)
    ap.add_argument("--n-kappa", type=int, default=20,
                    help="kappa-block size (rater-time tradeoff decided 2026-09-17: 20 "
                         "papers, all full-text, one blind measurement pass, no "
                         "calibration sub-round - see MOCK below for rubric training)")
    ap.add_argument("--n-calibration", type=int, default=0,
                    help="first N kappa-block papers scored as a calibration round before "
                         "a reconciliation call. Default 0 = single blind pass (2026-09-17 "
                         "decision); kept as an option if a future block wants the split.")
    ap.add_argument("--solo-per-extra", type=int, default=20,
                    help="solo-block size for each of EXTRA_REVIEWERS (Ian, Jack); "
                         "they also rate the whole kappa block. Bea takes the remainder.")
    args = ap.parse_args()

    if not args.corpus.exists():
        print(f"ERROR: corpus file not found: {args.corpus}")
        return 1
    rng = np.random.default_rng(args.seed)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Building paper frame from {args.corpus.name} ...")
    papers = build_paper_frame(args.corpus, args.pdf_manifest)
    frame_cols = ["paper_id", "doi_n", "doc_type", "era", "year", "journal", "language_hint"]
    papers[frame_cols].to_csv(OUT_DIR / "sample_frame.csv", index=False)
    print(f"  {len(papers):,} papers ({(papers.doc_type == 'full-text').sum():,} full-text)")

    # core sample: stratified by era + full-text oversample fraction only (no function/
    # continent - see header note). This is the whole sample now, not "core + rare".
    n_ft = int(round(args.n_core * args.full_text_frac))
    ft = papers[papers.doc_type == "full-text"]
    ab = papers[papers.doc_type == "abstract-only"]
    core = pd.concat([
        stratified_sample(ft, min(n_ft, len(ft)), rng, ["era"]),
        stratified_sample(ab, args.n_core - min(n_ft, len(ft)), rng, ["era"]),
    ]).drop_duplicates("paper_id")

    # kappa block: full-text only (2026-09-17 decision, rater-time tradeoff) - every
    # kappa paper gets both an abstract row and a full-text row from the same 5 raters,
    # so a 20-paper block still yields the abstract-vs-full-text comparison. Stratified
    # by era, ordered so any prefix stays balanced -> raising --n-kappa later is
    # valid even though there's no calibration sub-round by default.
    ft_core = core[core.doc_type == "full-text"]
    if len(ft_core) < args.n_kappa:
        print(f"\nERROR: only {len(ft_core)} full-text papers in the sample, need "
              f"{args.n_kappa} for the kappa block. Re-run with --pdf-manifest pointing "
              f"at the merged PDF manifest (or --n-kappa {len(ft_core)} to proceed "
              f"anyway, not recommended).")
        return 1
    pool_n = min(max(2 * args.n_kappa, args.n_kappa + 20), len(ft_core))
    kappa_pool = stratified_sample(ft_core, pool_n, rng, ["era"])
    kappa_pool = stratified_order(kappa_pool, rng, ["era"])
    kappa_pool["order"] = range(len(kappa_pool))
    kappa_ids = set(kappa_pool.head(args.n_kappa).paper_id)
    calibration_ids = set(kappa_pool.head(args.n_calibration).paper_id)

    sample = core.merge(kappa_pool[["paper_id", "order"]], on="paper_id",
                        how="left").reset_index(drop=True)
    sample["order"] = sample["order"].fillna(9999).astype(int)
    sample["assignment"] = np.where(sample.paper_id.isin(kappa_ids), "kappa_block", "solo")
    sample["phase"] = np.select(
        [sample.paper_id.isin(calibration_ids), sample.paper_id.isin(kappa_ids)],
        ["calibration", "measurement"], default="")

    # solo split: each EXTRA_REVIEWER takes a stratified slice of the solo block
    # (keeping the solo block's full-text mix); Bea takes the remainder.
    sample["annotator"] = np.where(sample.assignment == "kappa_block", "ALL", "bea")
    remaining = set(sample[sample.annotator == "bea"].paper_id)
    for who in EXTRA_REVIEWERS:
        pool = sample[sample.paper_id.isin(remaining)]
        n = min(args.solo_per_extra, len(pool))
        ft_n = round(n * (pool.doc_type == "full-text").mean())
        pick = pd.concat([
            stratified_sample(pool[pool.doc_type == "full-text"], ft_n, rng, ["era"]),
            stratified_sample(pool[pool.doc_type == "abstract-only"], n - ft_n, rng, ["era"]),
        ]).drop_duplicates("paper_id")
        sample.loc[sample.paper_id.isin(pick.paper_id), "annotator"] = who
        remaining -= set(pick.paper_id)

    sample = sample.sort_values(["assignment", "order", "doc_type"])
    sample.to_csv(OUT_DIR / "sample_selected.csv", index=False)

    write_workbooks(papers, sample, rng)
    write_stratification_report(papers, sample, args)

    kb = (sample.assignment == "kappa_block").sum()
    ft = (sample.doc_type == "full-text").sum()
    per = " | ".join(f"{ANNOTATORS[k]} {(sample.annotator == k).sum()}"
                     for k in ["bea", *EXTRA_REVIEWERS])
    print(f"\nSample: {len(sample)} papers ({ft} full-text -> paired abstract+full-text "
          f"rows) | kappa block {kb} (all {len(ANNOTATORS)} annotators) | {per}")
    print(f"Outputs in {OUT_DIR}")
    return 0


def expand_rows(block: pd.DataFrame) -> pd.DataFrame:
    """One row per (paper, reading stage). Full-text papers -> an abstract-only row
    then a full-text row (adjacent). Abstract-only papers -> a single abstract row."""
    out = []
    for _, r in block.iterrows():
        if r["doc_type"] == "full-text":
            a = r.copy(); a["reading_stage"] = "abstract"; a["stage_suffix"] = "a"
            b = r.copy(); b["reading_stage"] = "full text"; b["stage_suffix"] = "b"
            out += [a, b]
        else:
            r = r.copy(); r["reading_stage"] = "abstract"; r["stage_suffix"] = ""
            out.append(r)
    return pd.DataFrame(out).reset_index(drop=True)


def write_workbooks(papers: pd.DataFrame, sample: pd.DataFrame, rng) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    HEADER = Font(bold=True, color="FFFFFF", size=10)
    HEADER_FILL = PatternFill("solid", start_color="2C5F8A")
    METHOD_FILL = PatternFill("solid", start_color="E7E0EF")
    SLOT_A = PatternFill("solid", start_color="EAF1F8")
    SLOT_B = PatternFill("solid", start_color="F3ECDA")
    WRAP = Alignment(wrap_text=True, vertical="top")

    Q1 = "Q1  does this paper report a fungus coming from a plant?"
    Q2 = "Q2  paper's main purpose"
    Q3 = "Q3  how were the fungi obtained in this paper?"
    Q4 = "Q4  language of the text you are reading"
    Q5 = "Q5  any sequence-only (uncultured) taxa?"
    Q6 = "Q6  strain-level variation noted?"
    Q7a, Q7b, Q7c = Q7A, Q7B, Q7C
    # 2026-09-22 (Bea Bock, "simplifying could be a good idea"): Q8 absorbs the old separate
    # location-source question (supplement / cited-study deferral is now just more Q8 values).
    Q8 = "Q8  what geographic information does the text contain?"
    Q9 = "Q9  biome (WWF category)"
    Q10 = "Q10  how many distinct fungus-host pairs?"
    Q11 = "Q11  was the surface-sterilisation checked?"

    left_cols = [
        ("row_id", 8), ("text_reviewed", 22), ("date_reviewed", 12),
        ("reading_stage", 12), ("paper_id", 22), ("doi_link", 20),
        ("year", 6), ("journal", 18), ("title", 40), ("abstract", 66),
        (Q1, 15), (Q2, 20), (Q3, 22), (Q4, 13), (Q5, 15), (Q6, 15),
        (Q7a, 24), (Q7b, 30), (Q7c, 20), (Q8, 30), (Q9, 20), (Q10, 12), (Q11, 22),
    ]
    slot_cols = ["fungus", "host_plant", "tissue",
                 "fungal_lifestyle", "effect_on_host", "evidence_basis"]
    right_cols = [
        ("extra_pairs_or_NGS_community_summary", 44),
        ("anything_you_were_unsure_about", 30),
    ]
    dv = {
        "text_reviewed": "text_reviewed",
        Q1: "yn_unclear", Q2: "primary_aim", Q3: "sampling_approach",
        Q4: "language", Q5: "yn_unclear", Q6: "strain_variation",
        Q7a: "country",
        Q8: "sampling_location_status", Q9: "biome",
        Q11: "sterilisation_checked",
        "tissue": "tissue", "fungal_lifestyle": "fungal_lifestyle",
        "effect_on_host": "effect_on_host", "evidence_basis": "evidence_basis",
    }
    for m in METHOD_COLS:
        # the last column ("method not stated") is the roll-up flag: plain yes/no
        if m != "method not stated":          # that one is a formula (set_rollup_formula)
            dv[m] = "method_status"
    q_headers = [Q1, Q2, Q3, Q4, Q5, Q6, Q7a, Q7b, Q7c, Q8, Q9, Q10, Q11]

    def add_lists_sheet(wb):
        ws = wb.create_sheet("Lists")
        ws.sheet_state = "hidden"
        ranges = {}
        for col, (key, vals) in enumerate(VOCAB.items(), start=1):
            letter = get_column_letter(col)
            ws.cell(1, col, key)
            for i, val in enumerate(vals, start=2):
                ws.cell(i, col, val)
            ranges[key] = f"Lists!${letter}$2:${letter}${len(vals) + 1}"
        return ranges

    def build_sheet(ws, rows: pd.DataFrame, list_ranges):
        headers = [c for c, _ in left_cols] + list(METHOD_COLS)
        for s in range(1, N_SLOTS + 1):
            headers += [f"{c}_{s}" for c in slot_cols]
        headers += [c for c, _ in right_cols]
        ws.append(headers)

        widths = {c: w for c, w in left_cols + right_cols}
        slot_w = {"fungus": 20, "host_plant": 20, "tissue": 15,
                  "fungal_lifestyle": 26, "effect_on_host": 26, "evidence_basis": 26}
        for ci, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=ci)
            cell.font, cell.fill, cell.alignment = HEADER, HEADER_FILL, WRAP
            base = h.rsplit("_", 1)[0] if h[-1].isdigit() else h
            ws.column_dimensions[get_column_letter(ci)].width = (
                widths.get(h) or slot_w.get(base) or (19 if h in METHOD_COLS else 13))
        ws.row_dimensions[1].height = 60

        n_q_blanks = sum(1 for c, _ in left_cols if c.startswith("Q"))
        for _, r in rows.iterrows():
            q_vals = [""] * n_q_blanks
            q_vals[3] = str(r.get("language_hint", "") or "")  # Q4 pre-fill hint
            ws.append([
                r["row_id"], "", "", r["reading_stage"],
                r["paper_id"], r["doi_link"], r.get("year", ""),
                str(r.get("journal", ""))[:120], str(r.get("title", ""))[:300],
                str(r.get("abstract", "") or "")[:5000],
            ] + q_vals + [""] * len(METHOD_COLS)
              + [""] * (N_SLOTS * len(slot_cols)) + ["", ""])

        n = len(rows) + 1
        n_left = len(left_cols)
        for ci in range(n_left + 1, n_left + len(METHOD_COLS) + 1):
            col = get_column_letter(ci)
            for rr in range(2, n + 1):
                ws[f"{col}{rr}"].fill = METHOD_FILL
        for si in range(N_SLOTS):
            fill = SLOT_A if si % 2 == 0 else SLOT_B
            c0 = n_left + len(METHOD_COLS) + si * len(slot_cols) + 1
            for ci in range(c0, c0 + len(slot_cols)):
                col = get_column_letter(ci)
                for rr in range(2, n + 1):
                    ws[f"{col}{rr}"].fill = fill

        for ci, h in enumerate(headers, 1):
            base = h.rsplit("_", 1)[0] if h and h[-1].isdigit() else h
            key = dv.get(h) or dv.get(base)
            if not key:
                continue
            # range-referenced (values may contain commas) + "warning" style so an
            # annotator can also type a value that isn't in the list.
            v = DataValidation(type="list", formula1=list_ranges[key], allow_blank=True,
                               showDropDown=False, showErrorMessage=True,
                               errorStyle="warning",
                               error="Not in the list - OK to keep if you mean it.",
                               errorTitle="Custom value")
            ws.add_data_validation(v)
            col = get_column_letter(ci)
            v.add(f"{col}2:{col}{n}")

        abs_col = get_column_letter([c for c, _ in left_cols].index("abstract") + 1)
        for rr, row in enumerate(ws.iter_rows(min_row=2, max_row=n), start=2):
            for cell in row:
                cell.alignment = WRAP
            ws[f"{abs_col}{rr}"].font = Font(size=10)
            ws.row_dimensions[rr].height = 150
        ws.freeze_panes = "E2"  # row_id | text_reviewed | date_reviewed | reading_stage
        ws.title = "Review"

    def instructions_sheet(ws, who: str, is_kappa: bool, calib_cut: str = ""):
        write_instructions(ws, who, is_kappa)   # single shared source (rubric_sheet.py)
        ws.title = "Instructions"

    def assign_ids(block: pd.DataFrame, prefix: str, is_kappa: bool) -> pd.DataFrame:
        # kappa block: order by the stratified sequence so the calibration papers are the
        # first rows. Solo blocks: order by doc type / era for a tidy read.
        sort_by = ["order"] if is_kappa else ["doc_type", "era"]
        block = block.sort_values(sort_by).reset_index(drop=True)
        block["row_id"] = [f"{prefix}%03d" % (i + 1) for i in range(len(block))]
        rows = expand_rows(block)
        rows["row_id"] = rows["row_id"] + rows["stage_suffix"]
        return rows

    def make_wb(block, prefix, who, path, is_kappa):
        wb = Workbook()
        rows = assign_ids(block, prefix, is_kappa)
        calib_cut = ""
        if is_kappa:
            cal = rows[rows["phase"] == "calibration"]
            if len(cal):
                calib_cut = str(cal["row_id"].iloc[-1])
        instructions_sheet(wb.active, who, is_kappa, calib_cut)
        add_rubric_sheet(wb)   # Rubric tab, index 1 (rendered from guild_rubric.md)
        list_ranges = add_lists_sheet(wb)
        build_sheet(wb.create_sheet("Review"), rows, list_ranges)
        set_rollup_formula(wb)  # 'method not stated' fills itself in
        remove_completeness(wb)  # no-op on a fresh build; keeps the two pipelines identical
        force_recalc(wb)       # Excel recalculates the above formulas on open, not on a stale cache
        try:
            wb.save(OUT_DIR / path)
        except PermissionError:
            alt = OUT_DIR / (Path(path).stem + "_NEW.xlsx")
            wb.save(alt)
            print(f"  WARNING: {path} is open/locked - wrote {alt.name} instead. "
                  f"Close the old file and rename.")

    kappa = sample[sample.assignment == "kappa_block"].copy()
    n_kb_rows = len(expand_rows(kappa))
    for key, label in ANNOTATORS.items():
        make_wb(kappa, "K",
                f"{label} - shared agreement block ({len(kappa)} papers, {n_kb_rows} rows)",
                f"groundtruth_kappa_{key}.xlsx", is_kappa=True)

    for key in ("bea", *EXTRA_REVIEWERS):
        block = sample[(sample.assignment == "solo") & (sample.annotator == key)].copy()
        make_wb(block, key[0].upper(),
                f"{ANNOTATORS[key]} - main block ({len(block)} papers)",
                f"groundtruth_{key}_main.xlsx", is_kappa=False)

    # MOCK: 2 worked examples (1 abstract-only, 1 full-text) for rubric training BEFORE
    # the real kappa block starts. Drawn from OUTSIDE `sample` entirely (2026-09-17 fix -
    # these used to be the kappa block's own first papers, which meant discussing them
    # as a training exercise would have re-scored already-seen papers inside the real
    # blind kappa measurement). Not scored for agreement; not part of any total.
    mock_pool = papers[~papers.paper_id.isin(sample.paper_id)]
    mock = pd.concat([
        mock_pool[mock_pool.doc_type == "abstract-only"].sample(
            n=1, random_state=rng.integers(1 << 31)),
        mock_pool[mock_pool.doc_type == "full-text"].sample(
            n=1, random_state=rng.integers(1 << 31)),
    ])
    make_wb(mock, "M",
            "MOCK - 2 worked examples (1 abstract-only, 1 full-text) - training only, "
            "not scored, not part of the sample",
            "groundtruth_MOCK.xlsx", is_kappa=False)


def write_stratification_report(papers, sample, args) -> None:
    ft = int((sample.doc_type == "full-text").sum())
    L = [
        "# Ground-truth sample - stratification report", "",
        f"- corpus: `{args.corpus.name}`  |  seed: `{args.seed}`",
        f"- n = {args.n_core} (full-text fraction {args.full_text_frac}). Stratified by "
        f"era + doc_type only (2026-09-17: no function/continent stratification until "
        f"the Task 1 re-extraction runs on this corpus - see the script header note)",
        f"- kappa block n = {args.n_kappa} papers, all full-text, rated by ALL annotators; "
        f"it is the balanced prefix of a stratified pool, so raising --n-kappa later stays "
        f"valid",
        (f"- within the kappa block, the first **{args.n_calibration}** papers are a "
         f"calibration round: everyone does them, then a reconciliation call refines the "
         f"rubric before continuing. Reported Fleiss' kappa uses the remaining "
         f"{args.n_kappa - args.n_calibration} measurement papers (calibration agreement "
         f"reported separately as a pilot)" if args.n_calibration else
         f"- single blind measurement pass, no calibration sub-round (2026-09-17 decision - "
         f"rubric training instead happens on the 2 MOCK papers, drawn from outside the "
         f"sample, before the real block starts)"),
        f"- **{len(sample)} unique papers total**; the {ft} full-text papers each get a "
        f"paired abstract-only row + full-text row (~{len(sample) + ft} annotation rows)",
        "", "## Selected sample by stratum", "",
    ]
    for col in ["doc_type", "era", "assignment", "annotator"]:
        if col not in sample.columns:
            continue
        L.append(f"### {col}")
        fv = papers[col].value_counts() if col in papers.columns else None
        if fv is not None:
            L += ["| level | sampled | frame % |", "|---|---|---|"]
            for lvl, k in sample[col].value_counts().sort_index().items():
                L.append(f"| {lvl} | {k} | {100 * int(fv.get(lvl, 0)) / len(papers):.1f}% |")
        else:
            L += ["| level | sampled |", "|---|---|"]
            for lvl, k in sample[col].value_counts().sort_index().items():
                L.append(f"| {lvl} | {k} |")
        L.append("")
    # workload: abstract-only paper = 1 abstract row (~8 min); full-text paper =
    # an abstract row (~5 min) + a full-text row (~20 min).
    AB, FT_A, FT_B = 8 / 60, 5 / 60, 20 / 60

    def load(df):
        n_ab = int((df.doc_type == "abstract-only").sum())
        n_ft = int((df.doc_type == "full-text").sum())
        return n_ab, n_ft, n_ab + 2 * n_ft, n_ab * AB + n_ft * (FT_A + FT_B)

    kb = sample[sample.assignment == "kappa_block"]
    kb_ab, kb_ft, kb_rows, kb_hrs = load(kb)
    L += ["## Workload per annotator (kappa block + own solo block)", "",
          "| annotator | kappa papers | own solo papers | total papers | rows | est. hours |",
          "|---|---|---|---|---|---|"]
    for key in ANNOTATORS:
        solo = sample[(sample.assignment == "solo") & (sample.annotator == key)]
        s_ab, s_ft, s_rows, s_hrs = load(solo)
        L.append(f"| {ANNOTATORS[key]} | {len(kb)} | {len(solo)} | {len(kb) + len(solo)} "
                 f"| {kb_rows + s_rows} | ~{kb_hrs + s_hrs:.0f} |")
    L += ["",
          f"The kappa block is {len(kb)} papers ({kb_ab} abstract-only + {kb_ft} full-text "
          f"= {kb_rows} rows, ~{kb_hrs:.0f} h) - EVERY annotator rates it.",
          "Nancy & Kitty rate only the kappa block.",
          "Each full-text paper = an abstract-only row (done first, ~5 min) + a full-text",
          "row (~20 min); an abstract-only paper = one row (~8 min).",
          "The paired rows give a human-annotated measure of what abstracts omit vs their",
          "own full text - it strengthens the Task 1 abstract/full-text validation."]
    (OUT_DIR / "stratification_report.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
