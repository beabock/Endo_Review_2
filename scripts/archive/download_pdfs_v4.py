# BMB 2026-06-05
# Downloads PDFs from Monsoon scratch for full-text extraction. Cluster-only script.

import pandas as pd
import requests
import time
from pathlib import Path

# Configuration
CSV_PATH = "/scratch/bmb646/Abstracts_for_Monsoon.csv"
SAVE_DIR = Path("/scratch/bmb646/full_corpus")
EMAIL = "bmb646@nau.edu"  # REQUIRED for Unpaywall
SAVE_DIR.mkdir(parents=True, exist_ok=True)

def get_oa_pdf_link(doi):
    """Queries Unpaywall for the best Open Access PDF link."""
    url = f"https://api.unpaywall.org/v2/{doi}?email={EMAIL}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get('is_oa'):
                best_location = data.get('best_oa_location')
                if best_location:
                    return best_location.get('url_for_pdf')
    except Exception as e:
        print(f"   Error querying DOI {doi}: {e}")
    return None

def download_pdf(url, filename):
    """Downloads the PDF from the URL."""
    try:
        r = requests.get(url, timeout=20, stream=True)
        if r.status_code == 200:
            with open(SAVE_DIR / filename, 'wb') as f:
                f.write(r.content)
            return True
    except Exception as e:
        print(f"   Error downloading {url}: {e}")
    return False

def main():
    df = pd.read_csv(CSV_PATH)
    # Ensure DOIs are valid and drop empty ones
    dois = df['DOI'].dropna().unique()
    
    print(f"Found {len(dois)} unique DOIs. Starting download...")
    
    downloaded_count = 0
    missing_count = 0
    
    for i, doi in enumerate(dois):
        # Sanitize filename: replace / with _
        filename = f"{doi.replace('/', '_')}.pdf"
        
        # Skip if already exists
        if (SAVE_DIR / filename).exists():
            continue

        print(f"[{i+1}/{len(dois)}] Checking DOI: {doi}...")
        pdf_url = get_oa_pdf_link(doi)
        
        if pdf_url:
            if download_pdf(pdf_url, filename):
                print(f"   Downloaded: {filename}")
                downloaded_count += 1
            else:
                missing_count += 1
        else:
            print(f"   No OA PDF found for {doi}")
            missing_count += 1
        
        # Respect API etiquette (wait briefly)
        time.sleep(0.2)

    print(f"\nDone.")
    print(f"Downloaded: {downloaded_count}")
    print(f"Missing/No OA: {missing_count}")

if __name__ == "__main__":
    main()
