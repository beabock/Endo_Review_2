#!/usr/bin/env Rscript
# =================================================================================
# 08_biodiversity_priority_overlap.R
# =================================================================================
# Purpose: Compare understudied endophyte regions and biomes with current
#          biodiversity-priority estimates such as hotspots, richness layers,
#          or other externally supplied priority tables.
#
# Expected inputs:
#   - results/understudied_analysis/unstudied_countries.csv
#   - data/biodiversity_priority_countries.csv (optional but recommended)
#   - data/biodiversity_priority_biomes.csv (optional)
#
# Optional input formats:
#   country file columns:
#     - iso_a3 or country / country_name
#     - priority_score or richness_estimate
#     - priority_label or source
#
#   biome file columns:
#     - biome_clean or biome
#     - priority_score or richness_estimate
#     - priority_label or source
#
# Outputs:
#   - results/biodiversity_priority_overlap/overlap_by_country.csv
#   - results/biodiversity_priority_overlap/overlap_by_biome.csv
#   - results/biodiversity_priority_overlap/summary_metrics.csv
#   - results/biodiversity_priority_overlap/priority_overlap_scatter.png
#
# Usage:
#   Rscript scripts/04_analyses/08_biodiversity_priority_overlap.R
# =================================================================================

library(dplyr)
library(readr)
library(tidyr)
library(stringr)
library(ggplot2)
library(scales)

INPUT_ENDOPHYTE_COUNTRIES <- "results/country_analysis/country_gdp_latitude_summary.csv"
INPUT_UNSTUDIED_COUNTRIES <- "results/understudied_analysis/unstudied_countries.csv"
INPUT_ENDOPHYTE_DATA <- "data/Ollama_cleaned_synresolved_standardized_final.csv"
INPUT_PRIORITY_COUNTRIES <- "data/biodiversity_priority_countries.csv"
INPUT_PRIORITY_BIOMES <- "data/biodiversity_priority_biomes.csv"
OUTPUT_DIR <- "results/biodiversity_priority_overlap"

dir.create(OUTPUT_DIR, recursive = TRUE, showWarnings = FALSE)

if (!file.exists(INPUT_ENDOPHYTE_COUNTRIES)) {
  stop("Missing country summary file: ", INPUT_ENDOPHYTE_COUNTRIES)
}
if (!file.exists(INPUT_UNSTUDIED_COUNTRIES)) {
  stop("Missing understudied countries file: ", INPUT_UNSTUDIED_COUNTRIES)
}
if (!file.exists(INPUT_ENDOPHYTE_DATA)) {
  stop("Missing endophyte dataset file: ", INPUT_ENDOPHYTE_DATA)
}

country_summary <- read_csv(INPUT_ENDOPHYTE_COUNTRIES, show_col_types = FALSE)
unstudied_countries <- read_csv(INPUT_UNSTUDIED_COUNTRIES, show_col_types = FALSE)
endophyte_data <- read_csv(INPUT_ENDOPHYTE_DATA, show_col_types = FALSE)

normalize_text <- function(x) {
  x %>% as.character() %>% str_to_lower() %>% str_squish()
}

normalize_country <- function(x) {
  normalize_text(x)
}

standardize_biome <- function(x) {
  x <- str_to_lower(as.character(x))
  case_when(
    str_detect(x, "forest|forestry|woodland") ~ "Forest",
    str_detect(x, "agriculture|agricultural|field|vineyard|greenhouse|crop|orchard|plantation") ~ "Agriculture/Cultivated",
    str_detect(x, "grassland|meadow|pasture|prairie|steppe") ~ "Grassland/Pasture",
    str_detect(x, "marine|ocean|sea|coral|pelagic|intertidal") ~ "Marine",
    str_detect(x, "desert|arid|semi-arid") ~ "Desert",
    str_detect(x, "mangrove") ~ "Mangrove",
    str_detect(x, "mountain|alpine|montane|highland") ~ "Mountain/Alpine",
    str_detect(x, "tropical|rainforest|jungle") ~ "Tropical/Rainforest",
    str_detect(x, "savanna|shrubland|scrub|bushland|cerrado") ~ "Savanna/Shrubland/Cerrado",
    str_detect(x, "wetland|swamp|marsh|bog|fen") ~ "Wetland",
    str_detect(x, "urban|city|garden|park") ~ "Urban/Garden",
    str_detect(x, "antarctic|arctic|polar|tundra|ice") ~ "Polar/Tundra",
    is.na(x) | x %in% c("na", "n/a", "none", "unknown", "not specified") ~ NA_character_,
    TRUE ~ "Other/Specific"
  )
}

