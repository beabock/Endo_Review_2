# BMB 2026-06-05
# Merges per-task Ollama extraction output chunks from Monsoon into a single CSV.

import pandas as pd
import glob

path = "/scratch/bmb646/output_parts/endo_results_task_*.csv"
all_files = glob.glob(path)

li = []

print(f"Found {len(all_files)} files. Starting merge...")

for filename in all_files:
    try:
        # Read the CSV
        df = pd.read_csv(filename, index_col=None, header=0)
        
        # Drop rows where the Ollama extraction leaked column names into the taxon field
        if 'fungal_taxon' in df.columns:
            df = df[~df['fungal_taxon'].str.contains('presence_absence', na=False)]
            df = df[df['fungal_taxon'] != "Unknown"]

        # Drop any rows where the PDF was unreadable
        if 'presence_absence' in df.columns:
            df = df[df['presence_absence'] != 'PDF Unreadable']
            
        li.append(df)
    except Exception as e:
        print(f"Error processing {filename}: {e}")

# Combine everything
final_df = pd.concat(li, axis=0, ignore_index=True)

# Save the final product
output_file = "/scratch/bmb646/GLOBAL_ENDOPHYTE_DATABASE_2026.csv"
final_df.to_csv(output_file, index=False)

print(f"Done. {len(final_df)} interactions saved to: {output_file}")
