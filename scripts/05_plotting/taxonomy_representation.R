#!/usr/bin/env Rscript
# BMB 2026-06-05
# All the taxonomy coverage plots — absolute counts and relative representation
# of plant species, genera, and families by phylum.

library(dplyr)
library(readr)
library(tidyr)
library(ggplot2)
library(scales)

theme_utils_paths <- c(
  "scripts/05_plotting/theme_utils.R",
  "scripts/plotting/theme_utils.R"
)
for (theme_utils_path in theme_utils_paths) {
  if (file.exists(theme_utils_path)) {
    source(theme_utils_path)
    break
  }
}

# Configuration
TAXONOMY_RESULTS_DIR <- "results/taxonomy_analysis"
PLOTS_OUTPUT_DIR <- "results/taxonomy_analysis/plots"
TAXONOMY_LEVELS <- list(
  species = "plant_species_coverage_by_phylum.csv",
  genus = "plant_genus_coverage_by_phylum.csv",
  family = "plant_family_coverage_by_phylum.csv"
)

# Phylum common name mapping
phylum_common_names <- tibble(
  phylum = c("Tracheophyta", "Bryophyta", "Marchantiophyta", "Anthocerotophyta",
             "Rhodophyta", "Chlorophyta", "Charophyta", "Glaucophyta", "Langiophytophyta"),
  common_name = c("Vascular Plants", "Mosses", "Liverworts", "Hornworts",
                  "Red Algae", "Green Algae", "Stoneworts", "Glaucophytes", "Langiophytes")
)

# Create output directory
dir.create(PLOTS_OUTPUT_DIR, recursive = TRUE, showWarnings = FALSE)

# --- Load Year-Enriched Data for Time-Series ---
TIME_SERIES_INPUT_FILE <- "data/Ollama_cleaned_synresolved_standardized_year.csv"
time_df <- if (file.exists(TIME_SERIES_INPUT_FILE)) {
  read_csv(TIME_SERIES_INPUT_FILE, show_col_types = FALSE)
} else {
  NULL
}

# =================================================================================
# DATA LOADING AND PREPARATION
# =================================================================================

#' Load and prepare taxonomy coverage data
#' @param filename CSV filename in TAXONOMY_RESULTS_DIR
#' @param level_name Name of the taxonomic level for labeling
#' @param phylum_order Optional factor levels for consistent phylum ordering
#' @return Prepared data frame ready for plotting
load_taxonomy_data <- function(filename, level_name, phylum_order = NULL) {
  file_path <- file.path(TAXONOMY_RESULTS_DIR, filename)
  
  if (!file.exists(file_path)) {
    stop(paste("File not found:", file_path))
  }
  
  data <- read_csv(file_path, show_col_types = FALSE) %>%
    mutate(level = level_name) %>%
    filter(phylum != "Unassigned") %>%
    left_join(phylum_common_names, by = "phylum")
  
  # Identify the known/studied column pair for this level
  known_col <- colnames(data)[grepl("^known_", colnames(data))]
  
  # Only filter if we have a valid known column
  if (length(known_col) > 0) {
    data <- data %>%
      filter(.data[[known_col]] > 0)
  }
  
  # Apply consistent phylum ordering if provided
  if (!is.null(phylum_order)) {
    data <- data %>%
      mutate(phylum = factor(phylum, levels = phylum_order))
  }
  
  return(data)
}

# Load all three levels first to establish consistent ordering
cat("Loading taxonomy coverage data...\n")
species_data_raw <- read_csv(
  file.path(TAXONOMY_RESULTS_DIR, TAXONOMY_LEVELS$species), 
  show_col_types = FALSE
) %>%
  filter(phylum != "Unassigned")

# Create consistent phylum ordering based on total known species (most to least)
phylum_order <- species_data_raw %>%
  arrange(desc(known_species)) %>%
  pull(phylum)

cat("Phylum ordering (by total known species, most to least):\n")
cat(paste0("  ", seq_along(phylum_order), ". ", phylum_order, "\n"), sep="")

# Load all three levels with consistent ordering
species_data <- load_taxonomy_data(
  TAXONOMY_LEVELS$species, 
  "Species",
  phylum_order = phylum_order
)
genus_data <- load_taxonomy_data(
  TAXONOMY_LEVELS$genus, 
  "Genus",
  phylum_order = phylum_order
)
family_data <- load_taxonomy_data(
  TAXONOMY_LEVELS$family, 
  "Family",
  phylum_order = phylum_order
)

# =================================================================================
# TAXONOMY SUMMARY PLOTS
# =================================================================================