collect_endophyte_biomes <- function(df) {
  if (!"biome" %in% names(df)) {
    return(tibble(biome_clean = character(), study_count = integer()))
  }

  df %>%
    mutate(
      paper_id = as.character(paper_id),
      biome_clean = standardize_biome(biome)
    ) %>%
    filter(!is.na(paper_id), !is.na(biome_clean), biome_clean != "Other/Specific") %>%
    distinct(paper_id, biome_clean) %>%
    count(biome_clean, name = "study_count", sort = TRUE)
}

prepare_priority_country_file <- function(path) {
  if (!file.exists(path)) {
    return(NULL)
  }

  priority <- read_csv(path, show_col_types = FALSE)
  if (!any(c("iso_a3", "country", "country_name") %in% names(priority))) {
    stop("Priority country file must contain iso_a3, country, or country_name.")
  }

  priority %>%
    mutate(
      iso_a3 = if ("iso_a3" %in% names(.)) as.character(iso_a3) else NA_character_,
      country_name = if ("country_name" %in% names(.)) country_name else if ("country" %in% names(.)) country else NA_character_,
      priority_score = if ("priority_score" %in% names(.)) as.numeric(priority_score) else if ("richness_estimate" %in% names(.)) as.numeric(richness_estimate) else NA_real_,
      priority_label = if ("priority_label" %in% names(.)) as.character(priority_label) else if ("source" %in% names(.)) as.character(source) else "biodiversity_priority"
    ) %>%
    distinct()
}

prepare_priority_biome_file <- function(path) {
  if (!file.exists(path)) {
    return(NULL)
  }

  priority <- read_csv(path, show_col_types = FALSE)
  if (!any(c("biome_clean", "biome") %in% names(priority))) {
    stop("Priority biome file must contain biome_clean or biome.")
  }

  priority %>%
    mutate(
      biome_clean = if ("biome_clean" %in% names(.)) as.character(biome_clean) else as.character(biome),
      priority_score = if ("priority_score" %in% names(.)) as.numeric(priority_score) else if ("richness_estimate" %in% names(.)) as.numeric(richness_estimate) else NA_real_,
      priority_label = if ("priority_label" %in% names(.)) as.character(priority_label) else if ("source" %in% names(.)) as.character(source) else "biodiversity_priority"
    ) %>%
    mutate(biome_clean = str_squish(biome_clean)) %>%
    distinct()
}

country_priority <- prepare_priority_country_file(INPUT_PRIORITY_COUNTRIES)
biome_priority <- prepare_priority_biome_file(INPUT_PRIORITY_BIOMES)

unstudied_countries <- unstudied_countries %>%
  mutate(
    country_name = if ("country_name" %in% names(.)) as.character(country_name) else if ("name" %in% names(.)) as.character(name) else NA_character_,
    country_key = normalize_country(country_name),
    iso_a3 = if ("iso_a3" %in% names(.)) as.character(iso_a3) else NA_character_
  )

country_summary <- country_summary %>%
  mutate(
    country_key = normalize_country(country_name)
  )

if (!is.null(country_priority)) {
  country_priority <- country_priority %>%
    mutate(country_key = normalize_country(country_name))
}

if (is.null(country_priority) && is.null(biome_priority)) {
  stop(
    "No biodiversity-priority input files found. Add one or both of:\n",
    "  - ", INPUT_PRIORITY_COUNTRIES, "\n",
    "  - ", INPUT_PRIORITY_BIOMES, "\n",
    "Each file should be a simple CSV with an iso_a3/country or biome column plus an optional priority_score."
  )
}

summary_metrics <- tibble(
  metric = c(
    "endophyte_countries_total",
    "endophyte_countries_studied",
    "endophyte_countries_understudied",
    "endophyte_biomes_total",
    "endophyte_biomes_studied",
    "endophyte_biomes_understudied"
  ),
  value = c(
    nrow(country_summary),
    sum(country_summary$study_count > 0, na.rm = TRUE),
    nrow(unstudied_countries),
    NA_integer_,
    NA_integer_,
    NA_integer_
  )
)

