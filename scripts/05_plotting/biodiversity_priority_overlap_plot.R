#!/usr/bin/env Rscript
# BMB 2026-06-05
# Plots the biodiversity priority overlap results - scatter plots, sensitivity
# panels, and unevenness figures.

library(readr)
library(dplyr)
library(ggplot2)
library(tidyr)
library(stringr)
library(gridExtra)
library(ggpubr)
library(reshape2)

library(scales)
source("scripts/05_plotting/theme_utils.R")

# Setup
INPUT_SENSITIVITY <- "results/biodiversity_priority_overlap/sensitivity_analysis.csv"
INPUT_COUNTRY_SUMMARY <- "results/country_analysis/country_gdp_latitude_summary.csv"
INPUT_COUNTRY_AREA <- "results/biodiversity_priority_overlap/country_land_area_summary.csv"
INPUT_PRIORITY_COUNTRIES <- "data/biodiversity/biodiversity_priority_countries.csv"
if (!file.exists(INPUT_PRIORITY_COUNTRIES)) {
  INPUT_PRIORITY_COUNTRIES <- "data/biodiversity_priority_countries.csv"
}
OUTPUT_PLOT <- file.path(OUTPUT_DIR, "priority_overlap_sensitivity.png")
OUTPUT_PLOT_DETAILED <- file.path(OUTPUT_DIR, "priority_overlap_sensitivity_detailed.png")

OUTPUT_SCATTER_COMBINED <- file.path(OUTPUT_DIR, "priority_overlap_scatter.png")
OUTPUT_SCATTER_TOTAL <- file.path(OUTPUT_DIR, "priority_overlap_scatter_total.png")
OUTPUT_SCATTER_ENDEMIC <- file.path(OUTPUT_DIR, "priority_overlap_scatter_endemic.png")
OUTPUT_SCATTER_THREATENED <- file.path(OUTPUT_DIR, "priority_overlap_scatter_threatened.png")
OUTPUT_SCATTER_HOTSPOT <- file.path(OUTPUT_DIR, "priority_overlap_hotspot_scatter.png")
OUTPUT_SCATTER_HOTSPOT_TOTAL <- file.path(OUTPUT_DIR, "priority_overlap_hotspot_scatter_total.png")
OUTPUT_SCATTER_HOTSPOT_ENDEMIC <- file.path(OUTPUT_DIR, "priority_overlap_hotspot_scatter_endemic.png")
OUTPUT_Unevenness_COMBINED <- file.path(OUTPUT_DIR, "priority_overlap_unevenness.png")
OUTPUT_Unevenness_DETAILED <- file.path(OUTPUT_DIR, "priority_overlap_unevenness_detailed.png")
OUTPUT_Unevenness_TOTAL <- file.path(OUTPUT_DIR, "priority_overlap_unevenness_total.png")
OUTPUT_Unevenness_ENDEMIC <- file.path(OUTPUT_DIR, "priority_overlap_unevenness_endemic.png")
OUTPUT_Unevenness_THREATENED <- file.path(OUTPUT_DIR, "priority_overlap_unevenness_threatened.png")
OUTPUT_GDP_CORR_PLOT <- file.path(OUTPUT_DIR, "gdp_biodiversity_correlation.png")
OUTPUT_UNDERSTUDIED_DIST_PLOT <- file.path(OUTPUT_DIR, "understudied_biodiversity_distribution.png")
OUTPUT_MODELING_PLOT <- file.path(OUTPUT_DIR, "modeling_results.png")
# Load data
sensitivity <- read_csv(INPUT_SENSITIVITY, show_col_types = FALSE)
country_summary <- read_csv(INPUT_COUNTRY_SUMMARY, show_col_types = FALSE)
country_area <- read_csv(INPUT_COUNTRY_AREA, show_col_types = FALSE)

priority_countries <- read_csv(INPUT_PRIORITY_COUNTRIES, show_col_types = FALSE)
priority_countries <- priority_countries %>%
  mutate(
    iso_a3 = if ("iso3" %in% names(.)) as.character(iso3) else if ("iso_a3" %in% names(.)) as.character(iso_a3) else NA_character_
  )
total_countries <- nrow(country_summary)
understudied_countries <- sum(country_summary$study_count == 0, na.rm = TRUE)

country_summary <- country_summary %>%
  left_join(country_area %>% select(iso_a3, country_area_km2), by = "iso_a3") %>%
  mutate(
    study_density_per_1000_km2 = if_else(!is.na(country_area_km2) & country_area_km2 > 0, study_count / country_area_km2 * 1000, NA_real_)
  )

