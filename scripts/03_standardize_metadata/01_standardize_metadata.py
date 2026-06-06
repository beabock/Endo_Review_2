#!/usr/bin/env python3
import argparse
import csv
import os
import re
import sys
import time
import pandas as pd
import itertools
from importlib import util
from pathlib import Path
from functools import lru_cache

COUNTRY_MAPPING_PATH = Path(__file__).resolve().parents[1] / 'utils' / 'country_mapping.py'
COUNTRY_MAPPING_SPEC = util.spec_from_file_location('country_mapping', COUNTRY_MAPPING_PATH)
if COUNTRY_MAPPING_SPEC is None or COUNTRY_MAPPING_SPEC.loader is None:
    raise ImportError(f'Could not load country mapping module: {COUNTRY_MAPPING_PATH}')

country_mapping = util.module_from_spec(COUNTRY_MAPPING_SPEC)
COUNTRY_MAPPING_SPEC.loader.exec_module(country_mapping)

extract_all_countries = country_mapping.extract_all_countries
extract_tissue_values = country_mapping.extract_tissue_values
extract_guild_values = country_mapping.extract_guild_values
extract_biome_values = country_mapping.extract_biome_values
ALIAS_TO_COUNTRY = country_mapping.ALIAS_TO_COUNTRY

DEFAULT_INPUT_FILE = 'data/Ollama_cleaned_synresolved.csv'
DEFAULT_OUTPUT_FILE = 'data/Ollama_cleaned_synresolved_standardized_final.csv'

# Aggressive NA detection for extraction noise and technical journal artifacts
NA_PHRASES = [
    'not specified', 'not provided', 'unknown', 'unkown', 'n/a', 
    'uncertain', 'vulnerability disclosure', 'hhs', 'empty',
    'not applicable', 'not_provided', 'not_specified', 'plant tissues',
    'aerial parts', 'not mentioned', 'not stated', 'not explicitly',
    'unspecified', 'terrestrial', 'not-provided', 'not provided in text',
    'text extract', 'brief message'
]

TISSUE_MAP = {
    'inner tissue': 'NA',
    'husk': 'seed',
    'aerial tissue': 'stem',
    'thallus': 'leaf',
    'gametophyte': 'leaf',
    'petiole': 'leaf',
    'healthy tissue': 'NA',
    'grape berries': 'fruit',
    'bulb': 'root',
    'corms': 'root',
    'root': 'root', 'rhizosphere': 'root', 'rhizome': 'root', 'tuber': 'root', 'nodule': 'root',
    'leaf': 'leaf', 'leaves': 'leaf', 'foliar': 'leaf', 'needle': 'leaf', 'foliage': 'leaf', 
    'phyllosphere': 'leaf', 'petiole': 'leaf', 'seaweed': 'leaf',
    'stem': 'stem', 'culm': 'stem', 'shoot': 'stem', 'wood': 'stem', 'bark': 'stem', 
    'twig': 'stem', 'branch': 'stem', 'trunk': 'stem', 'xylem': 'stem',
    'seed': 'seed', 'grain': 'seed', 'kernel': 'seed',
    'fruit': 'fruit', 'berry': 'fruit', 'flower': 'reproductive', 'reproductive': 'reproductive'
}

GUILD_MAP = {
    'plant growth promoting': 'pgpr',
    'endophytic': 'endophyte',
    'biological control': 'biocontrol',
    'pgpr': 'pgpr',
    'biological control agent': 'biocontrol',
    'nematophagous': 'biocontrol',
    'endophyte': 'endophyte', 'endophytic': 'endophyte',
    'pathogen': 'pathogen', 'pathogenic': 'pathogen', 'phytopathogen': 'pathogen',
    'mycorrhiza': 'mycorrhiza', 'mycorrhizal': 'mycorrhiza', 'ectomycorrhiza': 'mycorrhiza',
    'biocontrol': 'biocontrol', 'antagonist': 'biocontrol', 'antifungal': 'biocontrol',
    'pgpr': 'pgpr', 'growth-promoting': 'pgpr', 'growth promoting': 'pgpr',
    'saprotroph': 'saprotroph', 'decomposer': 'saprotroph', 'saprobic': 'saprotroph',
    'mutualist': 'mutualist', 'symbiotic': 'symbiotic', 'symbiont': 'symbiotic'
}