if (!is.null(country_priority)) {
  overlap_by_country <- unstudied_countries %>%
    left_join(country_priority, by = c("iso_a3" = "iso_a3"), suffix = c("", "_priority")) %>%
    left_join(country_priority %>% filter(is.na(iso_a3)) %>% select(country_key, priority_score, priority_label), by = "country_key", suffix = c("", "_name_priority")) %>%
    left_join(country_summary %>% select(iso_a3, country_name, country_key, study_count), by = c("iso_a3", "country_name", "country_key")) %>%
    mutate(
      priority_score = coalesce(priority_score, priority_score_name_priority),
      priority_label = coalesce(priority_label, priority_label_name_priority)
    ) %>%
    mutate(
      overlap_status = case_when(
        !is.na(priority_score) & study_count == 0 ~ "Understudied + priority area",
        !is.na(priority_score) & study_count > 0 ~ "Studied + priority area",
        is.na(priority_score) & study_count == 0 ~ "Understudied only",
        TRUE ~ "Studied only"
      )
    )

  write_csv(overlap_by_country, file.path(OUTPUT_DIR, "overlap_by_country.csv"))
}

biome_counts <- collect_endophyte_biomes(endophyte_data)

if (!is.null(biome_priority)) {
  overlap_by_biome <- biome_priority %>%
    left_join(biome_counts, by = "biome_clean") %>%
    mutate(
      study_count = replace_na(study_count, 0L),
      overlap_status = case_when(
        study_count == 0 & !is.na(priority_score) ~ "Understudied + priority biome",
        study_count > 0 & !is.na(priority_score) ~ "Studied + priority biome",
        study_count == 0 ~ "Understudied only",
        TRUE ~ "Studied only"
      )
    )

  write_csv(overlap_by_biome, file.path(OUTPUT_DIR, "overlap_by_biome.csv"))
}

if (!is.null(country_priority)) {
  plot_metric_source <- "WB_TOTAL"
  plot_metric_label <- "Total species"

  plot_data <- country_summary %>%
    left_join(country_priority %>% filter(source == plot_metric_source), by = c("iso_a3" = "iso_a3")) %>%
    mutate(
      metric_value = as.numeric(priority_score),
      study_count = as.numeric(study_count),
      understudied = study_count == 0
    ) %>%
    filter(!is.na(metric_value), !is.na(study_count)) %>%
    mutate(
      study_count_log = log10(study_count + 1)
    )

  if (nrow(plot_data) > 0) {
    scatter <- ggplot(plot_data, aes(x = metric_value, y = study_count_log)) +
      geom_point(aes(color = understudied), alpha = 0.8, size = 2.2) +
      geom_smooth(method = "lm", se = TRUE, color = "#b22222") +
      theme_endo_bw(base_size = 12) +
      labs(
        title = "Endophyte Study Effort vs World Bank Total Species Richness",
        subtitle = paste0("Scatter uses ", plot_metric_source, " (", plot_metric_label, "); understudied countries are highlighted"),
        x = "World Bank total species count",
        y = "log10(endophyte study count + 1)"
      ) +
      scale_x_continuous(labels = comma) +
      scale_color_manual(
        values = c(
          `TRUE` = "#E24A33",
          `FALSE` = "#1f78b4"
        ),
        labels = c("Studied countries", "Understudied countries"),
        name = NULL
      ) +
      theme(
        plot.title = element_text(face = "bold"),
        plot.subtitle = element_text(color = "gray40"),
        panel.grid.major.x = element_blank(),
        legend.position = "top"
      )

    ggsave(file.path(OUTPUT_DIR, "priority_overlap_scatter.png"), scatter, width = 8, height = 5, dpi = 300)
  }
}

if (!is.null(country_priority)) {
  summary_metrics <- bind_rows(
    summary_metrics,
    tibble(
      metric = c("priority_countries_matched", "priority_countries_unstudied_matched"),
      value = c(
        sum(!is.na(country_priority$priority_score), na.rm = TRUE),
        sum(!is.na(country_priority$priority_score) & country_priority$country_key %in% unstudied_countries$country_key, na.rm = TRUE)
      )
    )
  )
}

if (!is.null(biome_priority)) {
  summary_metrics <- bind_rows(
    summary_metrics,
    tibble(
      metric = c("priority_biomes_matched", "priority_biomes_understudied_matched"),
      value = c(
        sum(!is.na(biome_priority$priority_score), na.rm = TRUE),
        sum(!is.na(biome_priority$priority_score) & !biome_priority$biome_clean %in% biome_counts$biome_clean[biome_counts$study_count > 0], na.rm = TRUE)
      )
    )
  )
}

write_csv(summary_metrics, file.path(OUTPUT_DIR, "summary_metrics.csv"))

message("Biodiversity priority overlap analysis complete.")
message("Outputs written to: ", OUTPUT_DIR)