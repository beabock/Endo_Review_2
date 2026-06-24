#!/usr/bin/env python3
# BMB 2026-06-05
# Summarizes fungal taxon representation at species, genus, and family level by phylum.
#
# Usage: python3 scripts/04_analyses/03_fungal_taxonomic_bias.py
# =================================================================================

import pandas as pd
import csv
import sys
from pathlib import Path
from collections import defaultdict

# ==================== CONFIG ====================
INPUT_FILE = "data/Ollama_cleaned_synresolved_standardized_final.csv"
GBIF_TAXON_FILE = "data/Reference_datasets/gbif_backbone/Taxon.tsv"
PLANT_COVERAGE_FILE = "results/taxonomy_analysis/plant_species_coverage_summary.csv"
RESULTS_DIR = "results/taxonomy_analysis"

def first_existing_path(*candidates):
    for p in candidates:
        if Path(p).exists():
            return p
    return candidates[0]

GBIF_TAXON_FILE = first_existing_path(
    GBIF_TAXON_FILE,
    "../data/Reference_datasets/gbif_backbone/Taxon.tsv",
    "../../data/Reference_datasets/gbif_backbone/Taxon.tsv",
)

PLANT_COVERAGE_FILE = first_existing_path(
    PLANT_COVERAGE_FILE,
    "../results/taxonomy_analysis/plant_species_coverage_summary.csv",
    "../../results/taxonomy_analysis/plant_species_coverage_summary.csv",
)

OUTPUT_PHYLUM = Path(RESULTS_DIR) / "fungal_phylum_coverage.csv"
OUTPUT_GENUS = Path(RESULTS_DIR) / "fungal_genus_coverage.csv"
OUTPUT_FAMILY = Path(RESULTS_DIR) / "fungal_family_coverage.csv"
OUTPUT_TOP_GENERA = Path(RESULTS_DIR) / "top_studied_fungal_genera.csv"
OUTPUT_COMPARISON = Path(RESULTS_DIR) / "fungal_vs_plant_comparison.csv"
OUTPUT_MYCORRHIZAL = Path(RESULTS_DIR) / "mycorrhizal_annotation.csv"

OUTPUT_DIR = Path(RESULTS_DIR)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ==================== DATA LOADING ====================
print("Loading study-level fungal data...")
csv.field_size_limit(min(sys.maxsize, 10**9))

required_cols = [
    'paper_id', 'fungal_taxon_resolved', 'fungal_taxon_status', 
    'fungal_taxon_accepted_ids'
]

try:
    study_data = pd.read_csv(
        INPUT_FILE,
        dtype={'paper_id': str},
        usecols=['paper_id', 'fungal_taxon_resolved', 'fungal_taxon_status', 
                 'fungal_taxon_accepted_ids']
    )
    
    # Check for missing columns
    missing = set(required_cols) - set(study_data.columns)
    if missing:
        print(f"Warning: Missing columns {missing}. Fungal analysis may be limited.")
        print(f"Available columns: {study_data.columns.tolist()}")
        
except Exception as e:
    print(f"Error loading input data: {e}")
    sys.exit(1)

print(f"  Loaded {len(study_data)} rows from {INPUT_FILE}")

# ==================== GBIF INDEX BUILDING ====================
print("Loading GBIF backbone Fungi taxonomy...")

gbif_taxa = {}
gbif_phylum_map = {}
gbif_parent_map = {}

