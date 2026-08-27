# BMB 2026-06-05 / revised 2026-08-27
# Pearson and Spearman correlations between per-country study count and latitude.
# Provides the country-level study summary consumed by the biodiversity-overlap and
# geographic-plotting steps.
#
# Replaces the latitude half of the retired 01_country_gdp_latitude_analysis.R
# (GDP / Prediction 4 was cut for the NPH-MS-2026-57711 resubmission).

library(dplyr)
library(readr)
library(tidyr)
library(scales)

INPUT_FILE <- "data/country_enriched_data.csv"
RESULTS_DIR <- "results/country_analysis"
SUMMARY_FILE <- file.path(RESULTS_DIR, "country_study_summary.csv")
CORR_FILE <- file.path(RESULTS_DIR, "country_latitude_correlations.csv")

if (!file.exists(INPUT_FILE)) {
  stop("Input file not found: ", INPUT_FILE)
}

if (!dir.exists(RESULTS_DIR)) {
  dir.create(RESULTS_DIR, recursive = TRUE, showWarnings = FALSE)
}

country_data <- read_csv(INPUT_FILE, show_col_types = FALSE) %>%
  mutate(
    study_count = as.numeric(study_count),
    centroid_lat = as.numeric(centroid_lat),
    centroid_lon = as.numeric(centroid_lon)
  )

analysis_data <- country_data %>%
  filter(!is.na(study_count), !is.na(centroid_lat))

mod <- lm(study_count ~ centroid_lat, data = analysis_data)
print(summary(mod))

corr_pairs <- list(
  list(
    x = "centroid_lat",
    y = "study_count",
    label = "study_count_vs_latitude",
    x_label = "Country centroid latitude",
    y_label = "Study count"
  )
)

correlation_results <- lapply(corr_pairs, function(spec) {
  subset_data <- analysis_data %>% filter(!is.na(.data[[spec$x]]), !is.na(.data[[spec$y]]))

  pearson <- cor.test(subset_data[[spec$x]], subset_data[[spec$y]], method = "pearson")
  spearman <- cor.test(subset_data[[spec$x]], subset_data[[spec$y]], method = "spearman", exact = FALSE)

  tibble(
    analysis = spec$label,
    n = nrow(subset_data),
    pearson_r = unname(pearson$estimate),
    pearson_p = pearson$p.value,
    spearman_rho = unname(spearman$estimate),
    spearman_p = spearman$p.value
  )
}) %>%
  bind_rows()

write_csv(correlation_results, CORR_FILE)

summary_table <- analysis_data %>%
  select(iso_a3, country_name, study_count, centroid_lat, centroid_lon) %>%
  arrange(desc(study_count), country_name)

write_csv(summary_table, SUMMARY_FILE)

cat("Country latitude analysis complete:\n")
cat("  Input countries: ", nrow(country_data), "\n", sep = "")
cat("  Countries analyzed: ", nrow(analysis_data), "\n", sep = "")
cat("  Correlation rows written: ", nrow(correlation_results), "\n", sep = "")
cat("  Summary table saved to: ", SUMMARY_FILE, "\n", sep = "")
cat("  Correlations saved to: ", CORR_FILE, "\n", sep = "")
