#!/usr/bin/env Rscript
# BMB 2026-08-27
# Study-effort bias by biogeographic realm (Olson et al. 2001 / WWF terrestrial
# realms). Replaces 03b_geographic_bias_mapping_eu_grouped.R - the EU / Global
# North-South groupings were political, not biological (Referee 3,
# NPH-MS-2026-57711).
#
# Outputs (results/country_analysis/):
#   realm_breakdown.csv               - per-realm coverage + study totals (primary assignment)
#   realm_breakdown_sensitivity.csv   - same, with trans-realm countries reassigned to their secondary realm
#   geographic_bias_by_realm.csv      - per-country study counts + realm + percentile bias class
#   study_effort_by_realm.png         - bar chart

suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
  library(tidyr)
  library(ggplot2)
})

source("scripts/utils/biogeographic_mapping.R")
if (file.exists("scripts/05_plotting/theme_utils.R")) source("scripts/05_plotting/theme_utils.R")
if (!exists("theme_endo_bw")) theme_endo_bw <- function(...) ggplot2::theme_bw(...)

INPUT_FILE <- "data/country_enriched_data.csv"
RESULTS_DIR <- "results/country_analysis"
dir.create(RESULTS_DIR, recursive = TRUE, showWarnings = FALSE)

if (!file.exists(INPUT_FILE)) stop("Input file not found: ", INPUT_FILE)

message("Loading country-enriched data...")
country_data <- read_csv(INPUT_FILE, show_col_types = FALSE) %>%
  mutate(
    study_count = as.numeric(study_count),
    centroid_lat = as.numeric(centroid_lat),
    centroid_lon = as.numeric(centroid_lon)
  ) %>%
  distinct(iso_a3, .keep_all = TRUE)

country_data <- add_realm(country_data, iso_col = "iso_a3")

# Per-country percentile bias class (same scheme as 03_geographic_bias_mapping.R)
bias_by_country <- country_data %>%
  mutate(
    study_count_percentile = percent_rank(study_count),
    bias_class = case_when(
      study_count == 0 ~ "No studies",
      study_count_percentile >= 0.90 ~ "Over-studied (top 10%)",
      study_count_percentile >= 0.75 ~ "Well-studied (top 25%)",
      study_count_percentile >= 0.50 ~ "Moderate coverage (top 50%)",
      study_count_percentile >= 0.25 ~ "Under-studied (bottom 50%)",
      TRUE ~ "Rare/minimal coverage"
    )
  ) %>%
  select(iso_a3, country_name, realm, realm_secondary = realm_sensitivity,
         study_count, study_count_percentile, bias_class) %>%
  arrange(desc(study_count))

write_csv(bias_by_country, file.path(RESULTS_DIR, "geographic_bias_by_realm.csv"))

summarise_by_realm <- function(df, realm_col) {
  df %>%
    rename(realm_use = all_of(realm_col)) %>%
    filter(!is.na(realm_use), realm_use != "Unknown") %>%
    group_by(realm = realm_use) %>%
    summarise(
      num_countries = n_distinct(iso_a3),
      countries_with_studies = sum(study_count > 0, na.rm = TRUE),
      total_studies = sum(study_count, na.rm = TRUE),
      median_studies = median(study_count, na.rm = TRUE),
      mean_studies = mean(study_count, na.rm = TRUE),
      max_studies = max(study_count, na.rm = TRUE),
      .groups = "drop"
    ) %>%
    mutate(
      coverage_pct = 100 * countries_with_studies / num_countries,
      studies_per_country = total_studies / num_countries,
      concentration_pct = 100 * total_studies / sum(total_studies)
    ) %>%
    arrange(desc(total_studies))
}

realm_breakdown <- summarise_by_realm(
  country_data %>% mutate(realm = as.character(realm)), "realm"
)
realm_breakdown_sensitivity <- summarise_by_realm(
  country_data %>% mutate(realm_sensitivity = as.character(realm_sensitivity)),
  "realm_sensitivity"
)

write_csv(realm_breakdown, file.path(RESULTS_DIR, "realm_breakdown.csv"))
write_csv(realm_breakdown_sensitivity, file.path(RESULTS_DIR, "realm_breakdown_sensitivity.csv"))

message("\nStudy effort by biogeographic realm (primary assignment):")
print(realm_breakdown)

p <- ggplot(realm_breakdown, aes(x = reorder(realm, total_studies), y = total_studies)) +
  geom_col(fill = "#3B6B8F") +
  geom_text(aes(label = total_studies), hjust = -0.15, size = 3.2) +
  coord_flip() +
  labs(
    title = "Fungal endophyte research effort by biogeographic realm",
    subtitle = "Study counts summed over countries (Olson et al. 2001 realms)",
    x = NULL, y = "Total studies"
  ) +
  theme_endo_bw(base_size = 11)

ggsave(file.path(RESULTS_DIR, "study_effort_by_realm.png"), p, width = 7, height = 4.5, dpi = 300)

message("\nOutputs written to ", RESULTS_DIR)
