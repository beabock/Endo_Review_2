#!/usr/bin/env python3
# BMB 2026-11-05 (Thread B, extraction v6) - draws the DEV set used to tune prompts and to
# choose the extraction model. The 230-paper ground-truth sample is the locked TEST set and
# is NEVER used for tuning or model choice; this DEV set is drawn from everything else.
#
# See NPH_extraction_v6_design.md section "DEV / TEST protocol".
#
# What it does
#   --stage draw   Draw ~40 papers from the corpus, EXCLUDING the 230 sample papers, the 2
#                  MOCK papers and (belt and braces) every paper_id found in any
#                  groundtruth_*.xlsx. Stratified by
#                    * doc_type : abstract-only vs full-text (PDF downloaded)
#                    * era      : pre-2000 / 2000-2012 / 2013+ (same cut points as the sample)
#                    * design   : metabarcoding / isolate-culture / other (heuristic on
#                                 title + abstract - there is no extraction output yet)
#                    * table    : table-heavy vs prose (full-text only; needs --pdf-dir, so run
#                                 this stage on Monsoon where the PDFs are)
#                  Marginal-quota sampling (not proportional): rare-but-hard strata such as
#                  metabarcoding and pre-2000 are deliberately over-represented relative to
#                  the corpus, because the DEV set exists to find where models break.
#                  The result is written in a prefix-balanced ORDER, so any prefix (e.g. the
#                  first 25 papers = the proof-of-concept set) is itself balanced.
#   --stage sheet  Build the annotation workbook for Bea from the drawn set. The Review
#                  headers and the dropdown lists are READ from an existing reviewer workbook
#                  (read-only; default groundtruth_kappa_MASTER.xlsx) so the layout and
#                  vocabulary stay identical to what the human reviewers use and
#                  score_groundtruth.py can read the completed DEV sheet unchanged. Nothing in
#                  results/manual_validation/groundtruth/ is written to.
#   --stage all    both (default). On a machine without the PDFs the table-heaviness stratum
#                  is 'unknown' and a warning says so.
#
# Lightweight vs the TEST workbooks: ONE row per paper (abstract-only papers: an abstract row;
# full-text papers: a full-text row only - the paired abstract row is a TEST-set measure, not
# needed to choose a model); no protected cells, no rubric tab.
#
# Outputs (default results/manual_validation/dev_set/):
#   dev_set_selected.csv   drawn papers + strata + order + row_id
#   dev_set_report.md      what was excluded, target vs achieved strata, thresholds, seed
#   dev_pdf_filenames.csv  new_name (D007b.pdf) <- old_name (manifest filename), as for the TEST set
#   copy_dev_pdfs.sh       cp commands that stage the DEV PDFs under the new names
#   dev_ft_features.csv    (with --pdf-dir) per-PDF table / page features of the candidates
#   devset_bea.xlsx        the annotation workbook
#
# Usage:
#   # on Monsoon, where the PDFs are:
#   python scripts/04_analyses/draw_dev_set.py --stage draw \
#       --pdf-manifest /scratch/bmb646/full_corpus/pdf_manifest.csv \
#       --pdf-dir /scratch/bmb646/full_corpus
#   # on the laptop (needs only dev_set_selected.csv + the reviewer template):
#   python scripts/04_analyses/draw_dev_set.py --stage sheet

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import warnings
from collections import defaultdict
from copy import copy
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
GT_DIR = ROOT / "results" / "manual_validation" / "groundtruth"
DEFAULT_OUT = ROOT / "results" / "manual_validation" / "dev_set"
DEFAULT_CORPUS = ROOT / "data" / "Abstracts" / "All_abstracts_deduped.csv"
DEFAULT_MANIFEST = ROOT / "data" / "pdf_manifest.csv"

# ----------------------------------------------------------------------------- strata

# design hint from title + abstract. Heuristic ONLY (no extraction exists yet); the report
# prints how many papers each rule caught so Bea can sanity-check the thresholds.
META_RE = re.compile(
    r"metabarcod|amplicon|high[- ]throughput sequenc|next[- ]generation sequenc|\bNGS\b|"
    r"illumina|miseq|pyrosequenc|\b454\b|\bOTUs?\b|\bASVs?\b|metagenom|metatranscriptom|"
    r"community (?:composition|structure|assembly|diversity)|environmental DNA|\beDNA\b|"
    r"ITS[12]? (?:amplicon|region sequencing|rDNA sequencing)", re.I)