prepare_taxonomy_summary <- function(data, known_col, studied_col) {
  data %>%
    select(phylum, common_name, all_of(known_col), all_of(studied_col)) %>%
    distinct() %>%
    rename(
      known_count = all_of(known_col),
      studied_count = all_of(studied_col)
    ) %>%
    mutate(
      common_name = if_else(is.na(common_name) | common_name == "", phylum, common_name),
      not_studied_count = pmax(known_count - studied_count, 0),
      coverage_percent = if_else(known_count > 0, studied_count / known_count * 100, NA_real_),
      phylum_label = paste0(common_name, " (", phylum, ")\nn=", comma(known_count))
    ) %>%
    distinct(phylum, .keep_all = TRUE)
}

plot_coverage_bar <- function(summary_data, title, taxon_label) {
  plot_data <- summary_data %>%
    arrange(coverage_percent) %>%
    mutate(phylum_label = factor(phylum_label, levels = phylum_label))

  max_coverage <- max(plot_data$coverage_percent, na.rm = TRUE)
  if (is.na(max_coverage) || max_coverage <= 0) {
    max_coverage <- 1
  }

  ggplot(plot_data, aes(x = coverage_percent, y = phylum_label)) +
    geom_col(fill = "#0072B2", width = 0.72) +
    geom_text(
      aes(label = paste0(round(coverage_percent, 1), "%")),
      hjust = -0.12,
      size = 3.5
    ) +
    scale_x_continuous(
      labels = function(x) paste0(x, "%"),
      limits = c(0, max_coverage * 1.15),
      expand = expansion(mult = c(0, 0.02))
    ) +
    labs(
      title = title,
      x = "Coverage (%)",
      y = "Phylum",
      subtitle = paste("Simple coverage view for known plant", tolower(taxon_label), "represented in the literature")
    ) +
    scale_y_discrete(labels = scales::label_wrap(25)) +
    theme_endo_bw(base_size = 14) +
    theme(
      plot.title.position = "plot",
      plot.title = element_text(hjust = 0, size = 15, face = "bold"),
      plot.subtitle = element_text(size = 12),
      axis.title = element_text(size = 13, face = "bold"),
      axis.text = element_text(size = 12),
      axis.text.y = element_text(size = 12),
      panel.grid.major.y = element_blank(),
      legend.position = "none",
      plot.margin = margin(15, 10, 5, 5, "pt")
    )
}

plot_studied_count_bar <- function(summary_data, title, taxon_label) {
  plot_data <- summary_data %>%
    arrange(studied_count) %>%
    mutate(phylum_label = factor(phylum_label, levels = phylum_label))

  max_studied <- max(plot_data$studied_count, na.rm = TRUE)
  if (is.na(max_studied) || max_studied <= 0) {
    max_studied <- 1
  }

  ggplot(plot_data, aes(x = studied_count, y = phylum_label)) +
    geom_col(fill = "#009E73", width = 0.72) +
    geom_text(
      aes(label = comma(studied_count)),
      hjust = -0.12,
      size = 3.5
    ) +
    scale_x_continuous(
      labels = comma,
      limits = c(0, max_studied * 1.15),
      expand = expansion(mult = c(0, 0.02))
    ) +
    labs(
      title = title,
      x = paste("Studied", tolower(taxon_label)),
      y = "Phylum",
      subtitle = paste("Absolute number of studied plant", tolower(taxon_label), "by phylum")
    ) +
    scale_y_discrete(labels = scales::label_wrap(25)) +
    theme_endo_bw(base_size = 14) +
    theme(
      plot.title.position = "plot",
      plot.title = element_text(hjust = 0, size = 15, face = "bold"),
      plot.subtitle = element_text(size = 12),
      axis.title = element_text(size = 13, face = "bold"),
      axis.text = element_text(size = 12),
      axis.text.y = element_text(size = 12),
      panel.grid.major.y = element_blank(),
      legend.position = "none",
      plot.margin = margin(15, 10, 5, 5, "pt")
    )
}

