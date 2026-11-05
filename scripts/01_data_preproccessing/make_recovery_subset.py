#!/usr/bin/env python3
# Claude, 2026-09-17. Builds a small input CSV of just the DOIs worth retrying after the
# first full-corpus pull (job 31693127): 4,193/19,586 came back download_failed, and
# 2,770 of those (66%) never actually got a real network attempt - they were skipped
# because the host's circuit breaker had already tripped from a DIFFERENT shard's 403s.
# The circuit-breaker state is per-process (per shard), not shared across the 8-way
# array, so a host effectively saw up to 8x the intended request rate at once (this is
# already called out in fetch_fulltext_pdfs.py's own header comment). Retrying with a
# single shard - no parallel array - lets the existing per-host throttle behave as
# designed instead of getting steamrolled by 7 siblings hitting the same publisher.
#
# Also picks up the "not pdf" bucket (792 DOIs: resolver found a URL but got back an
# HTML landing page instead of a PDF) since the new OpenAIRE resolver may surface a
# different, non-publisher-hosted URL for some of these that the first pass never saw.
#
# 2026-09-17 update: CORE_API_KEY was blank for the entire first pull, so CORE (the
# resolver most likely to hand back its own cached copy instead of a publisher redirect)
# never ran on ANY of the 19,586 DOIs - not just the 4,193 failures. That means the
# 9,436 "no_oa_pdf" records were also never checked against CORE or OpenAIRE (added
# after the pull too). --include-no-oa-pdf widens the recovery subset to include them,
# which is the more complete fix for Bea's concern about the current full-text pool
# being systematically short on bot-blocking publishers (Wiley/MDPI/Elsevier/etc, incl.
# New Phytologist itself) - but it's a much bigger subset (~13.6k DOIs vs ~3.6k), so
# check your CORE daily token allowance before running it at that scale; --limit lets
# you test the actual token cost on a small slice first.
#
# Usage:
#   python make_recovery_subset.py --manifest /scratch/bmb646/full_corpus/pdf_manifest.csv \
#       --out /scratch/bmb646/full_corpus/recovery_input.csv
#   # wider (also re-check no_oa_pdf now that CORE + OpenAIRE are active):
#   python make_recovery_subset.py --manifest ... --out ... --include-no-oa-pdf

import argparse
from pathlib import Path

import pandas as pd


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--circuit-only", action="store_true",
                    help="only the never-really-attempted circuit-open DOIs; skip the "
                         "'not pdf' bucket")
    ap.add_argument("--include-no-oa-pdf", action="store_true",
                    help="also re-check no_oa_pdf DOIs (CORE + OpenAIRE never ran on "
                         "these the first time) - much larger subset, costs more API "
                         "calls/tokens, use --limit to test cost first")
    ap.add_argument("--limit", type=int, default=0,
                    help="cap the output to N DOIs (a quick, cheap sample to test "
                         "actual CORE token cost / hit rate before running the full "
                         "subset)")
    args = ap.parse_args()

    df = pd.read_csv(args.manifest, low_memory=False)
    failed = df[df["status"] == "download_failed"].copy()
    no_oa = df[df["status"] == "no_oa_pdf"].copy()

    circuit = failed["note"].astype(str).str.startswith("host circuit open")
    not_pdf = failed["note"].astype(str).str.startswith("not pdf")

    if args.circuit_only:
        subset = failed[circuit]
    else:
        subset = failed[circuit | not_pdf]

    print(f"download_failed total: {len(failed)}")
    print(f"  host circuit open : {circuit.sum()}")
    print(f"  not pdf           : {not_pdf.sum()}")
    print(f"  other (excluded)  : {len(failed) - circuit.sum() - not_pdf.sum()}")
    print(f"failed-bucket subset: {len(subset)}")

    if args.include_no_oa_pdf:
        print(f"no_oa_pdf total     : {len(no_oa)}  (adding all of these)")
        subset = pd.concat([subset, no_oa], ignore_index=True)

    if args.limit:
        subset = subset.sample(n=min(args.limit, len(subset)), random_state=0)
        print(f"--limit applied: sampled down to {len(subset)}")

    print(f"final recovery subset: {len(subset)}")

    out = subset[["doi"]].rename(columns={"doi": "DOI"}).drop_duplicates()
    out.to_csv(args.out, index=False)
    print(f"wrote {len(out)} DOIs -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
