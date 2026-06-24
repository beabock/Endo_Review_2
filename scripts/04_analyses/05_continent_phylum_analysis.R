#!/usr/bin/env Rscript
# BMB 2026-06-17
# Breaks down which plant phyla are understudied by continent, with a focus on bryophytes.

library(dplyr)
library(readr)
library(tidyr)
library(stringr)
library(rnaturalearth)
library(sf)

INPUT_FILE <- "data/Ollama_cleaned_synresolved_standardized_final.csv"
GBIF_TAXON_FILE <- "data/Reference_datasets/gbif_backbone/Taxon.tsv"
OUTPUT_DIR <- "results/understudied_analysis"

dir.create(OUTPUT_DIR, recursive = TRUE, showWarnings = FALSE)

cat("Loading study data...\n")
df <- read_csv(INPUT_FILE, show_col_types = FALSE)

cat("Loading world map to get continents...\n")
sf_use_s2(FALSE)
world <- ne_countries(scale = 50, returnclass = "sf") %>% 
  st_drop_geometry() %>%
  select(iso_a3, continent) %>%
  filter(!is.na(iso_a3))

cat("Loading GBIF taxonomy to get plant phyla...\n")
gbif_taxa <- read_tsv(
  GBIF_TAXON_FILE,
  col_select = c("taxonID", "phylum", "kingdom"),
  show_col_types = FALSE
) %>%
  filter(kingdom == "Plantae", !is.na(taxonID)) %>%
  mutate(taxonID = as.character(taxonID)) %>%
  select(taxonID, phylum) %>%
  distinct(taxonID, .keep_all = TRUE)

cat("Matching plants to phyla and assigning continents...\n")
df_matched <- df %>%
  filter(!is.na(plant_host_accepted_ids), plant_host_accepted_ids != "", !is.na(country)) %>%
  mutate(accepted_id = str_split(plant_host_accepted_ids, ";")) %>%
  unnest_longer(accepted_id) %>%
  mutate(accepted_id = str_trim(accepted_id)) %>%
  filter(!is.na(accepted_id), accepted_id != "") %>%
  # Join with GBIF for phylum
  left_join(gbif_taxa, by = c("accepted_id" = "taxonID")) %>%
  # Join with World map for continent
  left_join(world, by = c("country" = "iso_a3"))

# Count papers per phylum per continent
continent_phylum_counts <- df_matched %>%
  filter(!is.na(phylum), !is.na(continent)) %>%
  distinct(paper_id, continent, phylum) %>%
  count(continent, phylum, name = "study_count") %>%
  arrange(continent, desc(study_count))

# Pivot wider for a clean matrix
phylum_matrix <- continent_phylum_counts %>%
  pivot_wider(names_from = continent, values_from = study_count, values_fill = 0) %>%
  # Calculate row total
  mutate(Global_Total = rowSums(select(., -phylum))) %>%
  arrange(desc(Global_Total))

output_file <- file.path(OUTPUT_DIR, "continent_phylum_counts.csv")
write_csv(phylum_matrix, output_file)

cat("\nSaved matrix to:", output_file, "\n\n")

cat("Bryophyta studies by continent:\n")
print(continent_phylum_counts %>% filter(phylum == "Bryophyta") %>% arrange(desc(study_count)))