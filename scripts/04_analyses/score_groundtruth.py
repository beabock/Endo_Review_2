#!/usr/bin/env python3
# BMB 2026-08-28, completed 2026-09-03
# Scores the completed ground-truth workbooks (Task 2) against an extraction run and
# against each other. Produces:
#   - interaction precision / recall / F1, per reading stage (human = reference)
#   - field accuracy on matched interactions + on paper-level questions
#   - false-positive / false-negative rates
#   - Fleiss' kappa across annotators on the shared block, per field, with a
#     bootstrap 95% CI, split calibration vs measurement
#   - human abstract-vs-full-text delta (feeds the Task 1 paired analysis)
#
# Run after: build_groundtruth_sample.py -> annotators fill the workbooks -> (optionally)
# the chosen extraction pipeline has produced global_endo_extraction_v5.csv.
#
#   python scripts/04_analyses/score_groundtruth.py \
#       --completed-dir results/manual_validation/groundtruth/completed \
#       --extraction data/global_endo_extraction_v5.csv         # optional
#
# --extraction omitted -> only the human-only analyses (kappa, abstract/full-text delta,
# paper_reviewed breakdown) run.
#
# `--self-test` builds synthetic workbooks + a synthetic extraction and runs the whole
# pipeline, to check the plumbing before real annotations come back.
#
# Human dropdown values are mapped to the same tokens the extractor emits via
# scripts/01_data_preproccessing/extract_schema.py (HUMAN_TO_TOKEN); that module is the
# shared human<->model contract. If it is absent (e.g. on a checkout without the Task 1
# code) the script still runs, comparing raw strings.
#
# Kappa unit, by field:
#   paper-level (Q1/Q2/Q3/Q5/Q6/Q8/Q9/Q11, method ticks): 1 item = 1 paper
#   interaction-level (tissue, fungal_lifestyle, effect_on_host, evidence_basis):
#     1 item = 1 interaction that >=3 raters listed
#   Reported on the MEASUREMENT papers; calibration reported separately as a pilot;
#   full kappa block as a sensitivity check.

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
GT_DIR = ROOT / "results" / "manual_validation" / "groundtruth"
sys.path.insert(0, str(ROOT / "scripts" / "01_data_preproccessing"))

try:
    import extract_schema as S          # noqa: E402
    HUMAN_TO_TOKEN = S.HUMAN_TO_TOKEN
    METHOD_COL_TO_TOKEN = S.METHOD_COL_TO_TOKEN

    def human_token(field, label):
        return S.human_token(field, label)
except Exception:                        # branch without Task 1 code - vendor the essentials
    HUMAN_TO_TOKEN, METHOD_COL_TO_TOKEN = {}, {}

    def human_token(field, label):
        if label is None:
            return None
        s = str(label).strip()
        return s or None

RNG = np.random.default_rng(20260903)

# workbook Q-header -> (question key, extraction column, is this paper-level?)
Q_HEADERS = {
    "Q1  does this paper report a fungus coming from a plant?": ("q1", "is_fungus_in_plant_study"),
    "Q2  paper's main purpose": ("primary_aim", "primary_aim"),
    "Q3  how were the fungi obtained in this paper?": ("sampling_approach", "sampling_approach"),
    "Q4  language of the text you are reading": ("language", "language"),
    "Q5  any sequence-only (uncultured) taxa?": ("uncultured_taxa", "uncultured_taxa"),
    "Q6  strain-level variation noted?": ("strain_variation", "strain_variation"),
    "Q7  where was the plant SAMPLED? (not the authors' institution)": ("sampling_location", "sampling_location"),
    "Q8  what geographic information does the paper contain?": ("sampling_location_status", "sampling_location_status"),
    "Q9  biome (WWF category)": ("biome", "biome"),
    "Q10  how many distinct fungus-host pairs?": ("n_pairs", "n_distinct_pairs"),
    "Q11  was the surface-sterilisation checked?": ("sterilisation_checked", "sterilisation_checked"),
}
PAPER_KAPPA_FIELDS = ["q1", "primary_aim", "sampling_approach", "uncultured_taxa",
                      "strain_variation", "sampling_location_status", "sterilisation_checked"]