try:
    with open(GBIF_TAXON_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            tid = row.get('taxonID')
            if not tid:
                continue
            
            # Build parent map for lineage traversal
            parent_id = row.get('parentNameUsageID', '')
            if parent_id:
                gbif_parent_map[tid] = parent_id
            
            # Only index Fungi
            kingdom = row.get('kingdom', '').strip()
            if kingdom != 'Fungi':
                continue
            
            status = (row.get('taxonomicStatus', '').strip().lower())
            if status != 'accepted':
                continue
            
            rank = (row.get('taxonRank', '').strip().upper())
            phylum = (row.get('phylum', '').strip() if row.get('phylum') else '')
            
            # Store for later lookup
            gbif_taxa[tid] = {
                'taxonID': tid,
                'canonicalName': row.get('canonicalName', ''),
                'taxonRank': rank,
                'kingdom': kingdom,
                'phylum': phylum,
                'family': row.get('family', '').strip() if row.get('family') else '',
                'genus': row.get('genus', '').strip() if row.get('genus') else '',
            }
            
            # Store phylum info for backfilling
            if phylum:
                gbif_phylum_map[tid] = phylum

except Exception as e:
    print(f"Error loading GBIF data: {e}")
    sys.exit(1)

print(f"  Indexed {len(gbif_taxa)} accepted Fungi taxa from GBIF")

# ==================== HELPER: LINEAGE BACKFILL ====================
def resolve_phylum_from_lineage(taxon_id, max_steps=40):
    """Traverse parent lineage to find phylum."""
    current = taxon_id
    steps = 0
    while current and steps < max_steps:
        if current in gbif_phylum_map:
            return gbif_phylum_map[current]
        current = gbif_parent_map.get(current)
        steps += 1
    return ""

# ==================== ANALYSIS 1: EXTRACT STUDIED FUNGI ====================
print("Extracting studied fungal taxa...")

study_fungi_links = []
for idx, row in study_data.iterrows():
    paper_id = str(row.get('paper_id', '')) if pd.notna(row.get('paper_id')) else None
    accepted_ids_str = str(row.get('fungal_taxon_accepted_ids', '')) if pd.notna(row.get('fungal_taxon_accepted_ids')) else ''
    resolved = str(row.get('fungal_taxon_resolved', '')) if pd.notna(row.get('fungal_taxon_resolved')) else ''
    
    if not paper_id or paper_id == 'nan':
        continue
    if not accepted_ids_str or accepted_ids_str == 'nan':
        continue
    
    # Split multiple IDs
    for acc_id in accepted_ids_str.split(';'):
        acc_id = acc_id.strip()
        if acc_id:
            study_fungi_links.append({
                'paper_id': paper_id,
                'fungal_taxon_resolved': resolved,
                'accepted_id': acc_id
            })

# Deduplicate to unique paper_id + resolved name + ID combinations
df_links = pd.DataFrame(study_fungi_links)
df_links = df_links.drop_duplicates(subset=['paper_id', 'fungal_taxon_resolved', 'accepted_id'])

print(f"  Found {len(df_links)} unique fungal host records across {df_links['paper_id'].nunique()} papers")

# ==================== ANALYSIS 2: MATCH TO GBIF & BUILD REFERENCE ====================
print("Matching studied fungi to GBIF reference...")

# Build full reference dataset of all GBIF fungi by rank
gbif_fungi_species = {}
gbif_fungi_genus = {}
gbif_fungi_family = {}
missing_phylum_count = 0
backfilled_count = 0

for tid, taxon_info in gbif_taxa.items():
    rank = taxon_info['taxonRank']
    phylum = taxon_info['phylum']
    
    # Backfill missing phylum from lineage
    if not phylum or phylum == '':
        resolved_phylum = resolve_phylum_from_lineage(tid)
        if resolved_phylum:
            phylum = resolved_phylum
            backfilled_count += 1
        else:
            missing_phylum_count += 1
    
    if not phylum:
        phylum = "Unassigned"
    
    taxon_info['phylum'] = phylum
    
    if rank == 'SPECIES':
        gbif_fungi_species[tid] = taxon_info
    if rank == 'GENUS':
        gbif_fungi_genus[tid] = taxon_info
    if rank == 'FAMILY':
        gbif_fungi_family[tid] = taxon_info

total_fungi_species = len(gbif_fungi_species)
total_fungi_genus = len(gbif_fungi_genus)
total_fungi_family = len(gbif_fungi_family)

print(f"  GBIF Fungi reference stats:")
print(f"    - Species: {total_fungi_species}")
print(f"    - Genera: {total_fungi_genus}")
print(f"    - Families: {total_fungi_family}")
print(f"    - Missing phylum before backfill: {missing_phylum_count}")
print(f"    - Backfilled from lineage: {backfilled_count}")

# ==================== ANALYSIS 3: MATCH STUDIED TO REFERENCE ====================
print("Matching studied fungal IDs to GBIF reference...")

matched_taxa = []
for idx, link in df_links.iterrows():
    acc_id = link['accepted_id']
    if acc_id in gbif_fungi_species:
        taxon = gbif_fungi_species[acc_id].copy()
        taxon['paper_id'] = link['paper_id']
        matched_taxa.append(taxon)

df_matched = pd.DataFrame(matched_taxa)
unique_studied = df_matched.drop_duplicates(subset=['taxonID'])
unique_papers = df_matched['paper_id'].nunique()

print(f"  Matched {len(df_matched)} total records")
print(f"  Unique fungal species studied: {len(unique_studied)}")
print(f"  Unique papers: {unique_papers}")

# ==================== ANALYSIS 4: COVERAGE BY PHYLUM ====================
print("Computing fungal coverage by phylum...")

# Reference: known fungi by phylum
known_by_phylum = {}
for tid, taxon in gbif_fungi_species.items():
    phylum = taxon.get('phylum', 'Unassigned')
    if phylum not in known_by_phylum:
        known_by_phylum[phylum] = set()
    known_by_phylum[phylum].add(tid)

# Studied: fungi by phylum from matched data
studied_by_phylum = {}
if len(df_matched) > 0:
    for idx, row in unique_studied.iterrows():
        phylum = row.get('phylum', 'Unassigned')
        if phylum not in studied_by_phylum:
            studied_by_phylum[phylum] = set()
        studied_by_phylum[phylum].add(row['taxonID'])

# Create coverage table
coverage_phylum = []
for phylum in sorted(known_by_phylum.keys(), key=lambda p: len(known_by_phylum[p]), reverse=True):
    known_count = len(known_by_phylum[phylum])
    studied_count = len(studied_by_phylum.get(phylum, set()))
    coverage_pct = 100 * studied_count / known_count if known_count > 0 else 0
    
    coverage_phylum.append({
        'phylum': phylum,
        'known_species': known_count,
        'studied_species': studied_count,
        'coverage_percent': coverage_pct
    })

df_phylum_coverage = pd.DataFrame(coverage_phylum)
df_phylum_coverage.to_csv(OUTPUT_PHYLUM, index=False)
print(f"  Saved phylum coverage to {OUTPUT_PHYLUM}")

# ==================== ANALYSIS 5: GENUS & FAMILY COVERAGE ====================
print("Computing fungal coverage by genus and family...")

# Genus coverage
genus_by_phylum = defaultdict(set)
for tid, taxon in gbif_fungi_genus.items():
    phylum = taxon.get('phylum', 'Unassigned')
    genus_by_phylum[phylum].add(tid)

studied_genus_by_phylum = defaultdict(set)
if len(df_matched) > 0:
    for idx, row in df_matched.iterrows():
        phylum = row.get('phylum', 'Unassigned')
        genus = row.get('genus', '')
        if genus:
            studied_genus_by_phylum[phylum].add(genus)

coverage_genus = []
for phylum in sorted(genus_by_phylum.keys()):
    known_count = len(genus_by_phylum[phylum])
    studied_count = len(studied_genus_by_phylum.get(phylum, set()))
    coverage_pct = 100 * studied_count / known_count if known_count > 0 else 0
    
    coverage_genus.append({
        'phylum': phylum,
        'known_genera': known_count,
        'studied_genera': studied_count,
        'coverage_percent': coverage_pct
    })

df_genus_coverage = pd.DataFrame(coverage_genus)
df_genus_coverage.to_csv(OUTPUT_GENUS, index=False)
print(f"  Saved genus coverage to {OUTPUT_GENUS}")

# Family coverage
family_by_phylum = defaultdict(set)
for tid, taxon in gbif_fungi_family.items():
    phylum = taxon.get('phylum', 'Unassigned')
    family_by_phylum[phylum].add(tid)

studied_family_by_phylum = defaultdict(set)
if len(df_matched) > 0:
    for idx, row in df_matched.iterrows():
        phylum = row.get('phylum', 'Unassigned')
        family = row.get('family', '')
        if family:
            studied_family_by_phylum[phylum].add(family)

coverage_family = []
for phylum in sorted(family_by_phylum.keys()):
    known_count = len(family_by_phylum[phylum])
    studied_count = len(studied_family_by_phylum.get(phylum, set()))
    coverage_pct = 100 * studied_count / known_count if known_count > 0 else 0
    
    coverage_family.append({
        'phylum': phylum,
        'known_families': known_count,
        'studied_families': studied_count,
        'coverage_percent': coverage_pct
    })

df_family_coverage = pd.DataFrame(coverage_family)
df_family_coverage.to_csv(OUTPUT_FAMILY, index=False)
print(f"  Saved family coverage to {OUTPUT_FAMILY}")

# ==================== ANALYSIS 6: TOP STUDIED GENERA ====================
print("Identifying top-studied fungal genera...")

if len(df_matched) > 0:
    top_genera = df_matched.drop_duplicates(subset=['paper_id', 'taxonID', 'genus']) \
        .groupby(['genus', 'phylum', 'family']) \
        .size() \
        .reset_index(name='study_count') \
        .sort_values('study_count', ascending=False) \
        .head(100)
    
    top_genera.to_csv(OUTPUT_TOP_GENERA, index=False)
    print(f"  Saved top {len(top_genera)} genera to {OUTPUT_TOP_GENERA}")
else:
    top_genera = pd.DataFrame()
    top_genera.to_csv(OUTPUT_TOP_GENERA, index=False)
    print(f"  No studied fungi to report.")

# ==================== ANALYSIS 7: FUNGAL VS PLANT COMPARISON ====================
print("Comparing fungal vs plant research representation...")

# Load plant summary if available
plant_summary = {}
try:
    plant_df = pd.read_csv(PLANT_COVERAGE_FILE)
    for col in plant_df.columns:
        plant_summary[col] = plant_df[col].iloc[0] if len(plant_df) > 0 else None
except:
    print(f"  Warning: Could not load plant summary from {PLANT_COVERAGE_FILE}")

# Build fungal summary
fungal_summary = {
    'dataset_rows': len(study_data),
    'rows_with_fungi_records': len(study_data[study_data['fungal_taxon_accepted_ids'].notna() & (study_data['fungal_taxon_accepted_ids'] != '')]),
    'unique_papers_with_fungi': len(df_links['paper_id'].unique()),
    'unique_fungi_accepted_ids': len(df_links['accepted_id'].unique()),
    'unique_fungi_species_matched_to_gbif': len(unique_studied),
    'total_known_fungi_species_gbif': total_fungi_species,
    'coverage_percent': 100 * len(unique_studied) / total_fungi_species if total_fungi_species > 0 else 0,
    'phyla_represented': len(df_phylum_coverage),
    'phyla_with_studies': sum(df_phylum_coverage['studied_species'] > 0),
}

# Create comparison
comparison = pd.DataFrame({
    'Metric': list(fungal_summary.keys()),
    'Fungi': list(fungal_summary.values()),
    'Plants': [plant_summary.get(k) for k in fungal_summary.keys()]
})

comparison.to_csv(OUTPUT_COMPARISON, index=False)
print(f"  Saved comparison to {OUTPUT_COMPARISON}")

# ==================== ANALYSIS 8: MYCORRHIZAL FILTERING ====================
print("Checking for mycorrhizal associations...")

# Flag records that might be mycorrhizal based on resolved name patterns
mycorrhizal_keywords = [
    'mycorrhiz', 'amf', 'arbuscular', 'ectomycorrhiz', 
    'endomycorrhiz', 'ery', 'glomerales', 'glomeromycota'
]

study_data['has_mycorrhizal_keyword'] = study_data['fungal_taxon_resolved'].fillna('').str.lower().apply(
    lambda x: any(keyword in x for keyword in mycorrhizal_keywords)
)

mycorrhizal_records = study_data[study_data['has_mycorrhizal_keyword']]
print(f"  Found {len(mycorrhizal_records)} records with mycorrhizal keywords")
print(f"  ({100*len(mycorrhizal_records)/len(study_data):.1f}% of all records)")

mycorrhizal_summary = mycorrhizal_records[['paper_id', 'fungal_taxon_resolved']].drop_duplicates()
if len(mycorrhizal_summary) > 0:
    mycorrhizal_summary.to_csv(OUTPUT_MYCORRHIZAL, index=False)
    print(f"  Saved {len(mycorrhizal_summary)} unique mycorrhizal associations")
else:
    print(f"  No mycorrhizal records found.")

# ==================== SUMMARY OUTPUT ====================
print("\n" + "="*70)
print("Fungal Taxonomic Bias Analysis Complete")
print("="*70)
print(f"Total papers analyzed: {len(study_data)}")
print(f"Papers with fungal records: {len(df_links['paper_id'].unique())}")
print(f"Unique fungal species studied: {len(unique_studied)}")
print(f"Unique fungal phyla represented: {len(df_phylum_coverage)}")
print(f"\nTop 3 most-studied fungal phyla:")
for idx, row in df_phylum_coverage.head(3).iterrows():
    print(f"  - {row['phylum']}: {row['studied_species']} species ({row['coverage_percent']:.1f}% coverage)")
print(f"\nTop 3 most-studied fungal genera:")
if len(top_genera) > 0:
    for idx, row in top_genera.head(3).iterrows():
        print(f"  - {row['genus']} ({row['phylum']}): {int(row['study_count'])} studies")
else:
    print(f"  (No fungal genera matched)")
print(f"\nOutput files:")
print(f"  - {OUTPUT_PHYLUM}")
print(f"  - {OUTPUT_GENUS}")
print(f"  - {OUTPUT_FAMILY}")
print(f"  - {OUTPUT_TOP_GENERA}")
print(f"  - {OUTPUT_COMPARISON}")
print(f"  - {OUTPUT_MYCORRHIZAL}")
print("="*70)
