#!/usr/bin/env python3
# BMB 2026-09-02
# Parse a PubMed "Abstract (text)" export (the numbered "1. Journal. Year..." format,
# e.g. abstract-endophyteA-set.txt) into the 6-column CSV that
# combine_dedupe_abstracts.R expects: title, authors, doi, year, journal, abstract.
#
# Why: abstract-endophyteA-set.txt IS the authoritative Phase 2 PubMed result
# (website export, 2025-08-14, has lichen/photobiont/DSE terms). The pipeline used
# the draft-string API pull instead. Parsing the historical export keeps the search
# date fixed (a fresh rentrez pull would also grab 2025-2026 papers).
#
# Usage:
#   python parse_pubmed_textfile.py \
#       "data/Abstracts/All_abstracts_8-14-25/abstract-endophyteA-set.txt" \
#       "data/Abstracts/All_abstracts_8-14-25/pubmed_pull_phase2.csv"

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

REC_SPLIT = re.compile(r"\n\n(?=\d+\.\s)")
# year sits right after the journal name: "J Appl Microbiol. 2021 Feb;..."
YEAR_AFTER_JOURNAL_RE = re.compile(r"^\d+\.\s*.+?\.\s*((?:18|19|20)\d\d)\b")
YEAR_ANY_RE = re.compile(r"\b((?:18|19|20)\d\d)\b")
DOI_TRAILER_RE = re.compile(r"^DOI:\s*(\S+)", re.M)
DOI_CITE_RE = re.compile(r"\bdoi:\s*(\S+?)\.?(?:\s|$)", re.I)
PMID_RE = re.compile(r"^PMID:\s*(\d+)", re.M)

SKIP_PREFIXES = (
    "author information:", "erratum in", "erratum for", "comment in", "comment on",
    "update of", "updated in", "republished in", "republished from", "original report in",
    "copyright", "©", "� 2", "conflict of interest", "competing interest",
    "in:", "expression of concern", "retraction in", "retracted and republished",
    "plain language summary", "author contributions",
)


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("�", "")).strip()


def _looks_like_authors(block: str) -> bool:
    b = block.strip()
    if len(b) > 600 or "\n\n" in b:
        return False
    # "Smith AB, Jones C(1), ..." or "Smith AB(1)(2), et al."
    if re.search(r"[A-Z][a-z]+ [A-Z]{1,4}\b", b) and b.rstrip().endswith("."):
        # not a sentence-y abstract opener
        if not re.search(r"\b(the|we|this|here|a|an|our|in|study|results?)\b", b.split()[0].lower()):
            return True
    if re.match(r"^[A-Z][a-z]+ [A-Z]", b) and len(b) < 200 and b.count(",") >= 1:
        return True
    return False


def parse_record(rec: str) -> dict | None:
    rec = rec.strip()
    m = PMID_RE.search(rec)
    if not m:
        return None
    pmid = m.group(1)

    blocks = [b.strip() for b in re.split(r"\n\s*\n", rec) if b.strip()]
    if not blocks:
        return None

    citation = blocks[0]
    # journal = text before the first " YYYY" or first ". "
    jm = re.match(r"^\d+\.\s*(.+?)\.\s+(?:\d{4}|[A-Z][a-z]{2}\b|\()", citation)
    journal = _clean(jm.group(1)) if jm else _clean(re.sub(r"^\d+\.\s*", "", citation).split(".")[0])
    ym = YEAR_AFTER_JOURNAL_RE.match(citation)
    if not ym:
        # fall back to the first plausible year on the citation line
        cands = [int(y) for y in YEAR_ANY_RE.findall(citation) if 1750 <= int(y) <= 2026]
        year = str(cands[0]) if cands else ""
    else:
        year = ym.group(1)

    doi = ""
    dm = DOI_TRAILER_RE.search(rec)
    if dm:
        doi = dm.group(1).strip().rstrip(".")
    else:
        dm = DOI_CITE_RE.search(citation)
        if dm:
            doi = dm.group(1).strip().rstrip(".")
    doi = doi.lower()

    # walk the middle blocks: title, then (maybe) authors, then abstract
    mid = []
    for b in blocks[1:]:
        low = b.lower()
        if low.startswith("pmid:") or low.startswith("doi:") or low.startswith("pmcid:"):
            continue
        if any(low.startswith(p) for p in SKIP_PREFIXES):
            continue
        mid.append(b)
    if not mid:
        return None

    title = _clean(mid[0]).rstrip(".")

    # drop correction / erratum / retraction notices - no primary content
    if re.match(r"^(corrigendum|erratum|correction|author correction|withdrawal|"
                r"retraction|expression of concern)\b[:\s]", title, re.I):
        return None

    body = mid[1:]
    if body and _looks_like_authors(body[0]):
        authors = _clean(body[0]).rstrip(".")
        body = body[1:]
    else:
        authors = ""
    abstract = _clean(" ".join(body))

    # "abstract" that is really just a lone author line (old abstract-less records),
    # or a leftover correction pointer
    if _looks_like_authors(abstract) and not authors:
        authors, abstract = abstract.rstrip("."), ""
    if re.match(r"^\[?\s*(this corrects|a correction to|retraction of|"
                r"the authors wish to make)", abstract, re.I):
        abstract = ""

    return {"title": title, "authors": authors, "doi": doi, "year": year,
            "journal": journal, "abstract": abstract, "pmid": pmid}


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    text = src.read_text(encoding="utf-8", errors="replace")
    recs = REC_SPLIT.split(text)
    rows = [r for r in (parse_record(x) for x in recs) if r]

    df = pd.DataFrame(rows)
    n_all = len(df)
    df = df[df["abstract"].str.len() > 0].reset_index(drop=True)
    df = df.drop_duplicates("pmid").reset_index(drop=True)

    dst.parent.mkdir(parents=True, exist_ok=True)
    df[["title", "authors", "doi", "year", "journal", "abstract"]].to_csv(dst, index=False)

    print(f"parsed {len(recs)} record blocks -> {n_all} with a PMID -> "
          f"{len(df)} with an abstract")
    print(f"  with DOI: {(df['doi'].str.len() > 0).sum()}  |  no DOI: {(df['doi'].str.len() == 0).sum()}")
    print(f"  year range: {df['year'].replace('', pd.NA).dropna().astype(int).min()}"
          f"-{df['year'].replace('', pd.NA).dropna().astype(int).max()}")
    print(f"  wrote {dst}")
    # quick sanity: title/abstract not obviously swapped
    bad = df[df["title"].str.len() > df["abstract"].str.len()]
    if len(bad):
        print(f"  NOTE: {len(bad)} rows have title longer than abstract - spot-check these")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