INTERACTION_FIELDS = ["tissue", "fungal_lifestyle", "effect_on_host", "evidence_basis"]
SLOT_RE = re.compile(
    r"^(fungus|host_plant|tissue|fungal_lifestyle|effect_on_host|evidence_basis)_(\d+)$")
METHOD_HEADERS = ["culture from sterilised tissue", "microscopy in tissue",
                  "direct sequencing from tissue", "isolate ID by sequencing",
                  "resynthesis / re-inoculation", "method not stated"]


# ------------------------------------------------------------------ normalisation

def _blank(x) -> bool:
    return x is None or (isinstance(x, float) and pd.isna(x)) or str(x).strip() in ("", "nan")


def norm(s) -> str:
    if _blank(s):
        return ""
    return re.sub(r"[^a-z0-9 ]", "", str(s).lower()).strip()


def genus(name) -> str:
    n = norm(name)
    return n.split(" ")[0] if n else ""


def species_key(name) -> str:
    """genus + specific epithet (drops 'sp.', authorities, strain codes)."""
    parts = [p for p in norm(name).split(" ") if p not in ("sp", "spp", "cf", "aff")]
    return " ".join(parts[:2])


def tok_multi(field: str, cell) -> set[str]:
    """A workbook cell that may hold several comma-separated dropdown values."""
    if _blank(cell):
        return set()
    out = set()
    for piece in re.split(r"\s*[;,]\s*", str(cell)):
        piece = piece.strip()
        if piece:
            out.add(human_token(field, piece) or norm(piece))
    return out


def tok1(field: str, cell) -> str | None:
    if _blank(cell):
        return None
    return human_token(field, str(cell).strip()) or norm(cell)


# ------------------------------------------------------------------ load workbooks

def annotator_name(path: Path) -> str:
    return (path.stem.replace("groundtruth_", "").replace("_completed", "")
            .replace("kappa_", "").replace("_main", ""))


def load_completed(path: Path):
    wide = pd.read_excel(path, sheet_name="Review")
    wide.columns = [str(c) for c in wide.columns]
    who = annotator_name(path)

    slot_cols: dict[int, dict] = {}
    for c in wide.columns:
        m = SLOT_RE.match(c)
        if m:
            slot_cols.setdefault(int(m.group(2)), {})[m.group(1)] = c

    inter_rows, paper_rows = [], []
    for _, r in wide.iterrows():
        pid = "" if _blank(r.get("paper_id")) else str(r.get("paper_id")).strip()
        if not pid:
            continue
        stage = "abstract" if _blank(r.get("reading_stage")) else str(r.get("reading_stage")).strip()
        reviewed = "" if _blank(r.get("paper_reviewed")) else str(r.get("paper_reviewed")).strip().lower()

        prow = {"annotator": who, "paper_id": pid, "row_id": str(r.get("row_id", "")),
                "reading_stage": stage, "paper_reviewed": reviewed}
        for hdr, (key, _excol) in Q_HEADERS.items():
            if hdr in wide.columns:
                v = r.get(hdr)
                prow[key] = (str(v).strip() if pd.notna(v) else "")
                if key not in ("sampling_location", "n_pairs"):
                    prow[key + "_tok"] = tok1(key if key != "q1" else "yn_unclear", v) \
                        if key not in ("q1",) else norm(v) or None
        prow["methods_tok"] = {
            (METHOD_COL_TO_TOKEN.get(h, norm(h))) for h in METHOD_HEADERS
            if h in wide.columns and str(r.get(h, "")).strip().lower() in ("yes", "y", "x", "true", "1")
        }
        paper_rows.append(prow)

        for s, cols in sorted(slot_cols.items()):
            fu = r.get(cols.get("fungus", ""), "")
            ho = r.get(cols.get("host_plant", ""), "")
            if _blank(fu) and _blank(ho):
                continue
            fu = "" if _blank(fu) else str(fu).strip()
            ho = "" if _blank(ho) else str(ho).strip()
            inter_rows.append({
                "annotator": who, "paper_id": pid, "row_id": str(r.get("row_id", "")),
                "reading_stage": stage, "slot": s,
                "fungus": fu, "host": ho,
                "g_key": (genus(fu), genus(ho)), "sp_key": (species_key(fu), species_key(ho)),
                "tissue": tok_multi("tissue", r.get(cols.get("tissue", ""), "")),
                "fungal_lifestyle": tok1("fungal_lifestyle", r.get(cols.get("fungal_lifestyle", ""), "")),
                "effect_on_host": tok1("effect_on_host", r.get(cols.get("effect_on_host", ""), "")),
                "evidence_basis": tok1("evidence_basis", r.get(cols.get("evidence_basis", ""), "")),
            })
    return pd.DataFrame(inter_rows), pd.DataFrame(paper_rows)