plot_coverage_lollipop <- function(summary_data, title, taxon_label) {
  plot_data <- summary_data %>%
    arrange(coverage_percent) %>%
    mutate(phylum_label = factor(phylum_label, levels = phylum_label))

  max_coverage <- max(plot_data$coverage_percent, na.rm = TRUE)
  if (is.na(max_coverage) || max_coverage <= 0) {
    max_coverage <- 1
  }

  ggplot(plot_data, aes(x = coverage_percent, y = phylum_label)) +
    geom_segment(
      aes(x = 0, xend = coverage_percent, yend = phylum_label),
      linewidth = 1.1,
      color = "#D0D0D0"
    ) +
    geom_point(size = 3.2, color = "#D55E00") +
    geom_text(
      aes(label = paste0(round(coverage_percent, 1), "%")),
      hjust = -0.12,
      size = 3.5
    ) +
    scale_x_continuous(
      labels = function(x) paste0(x, "%"),
      limits = c(0, max_coverage * 1.15),
      expand = expansion(mult = c(0, 0.02))
    ) +
    labs(
      title = title,
      x = "Coverage (%)",
      y = "Phylum",
      subtitle = paste("Lollipop view of coverage for plant", tolower(taxon_label), "by phylum")
    ) +
    scale_y_discrete(labels = scales::label_wrap(25)) +
    theme_endo_bw(base_size = 14) +
    theme(
      plot.title.position = "plot",
      plot.title = element_text(hjust = 0, size = 15, face = "bold"),
      plot.subtitle = element_text(size = 12),
      axis.title = element_text(size = 13, face = "bold"),
      axis.text = element_text(size = 12),
      axis.text.y = element_text(size = 12),
      axis.text.x = element_text(size = 12, face = "bold"),
      panel.grid = element_blank(),
      legend.position = "none",
      plot.margin = margin(15, 10, 5, 5, "pt")
    )
}

plot_taxonomy_heatmap <- function(summary_data, title, taxon_label) {
  # Remove redundant count from labels for heatmap view as it is shown in the 'Known' column
  # We also convert to factor to preserve the phylum ordering
  summary_data <- summary_data %>%
    mutate(phylum_label = sub("\n.*$", "", phylum_label)) %>%
    mutate(phylum_label = factor(phylum_label, levels = rev(unique(phylum_label))))

  long_data <- summary_data %>%
    select(phylum_label, known_count, studied_count, coverage_percent) %>%
    pivot_longer(
      cols = c(known_count, studied_count, coverage_percent),
      names_to = "metric",
      values_to = "value"
    ) %>%
    mutate(
      metric = factor(
        metric,
        levels = c("known_count", "studied_count", "coverage_percent"),
        labels = c("Known", "Studied", "Coverage %")
      )
    ) %>%
    group_by(metric) %>%
    mutate(
      value_scaled = if (all(is.na(value))) {
        NA_real_
      } else if (dplyr::n_distinct(value, na.rm = TRUE) <= 1) {
        0.5
      } else {
        scales::rescale(value, to = c(0, 1), na.rm = TRUE)
      },
      label = case_when(
        metric == "Coverage %" ~ paste0(round(value, 1), "%"),
        TRUE ~ comma(value)
      ),
      text_color = if_else(is.na(value_scaled) | value_scaled < 0.65, "#222222", "white")
    ) %>%
    ungroup()

  ggplot(long_data, aes(x = metric, y = phylum_label, fill = value_scaled)) +
    geom_tile(color = "white", width = 0.92, height = 0.9) +
    geom_text(aes(label = label, color = text_color), size = 3.8, show.legend = FALSE) +
    scale_fill_gradient(low = "#F7F7F7", high = "#2C7FB8", limits = c(0, 1), na.value = "#F0F0F0", guide = "none") +
    scale_color_identity() +
    labs(
      title = title,
      x = NULL,
      y = "Phylum",
      subtitle = paste("Compact summary table for plant", tolower(taxon_label), "known, studied, and coverage")
    ) +
    scale_y_discrete(labels = scales::label_wrap(20)) +
    theme_endo_bw(base_size = 14) +
    theme(
      plot.title.position = "plot",
      plot.title = element_text(hjust = 0, size = 15, face = "bold"),
      plot.subtitle = element_text(size = 12),
      axis.title = element_text(size = 13, face = "bold"),
      axis.text = element_text(size = 12),
      axis.text.y = element_text(size = 12),
      axis.text.x = element_text(size = 12, face = "bold"),
      panel.grid = element_blank(),
      legend.position = "none",
      plot.margin = margin(15, 10, 5, 5, "pt")
    )
}

