#!/usr/bin/env python3
# BMB 2026-08-28
# Scores the completed ground-truth workbooks against an extraction run.
# Produces precision / recall / F1 (interaction level), field accuracy, false-positive /
# false-negative rates, and Fleiss' kappa across annotators on the shared block.
#
# Run this AFTER:
#   1. build_groundtruth_sample.py has produced the workbooks,
#   2. Bea / Nancy / Kitty have filled them in,
#   3. the chosen extraction pipeline has been run on the sampled papers.
#
# Usage:
#   python scripts/04_analyses/score_groundtruth.py \
#       --completed-dir results/manual_validation/groundtruth/completed \
#       --extraction data/<new_extraction>.csv
#
# STATUS: skeleton. The interaction-matching and field-comparison logic is wired for the
# current extraction columns; revisit the FIELD_MAP / matching once the new schema
# (NPH_extraction_schema_design.md) lands.
#
# Kappa unit, by field:
#   - paper-level fields (Q1, Q2, Q3, Q8, Q11, paper_reviewed): 1 item = 1 paper
#     -> ~35 measurement papers x 5 raters
#   - interaction-level fields (fungal_lifestyle, effect_on_host, tissue, evidence_basis):
#     1 item = 1 matched interaction -> ~80-100 items x 5 raters
#   Report Fleiss' kappa per field with a 95% CI on the MEASUREMENT papers only;
#   report calibration-round agreement separately as a pilot; also report kappa on the
#   full kappa block (calibration + measurement) as a sensitivity check.

from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
GT_DIR = ROOT / "results" / "manual_validation" / "groundtruth"

SLOT_RE = re.compile(
    r"^(fungus|host_plant|tissue|fungal_lifestyle|effect_on_host|evidence_basis)_(\d+)$")

# ground-truth column -> extraction column (update once the new schema lands)
FIELD_MAP = {
    "tissue": "tissue",
    "fungal_lifestyle": "primary_guild",   # -> fungal_lifestyle once re-extracted
    "effect_on_host": "effect_on_host",    # new field in the re-extraction
    "Q7": "country",                       # header now starts "Q7  where was..."
    "Q9": "biome",
}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", str(s).lower()).strip()


def genus(name: str) -> str:
    return norm(name).split(" ")[0] if name and str(name).strip() else ""


def load_completed(path: Path) -> pd.DataFrame:
    """Wide one-row-per-paper sheet -> long: one row per annotated interaction."""
    wide = pd.read_excel(path, sheet_name="Review")
    annotator = path.stem.replace("groundtruth_", "").replace("_completed", "")
    long_rows = []
    slot_cols = {}
    for c in wide.columns:
        m = SLOT_RE.match(str(c))
        if m:
            slot_cols.setdefault(int(m.group(2)), {})[m.group(1)] = c
    for _, r in wide.iterrows():
        for s, cols in sorted(slot_cols.items()):
            fungus = r.get(cols.get("fungus", ""), "")
            host = r.get(cols.get("host_plant", ""), "")
            if not str(fungus).strip() and not str(host).strip():
                continue
            long_rows.append({
                "annotator": annotator,
                "paper_id": r["paper_id"],
                "row_id": r.get("row_id"),
                "reading_stage": r.get("reading_stage", "abstract"),
                "slot": s,
                "gt_fungus": fungus, "gt_host": host,
                "gt_tissue": r.get(cols.get("tissue", ""), ""),
                "gt_lifestyle": r.get(cols.get("fungal_lifestyle", ""), ""),
                "gt_effect": r.get(cols.get("effect_on_host", ""), ""),
                "gt_evidence": r.get(cols.get("evidence_basis", ""), ""),
            })
    paper_level = wide[[c for c in wide.columns if c.startswith(("row_id", "paper_id", "Q"))
                        or c in ("annotator", "date_reviewed")]].copy()
    paper_level["annotator"] = annotator
    return pd.DataFrame(long_rows), paper_level


