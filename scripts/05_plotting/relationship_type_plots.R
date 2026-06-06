#!/usr/bin/env Rscript
# =================================================================================
# relationship_type_plots.R
# =================================================================================
# Purpose: Plot the relationship-type summaries generated in Stage 04.
#
# Inputs:
#   - results/interaction_analysis/relationship_type_counts_by_interaction.csv
#   - results/interaction_analysis/relationship_type_counts_by_study.csv
#   - results/interaction_analysis/relationship_type_counts_by_country.csv
#   - results/interaction_analysis/relationship_type_counts_by_year.csv (optional)
#
# Outputs:
#   - results/interaction_analysis/relationship_type_by_interaction.png
#   - results/interaction_analysis/relationship_type_by_study.png
#   - results/interaction_analysis/relationship_type_country_heatmap.png
#   - results/interaction_analysis/relationship_type_trends_over_time.png (if year data exists)
#
# Usage:
#   Rscript scripts/05_plotting/relationship_type_plots.R
# =================================================================================

library(dplyr)
library(ggplot2)
library(readr)
library(tidyr)
library(forcats)
library(stringr)

source("scripts/05_plotting/theme_utils.R")

INPUT_DIR <- "results/interaction_analysis"
BY_INTERACTION_FILE <- file.path(INPUT_DIR, "relationship_type_counts_by_interaction.csv")
BY_STUDY_FILE <- file.path(INPUT_DIR, "relationship_type_counts_by_study.csv")
BY_COUNTRY_FILE <- file.path(INPUT_DIR, "relationship_type_counts_by_country.csv")
BY_YEAR_FILE <- file.path(INPUT_DIR, "relationship_type_counts_by_year.csv")

OUT_INTERACTION <- file.path(INPUT_DIR, "relationship_type_by_interaction.png")
OUT_STUDY <- file.path(INPUT_DIR, "relationship_type_by_study.png")
OUT_COUNTRY <- file.path(INPUT_DIR, "relationship_type_country_heatmap.png")
OUT_YEAR <- file.path(INPUT_DIR, "relationship_type_trends_over_time.png")

if (!file.exists(BY_INTERACTION_FILE)) stop("Missing input file: ", BY_INTERACTION_FILE)
if (!file.exists(BY_STUDY_FILE)) stop("Missing input file: ", BY_STUDY_FILE)
if (!file.exists(BY_COUNTRY_FILE)) stop("Missing input file: ", BY_COUNTRY_FILE)

dir.create(INPUT_DIR, recursive = TRUE, showWarnings = FALSE)

message("Loading relationship type summaries...")
by_interaction <- read_csv(BY_INTERACTION_FILE, show_col_types = FALSE)
by_study <- read_csv(BY_STUDY_FILE, show_col_types = FALSE)
by_country <- read_csv(BY_COUNTRY_FILE, show_col_types = FALSE)

clean_relationship_order <- function(df, count_col) {
  df %>%
    mutate(relationship_type = fct_reorder(relationship_type, .data[[count_col]], .desc = TRUE))
}

# -----------------------------------------------------------------------------
# 1) Interaction-level bar plot
# -----------------------------------------------------------------------------
if (nrow(by_interaction) > 0) {
  p_interaction <- by_interaction %>%
    clean_relationship_order("interaction_count") %>%
    ggplot(aes(x = relationship_type, y = interaction_count, fill = relationship_type)) +
    geom_col(width = 0.72, color = "white", linewidth = 0.3) +
    geom_text(aes(label = interaction_count), vjust = -0.25, size = 3.4) +
    scale_fill_manual(values = c(
      "Endophytic" = "#0072B2",
      "Pathogenic" = "#D55E00",
      "Mycorrhizal" = "#009E73",
      "Antagonistic/Biocontrol" = "#E69F00",
      "Mutualistic" = "#CC79A7",
      "Saprotrophic" = "#56B4E9",
      "Commensal" = "#F0E442",
      "Absence/Negative" = "#666666",
      "Unknown/Other" = "#999999"
    )) +
    theme_endo_bw(base_size = 11) +
    labs(
      title = "Relationship Types Observed in the Dataset",
      x = NULL,
      y = "Interaction count",
      fill = "Relationship type"
    ) +
    theme(axis.text.x = element_text(angle = 35, hjust = 1), legend.position = "none")

  ggsave(OUT_INTERACTION, p_interaction, width = 6.5, height = 5, dpi = 300)
}