plot_compound_taxonomy_heatmap <- function(species_summary, genus_summary, family_summary, title) {
  # Combine all three summaries
  combined_data <- bind_rows(
    species_summary %>% mutate(level = "Species"),
    genus_summary %>% mutate(level = "Genus"),
    family_summary %>% mutate(level = "Family")
  ) %>%
    mutate(level = factor(level, levels = c("Species", "Genus", "Family")))

  # Strip the total n from labels for the phyla
  combined_data <- combined_data %>%
    mutate(phylum_label = sub("\n.*$", "", phylum_label)) %>%
    # Note: Use phylum_order here for proper sorting (left-to-right)
    mutate(phylum_label = factor(phylum_label, levels = unique(phylum_label)))

  # Reshape for metrics
  long_data <- combined_data %>%
    select(phylum_label, level, known_count, studied_count, coverage_percent) %>%
    pivot_longer(
      cols = c(known_count, studied_count, coverage_percent),
      names_to = "metric",
      values_to = "value"
    ) %>%
    mutate(
      metric = factor(
        metric,
        levels = rev(c("known_count", "studied_count", "coverage_percent")),
        labels = rev(c("Known Taxa", "Studied Taxa", "Coverage (%)"))
      )
    ) %>%
    group_by(level, metric) %>%
    mutate(
      value_scaled = if (all(is.na(value))) {
        NA_real_
      } else if (dplyr::n_distinct(value, na.rm = TRUE) <= 1) {
        0.5
      } else {
        scales::rescale(value, to = c(0, 1), na.rm = TRUE)
      },
      label = case_when(
        metric == "Coverage (%)" ~ paste0(round(value, 1), "%"),
        TRUE ~ comma(value)
      ),
      text_color = if_else(is.na(value_scaled) | value_scaled < 0.65, "#222222", "white")
    ) %>%
    ungroup()

  ggplot(long_data, aes(x = metric, y = phylum_label, fill = value_scaled)) +
    geom_tile(color = "white", linewidth = 1, width = 0.95, height = 0.85) +
    geom_text(aes(label = label, color = text_color), size = 3, show.legend = FALSE) +
    facet_grid(. ~ level) +
    scale_fill_gradient(low = "#F7F7F7", high = "#2C7FB8", limits = c(0, 1), na.value = "#F0F0F0", guide = "none") +
    scale_color_identity() +
    labs(
      title = title,
      x = "Metric",
      y = "Phylum"
    ) +
    scale_y_discrete(labels = scales::label_wrap(20)) +
    theme_endo_bw(base_size = 12) +
    theme(
      plot.title.position = "plot",
      plot.title = element_text(hjust = 0, size = 14, face = "bold", margin = margin(b = 15)),
      axis.title = element_text(size = 12, face = "bold"),
      axis.text = element_text(size = 11),
      axis.text.y = element_text(size = 11, lineheight = 0.85),
      axis.ticks.y = element_line(color = "gray50"),
      axis.text.x = element_text(size = 11, angle = 45, hjust = 1, vjust = 1),
      panel.grid = element_blank(),
      strip.text = element_text(size = 12, face = "bold"),
      legend.position = "none",
      plot.margin = margin(15, 10, 5, 5, "pt")
    )
}

save_plot <- function(plot, filename, width = 6.5, height = 5) {
  filepath <- file.path(PLOTS_OUTPUT_DIR, filename)
  ggsave(
    filepath,
    plot,
    width = width,
    height = height,
    dpi = 300,
    units = "in"
  )
  cat("Saved:", filepath, "\n")
}

build_taxonomy_views <- function(data, taxon_label, known_col, studied_col) {
  summary_data <- prepare_taxonomy_summary(data, known_col, studied_col)

  list(
    coverage_bar = plot_coverage_bar(
      summary_data,
      paste0("Plant ", taxon_label, ": Coverage by Phylum"),
      taxon_label
    ),
    studied_bar = plot_studied_count_bar(
      summary_data,
      paste0("Plant ", taxon_label, ": Studied Counts by Phylum"),
      taxon_label
    ),
    lollipop = plot_coverage_lollipop(
      summary_data,
      paste0("Plant ", taxon_label, ": Coverage Lollipop by Phylum"),
      taxon_label
    ),
    heatmap = plot_taxonomy_heatmap(
      summary_data,
      paste0("Plant ", taxon_label, ": Summary Heatmap by Phylum"),
      taxon_label
    )
  )
}

# =================================================================================
# GENERATE PLOTS
# =================================================================================

cat("Generating taxonomy bias plots...\n")

species_views <- build_taxonomy_views(species_data, "Species", "known_species", "studied_species")
genus_views <- build_taxonomy_views(genus_data, "Genera", "known_genera", "studied_genera")
family_views <- build_taxonomy_views(family_data, "Families", "known_families", "studied_families")

# =================================================================================
# SAVE PLOTS
# =================================================================================

cat("Saving plots to", PLOTS_OUTPUT_DIR, "\n")

