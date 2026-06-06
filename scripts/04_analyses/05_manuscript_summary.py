#!/usr/bin/env python3
# =================================================================================
# 05_manuscript_summary.py
# =================================================================================
# Purpose: Generate a comprehensive dataset description report for the manuscript,
#          aggregating high-level statistics about the endophyte review data.
#
# Inputs:
#  - data/Ollama_cleaned_synresolved_standardized_year.csv
#
# Outputs:
#  - results/manuscript_dataset_summary.md
#  - results/manuscript_dataset_summary.txt
#
# Usage: python3 scripts/04_analyses/05_manuscript_summary.py
# =================================================================================

import pandas as pd
from pathlib import Path
import csv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = PROJECT_ROOT / "data" / "Ollama_cleaned_synresolved_standardized_year.csv"
OUTPUT_MD = PROJECT_ROOT / "results" / "manuscript_dataset_summary.md"
OUTPUT_TXT = PROJECT_ROOT / "results" / "manuscript_dataset_summary.txt"

def main():
    print(f"Loading data from {INPUT_FILE}...")
    try:
        df = pd.read_csv(INPUT_FILE, dtype={'paper_id': str, 'publication_year': 'Int64'})
    except FileNotFoundError:
        print(f"Error: Could not find {INPUT_FILE}. Ensure previous steps are complete.")
        return

    print("Generating manuscript summary...")

    summary_lines = []
    summary_lines.append("# Dataset Description Summary")
    summary_lines.append("This report contains aggregate statistics for manuscript inclusion.\n")

    # 1. Corpus Size & Interactions
    total_rows = len(df)
    unique_papers = df['paper_id'].nunique()
    unique_interactions = df['interaction_id'].nunique()
    
    summary_lines.append("## 1. Corpus Size")
    summary_lines.append(f"- **Total unique papers analyzed:** {unique_papers:,}")
    summary_lines.append(f"- **Total unique fungal-plant interactions:** {unique_interactions:,}")
    summary_lines.append(f"- **Total expanded metadata rows:** {total_rows:,}\n")

    # 2. Document Sources
    summary_lines.append("## 2. Document Types & Sources")
    if 'doc_type_ai_clean' in df.columns:
        doc_types = df.drop_duplicates(subset=['paper_id'])['doc_type_ai_clean'].value_counts()
        summary_lines.append("- **Document Types:**")
        for dtype, count in doc_types.items():
            summary_lines.append(f"  - {dtype.capitalize()}: {count:,} ({count/unique_papers:.1%})")
    
    # 3. Temporal Coverage
    summary_lines.append("\n## 3. Temporal Coverage")
    if 'publication_year' in df.columns and not df['publication_year'].isna().all():
        valid_years = df.drop_duplicates(subset=['paper_id'])['publication_year'].dropna()
        min_year = valid_years.min()
        max_year = valid_years.max()
        median_year = valid_years.median()
        summary_lines.append(f"- **Publication Year Range:** {min_year:.0f} - {max_year:.0f}")
        summary_lines.append(f"- **Median Publication Year:** {median_year:.0f}")
        summary_lines.append(f"- **Papers with known publication year:** {len(valid_years):,} ({len(valid_years)/unique_papers:.1%})")
    else:
        summary_lines.append("- *Publication year data not available or not enriched yet.*")

    # 4. Taxonomic Resolution
    summary_lines.append("\n## 4. Taxonomic Resolution Quality")
    
    fungal_resolved = df['fungal_taxon_resolution_method'].notna() & (df['fungal_taxon_resolution_method'] != 'unresolved')
    fungal_resolved_pct = fungal_resolved.sum() / len(df)
    
    plant_resolved = df['plant_host_resolution_method'].notna() & (df['plant_host_resolution_method'] != 'unresolved')
    plant_resolved_pct = plant_resolved.sum() / len(df)
    
    summary_lines.append(f"- **Fungal taxa successfully resolved to GBIF:** {fungal_resolved.sum():,} records ({fungal_resolved_pct:.1%})")
    summary_lines.append(f"- **Plant hosts successfully resolved to GBIF:** {plant_resolved.sum():,} records ({plant_resolved_pct:.1%})")

    # 5. Geographic & Environmental Scope
    summary_lines.append("\n## 5. Scope & Diversity")
    if 'country' in df.columns:
        unique_countries = df['country'].nunique()
        summary_lines.append(f"- **Unique countries represented:** {unique_countries:,}")
    if 'biome' in df.columns:
        unique_biomes = df['biome'].nunique()
        summary_lines.append(f"- **Unique biomes represented:** {unique_biomes:,}")
    if 'tissue' in df.columns:
        unique_tissues = df['tissue'].nunique()
        summary_lines.append(f"- **Unique plant tissues sampled:** {unique_tissues:,}")
        
    unique_fungal_taxa = df['fungal_taxon_accepted_ids'].nunique()
    unique_plant_taxa = df['plant_host_accepted_ids'].nunique()
    
    summary_lines.append(f"- **Unique standardized fungal taxa (IDs):** {unique_fungal_taxa:,}")
    summary_lines.append(f"- **Unique standardized plant hosts (IDs):** {unique_plant_taxa:,}")

    # Write to files
    print(f"Writing markdown summary to {OUTPUT_MD}...")
    with open(OUTPUT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(summary_lines))
        
    print(f"Writing text summary to {OUTPUT_TXT}...")
    with open(OUTPUT_TXT, 'w', encoding='utf-8') as f:
        # Strip simple markdown for the txt version
        txt_lines = [line.replace('**', '').replace('# ', '').replace('## ', '') for line in summary_lines]
        f.write("\n".join(txt_lines))

    print("Summary generation complete.")
    for line in summary_lines[:20]:  # Print a preview
        print(line)

if __name__ == "__main__":
    main()