ISOLATE_RE = re.compile(
    r"fungal isolates?|endophytic isolates?|\bisolates? (?:of|from|were)|strains? (?:of|from|were)|"
    r"culturable|culture[- ]dependent|surface[- ]steril|were isolated from (?:the )?"
    r"(?:leaves|roots|stems|twigs|plants?|tissues?|bark|seeds?|needles|petioles|rhizomes)|"
    r"isolated from (?:healthy )?(?:leaves|roots|stems|twigs|plants?|tissues?|bark|seeds?|needles)|"
    r"potato dextrose|\bPDA\b|\bMEA\b", re.I)
CHEM_RE = re.compile(r"\bNMR\b|HR-?ESI|cytotoxic|metabolite|compounds?\b|fractionation|"
                     r"antibacterial|antifungal activit|bioactiv|secondary metabolit|"
                     r"new (?:alkaloid|polyketide|terpenoid|diketopiperazine)", re.I)


FUNGAL_RE = re.compile(r"fung|yeast|mycorrhiz|mycobiom|mycobiot|ITS|mycelium|hyph", re.I)


def design_hint(title: str, abstract: str) -> str:
    t = f"{title or ''} {abstract or ''}"
    if not FUNGAL_RE.search(t):
        return "other"            # bacteria-only 16S papers etc. must not count as metabarcoding
    if META_RE.search(t):
        return "metabarcoding"
    if ISOLATE_RE.search(t):
        return "isolate_culture"
    return "other"


def era_of(year) -> str:          # same cut points as build_groundtruth_sample.era_of
    if pd.isna(year):
        return "unknown"
    y = int(year)
    return "pre-2000" if y < 2000 else "2000-2012" if y <= 2012 else "2013+"


def norm_doi(x):
    if pd.isna(x):
        return None
    s = str(x).strip().lower()
    for p in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "doi:"):
        if s.startswith(p):
            s = s[len(p):]
    return s.strip() or None


# ----------------------------------------------------------------------------- exclusions

def excluded_ids(sample_selected: Path, gt_dir: Path, mock_wb: Path) -> tuple[set, dict]:
    """Union of: the 230 sample papers, the MOCK papers, and every paper_id found in any
    groundtruth_*.xlsx (read-only). Returns (set, {source: n})."""
    ex, counts = set(), {}
    if sample_selected.exists():
        s = pd.read_csv(sample_selected, low_memory=False)
        ids = {norm_doi(x) for x in s["paper_id"]} - {None}
        counts["sample_selected.csv"] = len(ids)
        ex |= ids
    else:
        sys.exit(f"ERROR: {sample_selected} not found - refusing to draw a DEV set without the "
                 f"exclusion list.")
    try:
        import openpyxl
        warnings.simplefilter("ignore")
        paths = sorted(gt_dir.glob("groundtruth_*.xlsx"))
        if mock_wb.exists() and mock_wb not in paths:
            paths.append(mock_wb)
        for p in paths:
            try:
                wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
                ws = wb["Review"]
                rows = ws.iter_rows(values_only=True)
                hdr = list(next(rows))
                ci = hdr.index("paper_id")
                ids = {norm_doi(r[ci]) for r in rows if r[ci]} - {None}
                wb.close()
                counts[p.name] = len(ids)
                ex |= ids
            except Exception as e:                       # noqa: BLE001
                print(f"  note: could not read {p.name} ({type(e).__name__}) - skipped")
    except ImportError:
        print("  note: openpyxl missing - only sample_selected.csv used for exclusion")
    return ex, counts


# ----------------------------------------------------------------------------- frame

