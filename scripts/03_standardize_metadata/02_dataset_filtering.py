#!/usr/bin/env python3
# BMB 2026-06-05
# Filters out low-quality records - irrelevant papers, bad taxon entries,
# and clear non-endophyte studies.

import csv
import os
from importlib import util
from pathlib import Path

TAXON_MAPPING_PATH = Path(__file__).resolve().parents[1] / 'utils' / 'taxon_mapping.py'
TAXON_MAPPING_SPEC = util.spec_from_file_location('taxon_mapping', TAXON_MAPPING_PATH)
if TAXON_MAPPING_SPEC is None or TAXON_MAPPING_SPEC.loader is None:
    raise ImportError(f'Could not load taxon mapping module: {TAXON_MAPPING_PATH}')

taxon_mapping = util.module_from_spec(TAXON_MAPPING_SPEC)
TAXON_MAPPING_SPEC.loader.exec_module(taxon_mapping)

get_allowed_kingdoms = taxon_mapping.get_allowed_kingdoms
get_excluded_phyla = taxon_mapping.get_excluded_phyla
get_excluded_classes = taxon_mapping.get_excluded_classes
get_excluded_guilds = taxon_mapping.get_excluded_guilds

INPUT_FILE = 'data/Ollama_cleaned_synresolved_standardized_year.csv'
OUTPUT_FILE = 'data/Ollama_cleaned_synresolved_filtered.csv'
FILTERED_ROWS_FILE = 'results/logs/filtered_rows.csv'

# 1. Study-Specific Constraints (centralized)
ALLOWED_KINGDOMS = set(get_allowed_kingdoms())
EXCLUDED_PHYLA = set(get_excluded_phyla())
EXCLUDED_CLASSES = set(get_excluded_classes())
EXCLUDED_GUILDS = set(get_excluded_guilds())

def filter_dataset():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    # First pass: count initial unique papers and rows
    initial_papers = set()
    with open(INPUT_FILE, 'r', encoding='utf-8') as f_in:
        reader = csv.DictReader(f_in)
        for row in reader:
            paper_id = row.get('paper_id', '')
            if paper_id:
                initial_papers.add(paper_id)

        # Second pass: apply filters and track papers removed at each stage
        os.makedirs(os.path.dirname(FILTERED_ROWS_FILE), exist_ok=True)
        with open(INPUT_FILE, 'r', encoding='utf-8') as f_in, \
             open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out, \
             open(FILTERED_ROWS_FILE, 'w', encoding='utf-8') as f_filtered:

            reader = csv.DictReader(f_in)
            writer = csv.DictWriter(f_out, fieldnames=reader.fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()

            filtered_fieldnames = list(reader.fieldnames or []) + ['filter_reason']
            filtered_writer = csv.DictWriter(
                f_filtered, fieldnames=filtered_fieldnames, quoting=csv.QUOTE_ALL
            )
            filtered_writer.writeheader()

            in_count = 0
            out_count = 0
            final_papers = set()

            # Track papers removed by each filter
            papers_by_filter = {
                'relevance': set(),
                'kingdom': set(),
                'phylum_class': set(),
                'guild': set()
            }

            for row in reader:
                in_count += 1
                paper_id = row.get('paper_id', '')

                # Extract values and normalize to lowercase for matching
                kingdom = str(row.get('fungal_taxon_kingdom', '')).lower()
                phylum = str(row.get('fungal_taxon_phylum', '')).lower()
                class_val = str(row.get('fungal_taxon_class', '')).lower()
                guild = str(row.get('primary_guild', '')).lower()
                relevance = str(row.get('relevance', '')).lower()

                # apply filters in order

                # Rule 1: Relevance Check
                if relevance != 'relevant':
                    if paper_id:
                        papers_by_filter['relevance'].add(paper_id)
                    filtered_row = dict(row)
                    filtered_row['filter_reason'] = 'relevance'
                    filtered_writer.writerow(filtered_row)
                    continue

                # Rule 2: Kingdom Check (keep NA/empty kingdoms)
                if kingdom and kingdom not in ALLOWED_KINGDOMS:
                    if paper_id:
                        papers_by_filter['kingdom'].add(paper_id)
                    filtered_row = dict(row)
                    filtered_row['filter_reason'] = 'kingdom'
                    filtered_writer.writerow(filtered_row)
                    continue

                # Rule 3: Explicit Phylum Exclusion (Removes AMF and Bacteria)
                if phylum in EXCLUDED_PHYLA or class_val in EXCLUDED_CLASSES:
                    if paper_id:
                        papers_by_filter['phylum_class'].add(paper_id)
                    filtered_row = dict(row)
                    filtered_row['filter_reason'] = 'phylum_class'
                    filtered_writer.writerow(filtered_row)
                    continue

                # Rule 4: Guild Exclusion (Removes Mycorrhizae)
                if guild in EXCLUDED_GUILDS:
                    if paper_id:
                        papers_by_filter['guild'].add(paper_id)
                    filtered_row = dict(row)
                    filtered_row['filter_reason'] = 'guild'
                    filtered_writer.writerow(filtered_row)
                    continue

                # If it passes all rules, write to new file
                writer.writerow(row)
                out_count += 1
                if paper_id:
                    final_papers.add(paper_id)

    # Calculate cumulative papers remaining after each filter
    after_relevance = initial_papers - papers_by_filter['relevance']
    after_kingdom = after_relevance - papers_by_filter['kingdom']
    after_phylum = after_kingdom - papers_by_filter['phylum_class']
    after_guild = after_phylum - papers_by_filter['guild']

    print("="*70)
    print("FILTERING COMPLETE")
    print("="*70)
    print(f"\nSTARTING DATASET:")
    print(f"  Interactions: {in_count:,}  |  Unique Papers: {len(initial_papers):,}")

    print(f"\nPAPERS LOST BY EACH FILTER:")
    print(f"  After Relevance Check:    {len(initial_papers):,} → {len(after_relevance):,}  (Lost {len(papers_by_filter['relevance']):,})")
    print(f"  After Kingdom Check:      {len(after_relevance):,} → {len(after_kingdom):,}  (Lost {len(papers_by_filter['kingdom']):,})")
    print(f"  After Phylum/Class Check: {len(after_kingdom):,} → {len(after_phylum):,}  (Lost {len(papers_by_filter['phylum_class']):,})")
    print(f"  After Guild Check:        {len(after_phylum):,} → {len(after_guild):,}  (Lost {len(papers_by_filter['guild']):,})")

    print(f"\nFINAL DATASET:")
    print(f"  Interactions: {out_count:,}  |  Unique Papers: {len(final_papers):,}")
    print(f"  Total Papers Lost: {len(initial_papers) - len(final_papers):,}")
    print(f"  Output File: {OUTPUT_FILE}")
    print(f"  Filtered Rows File: {FILTERED_ROWS_FILE}")
    print("="*70)

if __name__ == "__main__":
    filter_dataset()