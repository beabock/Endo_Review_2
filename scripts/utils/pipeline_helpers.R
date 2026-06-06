# pipeline_helpers.R

# Define shared directory paths to ensure consistency across all analysis scripts.
# This avoids errors from typos or case-sensitivity issues on different filesystems.

RESULTS_DIR <- "results"
TAXONOMY_DIR <- file.path(RESULTS_DIR, "taxonomy_analysis")
CACHE_DIR <- file.path(TAXONOMY_DIR, "cache")

# Helper function to read cached objects, with fallback from qs to rds.
cache_read_object <- function(qs_path, rds_path) {
  if (file.exists(qs_path)) {
    if (requireNamespace("qs", quietly = TRUE)) {
      cat("Reading from qs cache:", qs_path, "\n")
      return(qs::qread(qs_path))
    } else {
      cat("qs package not available, falling back to RDS for reading.\n")
    }
  }
  if (file.exists(rds_path)) {
    cat("Reading from RDS cache:", rds_path, "\n")
    return(readRDS(rds_path))
  }
  stop("Neither qs nor RDS cache file found. Please ensure '02_taxonomy.R' has been run successfully.")
}
