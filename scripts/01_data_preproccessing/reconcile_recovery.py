#!/usr/bin/env python3
# Claude, 2026-09-17. Folds a recovery-pass manifest back into the main merged
# pdf_manifest.csv: for any DOI the recovery pass turned into "downloaded", replace its
# row; everything else keeps its original row from the first full pull. Writes a new
# file rather than overwriting in place, so the original merged manifest is never lost.
#
# Usage:
#   python reconcile_recovery.py \
#       --main /scratch/bmb646/full_corpus/pdf_manifest.csv \
#       --recovery /scratch/bmb646/full_corpus/pdf_manifest_recovery.csv \
#       --out /scratch/bmb646/full_corpus/pdf_manifest_v2.csv

import argparse
from pathlib import Path

import pandas as pd


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", type=Path, required=True)
    ap.add_argument("--recovery", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    main_df = pd.read_csv(args.main, low_memory=False).set_index("doi")
    rec_df = pd.read_csv(args.recovery, low_memory=False).set_index("doi")

    recovered = rec_df[rec_df["status"] == "downloaded"]
    still_failed = rec_df[rec_df["status"] != "downloaded"]

    before = (main_df["status"] == "downloaded").sum()
    main_df.update(recovered)
    after = (main_df["status"] == "downloaded").sum()

    main_df.reset_index().to_csv(args.out, index=False)

    n = len(main_df)
    print(f"recovery pass covered {len(rec_df)} DOIs")
    print(f"  newly downloaded : {len(recovered)}")
    print(f"  still failed     : {len(still_failed)}")
    print(f"downloaded before -> after: {before} -> {after}  "
          f"({before/n:.1%} -> {after/n:.1%} of {n})")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