# Convert quantiles to percentile labels (top X%) and add random-expectation baselines
sensitivity <- sensitivity %>%
  mutate(
    priority_pct = 100 * (1 - quantile),
    priority_label = paste0("Top ", round(priority_pct, 0), "%"),
    priority_label = factor(priority_label,
      levels = c("Top 10%", "Top 25%", "Top 50%", "Top 75%")
    ),
    expected_overlap_pct = 100 * n_priority_countries / total_countries,
    expected_overlap_count = understudied_countries * n_priority_countries / total_countries
  ) %>%
  arrange(priority_label)

plot_metric_map <- c(
  WB_TOTAL = "Total species",
  WB_SMALL50XENDEMIC100 = "Endemic species",
  WB_TPROB80 = "Threatened species probability"
)

plot_data <- country_summary %>%
  select(iso_a3, country_name, study_count, country_area_km2, study_density_per_1000_km2, gdp_log10) %>%
  mutate(
    study_count = as.numeric(study_count),
    study_count_log = log10(study_count + 1),
    understudied = study_count == 0
  ) %>%
  left_join(
    priority_countries %>%
      filter(source %in% names(plot_metric_map)) %>%
      mutate(metric_label = recode(source, !!!plot_metric_map)) %>%
      select(iso_a3, source, metric_label, priority_score),
    by = "iso_a3"
  ) %>%
  filter(!is.na(priority_score)) %>%
  mutate(
    metric_value = as.numeric(priority_score),
    metric_density_per_1000_km2 = if_else(!is.na(country_area_km2) & country_area_km2 > 0, metric_value / country_area_km2 * 1000, NA_real_),
    metric_label = factor(metric_label, levels = unname(plot_metric_map))
  )

plot_data_hotspot <- plot_data %>%
  filter(metric_label %in% c("Total species", "Endemic species")) %>%
  filter(!is.na(country_area_km2) & country_area_km2 > 0) %>%
  mutate(
    study_density_log = log10(study_density_per_1000_km2 + 1),
    metric_density_log = log10(metric_density_per_1000_km2 + 1)
  )

