#!/usr/bin/env python3
# BMB 2026-08-28, completed 2026-09-03
# Scores the completed ground-truth workbooks (Task 2) against an extraction run and
# against each other. Produces:
#   - interaction precision / recall / F1, per reading stage (human = reference)
#   - field accuracy on matched interactions + on paper-level questions
#   - false-positive / false-negative rates
#   - Fleiss' kappa AND Gwet's AC1 across annotators on the shared block, per field,
#     each with a bootstrap 95% CI. AC1 is the primary agreement metric (Ian Mounts,
#     2026-09-17): kappa's chance-agreement term inflates when one category is very
#     common (the "kappa paradox"), which is likely here (e.g. Q1, effect_on_host).
#     Kappa is still reported for comparability with the IRR literature.
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
# text_reviewed breakdown) run.
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
#   paper-level (PAPER_KAPPA_FIELDS; columns found by keyword - see find_columns, 2026-10-08
#   layout: Q1-Q11 + method columns, with q1 derived from text_reviewed): 1 item = 1 paper
#   interaction-level (tissue, fungal_lifestyle, effect_on_host, evidence_basis):
#     1 item = 1 interaction that >=3 raters listed
#   Reported on the MEASUREMENT papers; calibration reported separately as a pilot;
#   full kappa block as a sensitivity check.
#
# If AC1 comes back low (2026-09-17 decision, see NPH_task2_ground_truth_plan.md):
#   threshold decided in advance, not after seeing the number (same Landis & Koch bands
#   used for kappa, applied to AC1: <0.4 poor, 0.4-0.6 moderate, >=0.6 substantial - AC1
#   is on the same -1..1 scale). If below threshold: 1) use the per-field breakdown
#   below to find which field(s) drive it, 2) group
#   reconciliation on the disagreeing items only, tighten that field's rubric, 3)
#   re-test the fix on a FRESH disjoint set of papers, never re-score the same 20
#   (that would trivially inflate agreement), 4) report the real number either way,
#   with the reconciliation described. Still weak after one revision -> collapse that
#   field to coarser categories (same escape hatch as reported_function in
#   NPH_extraction_schema_design.md) rather than present an unreliable fine-grained
#   field as validated.

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
    collapse_lifestyle = S.collapse_lifestyle

    def human_token(field, label):
        return S.human_token(field, label)
except Exception:                        # branch without Task 1 code - vendor the essentials
    HUMAN_TO_TOKEN, METHOD_COL_TO_TOKEN = {}, {}

    def human_token(field, label):
        if label is None:
            return None
        s = str(label).strip()
        return s or None

    def collapse_lifestyle(token):
        return token

RNG = np.random.default_rng(20260903)

# 2026-10-08: columns are found by KEYWORDS in the header, not by exact header text, so the
# wording and Q-numbers on the sheet can change without silently dropping a field.
# (key, keywords - any one in the lower-cased header, extraction column)
Q_FIELDS = [
    ("q1", ("fungus coming from a plant",), "is_fungus_in_plant_study"),   # dropped 2026-10-08: derived
    ("primary_aim", ("main purpose",), "primary_aim"),
    ("fungus_source", ("where did the fungi come from",), "fungus_source"),
    ("sampling_approach", ("how were the fungi obtained",), "sampling_approach"),  # dropped 2026-10-08
    ("language", ("language of the text",), "language"),
    ("uncultured_taxa", ("sequence-only",), "uncultured_taxa"),
    ("strain_variation", ("strain-level",), "strain_variation"),
    ("sampling_country", ("country where",), "sampling_country"),
    ("sampling_location", ("site / locality",), "sampling_location"),       # dropped 2026-10-08
    ("coordinates_given", ("coordinates",), "coordinates_given"),
    ("sampling_location_status", ("geographic information",), "sampling_location_status"),
    ("biome", ("biome",), "biome"),
    ("n_pairs", ("fungus-host pairs",), "n_distinct_pairs"),
    ("sterilisation_checked", ("sterilisation checked", "surface-sterilisation"), "sterilisation_checked"),
    ("ubiquity_claim", ("all or nearly all plants",), "contains_ubiquity_claim"),  # vs 06_detect_ubiquity
]
METHOD_FIELDS = [                     # method column -> DETECTION_METHODS token
    ("culture_sterilised", ("surface-sterilised tissue", "culture from sterilised")),
    ("microscopy_in_tissue", ("microscopy",)),
    ("direct_sequencing", ("sequencing from tissue",)),
    ("isolate_id_sequencing", ("isolate id",)),
    ("resynthesis_inoculation", ("inoculat", "resynthesis")),
]
# q1 is now implied by text_reviewed (complete = yes; review / not fungus-in-plant = no), so its
# agreement mirrors text_reviewed. "inoculation" = confirmed / not confirmed inside the plant.
PAPER_KAPPA_FIELDS = ["q1", "primary_aim", "fungus_source", "uncultured_taxa",
                      "strain_variation", "sampling_country", "coordinates_given",
                      "sampling_location_status", "biome", "sterilisation_checked",
                      "ubiquity_claim", "inoculation"]
INTERACTION_FIELDS = ["tissue", "fungal_lifestyle", "effect_on_host", "evidence_basis"]
SLOT_RE = re.compile(
    r"^(fungus|host_plant|tissue|fungal_lifestyle|effect_on_host|evidence_basis)_(\d+)\b")


