# BMB 2026-06-24
# Exploratory script checking bryophyte representation — how many countries have
# zero or very few bryophyte endophyte studies.

library(dplyr)
library(readr)
library(stringr)
library(tidyr)

INPUT_FILE <- "data/Ollama_cleaned_synresolved_standardized_final.csv"
GBIF_TAXON_FILE <- "data/Reference_datasets/gbif_backbone/Taxon.tsv"

cat("Loading data...\n")
df <- read_csv(INPUT_FILE, show_col_types = FALSE)

# Load list of valid countries (ISO A3 codes)
valid_countries <- read_csv("data/country_enriched_data.csv", show_col_types = FALSE) %>%
  pull(iso_a3) %>%
  unique()

cat("Loading GBIF taxonomy to get phylum...\n")
# Read only the necessary columns from GBIF
gbif_taxa <- read_tsv(
  GBIF_TAXON_FILE,
  col_select = c("taxonID", "phylum", "kingdom"),
  show_col_types = FALSE
) %>%
  filter(kingdom == "Plantae", !is.na(taxonID)) %>%
  mutate(taxonID = as.character(taxonID)) %>%
  select(taxonID, phylum) %>%
  distinct(taxonID, .keep_all = TRUE)

cat("Matching plants to phyla...\n")
# Extract accepted IDs from our data
df_matched <- df %>%
  filter(!is.na(plant_host_accepted_ids), plant_host_accepted_ids != "", !is.na(country), country %in% valid_countries) %>%
  mutate(accepted_id = str_split(plant_host_accepted_ids, "\\s*;\\s*")) %>%
  unnest_longer(accepted_id) %>%
  mutate(accepted_id = str_squish(accepted_id)) %>%
  filter(!is.na(accepted_id), accepted_id != "") %>%
  # Join with GBIF
  left_join(gbif_taxa, by = c("accepted_id" = "taxonID"))

# Filter to Bryophyta and count by country
cat("Calculating Bryophyta studies by country...\n")
bryophyta_counts <- df_matched %>%
  filter(phylum == "Bryophyta") %>%
  distinct(paper_id, country) %>%
  count(country, name = "bryophyta_study_count") %>%
  arrange(desc(bryophyta_study_count))

# Find countries with fewer than 10 studies
undersampled_bryophyta <- bryophyta_counts %>%
  filter(bryophyta_study_count < 3)

cat("\n--- Countries with <3 Bryophyta studies ---\n")
print(undersampled_bryophyta, n = Inf)

# Also check which valid countries have ZERO Bryophyta studies
zero_bryo_countries <- setdiff(valid_countries, bryophyta_counts$country)
cat("\nPlus", length(zero_bryo_countries), "countries with 0 Bryophyta studies.\n")
write_csv(tibble(country = zero_bryo_countries, bryophyta_study_count = 0), "results/exploratory/bryophyta_zero_study_countries.csv")
write_csv(bryophyta_counts, "results/exploratory/bryophyta_counts_by_country.csv")
cat("\nFull country counts saved to results/exploratory/bryophyta_counts_by_country.csv\n")