def _col(df: pd.DataFrame, *names) -> pd.Series:
    for n in names:
        if n in df.columns:
            return df[n]
    return pd.Series([""] * len(df), index=df.index)


def load_extraction(path: Path):
    ex = pd.read_csv(path, low_memory=False)
    ex["paper_id"] = ex["paper_id"].astype(str)
    ds = _col(ex, "data_source").astype(str).str.lower()
    ex["stage"] = np.where(ds.str.contains("full"), "full text", "abstract")
    fu, ho = _col(ex, "fungus", "fungal_taxon"), _col(ex, "host_plant", "plant_host")
    ex["g_key"] = list(zip(fu.map(genus), ho.map(genus)))
    ex["sp_key"] = list(zip(fu.map(species_key), ho.map(species_key)))
    ex["tissue_set"] = _col(ex, "tissue").fillna("").map(
        lambda x: {t.strip() for t in re.split(r"[|;,]", str(x)) if t.strip() and t.strip() != "nan"})
    for f in ("fungal_lifestyle", "effect_on_host", "evidence_basis"):
        if f not in ex.columns:
            ex[f] = None
    return ex


# ------------------------------------------------------------------ interaction P/R/F1

def prf_by_stage(gt_i: pd.DataFrame, ex: pd.DataFrame, out_dir: Path):
    rows = []
    for stage in sorted(gt_i["reading_stage"].dropna().unique()):
        g = gt_i[gt_i["reading_stage"] == stage]
        e = ex[ex["stage"] == stage] if stage in set(ex["stage"]) else ex
        tp = fp = fn = tp_sp = 0
        for pid, gg in g.groupby("paper_id"):
            ee = e[e["paper_id"] == pid]
            gp = {k for k in gg["g_key"] if k != ("", "")}
            ep = {k for k in ee["g_key"] if k != ("", "")}
            gsp = {k for k in gg["sp_key"] if all(k)}
            esp = {k for k in ee["sp_key"] if all(k)}
            tp += len(gp & ep); fp += len(ep - gp); fn += len(gp - ep)
            tp_sp += len(gsp & esp)
        prec = tp / (tp + fp) if tp + fp else np.nan
        rec = tp / (tp + fn) if tp + fn else np.nan
        f1 = 2 * prec * rec / (prec + rec) if prec and rec else np.nan
        rows.append(dict(reading_stage=stage, tp=tp, fp=fp, fn=fn,
                         precision=round(prec, 3), recall=round(rec, 3), f1=round(f1, 3),
                         species_level_tp=tp_sp))
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "interaction_prf_by_stage.csv", index=False)
    print("\n== interaction precision / recall / F1 ==\n", df.to_string(index=False))
    return df


