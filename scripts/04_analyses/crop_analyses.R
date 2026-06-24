# BMB 2026-06-05
# Quantifies the bias toward crop families (Poaceae, Fabaceae, Solanaceae) and
# key fungal genera (Fusarium, Aspergillus, Epichloe) in the dataset.

library(dplyr)
library(readr)
library(stringr)
library(tidyr)
library(scales)

source("scripts/utils/pipeline_helpers.R")

INPUT_FILE <- "data/Ollama_cleaned_synresolved_standardized_final.csv"
GBIF_REF_RDS <- file.path(CACHE_DIR, "gbif_reference_species.rds")
GBIF_REF_QS <- file.path(CACHE_DIR, "gbif_reference_species.qs")
OUTPUT_DIR <- "results/crop_analysis"

if (!dir.exists(OUTPUT_DIR)) {
  dir.create(OUTPUT_DIR, recursive = TRUE, showWarnings = FALSE)
}

# Major crop genera/families based on top global agricultural commodities
MAJOR_CROP_FAMILIES <- c("Poaceae", "Fabaceae", "Solanaceae")

# We include common crops, forage, and models that dominate agricultural research
MAJOR_CROP_GENERA <- c(
  "Triticum", "Zea", "Oryza", "Hordeum", "Saccharum", "Sorghum", "Avena", "Secale", # Poaceae staples
  "Glycine", "Phaseolus", "Arachis", "Medicago", "Trifolium", "Vigna", "Cicer", "Lens", "Pisum", # Fabaceae staples
  "Solanum", "Nicotiana", "Capsicum", # Solanaceae
  "Vitis", "Malus", "Cucumis", "Gossypium", "Brassica", "Allium", "Citrus", "Coffea", "Musa", 
  "Daucus", "Fragaria", "Camellia", "Lolium", "Festuca", "Beta", "Ipomoea", "Manihot", 
  "Dioscorea", "Colocasia", "Sesamum", "Linum", "Carthamus", "Elaeis", "Cocos", "Olea", 
  "Prunus", "Pyrus", "Rubus", "Vaccinium", "Ribes", "Actinidia", "Ananas", "Carica", 
  "Mangifera", "Persea", "Ficus", "Punica", "Juglans", "Carya", "Pistacia", "Corylus", 
  "Castanea", "Macadamia", "Theobroma", "Hevea"
)

message("Loading study-level host data...")
df <- read_csv(INPUT_FILE, show_col_types = FALSE) %>%
  filter(
    relevance == "Relevant",
    doc_type_ai_clean %in% c("Abstract", "Full Text")
  )

message("Loading GBIF cache...")
gbif_taxa_min <- cache_read_object(GBIF_REF_QS, GBIF_REF_RDS)

# Expand multiple accepted_ids in the plant host column
df_expanded <- df %>%
  mutate(accepted_id = str_split(plant_host_accepted_ids, "\\|")) %>%
  unnest(accepted_id) %>%
  filter(!is.na(accepted_id), accepted_id != "") %>%
  mutate(accepted_id = as.character(accepted_id))

# Join with GBIF taxonomy to get family and genus
study_species <- df_expanded %>%
  left_join(
    gbif_taxa_min,
    by = c("accepted_id" = "taxonID")
  )

# Calculate total unique papers with a resolved plant host
total_papers <- n_distinct(study_species$paper_id)

message("Total papers with resolved plant host: ", total_papers)

# 1. Percent of studies focusing on Poaceae
poaceae_studies <- study_species %>%
  filter(family == "Poaceae") %>%
  distinct(paper_id) %>%
  nrow()

poaceae_pct <- (poaceae_studies / total_papers) * 100
message("Poaceae studies: ", poaceae_studies, " (", round(poaceae_pct, 2), "%)")

# 2. Percent of studies focusing on any major crop family
major_family_studies <- study_species %>%
  filter(family %in% MAJOR_CROP_FAMILIES) %>%
  distinct(paper_id) %>%
  nrow()

major_family_pct <- (major_family_studies / total_papers) * 100
message("Major crop family studies (Poaceae, Fabaceae, Solanaceae): ", major_family_studies, " (", round(major_family_pct, 2), "%)")

# 3. Percent of studies focusing on major crop/agricultural genera
crop_genera_studies <- study_species %>%
  filter(genus %in% MAJOR_CROP_GENERA) %>%
  distinct(paper_id) %>%
  nrow()

crop_genera_pct <- (crop_genera_studies / total_papers) * 100
message("Major crop/agricultural genera studies: ", crop_genera_studies, " (", round(crop_genera_pct, 2), "%)")

# Detailed summary by top families
family_summary <- study_species %>%
  distinct(paper_id, family) %>%
  filter(!is.na(family), family != "") %>%
  count(family, name = "study_count", sort = TRUE) %>%
  mutate(percent_of_studies = (study_count / total_papers) * 100)

