import re
import csv
import sys

input_file = "data/Ollama_extraction_all.csv"
output_file = "data/Ollama_python_healed.csv"

# The exact 15 columns we need to lock in
HEADERS = [
    "relevance", "doc_type_ai", "doc_type_pages", "page_count", "doi", 
    "plant_host", "fungal_taxon", "tissue", "presence_absence", 
    "primary_guild", "interaction_notes", "biome", "country", 
    "data_source", "source_file"
]

ROW_START_PATTERN = re.compile(r"^(relev|irrelev|not|uncertain)", re.IGNORECASE)


def sanitize_line(line: str):
    # Drop backslashes to avoid JSON escape artifacts in CSV parsing.
    sanitized = line.replace("\\", "")
    # If quotes are unbalanced, remove them to avoid CSV parser issues.
    has_unbalanced_quotes = sanitized.count('"') % 2 == 1
    if has_unbalanced_quotes:
        sanitized = sanitized.replace('"', '')
    return sanitized, has_unbalanced_quotes


def assemble_rows(lines):
    data_lines = []
    merged_line_count = 0
    buffer = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        is_new_row = bool(ROW_START_PATTERN.match(stripped))
        if buffer and is_new_row:
            data_lines.append(buffer)
            buffer = stripped
        else:
            if buffer:
                merged_line_count += 1
                buffer = f"{buffer} {stripped}".strip()
            else:
                buffer = stripped

    if buffer:
        data_lines.append(buffer)

    return data_lines, merged_line_count

def heal_and_align():
    print(f"Reading raw data from {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
        raw_text = f.read()

    lines = raw_text.split('\n')
    data_lines, merged_line_count = assemble_rows(lines[1:])
    raw_line_count = len([line for line in lines[1:] if line.strip()])
    
    clean_rows = []
    
    print("Aligning drifting columns...")
    doi_anchor_hits = 0
    doi_anchor_misses = 0
    missing_data_source = 0
    missing_source_file = 0
    middle_exact = 0
    middle_overflow = 0
    middle_short = 0
    overflow_extra_parts = 0
    rows_gt_15_parts = 0
    unbalanced_quote_lines = 0
    for line in data_lines:
        sanitized, had_unbalanced_quotes = sanitize_line(line)
        if had_unbalanced_quotes:
            unbalanced_quote_lines += 1
        parts = [p.strip() for p in sanitized.split(',')]
        if len(parts) > 15:
            rows_gt_15_parts += 1
        
        # Initialize an empty 15-slot row
        row = ["NA"] * 15
        
        # --- LEFT ANCHORS (Cols 0 to 4) ---
        # We know Relevance and Doc Types are at the start. 
        # We look for the DOI to anchor column 4.
        doi_index = -1
        for i, part in enumerate(parts[:8]): # DOI should be in the first few cols
            if part.startswith("10."):
                doi_index = i
                break
                
        if doi_index != -1:
            doi_anchor_hits += 1
            # Safely map whatever came before the DOI
            for i in range(min(doi_index, 4)):
                row[i] = parts[i]
            row[4] = parts[doi_index] # Lock DOI
            parts = parts[doi_index+1:] # Remaining parts
        else:
            doi_anchor_misses += 1
            # If no DOI found, just dump the first 5 parts
            for i in range(min(len(parts), 5)):
                row[i] = parts[i]
            parts = parts[5:] if len(parts) > 5 else []

        # --- RIGHT ANCHORS (Cols 13 & 14) ---
        # The last columns are always data_source (e.g. abstract-csv) and source_file (e.g. doi_...)
        if len(parts) >= 2:
            row[14] = parts[-1]
            row[13] = parts[-2]
            parts = parts[:-2]
        elif len(parts) == 1:
            row[14] = parts[-1]
            parts = []

        # --- MIDDLE MESS (Cols 5 to 12) ---
        # We now have the remaining parts that belong in Host, Taxon, Tissue, etc.
        # If there are exactly 8 parts left, perfect! 1-to-1 mapping.
        if len(parts) == 8:
            middle_exact += 1
            for i in range(8):
                row[5+i] = parts[i]
        
        # If there are MORE than 8 parts, the AI hallucinated commas.
        # We glue the "extra" parts into the interaction_notes (Col 10)
        elif len(parts) > 8:
            middle_overflow += 1
            overflow_extra_parts += len(parts) - 8
            row[5] = parts[0] # Host
            row[6] = parts[1] # Taxon
            row[7] = parts[2] # Tissue
            row[8] = parts[3] # Presence/Absence
            row[9] = parts[4] # Guild
            
            # The "overflow" goes into Interaction Notes
            overflow_count = len(parts) - 8
            notes_end = 5 + overflow_count
            row[10] = "; ".join(parts[5:notes_end+1])
            
            # The last 2 parts go to Biome and Country
            row[11] = parts[-2]
            row[12] = parts[-1]
            
        # If there are FEWER than 8 parts, the AI skipped columns. 
        # Just map them left-to-right until we run out.
        else:
            middle_short += 1
            for i in range(len(parts)):
                row[5+i] = parts[i]

        if row[13] == "NA":
            missing_data_source += 1
        if row[14] == "NA":
            missing_source_file += 1

        clean_rows.append(row)

    # Write the beautifully aligned data to a new CSV using Python's native CSV writer
    # This automatically adds quotes around fields ONLY when necessary.
    print(f"Writing {len(clean_rows)} aligned rows to {output_file}...")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)
        writer.writerows(clean_rows)
        
    print("Done! The dataset is structurally perfect.")
    print("Repair report:")
    print(f"  Raw lines (non-empty): {raw_line_count}")
    print(f"  Assembled rows: {len(data_lines)}")
    print(f"  Lines merged into previous rows: {merged_line_count}")
    print(f"  Rows with unbalanced quotes fixed: {unbalanced_quote_lines}")
    print(f"  DOI anchor hits: {doi_anchor_hits} | misses: {doi_anchor_misses}")
    print(f"  Missing data_source: {missing_data_source} | missing source_file: {missing_source_file}")
    print(f"  Rows with >15 raw parts: {rows_gt_15_parts}")
    print(
        f"  Middle columns: exact={middle_exact} overflow={middle_overflow} short={middle_short}"
    )
    print(f"  Extra overflow parts merged into notes: {overflow_extra_parts}")

if __name__ == "__main__":
    heal_and_align()