def match_interactions(gt: pd.DataFrame, ex: pd.DataFrame):
    """Per paper: match GT pairs to extraction pairs on (fungus genus, host genus)."""
    tp, fp, fn = 0, 0, 0
    matched = []
    for pid, g in gt.groupby("paper_id"):
        e = ex[ex["paper_id"] == pid]
        gt_pairs = {(genus(a), genus(b)) for a, b in zip(g["gt_fungus"], g["gt_host"])}
        ex_pairs = {(genus(a), genus(b)) for a, b in zip(e["fungal_taxon"], e["plant_host"])}
        gt_pairs.discard(("", ""))
        ex_pairs.discard(("", ""))
        tp += len(gt_pairs & ex_pairs)
        fp += len(ex_pairs - gt_pairs)
        fn += len(gt_pairs - ex_pairs)
        for pair in gt_pairs & ex_pairs:
            matched.append((pid, pair))
    prec = tp / (tp + fp) if tp + fp else np.nan
    rec = tp / (tp + fn) if tp + fn else np.nan
    f1 = 2 * prec * rec / (prec + rec) if prec and rec else np.nan
    return dict(tp=tp, fp=fp, fn=fn, precision=prec, recall=rec, f1=f1), matched


def fleiss_kappa(table: np.ndarray) -> float:
    n_items, n_cat = table.shape
    n_raters = table.sum(axis=1)[0]
    p_j = table.sum(axis=0) / (n_items * n_raters)
    P_i = (table ** 2).sum(axis=1) - n_raters
    P_i = P_i / (n_raters * (n_raters - 1))
    P_bar = P_i.mean()
    P_e = (p_j ** 2).sum()
    return (P_bar - P_e) / (1 - P_e) if 1 - P_e else np.nan


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--completed-dir", type=Path, default=GT_DIR / "completed")
    ap.add_argument("--extraction", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, default=GT_DIR / "metrics")
    args = ap.parse_args()

    files = sorted(args.completed_dir.glob("groundtruth_*.xlsx"))
    if not files:
        print(f"No completed workbooks in {args.completed_dir}")
        return 1
    args.out_dir.mkdir(parents=True, exist_ok=True)

    ex = pd.read_csv(args.extraction, low_memory=False)
    ex["paper_id"] = ex["paper_id"].astype(str)

    gt_long, paper_long = [], []
    for f in files:
        gl, pl = load_completed(f)
        gt_long.append(gl)
        paper_long.append(pl)
    gt_long = pd.concat(gt_long, ignore_index=True)
    gt_long["paper_id"] = gt_long["paper_id"].astype(str)

    # interaction-level P/R/F1 — one annotator per paper, scored PER reading stage:
    #   'abstract' rows  vs the model's abstract-extraction for that paper
    #   'full text' rows vs the model's full-text-extraction for that paper
    primary = (gt_long.sort_values("annotator")
               .drop_duplicates(["paper_id", "reading_stage", "slot"]))
    for stage in sorted(primary["reading_stage"].dropna().unique()):
        g = primary[primary["reading_stage"] == stage]
        e = ex[ex.get("data_source", "").astype(str).str.contains(
            "full" if "full" in stage else "abstract", case=False, na=False)] \
            if "data_source" in ex.columns else ex
        metrics, _ = match_interactions(g, e)
        metrics["reading_stage"] = stage
        pd.DataFrame([metrics]).to_csv(
            args.out_dir / f"interaction_prf_{stage.replace(' ', '_')}.csv", index=False)
        print(f"Interaction-level ({stage}):", metrics)

    # human abstract-vs-full-text: for full-text papers, what the 'full text' row adds
    print("Abstract vs full-text (human): compare per-paper 'abstract' and 'full text' "
          "rows in gt_long — implement alongside the Task 1 paired analysis.")

    # field accuracy on matched pairs — TODO once new schema lands (FIELD_MAP)
    print("Field accuracy + kappa: implement against the re-extraction schema "
          "(see FIELD_MAP and NPH_extraction_schema_design.md).")

    pd.concat(paper_long, ignore_index=True).to_csv(
        args.out_dir / "paper_level_answers.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