def fp_fn_detail(gt_i, gt_p, ex, out_dir):
    """FP: model interactions in papers the human marked Q1=no / not-a-fungus-study."""
    neg = set(gt_p[(gt_p["q1"].str.lower().isin(["no"]))
                   | (gt_p["paper_reviewed"].str.contains("not a fungus", na=False))]["paper_id"])
    fp_neg = ex[ex["paper_id"].isin(neg) & ex["g_key"].map(lambda k: k != ("", ""))]
    rows = []
    for pid, gg in gt_i.groupby("paper_id"):
        ee = ex[ex["paper_id"] == pid]
        gp = {k for k in gg["g_key"] if k != ("", "")}
        ep = {k for k in ee["g_key"] if k != ("", "")}
        for k in ep - gp:
            rows.append(dict(paper_id=pid, kind="model_only_pair", fungus=k[0], host=k[1]))
        for k in gp - ep:
            rows.append(dict(paper_id=pid, kind="human_only_pair", fungus=k[0], host=k[1]))
    det = pd.DataFrame(rows)
    det.to_csv(out_dir / "fp_fn_detail.csv", index=False)
    summary = dict(
        papers_marked_negative=len(neg),
        model_interactions_in_negative_papers=len(fp_neg),
        model_only_pairs=int((det["kind"] == "model_only_pair").sum()) if len(det) else 0,
        human_only_pairs=int((det["kind"] == "human_only_pair").sum()) if len(det) else 0,
    )
    print("\n== false positive / negative ==\n", summary)
    pd.DataFrame([summary]).to_csv(out_dir / "fp_fn_summary.csv", index=False)


def field_accuracy(gt_i, ex, out_dir):
    """Agreement on tissue / lifestyle / effect / evidence for matched interactions.
    Accuracy is computed only where BOTH sides gave a codeable value; blanks are
    reported separately as coverage."""
    rows = []
    for stage in sorted(gt_i["reading_stage"].dropna().unique()):
        g = gt_i[gt_i["reading_stage"] == stage]
        e = ex[ex["stage"] == stage] if stage in set(ex["stage"]) else ex
        for pid, gg in g.groupby("paper_id"):
            ee = e[e["paper_id"] == pid]
            for _, gr in gg.iterrows():
                cand = ee[ee["g_key"] == gr["g_key"]]
                if cand.empty:
                    continue
                mr = cand.iloc[0]
                for f in INTERACTION_FIELDS:
                    hv = gr[f]
                    mv = mr.get("tissue_set") if f == "tissue" else mr.get(f)
                    h_has = bool(hv) if f == "tissue" else hv not in (None, "", "not_stated")
                    m_has = bool(mv) if f == "tissue" else (
                        mv not in (None, "", "not_stated") and not pd.isna(mv))
                    both = h_has and m_has
                    ok = (bool(hv & mv) if f == "tissue" else (hv == mv)) if both else False
                    rows.append(dict(reading_stage=stage, field=f,
                                     both_coded=int(both), agree=int(ok),
                                     human_blank=int(not h_has), model_blank=int(not m_has)))
    if not rows:
        print("\n== field accuracy ==  (no matched interactions yet)")
        return
    d = pd.DataFrame(rows)
    fa = (d[d.both_coded == 1].groupby(["reading_stage", "field"])["agree"]
          .agg(accuracy="mean", n_both_coded="count").round(3).reset_index())
    cov = (d.groupby(["reading_stage", "field"])
           .agg(n_matched=("both_coded", "size"),
                human_blank=("human_blank", "sum"),
                model_blank=("model_blank", "sum")).reset_index())
    fa = fa.merge(cov, on=["reading_stage", "field"], how="right")
    fa.to_csv(out_dir / "field_accuracy.csv", index=False)
    print("\n== field accuracy (matched interactions; accuracy = both-coded only) ==\n",
          fa.to_string(index=False))


# ------------------------------------------------------------------ Fleiss' kappa

