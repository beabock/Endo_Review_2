#!/bin/bash
#SBATCH --job-name=endo_stage04_analyses
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=24G
#SBATCH --time=03:00:00
#SBATCH --output=results/logs/stage04_analyses_%j.out

set -euo pipefail

# Resolve project root robustly, regardless of where sbatch is launched from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# If launched from an explicit submit dir that looks like the project root, prefer it.
if [ -n "${SLURM_SUBMIT_DIR:-}" ] && [ -d "${SLURM_SUBMIT_DIR}/scripts/04_analyses" ]; then
    PROJECT_ROOT="${SLURM_SUBMIT_DIR}"
fi

cd "$PROJECT_ROOT"

mkdir -p results/logs
mkdir -p .rlibs/R/library

# Reuse shared GBIF backbone from parent checkout if local copy is missing.
LOCAL_GBIF_DIR="data/Reference_datasets/gbif_backbone"
PARENT_GBIF_DIR="../data/Reference_datasets/gbif_backbone"
mkdir -p "$(dirname "$LOCAL_GBIF_DIR")"
if [ -L "$LOCAL_GBIF_DIR" ]; then
    echo "GBIF symlink already exists: $LOCAL_GBIF_DIR -> $(readlink "$LOCAL_GBIF_DIR")"
elif [ -d "$LOCAL_GBIF_DIR" ]; then
    echo "GBIF directory already exists at $LOCAL_GBIF_DIR; skipping symlink creation"
elif [ -d "$PARENT_GBIF_DIR" ]; then
    ln -s "$PARENT_GBIF_DIR" "$LOCAL_GBIF_DIR" && echo "Linked $LOCAL_GBIF_DIR -> $PARENT_GBIF_DIR" || echo "Warning: failed to create symlink $LOCAL_GBIF_DIR"
else
    echo "GBIF backbone not found in parent path: $PARENT_GBIF_DIR; continuing without symlink"
fi

# Default START_STEP for Stage 04 is step 1 unless overridden.
if [ -z "${START_STEP:-}" ]; then
    START_STEP=1
fi

module purge
module load R/4.5.2

# Prefer project virtual environment.
if [ -x ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
elif [ -x ".venv/Scripts/python.exe" ]; then
    PYTHON_BIN=".venv/Scripts/python.exe"
else
    module load python/3.11
    python -m venv .venv
    PYTHON_BIN=".venv/bin/python"
fi

# Python deps
if ! "$PYTHON_BIN" -c "import pandas" >/dev/null 2>&1; then
    "$PYTHON_BIN" -m pip install --upgrade pip pandas
fi

export R_LIBS_USER="$PROJECT_ROOT/.rlibs/R/library"

echo "--- Environment Preflight (Stage 04) ---"
"$PYTHON_BIN" - <<'PY'
import sys
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version.split()[0]}")
try:
    import pandas  # noqa: F401
    print("Python dependency check: pandas OK")
except Exception as exc:
    raise SystemExit(f"Python dependency check failed (pandas): {exc}")
PY

Rscript -e "cat('R version:', as.character(getRversion()), '\n')"
Rscript -e "if (!requireNamespace('dplyr', quietly=TRUE)) stop('Missing R package: dplyr')"
Rscript -e "if (!requireNamespace('readr', quietly=TRUE)) stop('Missing R package: readr')"
Rscript -e "if (!requireNamespace('tidyr', quietly=TRUE)) stop('Missing R package: tidyr')"
Rscript -e "if (!requireNamespace('stringr', quietly=TRUE)) stop('Missing R package: stringr')"
Rscript -e "if (!requireNamespace('ggplot2', quietly=TRUE)) stop('Missing R package: ggplot2')"
Rscript -e "if (!requireNamespace('forcats', quietly=TRUE)) stop('Missing R package: forcats')"
Rscript -e "if (!requireNamespace('scales', quietly=TRUE)) stop('Missing R package: scales')"
Rscript -e "dir.create(Sys.getenv('R_LIBS_USER'), recursive=TRUE, showWarnings=FALSE); if (!requireNamespace('sf', quietly=TRUE)) { install.packages('sf', lib=Sys.getenv('R_LIBS_USER'), repos='https://cloud.r-project.org'); if (!requireNamespace('sf', quietly=TRUE)) stop('Missing R package: sf (and automatic install failed)') }"
Rscript -e "dir.create(Sys.getenv('R_LIBS_USER'), recursive=TRUE, showWarnings=FALSE); if (!requireNamespace('rnaturalearth', quietly=TRUE)) { install.packages('rnaturalearth', lib=Sys.getenv('R_LIBS_USER'), repos='https://cloud.r-project.org') }"
Rscript -e "dir.create(Sys.getenv('R_LIBS_USER'), recursive=TRUE, showWarnings=FALSE); if (!requireNamespace('rnaturalearthdata', quietly=TRUE)) { install.packages('rnaturalearthdata', lib=Sys.getenv('R_LIBS_USER'), repos='https://cloud.r-project.org') }"

# Required inputs check
REQUIRED_FILES=(
    "data/Ollama_cleaned_synresolved_standardized_final.csv"
    "data/Ollama_cleaned_synresolved_filtered.csv"
    "data/country_enriched_data.csv"
)
for f in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$f" ]; then
        echo "ERROR: Required input not found: $f"
        echo "Run Stage 03 first (or sync required files) before Stage 04 analyses."
        exit 1
    fi
done

echo "--- Starting Stage 04 Analyses ---"
echo "Step 1: Geographic Bias Analysis"
if [ "$START_STEP" -le 1 ]; then
    Rscript scripts/04_analyses/01_country_gdp_latitude_analysis.R
else
    echo "Skipping Step 1 (START_STEP=${START_STEP})"
fi

echo "Step 2: Taxonomic Bias Analysis"
if [ "$START_STEP" -le 2 ]; then
    Rscript scripts/04_analyses/02_taxonomy.R
else
    echo "Skipping Step 2 (START_STEP=${START_STEP})"
fi

echo "Step 3: Fungal Taxonomic Bias"
if [ "$START_STEP" -le 3 ]; then
    "$PYTHON_BIN" scripts/04_analyses/03_fungal_taxonomic_bias.py
else
    echo "Skipping Step 3 (START_STEP=${START_STEP})"
fi

echo "Step 4: Interaction Bias Analysis"
if [ "$START_STEP" -le 4 ]; then
    Rscript scripts/04_analyses/04_interaction_bias.R
else
    echo "Skipping Step 4 (START_STEP=${START_STEP})"
fi

echo "Step 5: Manuscript Summary"
if [ "$START_STEP" -le 5 ]; then
    "$PYTHON_BIN" scripts/04_analyses/05_manuscript_summary.py
else
    echo "Skipping Step 5 (START_STEP=${START_STEP})"
fi

echo "Step 6: Identify Understudied Taxa & Countries"
if [ "$START_STEP" -le 6 ]; then
    Rscript scripts/04_analyses/03_identify_understudied_taxa.R
else
    echo "Skipping Step 6 (START_STEP=${START_STEP})"
fi

echo "Step 7: Crop Analyses"
if [ "$START_STEP" -le 7 ]; then
    Rscript scripts/04_analyses/crop_analyses.R
else
    echo "Skipping Step 7 (START_STEP=${START_STEP})"
fi

echo "Stage 04 complete. Check results/country_analysis, results/taxonomy_analysis, results/interaction_analysis, results/manuscript_dataset_summary.*, results/understudied_analysis, and results/crop_analysis"
