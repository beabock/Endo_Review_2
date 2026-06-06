import pandas as pd
import glob
import os

# Path to your individual chunks
path = "/scratch/bmb646/output_parts/endo_results_task_*.csv"
all_files = glob.glob(path)

li = []

print(f"Found {len(all_files)} files. Starting merge...")

for filename in all_files:
    try:
        # Read the CSV
        df = pd.read_csv(filename, index_col=None, header=0)
        
        # 1. Remove the JSON glitch rows (where the LLM leaked 'presence_absence' into the taxon)
        if 'fungal_taxon' in df.columns:
            initial_count = len(df)
            df = df[~df['fungal_taxon'].str.contains('presence_absence', na=False)]
            # Also catch the Unknowns or generic placeholders if they are messy
            df = df[df['fungal_taxon'] != "Unknown"]
        
        # 2. Drop any rows where the PDF was unreadable
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

print("-" * 30)
print(f"SUCCESS!")
print(f"Final interaction count: {len(final_df)}")
print(f"File saved to: {output_file}")