BIOME_MAP = {
    'xishuangbanna': 'forest',
    'citrus': 'agriculture',
    'botanical garden': 'agriculture',
    'nursery': 'agriculture',
    'ghats': 'mountain',
    'volcanic belt': 'mountain',
    'queensland': 'NA',
    'western ghats': 'mountain',
    'northeast-iran': 'desert',
    'tropics': 'tropical forest',
    'agricultural': 'agriculture', 'agriculture': 'agriculture', 'field': 'agriculture', 'orchard': 'agriculture', 
    'vineyard': 'agriculture', 'viticulture': 'agriculture', 'farmland': 'agriculture',
    'agroecosystem': 'agriculture', 'nursery': 'agriculture',
    'forest': 'forest', 'woodland': 'forest', 'rainforest': 'forest',
    'tropical': 'tropical forest', 'mangrove': 'mangrove',
    'marine': 'marine', 'ocean': 'marine', 'aquatic': 'marine', 'estuarine': 'marine',
    'grassland': 'grassland', 'prairie': 'grassland', 'pasture': 'grassland', 
    'mountain': 'mountain', 'alpine': 'mountain', 'desert': 'desert', 'arid': 'desert',
    'tundra': 'tundra', 'urban': 'urban', 'wetland': 'wetland', 'salt marsh': 'wetland',
    'savanna': 'savanna', 'cerrado': 'savanna', 'antarctic': 'antarctic', 'antarctica': 'antarctic'
}

# Use comprehensive country mapping from shared utility (replaces old minimal COUNTRY_MAP)
COUNTRY_MAP = ALIAS_TO_COUNTRY

DOC_TYPE_MAP = {
    'abstract': 'abstract',
    'full-text': 'full-text',
    'review': 'review',
    'article': 'full-text',
    'title': 'title'
}

GBIF_TAXON_TSV = os.path.join('data', 'Reference_datasets', 'gbif_backbone', 'Taxon.tsv')

DEFAULT_FUNGAL_PHYLUM_TERMS = {
    'ascomycota', 'basidiomycota', 'chytridiomycota', 'glomeromycota',
    'mucoromycota', 'mortierellomycota', 'blastocladiomycota',
    'neocallimastigomycota', 'microsporidia', 'kickxellomycota',
    'aphelidiomycota', 'zoopagomycota', 'entomophthoromycota',
    'olpidiomycota', 'rozellomycota'
}

DEFAULT_PLANT_PHYLUM_TERMS = {
    'tracheophyta', 'marchantiophyta', 'bryophyta', 'anthocerotophyta',
    'magnoliophyta', 'pinophyta', 'pteridophyta', 'lycophyta',
    'lycopodiophyta', 'chlorophyta', 'charophyta'
}

DEFAULT_FUNGAL_CLASS_TERMS = {
    'agaricomycetes', 'ascomycetes', 'basidiomycetes', 'dothideomycetes',
    'eurotiomycetes', 'exobasidiomycetes', 'glomeromycetes',
    'leotiomycetes', 'mucoromycetes', 'microbotryomycetes',
    'pezizomycetes', 'sordariomycetes', 'ustilaginomycetes'
}

DEFAULT_PLANT_CLASS_TERMS = {
    'magnoliopsida', 'liliopsida', 'bryopsida', 'marchantiopsida',
    'anthocerotopsida', 'lycopodiopsida', 'polypodiopsida', 'pinopsida',
    'ginkgoopsida', 'equisetopsida'
}