def fleiss_kappa(counts: np.ndarray) -> float:
    """counts[i, j] = # raters who put item i in category j. Handles variable n_i."""
    counts = counts[counts.sum(axis=1) >= 2]
    if len(counts) < 2:
        return np.nan
    n_i = counts.sum(axis=1)
    p_j = counts.sum(axis=0) / n_i.sum()
    P_i = ((counts ** 2).sum(axis=1) - n_i) / (n_i * (n_i - 1))
    P_bar, P_e = P_i.mean(), (p_j ** 2).sum()
    return (P_bar - P_e) / (1 - P_e) if (1 - P_e) else np.nan


def kappa_ci(counts: np.ndarray, n_boot: int = 2000):
    k = fleiss_kappa(counts)
    used_cats = (counts.sum(axis=0) > 0).sum()
    # a percentile bootstrap is only meaningful with enough items and real variation
    if np.isnan(k) or len(counts) < 10 or used_cats < 2:
        return k, np.nan, np.nan
    boot = np.array([fleiss_kappa(counts[RNG.integers(0, len(counts), len(counts))])
                     for _ in range(n_boot)])
    boot = boot[~np.isnan(boot)]
    if len(boot) < n_boot // 2:
        return k, np.nan, np.nan
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return k, min(k, lo), max(k, hi)


def rating_table(labels_per_item: list[list[str]]) -> np.ndarray:
    cats = sorted({c for item in labels_per_item for c in item if c not in (None, "")})
    idx = {c: j for j, c in enumerate(cats)}
    tab = np.zeros((len(labels_per_item), max(len(cats), 1)))
    for i, item in enumerate(labels_per_item):
        for c in item:
            if c in idx:
                tab[i, idx[c]] += 1
    return tab


def kappa_block(gt_i, gt_p, calib_cut: int, out_dir: Path):
    def block(df):
        return df[df["row_id"].str.match(r"^K\d", na=False)].copy()

    pi, pp = block(gt_i), block(gt_p)
    if pp.empty:
        print("\n== Fleiss' kappa ==  (no K-block rows found)")
        return
    pp["pnum"] = pd.to_numeric(pp["row_id"].str.extract(r"K(\d+)", expand=False), errors="coerce")
    pi = pi.merge(pp[["paper_id", "reading_stage", "pnum"]].drop_duplicates(),
                  on=["paper_id", "reading_stage"], how="left")

    out = []
    for phase, sel in [("calibration", lambda n: n <= calib_cut),
                       ("measurement", lambda n: n > calib_cut),
                       ("full_block", lambda n: n > 0)]:
        pp_s = pp[pp["pnum"].map(sel, na_action="ignore").fillna(False)]
        pi_s = pi[pi["pnum"].map(sel, na_action="ignore").fillna(False)]
        # paper-level fields
        for f in PAPER_KAPPA_FIELDS:
            col = f + "_tok" if (f + "_tok") in pp_s.columns else f
            items = [g[col].dropna().astype(str).tolist()
                     for _, g in pp_s.groupby(["paper_id", "reading_stage"]) if col in pp_s]
            items = [it for it in items if len(it) >= 2]
            if len(items) >= 3:
                k, lo, hi = kappa_ci(rating_table(items))
                out.append(dict(phase=phase, level="paper", field=f, n_items=len(items),
                                kappa=round(k, 3), ci_lo=round(lo, 3), ci_hi=round(hi, 3)))
        # interaction-level fields: one item = a (paper, genus-pair) >=3 raters listed
        for f in INTERACTION_FIELDS:
            groups: dict = {}
            for _, r in pi_s.iterrows():
                key = (r["paper_id"], r["reading_stage"], r["g_key"])
                v = r[f]
                v = (",".join(sorted(v)) if isinstance(v, set) else v)
                groups.setdefault(key, []).append((r["annotator"], v))
            items = [[v for _a, v in vs if v not in (None, "", "nan")]
                     for vs in groups.values() if len({a for a, _ in vs}) >= 3]
            items = [it for it in items if len(it) >= 3]
            if len(items) >= 3:
                k, lo, hi = kappa_ci(rating_table(items))
                out.append(dict(phase=phase, level="interaction", field=f, n_items=len(items),
                                kappa=round(k, 3), ci_lo=round(lo, 3), ci_hi=round(hi, 3)))
    kdf = pd.DataFrame(out)
    kdf.to_csv(out_dir / "fleiss_kappa.csv", index=False)
    print("\n== Fleiss' kappa (>=3 raters per item) ==\n",
          kdf.to_string(index=False) if len(kdf) else "  (not enough overlapping ratings yet)")


