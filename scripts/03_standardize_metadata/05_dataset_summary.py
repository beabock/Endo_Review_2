#!/usr/bin/env python3
# BMB 2026-06-05
# Quick QA summary — prints column completeness stats after filtering. Not in main pipeline.

import argparse
import csv
from collections import Counter


DEFAULT_FILE_PATH = 'data/Ollama_cleaned_synresolved_filtered.csv'

CATEGORICAL_COLUMNS = [
    'fungal_taxon_phylum',
    'fungal_taxon_class',
    'plant_host_phylum',
    'plant_host_class',
    'tissue',
    'primary_guild',
    'relevance',
    'doc_type_ai',
    'fungal_taxon_status',
    'plant_host_status',
]

ENV_COLUMNS = [
    'country',
    'biome',
    'data_source',
]


def summarize_data(file_path: str) -> None:
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        stats = {col: Counter() for col in CATEGORICAL_COLUMNS}
        total_rows = 0

        for row in reader:
            total_rows += 1
            for col in CATEGORICAL_COLUMNS:
                val = row.get(col, 'MISSING').strip()
                if not val:
                    val = 'EMPTY'
                stats[col][val] += 1

    print("=" * 60)
    print(f"DATABASE SUMMARY: {total_rows:,} total interactions")
    print("=" * 60)

    for col in CATEGORICAL_COLUMNS:
        print(f"\nTOP VALUES FOR: {col}")
        print("-" * 30)
        top_values = stats[col].most_common(10)
        for val, count in top_values:
            percentage = (count / total_rows) * 100 if total_rows else 0.0
            print(f"{count:7,d} ({percentage:5.1f}%) | {val}")


def summarize_environment(file_path: str) -> None:
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        stats = {col: Counter() for col in ENV_COLUMNS}
        total_rows = 0

        for row in reader:
            total_rows += 1
            for col in ENV_COLUMNS:
                val = row.get(col, 'NA').strip()
                if not val or val.lower() in ['na', 'none', 'null', 'unknown']:
                    val = 'NA'
                stats[col][val] += 1

    print("=" * 60)
    print(f"ENVIRONMENTAL AUDIT: {total_rows:,} total interactions")
    print("=" * 60)

    for col in ENV_COLUMNS:
        print(f"\nTOP VALUES FOR: {col}")
        print("-" * 30)
        top_values = stats[col].most_common(10)
        for val, count in top_values:
            percentage = (count / total_rows) * 100 if total_rows else 0.0
            print(f"{count:7,d} ({percentage:5.1f}%) | {val}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Summarize filtered dataset composition.')
    parser.add_argument('--file-path', default=DEFAULT_FILE_PATH, help='Input CSV path')
    parser.add_argument(
        '--mode',
        choices=['all', 'categorical', 'environment'],
        default='all',
        help='Which summary to run',
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        if args.mode in {'all', 'categorical'}:
            summarize_data(args.file_path)
        if args.mode in {'all', 'environment'}:
            print()
            summarize_environment(args.file_path)
    except FileNotFoundError:
        print(f"Error: Could not find '{args.file_path}'.")
        return 1
    except Exception as exc:
        print(f"An error occurred: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())