@lru_cache(maxsize=1)
def load_gbif_taxon_whitelists(taxon_tsv=GBIF_TAXON_TSV):
    """Load accepted GBIF fungal and plant phylum/class terms from Taxon.tsv."""
    fallback = {
        'fungal_phyla': frozenset(DEFAULT_FUNGAL_PHYLUM_TERMS),
        'plant_phyla': frozenset(DEFAULT_PLANT_PHYLUM_TERMS),
        'fungal_classes': frozenset(DEFAULT_FUNGAL_CLASS_TERMS),
        'plant_classes': frozenset(DEFAULT_PLANT_CLASS_TERMS),
    }

    if not os.path.exists(taxon_tsv):
        return fallback

    fungal_phyla = set()
    plant_phyla = set()
    fungal_classes = set()
    plant_classes = set()

    try:
        with open(taxon_tsv, 'r', encoding='utf-8', newline='') as handle:
            reader = csv.DictReader(handle, delimiter='\t')
            for row in reader:
                if standardize_value(row.get('taxonomicStatus', '')).lower() != 'accepted':
                    continue

                kingdom = standardize_value(row.get('kingdom', '')).lower()
                if kingdom not in {'fungi', 'plantae'}:
                    continue

                phylum = normalize_taxon_label(row.get('phylum', ''))
                class_name = normalize_taxon_label(row.get('class', ''))

                if kingdom == 'fungi':
                    if phylum:
                        fungal_phyla.add(phylum)
                    if class_name:
                        fungal_classes.add(class_name)
                else:
                    if phylum:
                        plant_phyla.add(phylum)
                    if class_name:
                        plant_classes.add(class_name)
    except (OSError, csv.Error):
        return fallback

    if not (fungal_phyla or plant_phyla or fungal_classes or plant_classes):
        return fallback

    return {
        'fungal_phyla': frozenset(fungal_phyla),
        'plant_phyla': frozenset(plant_phyla),
        'fungal_classes': frozenset(fungal_classes),
        'plant_classes': frozenset(plant_classes),
    }


def normalize_taxon_label(val):
    if not val:
        return ''

    text = clean_parentheticals(str(val)).lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text.strip("()_ .,;[]{}")


def detect_taxon_kingdom(val, field_name=''):
    """Return the most likely kingdom for a taxon label, if it can be inferred."""
    text = normalize_taxon_label(val)
    if not text or text in {'na', 'none', 'null', 'unknown', 'unresolved'}:
        return None

    field_lower = (field_name or '').lower()
    taxon_whitelists = load_gbif_taxon_whitelists()

    if field_lower.endswith('_phylum'):
        if text in taxon_whitelists['fungal_phyla'] or text.endswith('mycota'):
            return 'Fungi'
        if text in taxon_whitelists['plant_phyla'] or text.endswith('phyta'):
            return 'Plantae'

    if field_lower.endswith('_class'):
        if text in taxon_whitelists['fungal_classes'] or text.endswith('mycetes') or text.endswith('omycetes'):
            return 'Fungi'
        if text in taxon_whitelists['plant_classes'] or text.endswith('opsida'):
            return 'Plantae'

    if field_lower.endswith('_kingdom'):
        if text in {'fungi', 'fungal'}:
            return 'Fungi'
        if text in {'plantae', 'plant'}:
            return 'Plantae'

    return None