# ------------------------------------------------------------------ human abs vs full

def abstract_vs_fulltext(gt_i, gt_p, out_dir):
    """For papers with both rows from the same annotator: what the full text adds."""
    rows = []
    key = ["annotator", "paper_id"]
    ab = gt_i[gt_i["reading_stage"] == "abstract"].groupby(key)["g_key"].apply(
        lambda s: {k for k in s if k != ("", "")})
    ft = gt_i[gt_i["reading_stage"] == "full text"].groupby(key)["g_key"].apply(
        lambda s: {k for k in s if k != ("", "")})
    for k in set(ab.index) & set(ft.index):
        a, f = ab[k], ft[k]
        rows.append(dict(annotator=k[0], paper_id=k[1],
                         n_abstract=len(a), n_fulltext=len(f),
                         added_by_fulltext=len(f - a), dropped=len(a - f)))
    # paper-level "not stated" that the full text resolved
    pl = gt_p.pivot_table(index=["annotator", "paper_id"], columns="reading_stage",
                          values=[f + "_tok" for f in PAPER_KAPPA_FIELDS if f != "q1"],
                          aggfunc="first")
    df = pd.DataFrame(rows)
    if len(df):
        df.to_csv(out_dir / "human_abstract_vs_fulltext.csv", index=False)
        try:
            from scipy.stats import wilcoxon
            d = df[df["n_abstract"] != df["n_fulltext"]]
            w = wilcoxon(d["n_fulltext"], d["n_abstract"]) if len(d) >= 6 else None
        except Exception:
            w = None
        print("\n== human abstract vs full text ==")
        print(f"  {len(df)} paired papers | mean interactions abstract {df.n_abstract.mean():.2f} "
              f"-> full text {df.n_fulltext.mean():.2f}")
        print(f"  full text added a pair in {(df.added_by_fulltext > 0).sum()} papers, "
              f"dropped one in {(df.dropped > 0).sum()}")
        if w is not None:
            print(f"  paired Wilcoxon (n!=): W={w.statistic:.1f}, p={w.pvalue:.4f}")
    else:
        print("\n== human abstract vs full text ==  (no paired rows yet)")
    _ = pl


def paper_reviewed_breakdown(gt_p, out_dir):
    b = (gt_p.assign(pr=gt_p["paper_reviewed"].replace("", "(blank / not done)"))
         .groupby("pr")["paper_id"].nunique().sort_values(ascending=False))
    b.to_csv(out_dir / "paper_reviewed_breakdown.csv")
    print("\n== paper_reviewed ==\n", b.to_string())


# ------------------------------------------------------------------ self-test