def find_columns(columns):
    """-> ({question key: column}, {method token: column})."""
    q, m = {}, {}
    for c in columns:
        h = str(c).lower()
        if SLOT_RE.match(str(c)) or h.startswith(("extra_pairs", "anything_you")):
            continue
        hit = next((tok for tok, kws in METHOD_FIELDS if any(k in h for k in kws)), None)
        if hit:
            m.setdefault(hit, c)
            continue
        for key, kws, _ex in Q_FIELDS:
            if key not in q and any(k in h for k in kws):
                q[key] = c
                break
    return q, m


def q1_from_status(reviewed) -> str | None:
    s = str(reviewed or "").lower()
    if s.startswith("complete"):
        return "yes"
    if s.startswith("review") or "not a fungus" in s or "not a paper" in s:
        return "no"
    return None


# ------------------------------------------------------------------ normalisation

def _blank(x) -> bool:
    return x is None or (isinstance(x, float) and pd.isna(x)) or str(x).strip() in ("", "nan")


_NA_TOKENS = {"na", "n a", "none", "nil", "not applicable", "no pair", "no pairs", "no more pairs"}


def _is_na(x) -> bool:
    """Blank or an explicit not-applicable marker (n/a, none, ...) - NOT 'not stated'."""
    return _blank(x) or re.sub(r"[^a-z ]", " ", str(x).lower()).strip() in _NA_TOKENS \
        or re.sub(r"[^a-z]", "", str(x).lower()) in _NA_TOKENS


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
    whole = str(cell).strip()
    if whole in HUMAN_TO_TOKEN.get(field, {}):          # an untouched label that contains a comma
        return {HUMAN_TO_TOKEN[field][whole]}
    out = set()
    for piece in re.split(r"\s*[;,]\s*", whole):
        piece = piece.strip()
        if piece:
            out.add(tok1(field, piece))
    return {t for t in out if t}


_COUNTRY_ALIAS = {
    "usa": "united states", "us": "united states", "u s": "united states",
    "united states of america": "united states", "uk": "united kingdom",
    "great britain": "united kingdom", "england": "united kingdom", "scotland": "united kingdom",
    "wales": "united kingdom", "northern ireland": "united kingdom",
    "peoples republic of china": "china", "prc": "china", "republic of korea": "south korea",
    "korea": "south korea", "russian federation": "russia", "czech republic": "czechia",
    "cote divoire": "ivory coast", "viet nam": "vietnam", "turkiye": "turkey",
    "the netherlands": "netherlands", "holland": "netherlands", "burma": "myanmar",
    "drc": "democratic republic of the congo", "dr congo": "democratic republic of the congo",
    "swaziland": "eswatini", "cabo verde": "cape verde", "uae": "united arab emirates",
}


def country_set(cell) -> frozenset:
    """Q7a / model sampling_country -> set of normalised country names ('not stated' -> empty)."""
    if _blank(cell):
        return frozenset()
    out = set()
    for piece in re.split(r"\s*[;|]\s*", str(cell)):
        n = norm(piece)
        n = _COUNTRY_ALIAS.get(n, n)
        if n and n not in ("not stated", "unclear", "none", "na"):
            out.add(n)
    return frozenset(out)


def coords_given(cell) -> str | None:
    """Q7d is free text (coordinates as written, or 'not stated') -> yes / no for scoring."""
    if _blank(cell):
        return None
    return "no" if norm(cell) in ("no", "none", "not stated", "na", "n a", "not given",
                                    "not reported") else "yes"


def country_token(cell) -> str | None:
    """Single label for kappa: sorted countries joined by '; ', or 'not stated'."""
    if _blank(cell):
        return None
    cs = country_set(cell)
    return "; ".join(sorted(cs)) if cs else "not stated"


def _typed(field: str, s: str) -> str | None:
    """A value typed over a dropdown: 'other: ...', 'non-English: French', 'English + French'."""
    low = s.lower()
    if field == "language":
        if low.startswith(("non-english", "non english")):
            return "non_english"
        if low.startswith(("english +", "english and")):
            return "bilingual"
    if low.startswith("other"):
        return "other"
    return None