def recover_taxonomy_misplacements(row, headers):
    """Create a corrected copy when fungal/plant taxon values are clearly swapped.

    The original row is preserved. A second row is emitted only when a value
    can be confidently moved from the fungal side to the plant side or vice
    versa based on phylum/class kingdom cues.
    """
    col_indices = {name: idx for idx, name in enumerate(headers)}
    corrected_row = row[:]
    changed = False

    field_pairs = [
        ('fungal_taxon_kingdom', 'plant_host_kingdom'),
        ('fungal_taxon_phylum', 'plant_host_phylum'),
        ('fungal_taxon_class', 'plant_host_class'),
    ]

    for fungal_col, plant_col in field_pairs:
        if fungal_col not in col_indices or plant_col not in col_indices:
            continue

        fungal_idx = col_indices[fungal_col]
        plant_idx = col_indices[plant_col]
        fungal_val = row[fungal_idx] if fungal_idx < len(row) else ''
        plant_val = row[plant_idx] if plant_idx < len(row) else ''

        fungal_kingdom = detect_taxon_kingdom(fungal_val, fungal_col)
        plant_kingdom = detect_taxon_kingdom(plant_val, plant_col)

        # Strong signal: values clearly belong on opposite sides.
        if fungal_kingdom == 'Plantae' and plant_kingdom == 'Fungi':
            corrected_row[fungal_idx] = plant_val
            corrected_row[plant_idx] = fungal_val
            changed = True
            continue

        # We only move one-sided values when the opposite side is blank/unknown.
        if fungal_kingdom == 'Plantae' and plant_kingdom is None:
            corrected_row[fungal_idx] = 'NA'
            corrected_row[plant_idx] = fungal_val
            changed = True
            continue

        if plant_kingdom == 'Fungi' and fungal_kingdom is None:
            corrected_row[plant_idx] = 'NA'
            corrected_row[fungal_idx] = plant_val
            changed = True

    return [row, corrected_row] if changed else [row]


def expand_taxonomy_recovery_rows(rows, headers):
    """Expand rows to preserve original records and add corrected taxonomy copies."""
    expanded_rows = []

    for row in rows:
        expanded_rows.extend(recover_taxonomy_misplacements(row, headers))

    return expanded_rows

def expand_multi_value_rows(rows, headers):
    """
    Expand rows when multiple unique values detected across columns.
    Handles: country, tissue, primary_guild, biome.
    
    Creates separate rows for each unique value found (handles displaced values from LLM).
    Example: Paper with Canada in country column + Mexico in plant_host -> 2 rows
             Paper with leaf in tissue + stem in interaction_notes -> 2 rows
    
    Args:
        rows: list of row lists
        headers: list of column headers
    
    Returns:
        Expanded list of rows with duplicates for multi-value papers
    """
    print(f"  [expand_multi_value_rows] Starting with {len(rows)} rows", flush=True)
    expanded_rows = []
    col_indices = {name: idx for idx, name in enumerate(headers)}
    
    # Define extraction functions for each target column
    target_cols = {
        'country': (col_indices.get('country'), extract_all_countries),
        'tissue': (col_indices.get('tissue'), extract_tissue_values),
        'primary_guild': (col_indices.get('primary_guild'), extract_guild_values),
        'biome': (col_indices.get('biome'), extract_biome_values),
    }
    
    max_expansion = 0
    expansion_count = 0
    heavy_expansions = []  # Track rows that expand significantly
    
    for i, row in enumerate(rows):
        if i % 5000 == 0:
            print(f"    Processing row {i}/{len(rows)} (expanded to {len(expanded_rows)} so far)", flush=True)
        
        # Extract all possible values for each target column from all source columns
        all_extractions = {}
        expansion_needed = False
        
        for col_name, (col_idx, extract_func) in target_cols.items():
            if col_idx is None:
                continue  # Column doesn't exist in this dataset
                
            values = extract_func(row, headers)
            if values:
                # Get unique values (first element of tuple is the value)
                unique_vals = list(dict.fromkeys([val for val, _ in values]))
                all_extractions[col_idx] = unique_vals
                if len(unique_vals) > 1:
                    expansion_needed = True
        
        if not expansion_needed:
            # No expansion needed, just apply any extracted values
            for col_idx, values in all_extractions.items():
                if values:
                    row[col_idx] = values[0]
            expanded_rows.append(row)
        else:
            # Need to expand: build all combinations of multi-valued fields
            multi_cols = {idx: vals for idx, vals in all_extractions.items() if len(vals) > 1}
            single_vals = {idx: vals[0] for idx, vals in all_extractions.items() if len(vals) == 1}
            
            if multi_cols:
                # Generate all combinations using itertools.product
                col_idxs = list(multi_cols.keys())
                col_val_lists = [multi_cols[idx] for idx in col_idxs]
                
                # Calculate expansion factor
                expansion_factor = 1
                for vals in col_val_lists:
                    expansion_factor *= len(vals)
                
                if expansion_factor > max_expansion:
                    max_expansion = expansion_factor
                
                if expansion_factor > 10:
                    heavy_expansions.append({
                        'row_idx': i,
                        'expansion_factor': expansion_factor,
                        'multi_cols': {col_idxs[j]: len(col_val_lists[j]) for j in range(len(col_idxs))}
                    })
                
                expansion_count += expansion_factor
                
                for value_combo in itertools.product(*col_val_lists):
                    row_copy = row[:]
                    for col_idx, val in zip(col_idxs, value_combo):
                        row_copy[col_idx] = val
                    # Apply single extracted values
                    for col_idx, val in single_vals.items():
                        row_copy[col_idx] = val
                    expanded_rows.append(row_copy)
            else:
                expanded_rows.append(row)
    
    print(f"  [expand_multi_value_rows] Completed:", flush=True)
    print(f"    Input rows: {len(rows)}", flush=True)
    print(f"    Output rows: {len(expanded_rows)}", flush=True)
    print(f"    Total expansions: {expansion_count}", flush=True)
    print(f"    Max single-row expansion: {max_expansion}x", flush=True)
    if heavy_expansions:
        print(f"    Rows with 10+ expansions: {len(heavy_expansions)}", flush=True)
        for exp in heavy_expansions[:5]:  # Show first 5
            print(f"      Row {exp['row_idx']}: {exp['expansion_factor']}x - {exp['multi_cols']}", flush=True)
    
    return expanded_rows