make_scatter <- function(df, metric_name, output_path, plot_title, plot_subtitle, x_label) {
  metric_df <- df %>% filter(metric_label == metric_name)

  if (nrow(metric_df) == 0) {
    return(NULL)
  }

  fit <- lm(study_count_log ~ metric_value, data = metric_df)
  fit_summary <- summary(fit)
  correlation_test <- suppressWarnings(cor.test(metric_df$metric_value, metric_df$study_count_log, method = "spearman", exact = FALSE))

  stats_label <- paste0(
    "n = ", nrow(metric_df),
    "\nR2 = ", round(fit_summary$r.squared, 2),
    "\nSpearman r = ", round(unname(correlation_test$estimate), 2),
    "\np = ", format.pval(fit_summary$coefficients[2, 4], digits = 2, eps = 0.001)
  )

  label_data <- tibble(
    x_pos = quantile(metric_df$metric_value, 0.05, na.rm = TRUE),
    y_pos = max(metric_df$study_count_log, na.rm = TRUE),
    stats_label = stats_label
  )

  p <- ggplot(metric_df, aes(x = metric_value, y = study_count_log)) +
    geom_point(aes(color = understudied), alpha = 0.8, size = 2.2) +
    geom_smooth(method = "loess", se = TRUE, color = "#b22222", linewidth = 0.9, span = 0.9) +
    geom_label(
      data = label_data,
      aes(x = x_pos, y = y_pos, label = stats_label),
      inherit.aes = FALSE,
      hjust = 0,
      vjust = 1.1,
      size = 3.2,
      label.size = 0.25,
      fill = "white",
      alpha = 0.88
    ) +
    theme_endo_bw(base_size = 12) +
    labs(
      title = plot_title,
      subtitle = plot_subtitle,
      x = x_label,
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

  ggsave(output_path, p, width = 6.5, height = 4.5, dpi = 300, bg = "white")
  return(p)
}

# ===== PLOT 1: Observed vs expected overlap (percent) =====
p1 <- ggplot(sensitivity, aes(x = priority_label, group = 1)) +
  geom_line(aes(y = expected_overlap_pct, color = "Expected by chance"), linewidth = 1.0, linetype = "dashed") +
  geom_point(aes(y = expected_overlap_pct, color = "Expected by chance"), size = 2.8) +
  geom_line(aes(y = pct_understudied_overlapping, color = "Observed understudied overlap"), linewidth = 1.1) +
  geom_point(aes(y = pct_understudied_overlapping, color = "Observed understudied overlap"), size = 3.2) +
  geom_text(
    aes(y = pct_understudied_overlapping, label = paste0(round(pct_understudied_overlapping, 1), "%")),
    vjust = -0.9,
    fontface = "bold",
    size = 3.8,
    color = "#222222"
  ) +
  scale_color_manual(
    values = c(
      "Observed understudied overlap" = "#E24A33",
      "Expected by chance" = "#7A7A7A"
    ),
    name = NULL
  ) +
  scale_y_continuous(limits = c(0, 100), breaks = seq(0, 100, 20)) +
  labs(
    x = "Priority Level (World Bank Biodiversity Metrics)",
    y = "Understudied Endophyte Countries (%)",
    title = "Understudied Endophyte Regions are Concentrated in High-Priority Biodiversity Areas",
    subtitle = paste0(understudied_countries, " understudied countries compared against ", total_countries, " total countries")
  ) +
  theme_endo_bw() +
  theme(
    plot.title = element_text(size = 13, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 10, hjust = 0.5, color = "gray40", margin = margin(b = 10)),
    axis.title = element_text(size = 11, face = "bold"),
    axis.text = element_text(size = 10),
    panel.grid.major.x = element_blank(),
    panel.grid.minor.y = element_blank(),
    legend.position = "top"
  )

ggsave(OUTPUT_PLOT, p1, width = 6.5, height = 5, dpi = 300, bg = "white")
cat("Main plot saved to:", OUTPUT_PLOT, "\n")

# ===== PLOT 2: Observed vs expected counts =====
p2 <- ggplot(sensitivity, aes(x = priority_label, group = 1)) +
  geom_linerange(aes(ymin = expected_overlap_count, ymax = n_overlap_countries, color = "Observed minus expected"), linewidth = 1.2) +
  geom_point(aes(y = n_overlap_countries, color = "Observed overlap"), size = 3.2) +
  geom_point(aes(y = expected_overlap_count, color = "Expected overlap"), size = 2.8, shape = 17) +
  geom_text(
    aes(y = n_overlap_countries, label = n_overlap_countries),
    vjust = -0.9,
    fontface = "bold",
    size = 3.6,
    color = "#222222"
  ) +
  scale_color_manual(
    values = c(
      "Observed overlap" = "#E24A33",
      "Expected overlap" = "#7A7A7A",
      "Observed minus expected" = "#C0C0C0"
    ),
    name = NULL
  ) +
  labs(
    x = "Priority Level",
    y = "Number of Understudied Countries",
    title = "Observed Overlap Versus Random Expectation"
  ) +
  theme_endo_bw() +
  theme(
    plot.title = element_text(size = 11, face = "bold", hjust = 0.5),
    axis.title = element_text(size = 10, face = "bold"),
    panel.grid.major.x = element_blank(),
    panel.grid.minor.y = element_blank(),
    legend.position = "top"
  )

p2_combined <- grid.arrange(
  p1,
  p2,
  ncol = 1,
  heights = c(1.15, 0.95),
  top = grid::textGrob(
    "Priority Overlap Analysis",
    gp = grid::gpar(fontsize = 13, fontface = "bold")
  )
)

ggsave(OUTPUT_PLOT_DETAILED, p2_combined, width = 6.5, height = 8, dpi = 300, bg = "white")
cat("Detailed plot saved to:", OUTPUT_PLOT_DETAILED, "\n")

# ===== PLOT 3: Metric scatter plots (combined + standalone) =====
scatter_total <- make_scatter(
  plot_data,
  "Total species",
  OUTPUT_SCATTER_TOTAL,
  "Endophyte Study Effort vs World Bank Total Species Richness",
  paste0("WB_TOTAL; understudied countries highlighted (n = ", understudied_countries, ")"),
  "World Bank total species count"
)

scatter_endemic <- make_scatter(
  plot_data,
  "Endemic species",
  OUTPUT_SCATTER_ENDEMIC,
  "Endophyte Study Effort vs World Bank Endemic Species Richness",
  paste0("WB_SMALL50XENDEMIC100; understudied countries highlighted (n = ", understudied_countries, ")"),
  "World Bank endemic species count"
)

scatter_threatened <- make_scatter(
  plot_data,
  "Threatened species probability",
  OUTPUT_SCATTER_THREATENED,
  "Endophyte Study Effort vs World Bank Threatened Species Probability",
  paste0("WB_TPROB80; understudied countries highlighted (n = ", understudied_countries, ")"),
  "World Bank threatened species probability"
)

# ===== PLOT 3B: Area-normalized hotspot plots (count metrics only) =====
make_hotspot_scatter <- function(df, metric_name, output_path, plot_title, plot_subtitle, x_label) {
  metric_df <- df %>% filter(metric_label == metric_name)

  if (nrow(metric_df) == 0) {
    return(NULL)
  }

  fit <- lm(study_density_log ~ metric_density_log, data = metric_df)
  fit_summary <- summary(fit)
  correlation_test <- suppressWarnings(cor.test(metric_df$metric_density_log, metric_df$study_density_log, method = "spearman", exact = FALSE))

  stats_label <- paste0(
    "n = ", nrow(metric_df),
    "\nR2 = ", round(fit_summary$r.squared, 2),
    "\nSpearman r = ", round(unname(correlation_test$estimate), 2),
    "\np = ", format.pval(fit_summary$coefficients[2, 4], digits = 2, eps = 0.001)
  )

  label_data <- tibble(
    x_pos = quantile(metric_df$metric_density_log, 0.05, na.rm = TRUE),
    y_pos = max(metric_df$study_density_log, na.rm = TRUE),
    stats_label = stats_label
  )

  p <- ggplot(metric_df, aes(x = metric_density_log, y = study_density_log)) +
    geom_point(aes(color = understudied), alpha = 0.8, size = 2.2) +
    geom_smooth(method = "loess", se = TRUE, color = "#6a3d9a", linewidth = 0.9, span = 0.9) +
    geom_label(
      data = label_data,
      aes(x = x_pos, y = y_pos, label = stats_label),
      inherit.aes = FALSE,
      hjust = 0,
      vjust = 1.1,
      size = 3.2,
      label.size = 0.25,
      fill = "white",
      alpha = 0.88
    ) +
    theme_endo_bw(base_size = 12) +
    labs(
      title = plot_title,
      subtitle = plot_subtitle,
      x = x_label,
      y = "log10(study density per 1000 km^2 + 1)"
    ) +
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

  ggsave(output_path, p, width = 6.5, height = 4.5, dpi = 300, bg = "white")
  return(p)
}

hotspot_total <- make_hotspot_scatter(
  plot_data_hotspot,
  "Total species",
  OUTPUT_SCATTER_HOTSPOT_TOTAL,
  "Endophyte Study Density vs Total-Species Density",
  paste0("Area-normalized hotspot view; countries with land area matched from FAOSTAT (n = ", sum(!is.na(plot_data_hotspot$country_area_km2)), ")"),
  "log10(World Bank total species per 1000 km^2 + 1)"
)

hotspot_endemic <- make_hotspot_scatter(
  plot_data_hotspot,
  "Endemic species",
  OUTPUT_SCATTER_HOTSPOT_ENDEMIC,
  "Endophyte Study Density vs Endemic-Species Density",
  paste0("Area-normalized hotspot view; countries with land area matched from FAOSTAT (n = ", sum(!is.na(plot_data_hotspot$country_area_km2)), ")"),
  "log10(World Bank endemic species per 1000 km^2 + 1)"
)

hotspot_combined <- plot_data_hotspot %>%
  ggplot(aes(x = metric_density_log, y = study_density_log)) +
  geom_point(aes(color = understudied), alpha = 0.75, size = 1.9) +
  geom_smooth(method = "loess", se = TRUE, color = "#6a3d9a", linewidth = 0.8, span = 0.9) +
  facet_wrap(~ metric_label, scales = "free_x", nrow = 1) +
  theme_endo_bw(base_size = 11) +
  labs(
    title = "Endophyte Study Density vs Area-Normalized Biodiversity Hotspots",
    subtitle = "Counts were normalized by FAOSTAT country area; only count-based World Bank metrics are shown",
    x = NULL,
    y = "log10(study density per 1000 km^2 + 1)"
  ) +
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

ggsave(OUTPUT_SCATTER_HOTSPOT, hotspot_combined, width = 6.5, height = 4, dpi = 300, bg = "white")
cat("Combined hotspot-density plot saved to:", OUTPUT_SCATTER_HOTSPOT, "\n")

if (!is.null(hotspot_total)) cat("Standalone hotspot total-species plot saved to:", OUTPUT_SCATTER_HOTSPOT_TOTAL, "\n")
if (!is.null(hotspot_endemic)) cat("Standalone hotspot endemic-species plot saved to:", OUTPUT_SCATTER_HOTSPOT_ENDEMIC, "\n")

facet_plot <- plot_data %>%
  mutate(metric_label = factor(metric_label, levels = unname(plot_metric_map))) %>%
  ggplot(aes(x = metric_value, y = study_count_log)) +
  geom_point(aes(color = understudied), alpha = 0.8, size = 1.9) +
  geom_smooth(method = "loess", se = TRUE, color = "#b22222", linewidth = 0.8, span = 0.9) +
  facet_wrap(~ metric_label, scales = "free_x", nrow = 1) +
  theme_endo_bw(base_size = 11) +
  labs(
    title = "Endophyte Study Effort vs World Bank Biodiversity Metrics",
    subtitle = "Each panel shows a different World Bank richness metric; understudied countries are highlighted",
    x = NULL,
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
  geom_label(
    data = plot_data %>%
      group_by(metric_label) %>%
      summarise(
        x_pos = quantile(metric_value, 0.05, na.rm = TRUE),
        y_pos = max(study_count_log, na.rm = TRUE),
        stats_label = paste0(
          "n = ", n(),
          "\nR2 = ", round(summary(lm(study_count_log ~ metric_value))$r.squared, 2),
          "\nSpearman r = ", round(unname(cor.test(metric_value, study_count_log, method = "spearman", exact = FALSE)$estimate), 2),
          "\np = ", format.pval(summary(lm(study_count_log ~ metric_value))$coefficients[2, 4], digits = 2, eps = 0.001)
        ),
        .groups = "drop"
      ),
    aes(x = x_pos, y = y_pos, label = stats_label),
    inherit.aes = FALSE,
    hjust = 0,
    vjust = 1.1,
    size = 3,
    label.size = 0.25,
    fill = "white",
    alpha = 0.88
  ) +
  theme(
    plot.title = element_text(face = "bold"),
    plot.subtitle = element_text(color = "gray40"),
    panel.grid.major.x = element_blank(),
    legend.position = "top"
  )

ggsave(OUTPUT_SCATTER_COMBINED, facet_plot, width = 6.5, height = 4.5, dpi = 300, bg = "white")
cat("Combined scatter plot saved to:", OUTPUT_SCATTER_COMBINED, "\n")

if (!is.null(scatter_total)) cat("Standalone total-species scatter saved to:", OUTPUT_SCATTER_TOTAL, "\n")
if (!is.null(scatter_endemic)) cat("Standalone endemic-species scatter saved to:", OUTPUT_SCATTER_ENDEMIC, "\n")
if (!is.null(scatter_threatened)) cat("Standalone threatened-probability scatter saved to:", OUTPUT_SCATTER_THREATENED, "\n")

# ===== PLOT 4: Study-count unevenness across biodiversity-metric quartiles =====
unevenness_data <- plot_data %>%
  group_by(metric_label) %>%
  mutate(metric_quartile = ntile(metric_value, 4)) %>%
  ungroup() %>%
  mutate(
    metric_quartile = factor(
      metric_quartile,
      levels = c(1, 2, 3, 4),
      labels = c("Q1 (lowest)", "Q2", "Q3", "Q4 (highest)")
    )
  )

unevenness_stats <- unevenness_data %>%
  group_by(metric_label) %>%
  summarise(
    x_pos = 1.5,
    y_pos = max(study_count, na.rm = TRUE),
    p_value = suppressWarnings(kruskal.test(study_count ~ metric_quartile)$p.value),
    median_low = median(study_count[metric_quartile == "Q1 (lowest)"], na.rm = TRUE),
    median_high = median(study_count[metric_quartile == "Q4 (highest)"], na.rm = TRUE),
    stats_label = paste0(
      "Kruskal-Wallis p = ", format.pval(p_value, digits = 2, eps = 0.001),
      "\nmedian Q1 = ", round(median_low, 1),
      "\nmedian Q4 = ", round(median_high, 1)
    ),
    .groups = "drop"
  )

unevenness_plot <- unevenness_data %>%
  ggplot(aes(x = metric_quartile, y = study_count)) +
  geom_boxplot(aes(fill = metric_quartile), outlier.shape = NA, alpha = 0.75, width = 0.7) +
  geom_jitter(aes(color = understudied), width = 0.12, alpha = 0.45, size = 1.2) +
  facet_wrap(~ metric_label, scales = "free_y") +
  geom_label(
    data = unevenness_stats,
    aes(x = x_pos, y = y_pos, label = stats_label),
    inherit.aes = FALSE,
    hjust = 0,
    vjust = 1.1,
    size = 3,
    label.size = 0.25,
    fill = "white",
    alpha = 0.88
  ) +
  scale_fill_manual(
    values = c(
      "Q1 (lowest)" = "#d9d9d9",
      "Q2" = "#a6bddb",
      "Q3" = "#74a9cf",
      "Q4 (highest)" = "#0570b0"
    ),
    guide = "none"
  ) +
  scale_color_manual(
    values = c(
      `TRUE` = "#E24A33",
      `FALSE` = "#1f78b4"
    ),
    labels = c("Studied countries", "Understudied countries"),
    name = NULL
  ) +
  scale_y_continuous(labels = comma) +
  theme_endo_bw(base_size = 11) +
  labs(
    title = "Are Study Counts Uneven Across Biodiversity-Priority Quartiles?",
    subtitle = "Each panel bins countries by one World Bank biodiversity metric; higher quartiles should reveal lower study effort if bias is uneven",
    x = "Biodiversity priority quartile",
    y = "Endophyte study count"
  ) +
  theme(
    plot.title = element_text(face = "bold"),
    plot.subtitle = element_text(color = "gray40"),
    axis.title = element_text(face = "bold"),
    panel.grid.major.x = element_blank(),
    legend.position = "top"
  )

ggsave(OUTPUT_Unevenness_COMBINED, unevenness_plot, width = 6.5, height = 4.5, dpi = 300, bg = "white")
cat("Combined unevenness plot saved to:", OUTPUT_Unevenness_COMBINED, "\n")

unevenness_detailed <- unevenness_plot +
  theme(strip.text = element_text(face = "bold"))

ggsave(OUTPUT_Unevenness_DETAILED, unevenness_detailed, width = 6.5, height = 4.5, dpi = 300, bg = "white")
cat("Detailed unevenness plot saved to:", OUTPUT_Unevenness_DETAILED, "\n")

make_unevenness_plot <- function(df, metric_name, output_path, plot_title) {
  metric_df <- df %>% filter(metric_label == metric_name)
  if (nrow(metric_df) == 0) {
    return(NULL)
  }

  metric_df <- metric_df %>%
    mutate(
      metric_quartile = ntile(metric_value, 4),
      metric_quartile = factor(
        metric_quartile,
        levels = c(1, 2, 3, 4),
        labels = c("Q1 (lowest)", "Q2", "Q3", "Q4 (highest)")
      )
    )

  kw_test <- kruskal.test(study_count ~ metric_quartile, data = metric_df)
  quartile_medians <- metric_df %>%
    group_by(metric_quartile) %>%
    summarise(median_study_count = median(study_count, na.rm = TRUE), .groups = "drop")

  label_data <- tibble(
    x_pos = 1.5,
    y_pos = max(metric_df$study_count, na.rm = TRUE),
    stats_label = paste0(
      "Kruskal-Wallis p = ", format.pval(kw_test$p.value, digits = 2, eps = 0.001),
      "\nmedian Q1 = ", round(quartile_medians$median_study_count[quartile_medians$metric_quartile == "Q1 (lowest)"], 1),
      "\nmedian Q4 = ", round(quartile_medians$median_study_count[quartile_medians$metric_quartile == "Q4 (highest)"], 1)
    )
  )

  p <- ggplot(metric_df, aes(x = metric_quartile, y = study_count)) +
    geom_boxplot(aes(fill = metric_quartile), outlier.shape = NA, alpha = 0.75, width = 0.7) +
    geom_jitter(aes(color = understudied), width = 0.12, alpha = 0.45, size = 1.2) +
    geom_label(
      data = label_data,
      aes(x = x_pos, y = y_pos, label = stats_label),
      inherit.aes = FALSE,
      hjust = 0,
      vjust = 1.1,
      size = 3,
      label.size = 0.25,
      fill = "white",
      alpha = 0.88
    ) +
    scale_fill_manual(
      values = c(
        "Q1 (lowest)" = "#d9d9d9",
        "Q2" = "#a6bddb",
        "Q3" = "#74a9cf",
        "Q4 (highest)" = "#0570b0"
      ),
      guide = "none"
    ) +
    scale_color_manual(
      values = c(
        `TRUE` = "#E24A33",
        `FALSE` = "#1f78b4"
      ),
      labels = c("Studied countries", "Understudied countries"),
      name = NULL
    ) +
    scale_y_continuous(labels = comma) +
    theme_endo_bw(base_size = 11) +
    labs(
      title = plot_title,
      subtitle = "Countries are grouped into quartiles of the selected World Bank metric",
      x = "Biodiversity priority quartile",
      y = "Endophyte study count"
    ) +
    theme(
      plot.title = element_text(face = "bold"),
      plot.subtitle = element_text(color = "gray40"),
      axis.title = element_text(face = "bold"),
      panel.grid.major.x = element_blank(),
      legend.position = "top"
    )

  ggsave(output_path, p, width = 6.5, height = 4.5, dpi = 300, bg = "white")
  return(p)
}

uneven_total <- make_unevenness_plot(plot_data, "Total species", OUTPUT_Unevenness_TOTAL, "Study Counts Across Total-Species Quartiles")
uneven_endemic <- make_unevenness_plot(plot_data, "Endemic species", OUTPUT_Unevenness_ENDEMIC, "Study Counts Across Endemic-Species Quartiles")
uneven_threatened <- make_unevenness_plot(plot_data, "Threatened species probability", OUTPUT_Unevenness_THREATENED, "Study Counts Across Threatened-Species-Probability Quartiles")

if (!is.null(uneven_total)) cat("Standalone unevenness plot saved to:", OUTPUT_Unevenness_TOTAL, "\n")
if (!is.null(uneven_endemic)) cat("Standalone unevenness plot saved to:", OUTPUT_Unevenness_ENDEMIC, "\n")
if (!is.null(uneven_threatened)) cat("Standalone unevenness plot saved to:", OUTPUT_Unevenness_THREATENED, "\n")

# ===== PLOT 5: GDP vs Biodiversity and Study Count =====

gdp_corr_data <- plot_data %>%
  select(metric_label, gdp_log10, study_count_log, metric_value, metric_density_per_1000_km2) %>%
  pivot_longer(
    cols = c(study_count_log, metric_value, metric_density_per_1000_km2),
    names_to = "measure",
    values_to = "value"
  ) %>%
  mutate(
    measure = factor(measure, levels = c("study_count_log", "metric_value", "metric_density_per_1000_km2"),
                     labels = c("log10(Study Count + 1)", "Raw Biodiversity Metric", "Biodiversity Density (per 1000 km²)"))
  ) %>%
  filter(!(measure == "Biodiversity Density (per 1000 km²)" & metric_label == "Threatened species probability"))

gdp_corr_plot <- ggplot(gdp_corr_data, aes(x = gdp_log10, y = value)) +
  geom_point(alpha = 0.5) +
  geom_smooth(method = "loess", se = FALSE) +
  facet_grid(measure ~ metric_label, scales = "free_y") +
  labs(
    title = "GDP, Biodiversity, and Research Effort",
    subtitle = "Relationships between log10(GDP), biodiversity metrics, and study counts",
    x = "log10(GDP)",
    y = ""
  ) +
  theme_endo_bw(base_size = 11) +
  theme(
    plot.title = element_text(face = "bold"),
    plot.subtitle = element_text(color = "gray40"),
    axis.title = element_text(face = "bold"),
    strip.text = element_text(face = "bold")
  )

ggsave(OUTPUT_GDP_CORR_PLOT, gdp_corr_plot, width = 6.5, height = 5, dpi = 300, bg = "white")
cat("GDP correlation plot saved to:", OUTPUT_GDP_CORR_PLOT, "\n")

# ===== PLOT 6: Biodiversity Distribution of Studied vs. Understudied Countries =====

plot_data_dist <- plot_data %>%
  mutate(
    understudied_cat = case_when(
      study_count < 10 ~ "Low (0-9)",
      study_count < 100 ~ "Medium (10-99)",
      TRUE ~ "High (>=100)"
    ),
    understudied_cat = factor(understudied_cat, levels = c("High (>=100)", "Medium (10-99)", "Low (0-9)"))
  )

dist_plot <- ggplot(plot_data_dist, aes(x = understudied_cat, y = log10(metric_value + 1), fill = understudied_cat)) +
  geom_boxplot(outlier.shape = NA, alpha = 0.8) +
  geom_jitter(width = 0.15, alpha = 0.2, size=0.7) +
  facet_wrap(~ metric_label, scales = "free_y") +
  stat_compare_means(comparisons = list(c("High (>=100)", "Low (0-9)"), c("High (>=100)", "Medium (10-99)")),
                     method = "wilcox.test", label = "p.signif") +
  scale_fill_brewer(palette = "RdYlBu", direction = -1) +
  labs(
    title = "Biodiversity Distribution by Study Effort",
    subtitle = "Comparison of biodiversity metrics for countries with different levels of endophyte research",
    x = "Study Effort Category",
    y = "log10(Biodiversity Metric Value + 1)"
  ) +
  theme_endo_bw(base_size = 11) +
  theme(
    plot.title = element_text(face = "bold"),
    plot.subtitle = element_text(color = "gray40"),
    axis.title = element_text(face = "bold"),
    strip.text = element_text(face = "bold"),
    legend.position = "none",
    axis.text.x = element_text(angle = 15, hjust = 1)
  )

ggsave(OUTPUT_UNDERSTUDIED_DIST_PLOT, dist_plot, width = 6.5, height = 5, dpi = 300, bg = "white")
cat("Understudied distribution plot saved to:", OUTPUT_UNDERSTUDIED_DIST_PLOT, "\n")

# ===== PLOT 7: Modeling Results =====

modeling_results <- read_csv("results/biodiversity_priority_overlap/modeling_results.csv", show_col_types = FALSE)

modeling_plot_data <- modeling_results %>%
  filter(variable != "Intercept", model == "raw") %>%
  mutate(
    variable = recode(variable,
                      "gdp_log10" = "log10(GDP)",
                      "metric_value" = "Biodiversity Metric (Raw)"
    )
  )

modeling_plot <- ggplot(modeling_plot_data, aes(x = coefficient, y = variable, color = p_value < 0.05)) +
  geom_point(size = 3) +
  geom_errorbarh(aes(xmin = coefficient - 1.96 * p_value, xmax = coefficient + 1.96 * p_value), height = 0.2) +
  facet_wrap(~ metric, nrow = 1) +
  geom_vline(xintercept = 0, linetype = "dashed", color = "gray50") +
  labs(
    title = "Predictors of Endophyte Study Effort (Raw Counts)",
    subtitle = "Coefficients from multiple regression models. Error bars represent 95% confidence intervals.",
    x = "Coefficient",
    y = ""
  ) +
  scale_color_manual(values = c("gray50", "firebrick"), name = "Significant (p < 0.05)") +
  theme_endo_bw(base_size = 11) +
  theme(
    plot.title = element_text(face = "bold"),
    plot.subtitle = element_text(color = "gray40"),
    axis.title = element_text(face = "bold"),
    strip.text = element_text(face = "bold"),
    legend.position = "bottom"
  )

ggsave(OUTPUT_MODELING_PLOT, modeling_plot, width = 6.5, height = 6, dpi = 300, bg = "white")
cat("Modeling results plot saved to:", OUTPUT_MODELING_PLOT, "\n")

# ===== PLOT 8: Correlation Heatmap =====

corr_data <- plot_data %>%
  select(study_count_log, gdp_log10, metric_value, metric_density_per_1000_km2, metric_label) %>%
  rename(
    `log10(Study Count)` = study_count_log,
    `log10(GDP)` = gdp_log10,
    `Biodiversity (Raw)` = metric_value,
    `Biodiversity (Density)` = metric_density_per_1000_km2
  )

corr_matrix <- corr_data %>%
  group_by(metric_label) %>%
  summarise(
    cor = list(cor(across(`log10(Study Count)`:`Biodiversity (Density)`), method = "spearman", use = "pairwise.complete.obs"))
  )

corr_plots <- lapply(setNames(nm = unique(corr_data$metric_label)), function(metric) {
  cormat <- corr_matrix$cor[[which(corr_matrix$metric_label == metric)]]
  melted_cormat <- melt(cormat)
  
  ggplot(data = melted_cormat, aes(x=Var1, y=Var2, fill=value)) +
    geom_tile() +
    geom_text(aes(label = round(value, 2)), color = "white", size = 4) +
    scale_fill_gradient2(low = "blue", high = "red", mid = "white",
                         midpoint = 0, limit = c(-1,1), space = "Lab",
                         name="Spearman\nCorrelation") +
    theme_minimal() +
    theme(axis.text.x = element_text(angle = 45, vjust = 1, size = 10, hjust = 1)) +
    coord_fixed() +
    labs(title = metric, x = "", y = "")
})

corr_heatmap <- ggarrange(plotlist = corr_plots, ncol = 3, common.legend = TRUE, legend = "right")

ggsave(file.path(OUTPUT_DIR, "correlation_heatmap.png"), corr_heatmap, width = 6.5, height = 3, dpi = 300, bg = "white")
cat("Correlation heatmap saved to:", file.path(OUTPUT_DIR, "correlation_heatmap.png"), "\n")


cat("\nPlots complete\n")