def build_frame(corpus: Path, manifest: Path, exclude: set, min_abs_chars: int,
                min_pages: int, max_pages: int) -> pd.DataFrame:
    df = pd.read_csv(corpus, low_memory=False)
    df["doi_n"] = df["DOI"].map(norm_doi)
    df = df.dropna(subset=["doi_n"]).drop_duplicates("doi_n")
    n0 = len(df)
    df = df[~df["doi_n"].isin(exclude)].copy()
    print(f"  corpus {n0:,} papers with a DOI; {n0 - len(df):,} excluded "
          f"(230 sample + MOCK + any groundtruth workbook) -> {len(df):,} available")
    papers = pd.DataFrame({
        "paper_id": df["doi_n"], "title": df["Title"], "authors": df["Authors"],
        "journal": df["Source.title"], "abstract": df["Abstract"].fillna(""),
        "language_hint": df.get("Language.of.Original.Document", pd.Series("", index=df.index)),
        "document_type": df.get("Document.Type", pd.Series("", index=df.index)),
        "year": pd.to_numeric(df["Year"], errors="coerce"),
    }).reset_index(drop=True)
    papers["era"] = papers["year"].map(era_of)
    papers["design"] = [design_hint(t, a) for t, a in zip(papers["title"], papers["abstract"])]
    papers["natural_products_hint"] = [bool(CHEM_RE.search(f"{t} {a}")) for t, a in
                                       zip(papers["title"], papers["abstract"])]
    man = pd.read_csv(manifest, low_memory=False)
    man["doi_n"] = man["doi"].map(norm_doi)
    man = man.dropna(subset=["doi_n"]).drop_duplicates("doi_n")
    ok = man[man["status"] == "downloaded"].set_index("doi_n")
    papers["has_pdf"] = papers["paper_id"].isin(ok.index)
    papers["pdf_filename"] = papers["paper_id"].map(ok["filename"]) if len(ok) else None
    papers["n_pages"] = papers["paper_id"].map(pd.to_numeric(ok["n_pages"], errors="coerce"))
    # eligibility - something to annotate, nothing pathological
    abs_ok = papers["abstract"].str.len() >= min_abs_chars
    ft_ok = papers["has_pdf"] & papers["n_pages"].between(min_pages, max_pages) & abs_ok
    papers["doc_type"] = np.where(ft_ok, "full-text", "abstract-only")
    papers = papers[(~papers["has_pdf"] & abs_ok) | ft_ok].copy()      # drop odd-page-count PDFs
    papers = papers[papers["era"] != "unknown"].reset_index(drop=True)
    print(f"  eligible: {int((papers.doc_type == 'full-text').sum()):,} full-text "
          f"({min_pages}-{max_pages} pages) / {int((papers.doc_type == 'abstract-only').sum()):,} "
          f"abstract-only (abstract >= {min_abs_chars} chars)")
    return papers


# ----------------------------------------------------------------------------- PDF features

TABLE_CAP = re.compile(r"(?mi)^\s*(?:table|tab\.)\s*([0-9]+|[ivx]+)\b")


def pdf_features(path: Path) -> dict:
    try:
        import fitz
    except ImportError:
        return {}
    out = {"n_pages_pdf": 0, "chars": 0, "digit_frac": np.nan, "table_captions": 0}
    try:
        with fitz.open(path) as doc:
            out["n_pages_pdf"] = doc.page_count
            txt = "\n".join(p.get_text("text") for p in doc)
        out["chars"] = len(txt)
        if txt:
            out["digit_frac"] = round(sum(c.isdigit() for c in txt) / len(txt), 4)
        out["table_captions"] = len({m.group(1).lower() for m in TABLE_CAP.finditer(txt)})
    except Exception as e:                                # noqa: BLE001
        out["error"] = type(e).__name__
    return out


def table_class(f: dict, heavy_min: int, digit_cut: float) -> str:
    if not f or f.get("error") or not f.get("chars"):
        return "unknown"
    caps, dfrac = f["table_captions"], f["digit_frac"]
    if caps >= heavy_min or (caps >= heavy_min - 1 and dfrac >= digit_cut):
        return "table-heavy"
    return "prose"


# ----------------------------------------------------------------------------- quota sampler