def clean_parentheticals(val):
    """Removes parentheticals like 'endophytic (diplodia allocellula)' to leave just 'endophytic'."""
    return re.sub(r'\(.*?\)', '', val).strip()


def standardize_value(val, mapping=None, match_mode='substring'):
    if not val:
        return 'NA'
    
    # 1. Strip technical parentheticals first
    val = clean_parentheticals(val)
    
    clean_val = val.lower().strip().strip('()_ ')
    
    # 2. Broad substring check for NA phrases
    if any(phrase in clean_val for phrase in NA_PHRASES):
        return 'NA'
    
    if mapping:
        # 3. Exact match first to avoid substring collisions
        if clean_val in mapping:
            return mapping[clean_val]

        # 4. Keyword check (e.g., "twigs" matches "twig" in TISSUE_MAP)
        keys = sorted(mapping.keys(), key=len, reverse=True)
        for key in keys:
            if match_mode == 'word':
                if re.search(rf"(?<!\w){re.escape(key)}(?!\w)", clean_val):
                    return mapping[key]
            else:
                if key in clean_val:
                    return mapping[key]
    
    # 5. Final safety for short strings
    if len(clean_val) < 2 or clean_val in ['na', 'none']:
        return 'NA'
        
    return clean_val

def run_standardization(input_file=DEFAULT_INPUT_FILE, output_file=DEFAULT_OUTPUT_FILE):
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting standardization...", flush=True)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Input file: {input_file}", flush=True)
    
    step_start = time.time()
    with open(input_file, 'r', encoding='utf-8') as f_in:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Opened file, reading headers...", flush=True)
        reader = csv.reader(f_in)
        headers = next(reader)
        h_idx = {name: i for i, name in enumerate(headers)}
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Headers: {len(headers)} columns", flush=True)
        
        # Load all rows first (needed for multi-country expansion)
        all_rows = []
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Processing {input_file}...", flush=True)
        
        for row_num, row in enumerate(reader):
            if row_num % 5000 == 0:
                elapsed = time.time() - step_start
                rate = row_num / elapsed if elapsed > 0 else 0
                print(f"  Row {row_num:6d} (elapsed: {elapsed:.1f}s, rate: {rate:.0f} rows/sec)", flush=True)
                
            if 'tissue' in h_idx:
                row[h_idx['tissue']] = standardize_value(row[h_idx['tissue']], TISSUE_MAP)
            if 'primary_guild' in h_idx:
                row[h_idx['primary_guild']] = standardize_value(row[h_idx['primary_guild']], GUILD_MAP)
            if 'biome' in h_idx:
                row[h_idx['biome']] = standardize_value(
                    row[h_idx['biome']], BIOME_MAP, match_mode='word'
                )
            if 'country' in h_idx:
                row[h_idx['country']] = standardize_value(
                    row[h_idx['country']], COUNTRY_MAP, match_mode='word'
                )
            if 'doc_type_ai' in h_idx:
                row[h_idx['doc_type_ai']] = standardize_value(row[h_idx['doc_type_ai']], DOC_TYPE_MAP)

            # Taxonomy cleaning: Force literal "EMPTY" or artifacts to "NA"
            tax_cols = ['fungal_taxon_phylum', 'fungal_taxon_class', 'plant_host_phylum', 'plant_host_class']
            for col in tax_cols:
                if col in h_idx:
                    row[h_idx[col]] = standardize_value(row[h_idx[col]])
            
            all_rows.append(row)
        
        read_time = time.time() - step_start
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Loaded {len(all_rows)} rows in {read_time:.1f}s", flush=True)
        
        # First recover clear fungal/plant taxonomy swaps, then expand multi-value fields.
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Recovering taxonomy misplacements...", flush=True)
        tax_start = time.time()
        taxonomy_recovered_rows = expand_taxonomy_recovery_rows(all_rows, headers)
        tax_time = time.time() - tax_start
        taxonomy_rows_added = len(taxonomy_recovered_rows) - len(all_rows)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Taxonomy recovery added {taxonomy_rows_added} rows in {tax_time:.1f}s", flush=True)

        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Expanding multi-value rows...", flush=True)
        expand_start = time.time()
        expanded_rows = expand_multi_value_rows(taxonomy_recovered_rows, headers)
        expand_time = time.time() - expand_start
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Multi-value expansion completed in {expand_time:.1f}s", flush=True)
        
        # Write all rows (including expanded ones)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Writing {len(expanded_rows)} rows to {output_file}...", flush=True)
        write_start = time.time()
        with open(output_file, 'w', encoding='utf-8') as f_out:
            writer = csv.writer(f_out, quoting=csv.QUOTE_ALL)
            writer.writerow(headers)
            writer.writerows(expanded_rows)
        write_time = time.time() - write_start
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Write completed in {write_time:.1f}s", flush=True)
    
    total_time = time.time() - step_start
    original_count = len(all_rows)
    taxonomy_count = len(taxonomy_recovered_rows)
    expanded_count = len(expanded_rows)
    new_rows_added = expanded_count - original_count
    
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Standardization complete in {total_time:.1f}s:", flush=True)
    print(f"  Original rows: {original_count}", flush=True)
    print(f"  Rows after taxonomy recovery: {taxonomy_count} (+{taxonomy_rows_added})", flush=True)
    print(f"  Expanded rows: {expanded_count}", flush=True)
    print(f"  New rows added (multi-value expansion): {new_rows_added}", flush=True)
    print(f"  Saved to: {output_file}", flush=True)
    print(f"  Values searched: country, tissue, primary_guild, biome, taxonomy recovery", flush=True)



def build_parser():
    parser = argparse.ArgumentParser(description='Standardize metadata fields after taxonomy resolution.')
    parser.add_argument('--input-file', default=DEFAULT_INPUT_FILE, help='Input CSV path')
    parser.add_argument('--output-file', default=DEFAULT_OUTPUT_FILE, help='Output CSV path')
    return parser

if __name__ == "__main__":
    args = build_parser().parse_args()
    run_standardization(input_file=args.input_file, output_file=args.output_file)