def tok1(field: str, cell) -> str | None:
    if _blank(cell):
        return None
    s = str(cell).strip()
    t = human_token(field, s)
    if t == s:                                   # not a known dropdown label
        t = _typed(field, s) or t
    if field == "fungal_lifestyle":
        t = collapse_lifestyle(t)
    return t or norm(cell)


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

    qcols, mcols = find_columns(wide.columns)
    stage_col = "text_type" if "text_type" in wide.columns else "reading_stage"
    unsure_col = next((c for c in wide.columns if c.startswith("anything_you")), None)

    inter_rows, paper_rows = [], []
    for _, r in wide.iterrows():
        pid = "" if _blank(r.get("paper_id")) else str(r.get("paper_id")).strip()
        if not pid:
            continue
        stage = "abstract" if _blank(r.get(stage_col)) else str(r.get(stage_col)).strip()
        reviewed = "" if _blank(r.get("text_reviewed")) else str(r.get("text_reviewed")).strip().lower()

        prow = {"annotator": who, "paper_id": pid, "row_id": str(r.get("row_id", "")),
                "reading_stage": stage, "text_reviewed": reviewed,
                "notes": "" if (unsure_col is None or _blank(r.get(unsure_col)))
                else str(r.get(unsure_col)).strip()}
        for key, col in qcols.items():
            v = r.get(col)
            prow[key] = (str(v).strip() if pd.notna(v) else "")
            if key == "sampling_country":
                prow[key + "_tok"] = country_token(v)
            elif key == "coordinates_given":
                prow["coordinates_text"] = prow[key]                 # kept for mapping
                prow[key + "_tok"] = coords_given(v)
            elif key in ("q1", "ubiquity_claim"):
                prow[key + "_tok"] = norm(v) or None
            elif key == "biome":                      # may list several -> sorted set token
                prow[key + "_tok"] = ";".join(sorted(tok_multi("biome", v))) or None
            elif key not in ("sampling_location", "n_pairs"):
                prow[key + "_tok"] = tok1(key, v)
        if "q1" not in qcols:                         # Q1 dropped 2026-10-08: implied by status
            prow["q1"] = prow["q1_tok"] = q1_from_status(reviewed)

        vals = {tok: ("" if _blank(r.get(col)) else str(r.get(col)).strip().lower())
                for tok, col in mcols.items()}
        prow["methods_tok"] = {tok for tok, v in vals.items()
                               if v in ("yes", "y", "x", "true", "1") or v.startswith("yes")}
        if len(vals) == 5 and all(v == "not stated" for v in vals.values()):   # derived roll-up
            prow["methods_tok"].add(METHOD_COL_TO_TOKEN.get("method not stated", "not_stated"))
        inoc = vals.get("resynthesis_inoculation", "")
        prow["inoculation_tok"] = ("confirmed" if "and confirmed" in inoc
                                   else "not_confirmed" if "not confirmed" in inoc
                                   else (norm(inoc) or None))
        paper_rows.append(prow)

        for s, cols in sorted(slot_cols.items()):
            fu = r.get(cols.get("fungus", ""), "")
            ho = r.get(cols.get("host_plant", ""), "")
            fu = "" if _is_na(fu) else fu          # "N/A" / "none" = an explicitly unused block
            ho = "" if _is_na(ho) else ho
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
    ex["fungal_lifestyle"] = ex["fungal_lifestyle"].map(collapse_lifestyle)   # v5.2 -> v5.3
    return ex


# ------------------------------------------------------------------ interaction P/R/F1

def prf_by_stage(gt_i: pd.DataFrame, ex: pd.DataFrame, out_dir: Path, partial=frozenset()):
    """`partial` = paper_ids whose human list is NOT exhaustive (Q10 > the 5 blocks). For those,
    model pairs the human did not list cannot be called false positives, so they add to
    tp / fn only (recall), never to fp (precision)."""
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
            tp += len(gp & ep); fn += len(gp - ep)
            if pid not in partial:
                fp += len(ep - gp)
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
                   | (gt_p["text_reviewed"].str.contains("not a fungus", na=False))]["paper_id"])
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


def _tissue_expand(ts):
    """'aerial_parts' (shoots, not separated) is compatible with leaf / stem."""
    ts = set(ts)
    return ts | {"leaf", "stem_wood_bark"} if "aerial_parts" in ts else ts


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
                    ok = (bool(_tissue_expand(hv) & _tissue_expand(mv)) if f == "tissue" else (hv == mv)) if both else False
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


# ------------------------------------------------------------------ consensus reference

def _mode(vals):
    """Most common non-blank value; ties -> the first one (callers pass annotator-sorted rows)."""
    vals = [v for v in vals if not _blank(v)]
    if not vals:
        return None
    cnt = {}
    for v in vals:
        cnt[str(v)] = cnt.get(str(v), 0) + 1
    best = max(cnt.values())
    return next(v for v in vals if cnt[str(v)] == best)


