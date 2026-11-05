#!/usr/bin/env python3
# BMB 2026-09-02
# Merge the per-shard manifests written by run_fetch_pdfs.sbatch into one
# pdf_manifest.csv, and (for a dry-run) regenerate the coverage report:
# overall OA coverage + missing PDFs grouped by publisher/journal (Referee 2's
# "are abstract-only papers concentrated in particular publishers?").

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=Path("/scratch/bmb646/full_corpus"))
    ap.add_argument("--glob", default="pdf_manifest_shard*.csv")
    args = ap.parse_args()

    parts = sorted(args.out_dir.glob(args.glob))
    if not parts:
        raise SystemExit(f"no shard manifests matching {args.out_dir/args.glob}")
    man = pd.concat([pd.read_csv(p) for p in parts], ignore_index=True)
    man = man.drop_duplicates("doi").reset_index(drop=True)

    merged = args.out_dir / "pdf_manifest.csv"
    man.to_csv(merged, index=False)
    print(f"{len(parts)} shards -> {len(man)} DOIs -> {merged}\n")
    print(man["status"].value_counts().to_string())

    is_dry = set(man["status"]) <= {"resolvable", "no_oa_pdf"}
    got = man["status"].isin(["resolvable", "downloaded"])
    print(f"\nfull-text obtainable: {got.mean():.1%}  ({got.sum()} / {len(man)})")

    # coalesce Unpaywall publisher/journal with the search-export's own fields
    for a, b in (("publisher", "db_publisher"), ("journal", "db_journal")):
        if b in man.columns:
            man[a] = man[a].fillna(man[b]) if a in man.columns else man[b]

    miss = man[~got]
    if len(miss):
        by_pub = (miss.groupby(["publisher", "journal"], dropna=False)
                  .size().reset_index(name="n_missing")
                  .sort_values("n_missing", ascending=False))
        rep = args.out_dir / "coverage_report.csv"
        by_pub.to_csv(rep, index=False)
        print(f"\nmissing full text by publisher/journal (top 20) -> {rep}")
        print(by_pub.head(20).to_string(index=False))

    # OA-status breakdown when available (dry-run has it from Unpaywall)
    if "oa_status" in man.columns and man["oa_status"].notna().any():
        print("\nUnpaywall oa_status:")
        print(man["oa_status"].value_counts(dropna=False).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
