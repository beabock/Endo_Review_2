#!/usr/bin/env python3
# BMB 2026-06-24
# Looks up missing publication years via CrossRef using DOIs.

import pandas as pd
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

# Use absolute paths or relative to project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = PROJECT_ROOT / "data" / "Ollama_cleaned_synresolved_standardized_final.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "Ollama_cleaned_synresolved_standardized_year.csv"
LOGS_DIR = PROJECT_ROOT / "results" / "logs"
CACHE_FILE = LOGS_DIR / "doi_year_cache.json"

LOGS_DIR.mkdir(parents=True, exist_ok=True)

def load_cache():
    if CACHE_FILE.exists():
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

def get_publication_year(doi, cache):
    if not doi or pd.isna(doi):
        return None
        
    doi = str(doi).strip()
    if doi in cache:
        return cache[doi]

    time.sleep(0.05) # Polite delay
    
    # Handle DOIs that might be full URLs
    if doi.startswith('http'):
        doi = doi.split('doi.org/')[-1]
    
    try:
        url = f"https://api.crossref.org/works/{doi}"
        # Placeholder email keeps this script in the CrossRef polite pool without
        # exposing the authors' address in a public repository.
        req = urllib.request.Request(url, headers={'User-Agent': 'EndophyteReview/1.0 (mailto:endo-research@example.com)'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        year = None
        # Try finding year in common fields
        msg = data.get('message', {})
        for field in ['published-print', 'published-online', 'created']:
            if field in msg and 'date-parts' in msg[field]:
                try:
                    year = msg[field]['date-parts'][0][0]
                    break
                except IndexError:
                    pass
                    
        if year:
            cache[doi] = int(year)
            return int(year)
            
    except urllib.error.HTTPError as e:
        if e.code == 404:
            cache[doi] = None
            return None
    except Exception as e:
        pass
    
    cache[doi] = None
    return None

def main():
    print(f"Loading data from {INPUT_FILE}...")
    try:
        df = pd.read_csv(INPUT_FILE, dtype={'doi': str})
    except FileNotFoundError:
        print(f"Error: Input file not found at {INPUT_FILE}")
        return

    if 'doi' not in df.columns:
        print("Error: 'doi' column not found in the input file.")
        return

    unique_dois = df['doi'].dropna().unique()
    print(f"Found {len(unique_dois)} unique DOIs to process.")

    doi_year_cache = load_cache()

    # Process DOIs
    print("Enriching with publication year from CrossRef...")
    
    # Simple progress tracking
    processed = 0
    total = len(unique_dois)
    for doi in unique_dois:
        if doi not in doi_year_cache:
            get_publication_year(doi, doi_year_cache)
            processed += 1
            if processed % 100 == 0:
                print(f"  Processed {processed}/{total} new DOIs...")
                save_cache(doi_year_cache)

    save_cache(doi_year_cache)
    print("Finished querying. Cache saved.")

    print("Mapping publication year to dataset...")
    # Clean up DOIs in the dataframe to match what we queried
    clean_dois = df['doi'].astype(str).str.strip().str.replace(r'^https?://(dx\.)?doi\.org/', '', regex=True)
    df['publication_year'] = clean_dois.map(doi_year_cache)

    years_found = df['publication_year'].notna().sum()
    total_rows = len(df)
    print(f"\nEnrichment complete. Found publication years for {years_found}/{total_rows} rows ({years_found/total_rows:.1%}).")

    print(f"Saving enriched data to {OUTPUT_FILE}...")
    df.to_csv(OUTPUT_FILE, index=False)
    print("Done.")

if __name__ == "__main__":
    main()