def consensus_reference(gt_i: pd.DataFrame, gt_p: pd.DataFrame, out_dir: Path):
    """Reference standard = majority of the annotators who rated the item (not one rater).

    Paper level: modal answer per question; a method counts if > half the raters ticked it.
    Interaction level: a pair is in the reference if > half of the raters listed it (matched on
    genus x genus); its fields are the modal values. Solo-block papers have one rater, so the
    reference is just that annotator. Everything the raters split on goes to
    reconciliation_items.csv - the list to resolve when discussing disagreements."""
    gp = gt_p.sort_values(["paper_id", "reading_stage", "annotator"])
    gi = gt_i.sort_values(["paper_id", "reading_stage", "annotator", "slot"])
    n_raters = gp[gp["text_reviewed"] == "complete"].groupby(
        ["paper_id", "reading_stage"])["annotator"].nunique().to_dict()
    recon = []

    prow = []
    for (pid, st), g in gp.groupby(["paper_id", "reading_stage"]):
        r = {"annotator": "consensus", "paper_id": pid, "reading_stage": st,
             "row_id": g["row_id"].iloc[0], "n_raters": len(g)}
        for c in g.columns:
            if c in r:
                continue
            if c == "methods_tok":
                cnt = {}
                for ms in g[c]:
                    for m in (ms or ()):
                        cnt[m] = cnt.get(m, 0) + 1
                r[c] = {m for m, k in cnt.items() if k * 2 > len(g)}
            else:
                r[c] = _mode(g[c].tolist())
        for c in [x for x in g.columns if x.endswith("_tok") and x != "methods_tok"]:
            vals = {a: v for a, v in zip(g["annotator"], g[c]) if not _blank(v)}
            if len(set(vals.values())) > 1:
                recon.append(dict(paper_id=pid, reading_stage=st, item=c[:-4],
                                  answers="; ".join(f"{a}={v}" for a, v in vals.items())))
        prow.append(r)
    ref_p = pd.DataFrame(prow)

    irow = []
    for (pid, st), g in gi.groupby(["paper_id", "reading_stage"]):
        n = max(int(n_raters.get((pid, st), 0)), g["annotator"].nunique(), 1)
        slot = 0
        for key, gg in g.groupby("g_key", sort=False):
            if key == ("", ""):
                continue
            support = gg["annotator"].nunique()
            if support * 2 <= n:
                recon.append(dict(paper_id=pid, reading_stage=st, item="pair_listed_by_minority",
                                  answers=f"{key[0]} x {key[1]}: {support}/{n} raters"))
                continue
            if support < n:
                recon.append(dict(paper_id=pid, reading_stage=st, item="pair_not_listed_by_all",
                                  answers=f"{key[0]} x {key[1]}: {support}/{n} raters"))
            slot += 1
            fu, ho = _mode(gg["fungus"].tolist()) or "", _mode(gg["host"].tolist()) or ""
            tcnt = {}
            for ts in gg["tissue"]:
                for t in (ts or ()):
                    tcnt[t] = tcnt.get(t, 0) + 1
            tis = {t for t, k in tcnt.items() if k * 2 > support} or set(tcnt)
            row = {"annotator": "consensus", "paper_id": pid, "row_id": gg["row_id"].iloc[0],
                   "reading_stage": st, "slot": slot, "fungus": fu, "host": ho, "g_key": key,
                   "sp_key": (species_key(fu), species_key(ho)), "tissue": tis}
            for f in ("fungal_lifestyle", "effect_on_host", "evidence_basis"):
                vals = gg[f].tolist()
                row[f] = _mode(vals)
                if len({v for v in vals if not _blank(v)}) > 1:
                    recon.append(dict(paper_id=pid, reading_stage=st, item=f"{f} ({key[0]})",
                                      answers="; ".join(f"{a}={v}" for a, v in zip(gg["annotator"], vals))))
            irow.append(row)
    ref_i = pd.DataFrame(irow)
    pd.DataFrame(recon).to_csv(out_dir / "reconciliation_items.csv", index=False)
    print(f"\n== consensus reference ==  {len(ref_p)} paper-rows, {len(ref_i)} consensus pairs; "
          f"{len(recon)} items where raters differ -> reconciliation_items.csv")
    return ref_i, ref_p


def paper_vs_model(gt_p, ex, out_dir):
    """Paper-level geography: human Q7a country / Q7c coordinates / Q8 status vs the model.
    One human answer per (paper, stage) (first annotator alphabetically)."""
    if "sampling_country" not in ex.columns:
        print("\n== geography vs model ==  (extraction has no sampling_country column - "
              "schema v5.1+ needed)")
        return
    h = gt_p.sort_values("annotator").drop_duplicates(["paper_id", "reading_stage"])
    h = h[h["text_reviewed"] == "complete"]
    mp = (ex.sort_values("paper_id").drop_duplicates(["paper_id", "stage"])
          .rename(columns={"stage": "reading_stage"}))
    d = h.merge(mp, on=["paper_id", "reading_stage"], how="inner", suffixes=("", "_m"))
    if d.empty:
        print("\n== geography vs model ==  (no overlapping complete papers yet)")
        return
    rows = []
    for stage, g in d.groupby("reading_stage"):
        hc = g["sampling_country"].map(country_set)
        mc = g["sampling_country_m"].map(country_set)
        both = [(a, b) for a, b in zip(hc, mc) if a and b]
        rows.append(dict(reading_stage=stage, field="country (exact set)", n=len(g),
                         human_stated=int((hc.map(len) > 0).sum()),
                         model_stated=int((mc.map(len) > 0).sum()),
                         both_stated=len(both),
                         accuracy_where_both=round(np.mean([a == b for a, b in both]), 3) if both else np.nan,
                         any_overlap_where_both=round(np.mean([bool(a & b) for a, b in both]), 3) if both else np.nan))
        if "coordinates_given_m" in g:
            ok = [(a == norm(b)) for a, b in zip(g["coordinates_given_tok"], g["coordinates_given_m"])
                  if a and not _blank(b)]
            rows.append(dict(reading_stage=stage, field="coordinates given", n=len(g),
                             both_stated=len(ok), accuracy_where_both=round(np.mean(ok), 3) if ok else np.nan))
        if "sampling_location_status_m" in g:
            ok = [(a == tok1("sampling_location_status", b)) for a, b in
                  zip(g["sampling_location_status_tok"], g["sampling_location_status_m"])
                  if a and not _blank(b)]
            rows.append(dict(reading_stage=stage, field="Q8 location status", n=len(g),
                             both_stated=len(ok), accuracy_where_both=round(np.mean(ok), 3) if ok else np.nan))
    r = pd.DataFrame(rows)
    r.to_csv(out_dir / "geography_vs_model.csv", index=False)
    print("\n== geography vs model (paper level, Q7a country is the headline) ==\n",
          r.to_string(index=False))



# ------------------------------------------------------------------ paper-level fields vs model

def _model_set(cell) -> set:
    """A model list cell ('a|b', "['a', 'b']", 'a; b') -> set of tokens."""
    if _blank(cell):
        return set()
    return {t.strip(" '\"[]").lower() for t in re.split(r"[|;,]", str(cell)) if t.strip(" '\"[]")}