# Detailed summary by top genera
genus_summary <- study_species %>%
  distinct(paper_id, genus, family) %>%
  filter(!is.na(genus), genus != "") %>%
  count(genus, family, name = "study_count", sort = TRUE) %>%
  mutate(
    percent_of_studies = (study_count / total_papers) * 100,
    is_major_crop_genus = genus %in% MAJOR_CROP_GENERA
  )

write_csv(family_summary, file.path(OUTPUT_DIR, "host_family_summary.csv"))
write_csv(genus_summary, file.path(OUTPUT_DIR, "host_genus_summary.csv"))

# Overall stats summary
overall_stats <- tibble(
  metric = c(
    "Total papers with resolved plant host",
    "Papers studying Poaceae",
    "Percent studying Poaceae",
    "Papers studying major crop families (Poaceae, Fabaceae, Solanaceae)",
    "Percent studying major crop families",
    "Papers studying major crop/ag genera",
    "Percent studying major crop/ag genera"
  ),
  value = c(
    total_papers,
    poaceae_studies,
    poaceae_pct,
    major_family_studies,
    major_family_pct,
    crop_genera_studies,
    crop_genera_pct
  )
)

# FUNGAL TAXONOMY ANALYSIS
message("Analyzing fungal genera...")

FUNGAL_GENERA_FILE <- "results/taxonomy_analysis/top_studied_fungal_genera.csv"

# Calculate total papers with ANY resolved fungal host
total_fungal_papers <- df %>%
  filter(!is.na(fungal_taxon_accepted_ids), fungal_taxon_accepted_ids != "") %>%
  distinct(paper_id) %>%
  nrow()

message("Total papers with resolved fungal host: ", total_fungal_papers)

if (file.exists(FUNGAL_GENERA_FILE)) {
  fungal_genera <- read_csv(FUNGAL_GENERA_FILE, show_col_types = FALSE)
  
  # The Python script calculates study_count per genus. Let's add percentages
  # relative to the total number of papers with a resolved fungal host.
  fungal_genera <- fungal_genera %>%
    mutate(percent_of_fungal_studies = (study_count / total_fungal_papers) * 100)
    
  write_csv(fungal_genera, file.path(OUTPUT_DIR, "fungal_genus_summary.csv"))
  
  # Highlight the specific requested genera
  target_fungi <- c("Fusarium", "Aspergillus", "Epichloe", "Alternaria", "Penicillium", "Trichoderma", "Colletotrichum")
  
  message("\nTop Fungal Genera of Interest:")
  fungal_interest <- fungal_genera %>%
    filter(genus %in% target_fungi) %>%
    arrange(desc(study_count))
  
  print(fungal_interest)
    
  # Add to overall stats summary
  overall_stats <- overall_stats %>%
    add_row(metric = "Total papers with resolved fungal host", value = total_fungal_papers)
    
  for (i in seq_len(nrow(fungal_interest))) {
    overall_stats <- overall_stats %>%
      add_row(metric = paste("Papers studying", fungal_interest$genus[i]), 
              value = fungal_interest$study_count[i]) %>%
      add_row(metric = paste("Percent studying", fungal_interest$genus[i]), 
              value = fungal_interest$percent_of_fungal_studies[i])
  }
  
  # Also calculate overall Phylum level dominance
  ascomycota_studies <- df %>%
    filter(!is.na(fungal_taxon_accepted_ids), fungal_taxon_accepted_ids != "") %>%
    # We use the Python output that already mapped all IDs to phyla for us, 
    # but we can get it straight from the FUNGAL_GENERA_FILE
    # Wait, FUNGAL_GENERA_FILE only has top genera.
    # We should pull it directly from the python phylum output.
    invisible()

} else {
  message("Warning: Fungal genera file not found: ", FUNGAL_GENERA_FILE)
}

FUNGAL_PHYLUM_FILE <- "results/taxonomy_analysis/fungal_phylum_coverage.csv"
if (file.exists(FUNGAL_PHYLUM_FILE)) {
  fungal_phyla <- read_csv(FUNGAL_PHYLUM_FILE, show_col_types = FALSE)
  ascomycota_species <- fungal_phyla %>% filter(phylum == "Ascomycota") %>% pull(studied_species)
  total_fungal_species <- sum(fungal_phyla$studied_species, na.rm = TRUE)
  
  if(length(ascomycota_species) > 0 && total_fungal_species > 0) {
      ascomycota_pct <- (ascomycota_species / total_fungal_species) * 100
      overall_stats <- overall_stats %>%
        add_row(metric = "Total studied fungal species (unique)", value = total_fungal_species) %>%
        add_row(metric = "Studied Ascomycota species", value = ascomycota_species) %>%
        add_row(metric = "Percent of fungal species that are Ascomycota", value = ascomycota_pct)
  }
}

write_csv(overall_stats, file.path(OUTPUT_DIR, "crop_analysis_summary.csv"))

message("Crop and fungal analyses complete. Results saved to ", OUTPUT_DIR)