def _self_test(out_dir: Path) -> int:
    """Generate synthetic completed workbooks + extraction, run the pipeline."""
    import openpyxl
    tmp = out_dir / "_selftest"
    (tmp / "completed").mkdir(parents=True, exist_ok=True)
    lifestyles = list(S.FUNGAL_LIFESTYLE) if "S" in globals() else ["endophyte", "plant_pathogen"]
    hdrs = (["row_id", "paper_reviewed", "date_reviewed", "reading_stage", "paper_id",
             "doi_link", "year", "journal", "title", "abstract"]
            + list(Q_HEADERS) + METHOD_HEADERS
            + [f"{c}_{s}" for s in range(1, 6)
               for c in ("fungus", "host_plant", "tissue", "fungal_lifestyle",
                         "effect_on_host", "evidence_basis")]
            + ["extra_pairs_or_NGS_community_summary", "anything_you_were_unsure_about"])
    papers = [f"P{i:03d}" for i in range(20)]
    for who in ["bea", "nancy", "kitty", "ian", "jack"]:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Review"
        ws.append(hdrs)
        for i, pid in enumerate(papers):
            row = {h: "" for h in hdrs}
            row.update({"row_id": f"K{i+1:03d}a", "paper_reviewed": "complete",
                        "reading_stage": "abstract", "paper_id": pid})
            row["Q1  does this paper report a fungus coming from a plant?"] = "yes"
            row["Q9  biome (WWF category)"] = "temperate or boreal forest"
            row["fungus_1"] = "Colletotrichum sp."
            row["host_plant_1"] = "Quercus robur"
            row["fungal_lifestyle_1"] = lifestyles[(i + (who == "nancy")) % len(lifestyles)]
            row["effect_on_host_1"] = "not reported (fungus just isolated / detected)"
            ws.append([row[h] for h in hdrs])
        wb.save(tmp / "completed" / f"groundtruth_kappa_{who}.xlsx")
    ex = pd.DataFrame([{"paper_id": p, "data_source": "abstract-reextract",
                        "fungus": "Colletotrichum gloeosporioides", "host_plant": "Quercus robur",
                        "tissue": "leaf", "fungal_lifestyle": "endophyte",
                        "effect_on_host": "not_reported", "evidence_basis": "inferred_from_taxon",
                        "is_fungus_in_plant_study": "yes", "biome": "temperate_boreal_forest"}
                       for p in papers])
    ex.to_csv(tmp / "extraction.csv", index=False)
    print("self-test data in", tmp)
    return run(tmp / "completed", tmp / "extraction.csv", tmp / "metrics", 15)


# ------------------------------------------------------------------ orchestration

def run(completed_dir: Path, extraction: Path | None, out_dir: Path, calib_cut: int) -> int:
    files = sorted(completed_dir.glob("groundtruth_*.xlsx"))
    if not files:
        print(f"No completed workbooks in {completed_dir}")
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    gi, gp = [], []
    for f in files:
        i, p = load_completed(f)
        gi.append(i); gp.append(p)
        print(f"  {f.name}: {len(p)} rows, {len(i)} interactions")
    gt_i = pd.concat(gi, ignore_index=True)
    gt_p = pd.concat(gp, ignore_index=True)
    gt_p.to_csv(out_dir / "paper_level_answers.csv", index=False)

    paper_reviewed_breakdown(gt_p, out_dir)
    kappa_block(gt_i, gt_p, calib_cut, out_dir)
    abstract_vs_fulltext(gt_i, gt_p, out_dir)

    if extraction and Path(extraction).exists():
        ex = load_extraction(Path(extraction))
        # score against ONE annotator per paper (first alphabetically) so P/R/F1 is
        # not inflated by counting each rater's list separately
        primary = gt_i.sort_values("annotator").drop_duplicates(
            ["paper_id", "reading_stage", "slot"])
        prf_by_stage(primary, ex, out_dir)
        field_accuracy(primary, ex, out_dir)
        fp_fn_detail(primary, gt_p.sort_values("annotator").drop_duplicates(
            ["paper_id", "reading_stage"]), ex, out_dir)
    else:
        print("\n(no --extraction: interaction P/R/F1, field accuracy and FP/FN skipped)")
    print(f"\nmetrics -> {out_dir}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--completed-dir", type=Path, default=GT_DIR / "completed")
    ap.add_argument("--extraction", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, default=GT_DIR / "metrics")
    ap.add_argument("--calib-cut", type=int, default=15,
                    help="K-block paper number at/below which = calibration round")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test(args.out_dir)
    return run(args.completed_dir, args.extraction, args.out_dir, args.calib_cut)


if __name__ == "__main__":
    raise SystemExit(main())