def largest_remainder(weights: dict, n: int, floor: int = 0, cap: dict | None = None) -> dict:
    keys = [k for k, w in weights.items() if w > 0]
    if not keys or n <= 0:
        return {}
    tot = sum(weights[k] for k in keys)
    raw = {k: n * weights[k] / tot for k in keys}
    q = {k: max(floor, int(np.floor(raw[k]))) for k in keys}
    if cap:
        q = {k: min(v, cap.get(k, v)) for k, v in q.items()}
    while sum(q.values()) < n:
        cand = [k for k in keys if not cap or q[k] < cap.get(k, 10**9)]
        if not cand:
            break
        k = max(cand, key=lambda k: raw[k] - q[k])
        q[k] += 1
    while sum(q.values()) > n:
        k = max(keys, key=lambda k: q[k] - raw[k])
        if q[k] <= floor and all(q[j] <= floor for j in keys):
            break
        q[k] -= 1
    return q


def quota_draw(pool: pd.DataFrame, n: int, quotas: dict[str, dict], rng) -> pd.DataFrame:
    """Marginal-quota sampling: walk a random permutation of the pool and accept a paper if
    every factor still has quota left for that paper's level. Second pass fills any shortfall
    with papers that hit the most unfilled quotas. Deterministic given rng."""
    order = pool.sample(frac=1, random_state=int(rng.integers(1 << 31))).reset_index(drop=True)
    left = {f: dict(q) for f, q in quotas.items()}
    chosen = []
    for i, r in order.iterrows():
        if len(chosen) >= n:
            break
        if all(left[f].get(r[f], 0) > 0 for f in left):
            chosen.append(i)
            for f in left:
                left[f][r[f]] -= 1
    if len(chosen) < n:                       # relax: best-effort fill
        rest = [i for i in range(len(order)) if i not in set(chosen)]
        def gain(i):
            return sum(left[f].get(order.at[i, f], 0) > 0 for f in left)
        rest.sort(key=lambda i: -gain(i))
        for i in rest[: n - len(chosen)]:
            chosen.append(i)
            for f in left:
                if order.at[i, f] in left[f]:
                    left[f][order.at[i, f]] -= 1
    return order.loc[chosen].copy()


def prefix_balanced_order(df: pd.DataFrame, keys: list[str], rng) -> pd.DataFrame:
    """Round-robin interleave the strata cells (largest first) so that any prefix is balanced.
    doc_type is part of the key list, so a prefix always holds both abstract and full text."""
    buckets = defaultdict(list)
    for _, r in df.sample(frac=1, random_state=int(rng.integers(1 << 31))).iterrows():
        buckets[tuple(r[k] for k in keys)].append(r)
    cells = sorted(buckets, key=lambda k: (-len(buckets[k]), str(k)))
    out, more = [], True
    while more:
        more = False
        for k in cells:
            if buckets[k]:
                out.append(buckets[k].pop(0))
                more = True
    return pd.DataFrame(out).reset_index(drop=True)


# ----------------------------------------------------------------------------- stage: draw