# human key -> (model column, kind)
PAPER_MODEL_FIELDS = {
    "q1": ("is_fungus_in_plant_study", "cat"),
    "primary_aim": ("primary_aim", "cat"),
    "fungus_source": ("fungus_source", "cat"),
    "language": ("language", "cat"),
    "uncultured_taxa": ("uncultured_taxa", "cat"),
    "strain_variation": ("strain_variation", "cat"),
    "sterilisation_checked": ("sterilisation_checked", "cat"),
    "biome": ("biome", "set"),
    "n_pairs": ("n_distinct_pairs", "num"),
}


def paper_fields_vs_model(ref_p, ex, out_dir):
    """Field-level accuracy of every paper-level field the model extracts (Referee 2), one
    reference answer per (paper, stage). Accuracy is over papers where BOTH sides answered;
    coverage columns show how often each side was blank. Geography is in geography_vs_model."""
    h = ref_p[ref_p["text_reviewed"].astype(str).str.startswith("complete")]
    mp = (ex.sort_values("paper_id").drop_duplicates(["paper_id", "stage"])
          .rename(columns={"stage": "reading_stage"}))
    d = h.merge(mp, on=["paper_id", "reading_stage"], how="inner", suffixes=("", "_m"))
    if d.empty:
        print("\n== paper-level fields vs model ==  (no overlapping complete papers yet)")
        return
    rows = []
    for stage, g in d.groupby("reading_stage"):
        for key, (mcol, kind) in PAPER_MODEL_FIELDS.items():
            mc = mcol + "_m" if mcol + "_m" in g.columns else mcol
            hcol = key if kind == "num" else key + "_tok"
            if mc not in g.columns or hcol not in g.columns:
                continue
            pairs = []
            for hv, mv in zip(g[hcol], g[mc]):
                if _blank(hv) or _blank(mv):
                    continue
                if kind == "cat":
                    pairs.append(str(hv) == norm(mv).replace(" ", "_") or norm(hv) == norm(mv))
                elif kind == "set":
                    hs = set(str(hv).split(";"))
                    ms = _model_set(mv)
                    pairs.append(hs == ms)
                else:
                    a = pd.to_numeric(re.sub(r"[^0-9.]", "", str(hv)), errors="coerce")
                    b = pd.to_numeric(mv, errors="coerce")
                    if pd.notna(a) and pd.notna(b):
                        pairs.append(a == b)
            rows.append(dict(reading_stage=stage, field=key, n_papers=len(g), both_answered=len(pairs),
                             accuracy=round(float(np.mean(pairs)), 3) if pairs else np.nan,
                             human_blank=int(g[hcol].map(_blank).sum()),
                             model_blank=int(g[mc].map(_blank).sum())))
        # method columns: does the model list the method the human marked "yes"?
        if "detection_methods" in g.columns or "detection_methods_m" in g.columns:
            dm = "detection_methods_m" if "detection_methods_m" in g.columns else "detection_methods"
            for tok, _kws in METHOD_FIELDS:
                pairs = [(tok in (hs or set())) == (tok in _model_set(ms))
                         for hs, ms in zip(g["methods_tok"], g[dm]) if not _blank(ms)]
                rows.append(dict(reading_stage=stage, field=f"method: {tok}", n_papers=len(g),
                                 both_answered=len(pairs),
                                 accuracy=round(float(np.mean(pairs)), 3) if pairs else np.nan))
    r = pd.DataFrame(rows)
    r.to_csv(out_dir / "paper_fields_vs_model.csv", index=False)
    print("\n== paper-level fields vs model (accuracy where both answered) ==\n",
          r.to_string(index=False))


def ubiquity_vs_detector(gt_p, path, out_dir):
    """Q11 (human) vs 06_detect_ubiquity_claims_ollama.py output (contains_ubiquity_claim).
    Human reference = majority answer per (paper, stage). Papers matched on the DOI with all
    punctuation removed (the detector's doc_id is a DOI-derived filename)."""
    if "ubiquity_claim_tok" not in gt_p.columns:
        return
    key = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower().replace(".pdf", ""))
    det = pd.read_csv(path, low_memory=False)
    det["k"] = det["doc_id"].map(key)
    det["reading_stage"] = np.where(det["source_type"].astype(str).str.contains("abs"),
                                    "abstract", "full text")
    det["det"] = det["contains_ubiquity_claim"].astype(str).str.lower().isin(["true", "1", "yes"])
    hum = (gt_p[gt_p["text_reviewed"].astype(str).str.startswith("complete")]
           .groupby(["paper_id", "reading_stage"])["ubiquity_claim_tok"].agg(_mode).reset_index())
    hum["k"] = hum["paper_id"].map(key)
    d = hum.merge(det[["k", "reading_stage", "det"]], on=["k", "reading_stage"], how="inner")
    d = d[d["ubiquity_claim_tok"].isin(["yes", "no"])]
    if d.empty:
        print("\n== Q11 vs ubiquity detector ==  (no matched papers)")
        return
    rows = []
    for stage, g in d.groupby("reading_stage"):
        hy = g["ubiquity_claim_tok"] == "yes"
        tp, fp = int((hy & g.det).sum()), int((~hy & g.det).sum())
        fn, tn = int((hy & ~g.det).sum()), int((~hy & ~g.det).sum())
        rows.append(dict(reading_stage=stage, n=len(g), human_yes=int(hy.sum()), tp=tp, fp=fp,
                         fn=fn, tn=tn, accuracy=round((tp + tn) / len(g), 3),
                         precision=round(tp / (tp + fp), 3) if tp + fp else np.nan,
                         recall=round(tp / (tp + fn), 3) if tp + fn else np.nan))
    r = pd.DataFrame(rows)
    r.to_csv(out_dir / "ubiquity_vs_detector.csv", index=False)
    print("\n== Q11 ubiquity claim: human vs detector ==\n", r.to_string(index=False))