save_plot(species_views$coverage_bar, "01_species_coverage_bar.png", width = 6.5, height = 5)
save_plot(species_views$studied_bar, "02_species_studied_bar.png", width = 6.5, height = 5)
save_plot(species_views$lollipop, "03_species_coverage_lollipop.png", width = 6.5, height = 5)
save_plot(species_views$heatmap, "04_species_summary_heatmap.png", width = 6.5, height = 5)

save_plot(genus_views$coverage_bar, "05_genera_coverage_bar.png", width = 6.5, height = 5)
save_plot(genus_views$studied_bar, "06_genera_studied_bar.png", width = 6.5, height = 5)
save_plot(genus_views$lollipop, "07_genera_coverage_lollipop.png", width = 6.5, height = 5)
save_plot(genus_views$heatmap, "08_genera_summary_heatmap.png", width = 6.5, height = 5)

save_plot(family_views$coverage_bar, "09_families_coverage_bar.png", width = 6.5, height = 5)
save_plot(family_views$studied_bar, "10_families_studied_bar.png", width = 6.5, height = 5)
save_plot(family_views$lollipop, "11_families_coverage_lollipop.png", width = 6.5, height = 5)
save_plot(family_views$heatmap, "12_families_summary_heatmap.png", width = 6.5, height = 5)

# 13. Compound Heatmap (Species, Genus, Family comparison)
species_summary <- prepare_taxonomy_summary(species_data, "known_species", "studied_species")
genus_summary <- prepare_taxonomy_summary(genus_data, "known_genera", "studied_genera")
family_summary <- prepare_taxonomy_summary(family_data, "known_families", "studied_families")

compound_heatmap <- plot_compound_taxonomy_heatmap(
  species_summary,
  genus_summary,
  family_summary,
  "Taxonomic Coverage Comparison Across Levels"
)
save_plot(compound_heatmap, "13_compound_taxonomy_heatmap.png", width = 6.5, height = 7.5)

# =================================================================================
# VISUALIZATION 14: Plant Family Research Over Time
# =================================================================================
if (!is.null(time_df)) {

  # --- Load Taxonomy Lookup for Family ---
  TAXA_LOOKUP_FILE <- "results/taxonomy_analysis/top_studied_plant_species.csv"
  if (!file.exists(TAXA_LOOKUP_FILE)) {
    stop("Taxonomy lookup file not found! Please run the 04_analyses scripts first.\n  Expected file: ", TAXA_LOOKUP_FILE)
  }

  taxa_lookup <- read_csv(TAXA_LOOKUP_FILE, show_col_types = FALSE) %>%
    select(canonicalName, family) %>%
    distinct()

  # Join family data to the main dataframe using a normalized join key
  df_with_family <- time_df %>%
    mutate(join_name = tolower(gsub("[^A-Za-z ]", "", plant_host_resolved)))

  taxa_lookup_norm <- taxa_lookup %>%
    mutate(join_name = tolower(gsub("[^A-Za-z ]", "", canonicalName))) %>%
    select(join_name, family) %>%
    distinct(join_name, .keep_all = TRUE)

  df_with_family <- df_with_family %>%
    left_join(taxa_lookup_norm, by = "join_name") %>%
    select(-join_name)

  # Determine the top 8 families from the full, joined dataset
  top_8_families <- df_with_family %>%
    filter(!is.na(family), family != "") %>%
    count(family, sort = TRUE) %>%
    slice_head(n = 8) %>%
    pull(family)
    
  # Create the time-series data using this definitive list
  family_time_data <- df_with_family %>%
    filter(
      !is.na(publication_year),
      publication_year >= 1990,
      publication_year <= 2024,
      family %in% top_8_families
    ) %>%
    count(publication_year, family)

  p_family_time <- ggplot(family_time_data, aes(x = publication_year, y = n, color = family)) +
    geom_line(linewidth = 1, alpha = 0.8) +
    geom_point(size = 1.5) +
    scale_color_manual(values = endo_palette_discrete, name = "Plant Family") +
    theme_endo_bw(base_size = 12) +
    labs(
      title = "Trends in Plant Family Research Over Time",
      subtitle = "Annual study counts for the top 8 most-studied plant families (1990-2024)",
      x = "Publication Year",
      y = "Number of Studies"
    )
    
  save_plot(p_family_time, "14_family_trends_over_time.png", width = 6.5, height = 5)

} else {
  cat("Skipping family time-series plot: year-enriched data file not found.\n")
}


cat("\nTaxonomy representation plots complete!\n")
