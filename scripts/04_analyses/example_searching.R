library(dplyr)
library(readr)
library(tidyr)

INPUT_FILE <- "data/Ollama_cleaned_synresolved_standardized_final.csv"
OUTPUT_PLANTS <- "results/temp/undersampled_unique_plants.csv"
OUTPUT_FUNGI <- "results/temp/undersampled_unique_fungi.csv"

if (!dir.exists("results/temp")) {
  dir.create("results/temp", recursive = TRUE)
}

# 1. Load data
cat("Loading data...\n")
df <- read_csv(INPUT_FILE, show_col_types = FALSE)

# Load list of valid countries (ISO A3 codes) to filter out non-country entities
valid_countries <- read_csv("data/country_enriched_data.csv", show_col_types = FALSE) %>%
  pull(iso_a3) %>%
  unique()

# 2. Determine undersampled countries (< 5 studies)
cat("Calculating study counts by country...\n")
country_counts <- df %>%
  filter(!is.na(country), country != "", country %in% valid_countries) %>%
  distinct(paper_id, country) %>%
  count(country, name = "study_count")

undersampled_countries <- country_counts %>%
  filter(study_count < 5) %>%
  pull(country)

cat("Found", length(undersampled_countries), "undersampled countries (<5 studies).\n")

# 3. Find unique taxa
# To find taxa ONLY in undersampled countries, we group by taxa, 
# list all countries they appear in, and check if ALL those countries are in our undersampled list.

cat("Finding unique plant hosts...\n")
unique_plants <- df %>%
  filter(!is.na(plant_host_resolved), plant_host_resolved != "", !is.na(country), country != "", country %in% valid_countries) %>%
  group_by(plant_host_resolved) %>%
  summarise(
    countries = list(unique(country)),
    total_records = n()
  ) %>%
  rowwise() %>%
  mutate(
    # Is every country this plant appears in an undersampled country?
    only_in_undersampled = all(unlist(countries) %in% undersampled_countries),
    country_list = paste(unlist(countries), collapse = ", ")
  ) %>%
  ungroup() %>%
  filter(only_in_undersampled) %>%
  arrange(desc(total_records))

cat("Finding unique fungal taxa...\n")
unique_fungi <- df %>%
  filter(!is.na(fungal_taxon_resolved), fungal_taxon_resolved != "", !is.na(country), country != "", country %in% valid_countries) %>%
  group_by(fungal_taxon_resolved) %>%
  summarise(
    countries = list(unique(country)),
    total_records = n()
  ) %>%
  rowwise() %>%
  mutate(
    # Is every country this fungus appears in an undersampled country?
    only_in_undersampled = all(unlist(countries) %in% undersampled_countries),
    country_list = paste(unlist(countries), collapse = ", ")
  ) %>%
  ungroup() %>%
  filter(only_in_undersampled) %>%
  arrange(desc(total_records))

# 4. Save results
write_csv(unique_plants %>% select(-countries), OUTPUT_PLANTS)
write_csv(unique_fungi %>% select(-countries), OUTPUT_FUNGI)

cat("Done! Found", nrow(unique_plants), "plant taxa and", nrow(unique_fungi), "fungal taxa unique to undersampled countries.\n")
cat("Results saved to:\n  ", OUTPUT_PLANTS, "\n  ", OUTPUT_FUNGI, "\n")