def stage_draw(a) -> pd.DataFrame:
    rng = np.random.default_rng(a.seed)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    print("== DEV set draw ==")
    exclude, ex_counts = excluded_ids(a.sample_selected, a.gt_dir, a.mock_workbook)
    print("  exclusion sources:", ex_counts, f"-> {len(exclude)} unique paper_ids")
    if len(exclude) < 232:
        sys.exit(f"ERROR: only {len(exclude)} papers to exclude; expected >= 232 (230 + 2 MOCK).")

    papers = build_frame(a.corpus, a.pdf_manifest, exclude, a.min_abstract_chars,
                         a.min_pages, a.max_pages)

    # ---- full-text candidates: table features (needs the PDFs)
    ft = papers[papers.doc_type == "full-text"].copy()
    ft["table"] = "unknown"
    feat_rows = []
    if a.pdf_dir and len(ft):
        cand = ft.sample(n=min(a.ft_candidates, len(ft)),
                         random_state=int(rng.integers(1 << 31)))
        print(f"  computing table features for {len(cand)} full-text candidates from {a.pdf_dir} ...")
        keep = []
        for _, r in cand.iterrows():
            p = Path(a.pdf_dir) / str(r["pdf_filename"])
            if not p.exists():
                continue
            f = pdf_features(p)
            f["paper_id"] = r["paper_id"]
            feat_rows.append(f)
            keep.append(r["paper_id"])
        feats = pd.DataFrame(feat_rows)
        if len(feats):
            feats["table"] = [table_class(f, a.table_heavy_min, a.table_digit_frac)
                              for f in feats.to_dict("records")]
            feats.to_csv(a.out_dir / "dev_ft_features.csv", index=False)
            ft = ft[ft.paper_id.isin(keep)].merge(feats[["paper_id", "table"]],
                                                  on="paper_id", suffixes=("_x", ""))
            ft = ft.drop(columns=[c for c in ft.columns if c.endswith("_x")])
            ft = ft[ft["table"] != "unknown"]
        print(f"  usable full-text candidates: {len(ft)}; table classes: "
              f"{ft['table'].value_counts().to_dict()}")
    else:
        print("  WARNING: no --pdf-dir -> table-heavy vs prose cannot be balanced "
              "(stratum 'unknown'). Re-run --stage draw on Monsoon for the final draw.")
    ab = papers[papers.doc_type == "abstract-only"].copy()
    ab["table"] = "n/a"

    # ---- quotas (marginal). era: sqrt-proportional (over-weights the small old strata);
    # design: fixed fractions; table: even split.
    def era_q(pool, n):
        w = {k: np.sqrt(v) for k, v in pool["era"].value_counts().items()}
        return largest_remainder(w, n, floor=min(2, n // 4))
    def design_q(pool, n):
        fr = {"metabarcoding": a.frac_metabarcoding, "isolate_culture": a.frac_isolate,
              "other": max(0.0, 1 - a.frac_metabarcoding - a.frac_isolate)}
        have = set(pool["design"])
        return largest_remainder({k: v for k, v in fr.items() if k in have}, n)

    draws = []
    for name, pool, n in (("abstract-only", ab, a.n_abstract), ("full-text", ft, a.n_fulltext)):
        if n <= 0:
            continue
        quotas = {"era": era_q(pool, n), "design": design_q(pool, n)}
        if name == "full-text" and (pool["table"] != "unknown").any():
            quotas["table"] = largest_remainder(
                {k: 1.0 for k in pool["table"].unique() if k != "unknown"}, n)
        d = quota_draw(pool, n, quotas, rng)
        d["quota_note"] = str({f: q for f, q in quotas.items()})
        draws.append(d)
        print(f"  {name}: drew {len(d)}; target {quotas}")
    dev = pd.concat(draws).reset_index(drop=True)

    # ---- optional non-English quota is deliberately NOT forced (Bea reads English/Spanish only)
    dev = prefix_balanced_order(dev, ["doc_type", "era", "design"], rng)
    dev["order"] = np.arange(len(dev))
    dev["row_id"] = [f"D{i + 1:03d}{'b' if t == 'full-text' else 'a'}"
                     for i, t in zip(dev["order"], dev["doc_type"])]
    dev["text_type"] = np.where(dev["doc_type"] == "full-text", "full text", "abstract")
    dev["doi_link"] = dev["paper_id"].map(lambda d: f"https://doi.org/{d}")
    dev["poc_prefix_25"] = dev["order"] < 25
    assert not (set(dev["paper_id"]) & exclude), "BUG: drew an excluded paper"

    cols = ["order", "row_id", "paper_id", "doc_type", "text_type", "era", "design", "table",
            "natural_products_hint", "year", "journal", "title", "abstract", "language_hint",
            "document_type", "doi_link", "pdf_filename", "n_pages", "poc_prefix_25"]
    dev[cols].to_csv(a.out_dir / "dev_set_selected.csv", index=False)

    # PDFs: same renaming convention as the TEST set (B123b.pdf <- doi-based name)
    pf = dev[dev.doc_type == "full-text"]
    pd.DataFrame({"new_name": pf["row_id"] + ".pdf", "old_name": pf["pdf_filename"]}).to_csv(
        a.out_dir / "dev_pdf_filenames.csv", index=False)
    with open(a.out_dir / "copy_dev_pdfs.sh", "w", newline="\n") as fh:
        fh.write("#!/bin/bash\n# stage the DEV PDFs under their row names (run on Monsoon)\n"
                 "set -euo pipefail\n"
                 'PDF_DIR="${PDF_DIR:-/scratch/bmb646/full_corpus}"\n'
                 'OUT="${OUT:-$HOME/dev_pdfs}"\nmkdir -p "$OUT"\n')
        for _, r in pf.iterrows():
            fh.write(f'cp -n "$PDF_DIR/{r["pdf_filename"]}" "$OUT/{r["row_id"]}.pdf"\n')
        fh.write('echo "staged $(ls "$OUT" | wc -l) PDFs in $OUT"\n')

    write_report(a, dev, papers, exclude, ex_counts)
    print(f"  wrote {a.out_dir / 'dev_set_selected.csv'} ({len(dev)} papers)")
    return dev


def md_table(df: pd.DataFrame) -> str:
    """Tiny markdown table writer (no `tabulate` dependency on Monsoon)."""
    cols = [str(c) for c in df.columns]
    rows = [[("" if pd.isna(v) else str(v)) for v in r] for r in df.itertuples(index=False)]
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return chr(10).join(out)


def write_report(a, dev, frame, exclude, ex_counts):
    def tab(s):
        return md_table(s.value_counts().rename_axis("level").reset_index(name="n"))
    try:
        sha = hashlib.sha1(Path(__file__).read_bytes()).hexdigest()[:10]
    except Exception:                                    # noqa: BLE001
        sha = "?"
    ft = dev[dev.doc_type == "full-text"]
    L = [
        "# DEV set - draw report", "",
        f"- seed `{a.seed}`, script sha1 `{sha}`, corpus `{Path(a.corpus).name}`, "
        f"PDF manifest `{Path(a.pdf_manifest).name}`",
        f"- n = {len(dev)} ({int((dev.doc_type == 'abstract-only').sum())} abstract-only, "
        f"{len(ft)} full-text). One annotation row per paper.",
        f"- excluded from the draw: {len(exclude)} paper_ids "
        f"({', '.join(f'{k}: {v}' for k, v in ex_counts.items())})",
        f"- eligible frame after exclusions: {len(frame):,} papers",
        "- quota sampling (marginals), NOT proportional - see header of draw_dev_set.py; "
        "design/table classes are heuristics on title+abstract / PDF text, not model output.",
        "- the first 25 rows (`poc_prefix_25`) are the proof-of-concept set and are balanced "
        "on their own.", "",
        "## Achieved vs frame", "",
        "### doc_type", tab(dev["doc_type"]), "", "### era (frame % in brackets)", "",
        md_table(dev["era"].value_counts().rename_axis("level").reset_index(name="n").assign(
            frame_pct=lambda d: d["level"].map(
                (frame["era"].value_counts(normalize=True) * 100).round(1)))), "",
        "### design hint (frame % in brackets)", "",
        md_table(dev["design"].value_counts().rename_axis("level").reset_index(name="n").assign(
            frame_pct=lambda d: d["level"].map(
                (frame["design"].value_counts(normalize=True) * 100).round(1)))), "",
        "### table-heaviness (full-text only)", tab(ft["table"]) if len(ft) else "(none)", "",
        "### natural-products hint (not stratified; just so you know what you are getting)",
        tab(dev["natural_products_hint"]), "",
        "### language_hint", tab(dev["language_hint"]), "",
        "### doc_type x era x design", "",
        md_table(dev.groupby(["doc_type", "era", "design"]).size().reset_index(name="n")), "",
        "## Rough annotation load for Bea", "",
        f"abstract rows x ~8 min + full-text rows x ~20 min = about "
        f"{(int((dev.doc_type == 'abstract-only').sum()) * 8 + len(ft) * 20) / 60:.1f} h. "
        "Annotate in `order` (first 25 first) so a partial pass is still usable.", "",
    ]
    if (ft["table"] == "unknown").any() or ft.empty:
        L += ["> **Table-heaviness was NOT balanced** (no --pdf-dir). This is a test draw; "
              "re-run `--stage draw` on Monsoon for the real one.", ""]
    (a.out_dir / "dev_set_report.md").write_text("\n".join(L), encoding="utf8")


# ----------------------------------------------------------------------------- stage: sheet

def list_for(h: str) -> str | None:
    hl = str(h).lower()
    if hl == "text_reviewed":
        return "text_reviewed"
    rules = [("main purpose", "primary_aim"), ("where did the fungi come from", "fungus_source"),
             ("language of the text", "language"), ("sequence-only", "yn_unclear"),
             ("strain-level", "strain_variation"), ("country where", "country"),
             ("gps coordinates", "yes_no"), ("geographic information", "location_status"),
             ("biome", "biome"), ("surface-sterilisation", "sterilisation"),
             ("all or nearly all plants", "yes_no"), ("fungus-host pairs", "__int__")]
    for k, v in rules:
        if k in hl:
            return v
    if hl.startswith("methods: fungus inoculated"):
        return "inoculation"
    if hl.startswith("methods:"):
        return "method_status"
    for pre, v in (("tissue_", "tissue"), ("fungal_lifestyle_", "fungal_lifestyle"),
                   ("effect_on_host_", "effect_on_host"), ("evidence_basis_", "evidence_basis")):
        if hl.startswith(pre):
            return v
    return None


def stage_sheet(a) -> None:
    import openpyxl
    from openpyxl.styles import Alignment
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation
    warnings.simplefilter("ignore")
    sel = a.out_dir / "dev_set_selected.csv"
    if not sel.exists():
        sys.exit(f"ERROR: {sel} not found - run --stage draw first.")
    dev = pd.read_csv(sel, low_memory=False).sort_values("order")
    tpl_path = a.template if a.template.exists() else GT_DIR / "groundtruth_MOCK.xlsx"
    print(f"== annotation sheet: layout + lists read (read-only) from {tpl_path.name} ==")
    tpl = openpyxl.load_workbook(tpl_path)               # in memory only; never saved
    tws, tl = tpl["Review"], tpl["Lists"]
    hdr = [c.value for c in tws[1]]

    lists, lcol = {}, {}
    for j, col in enumerate(tl.iter_cols(min_row=1, max_row=tl.max_row), start=1):
        vals = [c.value for c in col if c.value is not None]
        if vals:
            lists[str(vals[0])] = [str(v) for v in vals[1:]]
            lcol[str(vals[0])] = j

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Review"
    lws = wb.create_sheet("Lists")
    for name, vals in lists.items():
        lws.cell(1, lcol[name], name)
        for i, v in enumerate(vals, start=2):
            lws.cell(i, lcol[name], v)

    # header row + styling copied cell by cell (styles cannot be shared across workbooks)
    for j, h in enumerate(hdr, start=1):
        c, t = ws.cell(1, j, h), tws.cell(1, j)
        c.font, c.fill, c.alignment, c.border = (copy(t.font), copy(t.fill),
                                                 copy(t.alignment), copy(t.border))
        d = tws.column_dimensions.get(get_column_letter(j))
        if d is not None:
            ws.column_dimensions[get_column_letter(j)].width = d.width
            ws.column_dimensions[get_column_letter(j)].hidden = d.hidden
    ws.row_dimensions[1].height = tws.row_dimensions[1].height or 60
    ws.freeze_panes = tws.freeze_panes

    ix = {h: j for j, h in enumerate(hdr, start=1)}
    def col_of(prefix):
        return next((j for h, j in ix.items() if str(h).lower() == prefix), None)
    c_abs, c_id, c_dt, c_tt = col_of("abstract"), col_of("row_id"), col_of("date_reviewed"), col_of("text_type")
    c_pid, c_doi, c_yr, c_jn, c_ti = (col_of("paper_id"), col_of("doi_link"), col_of("year"),
                                      col_of("journal"), col_of("title"))
    c_lang = next((j for h, j in ix.items() if "language of the text" in str(h).lower()), None)
    for i, r in enumerate(dev.itertuples(index=False), start=2):
        # abstract: shown for abstract rows, but ALSO kept (hidden/narrow col) for full-text rows
        vals = {c_abs: r.abstract if r.text_type == "abstract" else "", c_id: r.row_id,
                c_tt: r.text_type, c_pid: r.paper_id, c_doi: r.doi_link,
                c_yr: int(r.year) if pd.notna(r.year) else None, c_jn: r.journal, c_ti: r.title}
        if c_lang and str(r.language_hint).strip().lower() == "english":
            vals[c_lang] = "English"                       # same time-saver as the TEST sheets
        for j, v in vals.items():
            if j:
                c = ws.cell(i, j, v)
                if j == c_abs:
                    c.alignment = Alignment(wrap_text=False, vertical="top")
    last = len(dev) + 1

    # dropdowns: warning-style (can still type a custom value), range-referenced to Lists
    missing = []
    for h, j in ix.items():
        ln = list_for(h)
        if ln is None:
            continue
        L = get_column_letter(j)
        if ln == "__int__":
            dv = DataValidation(type="whole", operator="greaterThanOrEqual", formula1="0",
                                allow_blank=True, errorStyle="warning",
                                error="A whole number please, never a range.")
        elif ln in lists:
            n = len(lists[ln]) + 1
            dv = DataValidation(type="list", allow_blank=True, errorStyle="warning",
                                formula1=f"=Lists!${get_column_letter(lcol[ln])}$2:"
                                         f"${get_column_letter(lcol[ln])}${n}",
                                error="Not in the list. Click Yes to keep what you typed.")
        else:
            missing.append((h, ln))
            continue
        ws.add_data_validation(dv)
        dv.add(f"{L}2:{L}{last}")
    if missing:
        print("  WARNING: list not found in template for:", missing)

    ins = wb.create_sheet("Instructions")
    for i, line in enumerate([
        "DEV set - Bea only. Same columns and rules as the reviewer workbooks; the reviewer guide applies unchanged.",
        "Work top to bottom (the order is balanced: the first 25 rows are the proof-of-concept set).",
        "One row per paper: text_type 'abstract' = read only the abstract in the row; 'full text' = open the PDF named like the row id (D007b -> D007b.pdf; run copy_dev_pdfs.sh to stage them).",
        "Do NOT look at any model output for these papers before you finish a row (blind).",
        "Evidence columns: the sheet has two (EFFECT / LIFESTYLE) per block, exactly as the TEST sheets - fill the one(s) that apply.",
    ], start=1):
        ins.cell(i, 1, line)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    out = a.out_dir / f"devset_{a.annotator.lower()}.xlsx"
    wb.save(out)
    print(f"  wrote {out} ({len(dev)} rows, {len(hdr)} columns)")


# ----------------------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", choices=["draw", "sheet", "all"], default="all")
    ap.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    ap.add_argument("--pdf-manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--pdf-dir", type=Path, default=None,
                    help="folder with the downloaded PDFs (Monsoon). Enables table-heaviness.")
    ap.add_argument("--sample-selected", type=Path, default=GT_DIR / "sample_selected.csv")
    ap.add_argument("--gt-dir", type=Path, default=GT_DIR)
    ap.add_argument("--mock-workbook", type=Path, default=GT_DIR / "groundtruth_MOCK.xlsx")
    ap.add_argument("--template", type=Path, default=GT_DIR / "groundtruth_kappa_MASTER.xlsx",
                    help="reviewer workbook to copy headers + dropdown lists from (read-only)")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--annotator", default="Bea")
    ap.add_argument("--seed", type=int, default=20261105)
    ap.add_argument("--n-abstract", type=int, default=24)
    ap.add_argument("--n-fulltext", type=int, default=16)
    ap.add_argument("--ft-candidates", type=int, default=500,
                    help="full-text papers to compute table features for before the final draw")
    ap.add_argument("--min-abstract-chars", type=int, default=300)
    ap.add_argument("--min-pages", type=int, default=4)
    ap.add_argument("--max-pages", type=int, default=40)
    ap.add_argument("--table-heavy-min", type=int, default=4,
                    help="distinct 'Table N' captions for table-heavy (3 + digit_frac also counts)")
    ap.add_argument("--table-digit-frac", type=float, default=0.10)
    ap.add_argument("--frac-metabarcoding", type=float, default=0.30)
    ap.add_argument("--frac-isolate", type=float, default=0.40)
    a = ap.parse_args()

    if a.stage in ("draw", "all"):
        stage_draw(a)
    if a.stage in ("sheet", "all"):
        stage_sheet(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
