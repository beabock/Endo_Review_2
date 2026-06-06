#!/bin/bash
#SBATCH --job-name=endo_stage05_plotting
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=results/logs/stage05_plotting_%j.out

set -euo pipefail

# Resolve project root robustly
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Ensure log directory exists
mkdir -p results/logs

# Set up R environment
module purge
module load R/4.5.2
export R_LIBS_USER="$PROJECT_ROOT/.rlibs/R/library"

echo "--- Starting Stage 05: Plotting ---"

# Default to running all steps if START_STEP is not set
if [ -z "${START_STEP:-}" ]; then
    START_STEP=1
fi

echo "Step 1: Geographic Plots"
if [ "$START_STEP" -le 1 ]; then
    Rscript scripts/05_plotting/geographic_plotting.R
else
    echo "Skipping Step 1 (START_STEP=${START_STEP})"
fi

echo "Step 2: Taxonomy Representation Plots"
if [ "$START_STEP" -le 2 ]; then
    Rscript scripts/05_plotting/taxonomy_representation.R
else
    echo "Skipping Step 2 (START_STEP=${START_STEP})"
fi

echo "Step 3: Tissue Analysis Plots"
if [ "$START_STEP" -le 3 ]; then
    Rscript scripts/05_plotting/tissue_plots.R
else
    echo "Skipping Step 3 (START_STEP=${START_STEP})"
fi

echo "Step 4: Biome Analysis Plots"
if [ "$START_STEP" -le 4 ]; then
    Rscript scripts/05_plotting/biome_plots.R
else
    echo "Skipping Step 4 (START_STEP=${START_STEP})"
fi

echo "Step 5: Relationship Type Plots"
if [ "$START_STEP" -le 5 ]; then
    Rscript scripts/05_plotting/relationship_type_plots.R
else
    echo "Skipping Step 5 (START_STEP=${START_STEP})"
fi

echo "Step 6: Abstract vs Full-Text Comparison Plots"
if [ "$START_STEP" -le 6 ]; then
    Rscript scripts/05_plotting/abs_fulltext_comparison_plots.R
else
    echo "Skipping Step 6 (START_STEP=${START_STEP})"
fi

echo "--- Stage 05: Plotting complete ---"