# -----------------------------------------------------------------------------
# 2) Study-level bar plot
# -----------------------------------------------------------------------------
if (nrow(by_study) > 0) {
  p_study <- by_study %>%
    clean_relationship_order("study_count") %>%
    ggplot(aes(x = relationship_type, y = study_count, fill = relationship_type)) +
    geom_col(width = 0.72, color = "white", linewidth = 0.3) +
    geom_text(aes(label = study_count), vjust = -0.25, size = 3.4) +
    scale_fill_manual(values = c(
      "Endophytic" = "#0072B2",
      "Pathogenic" = "#D55E00",
      "Mycorrhizal" = "#009E73",
      "Antagonistic/Biocontrol" = "#E69F00",
      "Mutualistic" = "#CC79A7",
      "Saprotrophic" = "#56B4E9",
      "Commensal" = "#F0E442",
      "Absence/Negative" = "#666666",
      "Unknown/Other" = "#999999"
    )) +
    theme_endo_bw(base_size = 11) +
    labs(
      title = "Relationship Types by Unique Study",
      x = NULL,
      y = "Study count",
      fill = "Relationship type"
    ) +
    theme(axis.text.x = element_text(angle = 35, hjust = 1), legend.position = "none")

  ggsave(OUT_STUDY, p_study, width = 6.5, height = 5, dpi = 300)
}

# -----------------------------------------------------------------------------
# 3) Country x relationship heatmap
# -----------------------------------------------------------------------------
if (nrow(by_country) > 0) {
  top_relationships <- by_country %>%
    group_by(relationship_type) %>%
    summarize(total = sum(study_count), .groups = "drop") %>%
    arrange(desc(total)) %>%
    slice_head(n = 8) %>%
    pull(relationship_type)

  top_countries <- by_country %>%
    group_by(country) %>%
    summarize(total = sum(study_count), .groups = "drop") %>%
    arrange(desc(total)) %>%
    slice_head(n = 15) %>%
    pull(country)

  country_plot_df <- by_country %>%
    filter(country %in% top_countries, relationship_type %in% top_relationships) %>%
    mutate(
      country = fct_reorder(country, study_count, .fun = sum, .desc = TRUE),
      relationship_type = fct_reorder(relationship_type, study_count, .fun = sum, .desc = TRUE)
    )

  p_country <- ggplot(country_plot_df, aes(x = relationship_type, y = country, fill = study_count)) +
    geom_tile(color = "white", linewidth = 0.25) +
    geom_text(aes(label = study_count), size = 3.1) +
    scale_fill_gradient(low = "#f7fbff", high = "#08306b") +
    theme_endo_bw(base_size = 10.5) +
    labs(
      title = "Relationship Types by Country",
      x = NULL,
      y = NULL,
      fill = "Studies"
    ) +
    theme(axis.text.x = element_text(angle = 35, hjust = 1))

  ggsave(OUT_COUNTRY, p_country, width = 6.5, height = 6, dpi = 300)
}

# -----------------------------------------------------------------------------
# 4) Trends over time (optional)
# -----------------------------------------------------------------------------
if (file.exists(BY_YEAR_FILE)) {
  by_year <- read_csv(BY_YEAR_FILE, show_col_types = FALSE)

  if (nrow(by_year) > 0 && all(c("publication_year", "relationship_type", "study_count") %in% names(by_year))) {
    p_year <- by_year %>%
      mutate(relationship_type = fct_reorder(relationship_type, study_count, sum, .desc = TRUE)) %>%
      ggplot(aes(x = publication_year, y = study_count, color = relationship_type)) +
      geom_line(linewidth = 0.7) +
      geom_point(size = 1.7) +
      facet_wrap(~ relationship_type, scales = "free_y", ncol = 3) +
      scale_color_manual(values = c(
        "Endophytic" = "#0072B2",
        "Pathogenic" = "#D55E00",
        "Mycorrhizal" = "#009E73",
        "Antagonistic/Biocontrol" = "#E69F00",
        "Mutualistic" = "#CC79A7",
        "Saprotrophic" = "#56B4E9",
        "Commensal" = "#F0E442",
        "Absence/Negative" = "#666666",
        "Unknown/Other" = "#999999"
      )) +
      theme_endo_bw(base_size = 10.5) +
      labs(
        title = "Temporal Trends in Relationship Types",
        x = "Publication year",
        y = "Study count",
        color = "Relationship type"
      ) +
      theme(legend.position = "none")

    ggsave(OUT_YEAR, p_year, width = 6.5, height = 6, dpi = 300)
  }
}

message("Relationship type plots complete.")
message("Outputs written to: ", INPUT_DIR)
