#!/usr/bin/env python3
"""
Merge per-shard ubiquity claims outputs into final aggregated files.

Usage:
  python scripts/04_analyses/merge_ubiquity_shards.py \
    --input-dir results/ubiquity_claims \
    --output-dir results/ubiquity_claims_final \
    --n-shards 4

Combines:
  - results/ubiquity_claims/shard_0/ubiquity_claims_all.csv
  - results/ubiquity_claims/shard_1/ubiquity_claims_all.csv
  - ...etc...
Into:
  - results/ubiquity_claims_final/ubiquity_claims_all.csv
  - results/ubiquity_claims_final/ubiquity_claims_positive.csv
  - results/ubiquity_claims_final/ubiquity_claims_all.jsonl
"""

import argparse
import os
import sys
from pathlib import Path
import pandas as pd
import json

def merge_shards(input_dir, output_dir, n_shards):
    """Merge per-shard output CSVs and JSONL files."""
    
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Merging {n_shards} shards from {input_dir} → {output_dir}")
    
    # 1. Merge ubiquity_claims_all.csv
    print("\n[1/3] Merging ubiquity_claims_all.csv...")
    all_dfs = []
    for shard_id in range(n_shards):
        shard_csv = input_dir / f"shard_{shard_id}" / "ubiquity_claims_all.csv"
        if shard_csv.exists():
            df = pd.read_csv(shard_csv)
            all_dfs.append(df)
            print(f"  ✓ shard_{shard_id}: {len(df)} rows")
        else:
            print(f"  ⚠ shard_{shard_id}: not found, skipping")
    
    if all_dfs:
        merged_all = pd.concat(all_dfs, ignore_index=True)
        output_csv = output_dir / "ubiquity_claims_all.csv"
        merged_all.to_csv(output_csv, index=False)
        print(f"  → Wrote {len(merged_all)} rows to {output_csv.name}")
    else:
        print("  ✗ No all.csv files found!")
        return False
    
    # 2. Extract and merge ubiquity_claims_positive.csv
    print("\n[2/3] Merging ubiquity_claims_positive.csv...")
    positive_rows = merged_all[merged_all['contains_ubiquity_claim'] == True]
    if len(positive_rows) > 0:
        output_positive = output_dir / "ubiquity_claims_positive.csv"
        positive_rows.to_csv(output_positive, index=False)
        print(f"  → Wrote {len(positive_rows)} positive rows to {output_positive.name}")
    else:
        print("  → No positive claims found (creating empty file)")
        output_positive = output_dir / "ubiquity_claims_positive.csv"
        positive_rows.to_csv(output_positive, index=False)
    
    # 3. Merge ubiquity_claims_all.jsonl
    print("\n[3/3] Merging ubiquity_claims_all.jsonl...")
    output_jsonl = output_dir / "ubiquity_claims_all.jsonl"
    with open(output_jsonl, 'w') as fout:
        row_count = 0
        for shard_id in range(n_shards):
            shard_jsonl = input_dir / f"shard_{shard_id}" / "ubiquity_claims_all.jsonl"
            if shard_jsonl.exists():
                with open(shard_jsonl, 'r') as fin:
                    for line in fin:
                        fout.write(line)
                        row_count += 1
                print(f"  ✓ shard_{shard_id}: {row_count} rows so far")
            else:
                print(f"  ⚠ shard_{shard_id} JSONL: not found, skipping")
    
    print(f"  → Wrote {row_count} rows to {output_jsonl.name}")
    
    # Summary statistics
    print("\n=== Merge Summary ===")
    print(f"Total rows processed: {len(merged_all)}")
    print(f"Positive claims: {len(positive_rows)} ({100*len(positive_rows)/len(merged_all):.1f}%)")
    print(f"Errors: {len(merged_all[merged_all['error'].notna()])}")
    print(f"Output files:")
    print(f"  - {output_csv.name}")
    print(f"  - {output_positive.name}")
    print(f"  - {output_jsonl.name}")
    
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", default="results/ubiquity_claims", help="Input directory with shard_* subdirs")
    parser.add_argument("--output-dir", default="results/ubiquity_claims_final", help="Output directory for merged files")
    parser.add_argument("--n-shards", type=int, default=4, help="Number of shards to merge")
    
    args = parser.parse_args()
    
    success = merge_shards(args.input_dir, args.output_dir, args.n_shards)
    sys.exit(0 if success else 1)
