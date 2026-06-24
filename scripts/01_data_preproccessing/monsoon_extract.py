# BMB 2026-06-05
# Runs Ollama on abstracts/PDFs on the Monsoon HPC cluster to extract structured
# metadata (taxon names, tissue, country, etc.) from each paper. Cluster-only.

import os
import pandas as pd
import json
import ollama
import fitz  # PyMuPDF
import signal
from pathlib import Path

# --- CONFIGURATION ---
PDF_FOLDER = Path("/scratch/bmb646/Bea_Nick_papers_endoreview")
OUTPUT_FILE = "/scratch/bmb646/global_endo_extraction_v4.csv"
MODEL_NAME = "mistral"

def handler(signum, frame):
    raise Exception("Model Timeout")

def extract_content(pdf_path):
    content = {"text": "", "page_count": 0, "detected_type_heuristic": "Abstract"}
    try:
        with fitz.open(pdf_path) as doc:
            content["page_count"] = len(doc)
            if content["page_count"] > 2:
                content["detected_type_heuristic"] = "Full-Text"
            for page in doc[:12]:
                content["text"] += page.get_text()
    except Exception as e:
        print(f"   [!] Error reading PDF {pdf_path.name}: {e}")
        return None
    return content

def process_text(text, source_type="Full-Text"):
    if not text:
        return None
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(120)

    prompt = f"""
    You are an expert mycologist and data extractor.
    Task: Extract every unique plant-fungus interaction described in the text.

    RELEVANCE CRITERIA:
    - Include ANY fungus (endophyte, pathogen, symbiont, or biocontrol agent) detected in or on a plant host.
    - Include genomics/methods papers if they specify the host plant they are studying.

    EXTRACTION RULES:
    1. ONE-ROW-PER-INTERACTION: Create a separate JSON object for each unique Plant x Fungus pair.
    2. CONTEXT IS KEY: Use 'interaction_notes' to describe context (e.g., "Isolated from surface-sterilized roots").

    JSON STRUCTURE:
    {{
      "relevance": "Relevant",
      "doi": "string",
      "plant_host": "Full Latin Name",
      "fungal_taxon": "Full Latin Name",
      "tissue": "leaf, root, etc.",
      "presence_absence": "Present",
      "primary_guild": "Endophytic, Pathogenic, Mutualistic, Saprotrophic, Mycorrhizal, or Unknown",
      "interaction_notes": "Specific context",
      "biome": "string",
      "country": "string",
      "doc_type": "Full-Text or Abstract"
    }}

    TEXT TO ANALYZE:
    {text[:8000]}
    """

    try:
        response_data = ollama.generate(model=MODEL_NAME, prompt=prompt, format='json')
        signal.alarm(0)
        return json.loads(response_data.get('response', '{}'))
    except Exception as e:
        signal.alarm(0)
        print(f"   [!] Error: {e}")
        return None

def main():
    cols = ['relevance', 'doc_type_ai', 'doc_type_pages', 'page_count', 'doi', 'plant_host', 'fungal_taxon',
            'tissue', 'presence_absence', 'primary_guild', 'interaction_notes', 'biome', 'country', 'data_source', 'source_file']

    if os.path.exists(OUTPUT_FILE):
        existing_df = pd.read_csv(OUTPUT_FILE)
        all_results = existing_df.to_dict('records')
        processed_files = set(existing_df['source_file'].dropna().unique())
        print(f"Resuming with {len(all_results)} records.")
    else:
        all_results = []
        processed_files = set()

    pdf_files = list(PDF_FOLDER.glob("*.pdf"))

    for i, pdf_path in enumerate(pdf_files):
        if pdf_path.name in processed_files:
            continue

        print(f"[{i+1}/{len(pdf_files)}] Processing {pdf_path.name}...")
        content = extract_content(pdf_path)
        if not content or not content["text"]:
            all_results.append({'source_file': pdf_path.name, 'presence_absence': 'PDF Unreadable', 'data_source': 'None'})
            continue

        data = process_text(content["text"])
        
        if data:
            # --- FLATTENING LOGIC ---
            entries = []
            if isinstance(data, dict):
                # Check for the "Yuan et al." nested dictionary style
                has_nested = any(isinstance(v, dict) and ('fungal_taxon' in v or 'plant_host' in v) for v in data.values())
                if has_nested:
                    for k, v in data.items():
                        if isinstance(v, dict): entries.append(v)
                else:
                    entries = [data]
            else:
                entries = data if isinstance(data, list) else [data]

            found_valid_entry = False
            for entry in entries:
                if not isinstance(entry, dict): continue
                
                # Split comma-separated strings into individual rows (for "Crous et al." style)
                plants = str(entry.get('plant_host') or entry.get('taxon') or "Unknown").split(',')
                fungi = str(entry.get('fungal_taxon') or entry.get('species') or "Unknown").split(',')

                for p in plants:
                    for f in fungi:
                        p_clean = p.strip()
                        f_clean = f.strip()
                        if p_clean == "Unknown" and f_clean == "Unknown": continue

                        clean_entry = {
                            'relevance': entry.get('relevance', 'Relevant'),
                            'doc_type_ai': entry.get('doc_type', 'Unknown'),
                            'doc_type_pages': content['detected_type_heuristic'],
                            'page_count': content['page_count'],
                            'doi': entry.get('doi') or entry.get('DOI'),
                            'plant_host': p_clean,
                            'fungal_taxon': f_clean,
                            'tissue': entry.get('tissue'),
                            'presence_absence': entry.get('presence_absence') or 'Present',
                            'primary_guild': entry.get('primary_guild') or 'Unknown',
                            'interaction_notes': entry.get('interaction_notes'),
                            'biome': entry.get('biome'),
                            'country': entry.get('country'),
                            'data_source': 'Full-Text',
                            'source_file': pdf_path.name
                        }
                        all_results.append(clean_entry)
                        found_valid_entry = True

            if not found_valid_entry:
                all_results.append({
                    'relevance': 'Irrelevant',
                    'doc_type_pages': content['detected_type_heuristic'],
                    'page_count': content['page_count'],
                    'presence_absence': 'None Found',
                    'source_file': pdf_path.name,
                    'data_source': 'Full-Text'
                })
        else:
            all_results.append({'source_file': pdf_path.name, 'presence_absence': 'No Data/Error', 'data_source': 'Full-Text'})

        if (i + 1) % 5 == 0:
            pd.DataFrame(all_results).reindex(columns=cols).to_csv(OUTPUT_FILE, index=False)

    pd.DataFrame(all_results).reindex(columns=cols).to_csv(OUTPUT_FILE, index=False)

if __name__ == "__main__":
    main()
