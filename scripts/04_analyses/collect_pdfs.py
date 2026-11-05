#!/usr/bin/env python3
# BMB / Claude, 2026-09-17
# Copies full-text PDFs from the Monsoon PDF corpus into a per-reviewer folder,
# renamed to match that reviewer's workbook row_id, ready to zip/upload to Drive.
# Generalized version of the one-off script used for the kappa block - same idea,
# reusable for anyone's solo folder without hand-editing a path each time.
#
# Run on Monsoon (where the PDFs actually live), once per reviewer, e.g.:
#   python collect_pdfs.py --csv bea_pdf_filenames.csv  --dest bea_pdfs_for_drive
#   python collect_pdfs.py --csv ian_pdf_filenames.csv  --dest ian_pdfs_for_drive
#
# --csv needs two columns: new_name (row_id.pdf, what the reviewer will see) and
# old_name (the actual filename in --src, from pdf_manifest.csv).
# --src defaults to the same PDF folder used for the kappa block; only pass it if
# that's wrong - don't hand-edit this file to change it.

import argparse
import shutil
import sys
from pathlib import Path

import pandas as pd


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True, type=Path,
                    help="CSV with new_name,old_name columns (e.g. bea_pdf_filenames.csv)")
    ap.add_argument("--src", type=Path, default=Path("/scratch/bmb646/full_corpus"),
                    help="folder the PDFs actually live in (default matches the kappa-block run)")
    ap.add_argument("--dest", required=True, type=Path,
                    help="folder to write the renamed copies into (created if missing)")
    args = ap.parse_args()

    if not args.csv.exists():
        print(f"ERROR: {args.csv} not found"); return 1
    if not args.src.exists():
        print(f"ERROR: --src {args.src} not found - check the path, don't guess it"); return 1

    df = pd.read_csv(args.csv)
    for col in ("new_name", "old_name"):
        if col not in df.columns:
            print(f"ERROR: {args.csv} is missing a '{col}' column"); return 1

    args.dest.mkdir(parents=True, exist_ok=True)
    missing = []
    copied = 0
    for _, r in df.iterrows():
        src = args.src / str(r["old_name"])
        if not src.exists():
            missing.append(str(r["old_name"]))
            continue
        shutil.copy(src, args.dest / str(r["new_name"]))
        copied += 1

    print(f"done -> {args.dest}  ({copied}/{len(df)} copied)")
    for m in missing:
        print("MISSING:", m)
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