# ------------------------------------------------------------------ Fleiss' kappa / Gwet's AC1

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


def gwet_ac1(counts: np.ndarray) -> float:
    """Gwet's AC1 (Gwet 2008/2014), generalized to variable n_i via the same
    counts[i, j] distribution table fleiss_kappa uses. Observed agreement P_bar is
    identical to Fleiss'; the difference is the chance-agreement term, which uses the
    mean per-item category proportion (pi_g) rather than the pooled proportion, so it
    does not inflate when one category dominates (the "kappa paradox" - see Wongpakaran
    et al. 2013, and Ian Mounts' 2026-09-17 review note). Added as the primary
    agreement metric for that reason; Fleiss' kappa is kept alongside for comparability."""
    counts = counts[counts.sum(axis=1) >= 2]
    if len(counts) < 2:
        return np.nan
    n_i = counts.sum(axis=1)
    q = counts.shape[1]
    if q < 2:
        return np.nan
    P_i = ((counts ** 2).sum(axis=1) - n_i) / (n_i * (n_i - 1))
    P_bar = P_i.mean()
    pi_g = (counts / n_i[:, None]).mean(axis=0)
    e_gamma = (pi_g * (1 - pi_g)).sum() / (q - 1)
    return (P_bar - e_gamma) / (1 - e_gamma) if (1 - e_gamma) else np.nan


def agreement_ci(counts: np.ndarray, stat_fn=fleiss_kappa, n_boot: int = 2000):
    k = stat_fn(counts)
    used_cats = (counts.sum(axis=0) > 0).sum()
    # a percentile bootstrap is only meaningful with enough items and real variation
    if np.isnan(k) or len(counts) < 10 or used_cats < 2:
        return k, np.nan, np.nan
    boot = np.array([stat_fn(counts[RNG.integers(0, len(counts), len(counts))])
                     for _ in range(n_boot)])
    boot = boot[~np.isnan(boot)]
    if len(boot) < n_boot // 2:
        return k, np.nan, np.nan
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return k, min(k, lo), max(k, hi)


# kept as an alias - existing call sites / anyone importing this module by name
kappa_ci = agreement_ci


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
                tab = rating_table(items)
                k, klo, khi = agreement_ci(tab, fleiss_kappa)
                a, alo, ahi = agreement_ci(tab, gwet_ac1)
                out.append(dict(phase=phase, level="paper", field=f, n_items=len(items),
                                ac1=round(a, 3), ac1_ci_lo=round(alo, 3), ac1_ci_hi=round(ahi, 3),
                                kappa=round(k, 3), kappa_ci_lo=round(klo, 3), kappa_ci_hi=round(khi, 3)))
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
                tab = rating_table(items)
                k, klo, khi = agreement_ci(tab, fleiss_kappa)
                a, alo, ahi = agreement_ci(tab, gwet_ac1)
                out.append(dict(phase=phase, level="interaction", field=f, n_items=len(items),
                                ac1=round(a, 3), ac1_ci_lo=round(alo, 3), ac1_ci_hi=round(ahi, 3),
                                kappa=round(k, 3), kappa_ci_lo=round(klo, 3), kappa_ci_hi=round(khi, 3)))
    kdf = pd.DataFrame(out)
    kdf.to_csv(out_dir / "agreement.csv", index=False)
    print("\n== inter-rater agreement (>=3 raters per item; AC1 is primary, see header) ==\n",
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
    vcols = [f + "_tok" for f in PAPER_KAPPA_FIELDS if f != "q1" and f + "_tok" in gt_p.columns]
    pl = (gt_p.pivot_table(index=["annotator", "paper_id"], columns="reading_stage",
                           values=vcols, aggfunc="first") if vcols else None)
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


def location_elsewhere_report(gt_p, out_dir):
    """Papers whose location details were deferred to a supplement / another study, from the
    annotators' Q8 answers (any rater), so the study can report how often it happens. (2026-
    09-22: Q8 absorbed the old separate location-source question, so this now reads Q8.)"""
    if "sampling_location_status_tok" not in gt_p.columns:
        return
    hit = gt_p[gt_p["sampling_location_status_tok"].isin(["supplement", "cited_work"])]
    d = (hit.groupby(["reading_stage", "paper_id"])["annotator"].agg(lambda s: "; ".join(sorted(set(s))))
         .reset_index().rename(columns={"annotator": "flagged_by"}))
    d.to_csv(out_dir / "location_elsewhere_papers.csv", index=False)
    per_stage = d.groupby("reading_stage")["paper_id"].nunique().to_dict()
    tot = gt_p.groupby("reading_stage")["paper_id"].nunique().to_dict()
    print("\n== location deferred to a supplement / another study (Q8 answers) ==\n ",
          {k: f"{per_stage.get(k, 0)} of {v} papers" for k, v in tot.items()})


def pair_count_check(gt_i, gt_p, out_dir):
    """QC: Q10 (declared pair count, capped at 5) vs interaction blocks actually filled."""
    c = gt_p[gt_p["text_reviewed"] == "complete"].copy()
    if c.empty or "n_pairs" not in c.columns:
        return
    c["q10"] = pd.to_numeric(c["n_pairs"].astype(str).str.extract(r"(\d+)", expand=False),
                             errors="coerce").clip(upper=5)
    filled = gt_i.groupby(["annotator", "row_id"]).size().rename("blocks_filled").reset_index()
    c = c.merge(filled, on=["annotator", "row_id"], how="left")
    c["blocks_filled"] = c["blocks_filled"].fillna(0).astype(int)
    bad = c[c["q10"].isna() | (c["q10"] != c["blocks_filled"])]
    bad[["annotator", "row_id", "paper_id", "n_pairs", "q10", "blocks_filled"]].to_csv(
        out_dir / "q10_vs_blocks_mismatch.csv", index=False)
    print(f"\n== Q10 vs filled interaction blocks ==  {len(bad)} of {len(c)} complete rows "
          f"disagree (see q10_vs_blocks_mismatch.csv)")


def text_reviewed_breakdown(gt_p, out_dir):
    b = (gt_p.assign(pr=gt_p["text_reviewed"].replace("", "(blank / not done)"))
         .groupby("pr")["paper_id"].nunique().sort_values(ascending=False))
    b.to_csv(out_dir / "text_reviewed_breakdown.csv")
    print("\n== text_reviewed ==\n", b.to_string())


# ------------------------------------------------------------------ self-test

def _self_test(out_dir: Path) -> int:
    """Generate synthetic completed workbooks + extraction, run the pipeline."""
    import openpyxl
    tmp = out_dir / "_selftest"
    (tmp / "completed").mkdir(parents=True, exist_ok=True)
    lifestyles = ["endophyte (lives inside plant tissue)", "plant pathogen (causing disease)",
                  "wood saprotroph"]                       # last one: an old (pre-merge) label
    # the 2026-10-08 workbook headers, verbatim
    fh = "fungus_{n} (name exactly as the authors write it)"
    hh = "host_plant_{n} (name exactly as the authors write it)"
    eh = "evidence_basis_{n} (how the EFFECT was shown; if effect = not reported, how the LIFESTYLE was shown)"
    H = {
        "aim": "Q1  paper's main purpose", "src": "Q2  where did the fungi come from?",
        "lang": "Q3  language of the text you are reading",
        "unc": "Q4  any sequence-only (uncultured) taxa? (detected only by DNA, never grown in culture)",
        "strain": "Q5  strain-level variation noted?",
        "country": "Q6a  COUNTRY where the plant was sampled (not the authors' institution)",
        "coords": "Q6b  does the text give GPS coordinates for where the plant was sampled?",
        "status": "Q7  what geographic information does the text contain?",
        "biome": "Q8  biome (WWF category; pick the closest option, or type your own if nothing fits)",
        "pairs": ("Q9  how many distinct fungus-host pairs does the text name? (count each fungus-host "
                  "combination the text reports, e.g. 2 fungi both found on oak = 2 pairs; never count "
                  "isolates or individual plants)"),
        "steril": "Q10  was the surface-sterilisation checked?",
        "ubiq": "Q11  does the text state that endophytes are found in all or nearly all plants?",
    }
    meth = ["Methods: cultured fungi from surface-sterilised tissue", "Methods: performed microscopy on tissue",
            "Methods: molecular (DNA) sequencing from tissue", "Methods: isolate ID by sequencing",
            "Methods: fungus inoculated onto a plant"]
    hdrs = (["row_id", "text_reviewed", "date_reviewed", "text_type", "paper_id",
             "doi_link", "year", "journal", "title", "abstract"]
            + list(H.values()) + meth
            + [h for n in range(1, 6) for h in (fh.format(n=n), hh.format(n=n), f"tissue_{n}",
               f"fungal_lifestyle_{n}", f"effect_on_host_{n}", eh.format(n=n))]
            + ["extra_pairs_or_NGS_community_summary (a count and a few words)",
               "anything_you_were_unsure_about"])
    papers = [f"P{i:03d}" for i in range(20)]
    for who in ["bea", "nancy", "kitty", "ian", "jack"]:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Review"
        ws.append(hdrs)
        for i, pid in enumerate(papers):
            row = {h: "" for h in hdrs}
            row.update({"row_id": f"K{i+1:03d}a", "text_reviewed": "complete",
                        "text_type": "abstract", "paper_id": pid})
            row[H["src"]] = "isolated or detected from plants sampled in this study"
            row[H["lang"]] = "non-English: French" if i == 3 else "English"
            row[H["biome"]] = "temperate or boreal forest"
            row[H["country"]] = "USA" if i % 4 else "Brazil; Peru"
            row[H["coords"]] = "yes" if i % 2 else "no"
            row[H["status"]] = ("the text says it is in another cited study" if i % 5 == 0
                                else "explicitly stated (country or coordinates)")
            row[H["biome"]] = ("temperate or boreal forest, agriculture / cultivated (crop, orchard, "
                               "plantation, sown pasture)" if i % 6 == 0 else "temperate or boreal forest")
            row[H["steril"]] = "no - sterilised, but no check described"
            row[H["aim"]] = "endophyte ecology / diversity / community"
            row[H["unc"]] = "no"
            row[H["ubiq"]] = "no" if i % 7 else "yes"
            for m in meth[:4]:
                row[m] = "not stated"
            row[meth[4]] = ("yes - inoculated, but not confirmed inside the plant" if i % 3 == 0
                            else "not stated")
            row[fh.format(n=2)], row[hh.format(n=2)] = "N/A", "none"   # must NOT count as a pair
            row[H["pairs"]] = "1"
            row[fh.format(n=1)] = "Colletotrichum sp."
            row[hh.format(n=1)] = "Quercus robur"
            row["fungal_lifestyle_1"] = lifestyles[(i + (who == "nancy")) % len(lifestyles)]
            row["effect_on_host_1"] = "not reported (fungus just isolated / detected)"
            ws.append([row[h] for h in hdrs])
        wb.save(tmp / "completed" / f"groundtruth_kappa_{who}.xlsx")
    ex = pd.DataFrame([{"paper_id": p, "data_source": "abstract-reextract",
                        "fungus": "Colletotrichum gloeosporioides", "host_plant": "Quercus robur",
                        "tissue": "leaf", "fungal_lifestyle": "endophyte",
                        "effect_on_host": "not_reported", "evidence_basis": "inferred_from_taxon",
                        "is_fungus_in_plant_study": "yes", "biome": "temperate_boreal_forest",
                        "sampling_country": "United States", "coordinates_given": "no",
                        "sampling_location_status": "explicit", "primary_aim": "endophyte_ecology",
                        "fungus_source": "from_study_plants", "language": "english",
                        "uncultured_taxa": "no", "sterilisation_checked": "no_check",
                        "n_distinct_pairs": 1, "detection_methods": "isolate_id_sequencing"}
                       for p in papers])
    ex.to_csv(tmp / "extraction.csv", index=False)
    pd.DataFrame([{"source_type": "abstract", "doc_id": p, "contains_ubiquity_claim": i % 3 == 0}
                  for i, p in enumerate(papers)]).to_csv(tmp / "ubiquity.csv", index=False)
    print("self-test data in", tmp)
    return run(tmp / "completed", tmp / "extraction.csv", tmp / "metrics", 15,
               ubiquity=tmp / "ubiquity.csv")


# ------------------------------------------------------------------ orchestration

def run(completed_dir: Path, extraction: Path | None, out_dir: Path, calib_cut: int,
        reference: str = "consensus", ubiquity: Path | None = None) -> int:
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

    text_reviewed_breakdown(gt_p, out_dir)
    pair_count_check(gt_i, gt_p, out_dir)
    location_elsewhere_report(gt_p, out_dir)
    kappa_block(gt_i, gt_p, calib_cut, out_dir)
    abstract_vs_fulltext(gt_i, gt_p, out_dir)

    if extraction and Path(extraction).exists():
        ex = load_extraction(Path(extraction))
        if reference == "consensus":
            primary, ref_p = consensus_reference(gt_i, gt_p, out_dir)
        else:                    # legacy: first annotator alphabetically (arbitrary - not advised)
            primary = gt_i.sort_values("annotator").drop_duplicates(
                ["paper_id", "reading_stage", "slot"])
            ref_p = gt_p.sort_values("annotator").drop_duplicates(["paper_id", "reading_stage"])
        q10 = pd.to_numeric(ref_p["n_pairs"].astype(str).str.extract(r"(\d+)", expand=False),
                            errors="coerce")
        partial = set(ref_p.loc[q10 > 5, "paper_id"])     # human list capped at 5 blocks
        if partial:
            print(f"\n({len(partial)} papers have Q10 > 5: the human list is partial, so they "
                  "count toward recall only, not precision)")
        prf_by_stage(primary, ex, out_dir, partial)
        field_accuracy(primary, ex, out_dir)
        paper_vs_model(ref_p, ex, out_dir)
        paper_fields_vs_model(ref_p, ex, out_dir)
        fp_fn_detail(primary, ref_p, ex, out_dir)
    else:
        print("\n(no --extraction: interaction P/R/F1, field accuracy and FP/FN skipped)")
    if ubiquity and Path(ubiquity).exists():
        ubiquity_vs_detector(gt_p, Path(ubiquity), out_dir)
    print(f"\nmetrics -> {out_dir}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--completed-dir", type=Path, default=GT_DIR / "completed")
    ap.add_argument("--extraction", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, default=GT_DIR / "metrics")
    ap.add_argument("--calib-cut", type=int, default=0,
                    help="K-block paper number at/below which = calibration round. "
                         "Default 0 matches the 2026-09-17 single-blind-pass design "
                         "(no calibration sub-round); set >0 only if a future block "
                         "reintroduces one.")
    ap.add_argument("--reference", choices=["consensus", "first"], default="consensus",
                    help="human reference for model comparison: majority of raters (default) "
                         "or the first annotator alphabetically (legacy)")
    ap.add_argument("--ubiquity", type=Path,
                    default=ROOT / "results" / "ubiquity_claims" / "ubiquity_claims_all.csv",
                    help="06_detect_ubiquity_claims_ollama.py output; Q11 is compared with it "
                         "if the file exists")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test(args.out_dir)
    return run(args.completed_dir, args.extraction, args.out_dir, args.calib_cut, args.reference,
               args.ubiquity)


if __name__ == "__main__":
    raise SystemExit(main())
