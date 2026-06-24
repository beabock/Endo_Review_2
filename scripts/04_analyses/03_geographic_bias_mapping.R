#!/usr/bin/env Rscript
# BMB 2026-06-05
# Makes the interactive Leaflet map and static heatmaps showing study density by country.

library(dplyr)
library(readr)
library(tidyr)
library(ggplot2)
library(leaflet)
library(sf)
library(rnaturalearth)
library(scales)

source("scripts/05_plotting/theme_utils.R")

INPUT_FILE <- "data/country_enriched_data.csv"
RESULTS_DIR <- "results/country_analysis"
INTERACTIVE_MAP_FILE <- file.path(RESULTS_DIR, "interactive_study_density.html")
BIAS_METRICS_FILE <- file.path(RESULTS_DIR, "geographic_bias_metrics.csv")
CONTINENTAL_FILE <- file.path(RESULTS_DIR, "continental_breakdown.csv")
BIAS_HEATMAP_FILE <- file.path(RESULTS_DIR, "geographic_bias_heatmap.png")

if (!file.exists(INPUT_FILE)) {
  stop("Input file not found: ", INPUT_FILE)
}

if (!dir.exists(RESULTS_DIR)) {
  dir.create(RESULTS_DIR, recursive = TRUE, showWarnings = FALSE)
}

message("Loading country-enriched data...")
country_data <- read_csv(INPUT_FILE, show_col_types = FALSE) %>%
  mutate(
    study_count = as.numeric(study_count),
    centroid_lat = as.numeric(centroid_lat),
    centroid_lon = as.numeric(centroid_lon),
    gdp_current_usd = as.numeric(gdp_current_usd),
    gdp_log10 = ifelse(!is.na(gdp_current_usd) & gdp_current_usd > 0, 
                       log10(gdp_current_usd), NA_real_)
  )

# Load world map with continent information
message("Loading world map...")
world <- ne_countries(scale = 50, returnclass = "sf")

# Join study data with world map
world_data <- world %>%
  left_join(
    country_data %>% select(iso_a3, country_name, study_count, gdp_current_usd, gdp_log10),
    by = c("iso_a3" = "iso_a3")
  ) %>%
  mutate(
    study_count = replace_na(study_count, 0),
    continent = as.character(continent),
    # For countries without ISO match, try to get continent from spatial join
    continent = ifelse(is.na(continent), "Unknown", continent)
  )

message("Computing geographic bias metrics...")

# Global statistics
total_studies <- sum(country_data$study_count, na.rm = TRUE)
countries_with_studies <- nrow(country_data %>% filter(study_count > 0))
total_countries <- nrow(country_data)

# Percentiles for bias classification
p75 <- quantile(country_data$study_count, 0.75, na.rm = TRUE)
p90 <- quantile(country_data$study_count, 0.90, na.rm = TRUE)
p25 <- quantile(country_data$study_count, 0.25, na.rm = TRUE)

# Classify countries as over/under-studied relative to GDP (if available)
bias_metrics <- country_data %>%
  mutate(
    # Global percentile ranking
    study_count_percentile = percent_rank(study_count),
    # Classification
    bias_class = case_when(
      study_count == 0 ~ "No studies",
      study_count_percentile >= 0.90 ~ "Over-studied (top 10%)",
      study_count_percentile >= 0.75 ~ "Well-studied (top 25%)",
      study_count_percentile >= 0.50 ~ "Moderate coverage (top 50%)",
      study_count_percentile >= 0.25 ~ "Under-studied (bottom 50%)",
      TRUE ~ "Rare/minimal coverage"
    ),
    # GDP bias: if high GDP but low studies, it's a bias
    gdp_studies_ratio = ifelse(!is.na(gdp_log10), study_count / (10^(gdp_log10 / 10)), NA_real_),
    gdp_bias_class = case_when(
      is.na(gdp_log10) ~ "GDP unknown",
      gdp_log10 < 20 & study_count > p90 ~ "Developing + high studies (research focus)",
      gdp_log10 < 20 & study_count < 5 ~ "Developing + low studies (biased)",
      gdp_log10 >= 24 & study_count < p25 ~ "Developed + low studies (biased)",
      gdp_log10 >= 24 & study_count >= p90 ~ "Developed + high studies (natural)",
      TRUE ~ "Balanced"
    )
  ) %>%
  select(iso_a3, country_name, study_count, study_count_percentile, bias_class, 
         gdp_current_usd, gdp_log10, gdp_bias_class) %>%
  arrange(desc(study_count))

write_csv(bias_metrics, BIAS_METRICS_FILE)

message("Computing continental breakdown...")

continental_data <- world_data %>%
  st_drop_geometry() %>%
  filter(!is.na(continent), continent != "Unknown") %>%
  group_by(continent) %>%
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
    concentration = total_studies / sum(total_studies) * 100
  ) %>%
  arrange(desc(total_studies))

write_csv(continental_data, CONTINENTAL_FILE)

cat("\nContinental breakdown:\n")
print(continental_data)

message("Creating interactive leaflet map...")

# Prepare data for leaflet
map_data <- country_data %>%
  left_join(
    world %>% 
      st_drop_geometry() %>% 
      select(iso_a3, name, continent) %>%
      rename(country_name_world = name),
    by = "iso_a3"
  ) %>%
  filter(!is.na(centroid_lat), !is.na(centroid_lon))

# Color palette based on study count (log scale for better visualization)
map_data <- map_data %>%
  mutate(study_count_log = log10(study_count + 1))

# Create color function using bins to handle tied values gracefully
bins <- quantile(map_data$study_count_log, probs = seq(0, 1, by = 0.14), include.lowest = TRUE)
# Remove duplicates from bins (handles case where many countries have same count)
bins <- unique(bins)
if (length(bins) < 3) {
  bins <- pretty(map_data$study_count_log, n = 5)
}

color_func <- colorBin(
  palette = "YlOrRd",
  domain = map_data$study_count_log,
  bins = bins,
  na.color = "#D3D3D3"
)

# Build interactive map
interactive_map <- leaflet(map_data) %>%
  addTiles(urlTemplate = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png") %>%
  addCircles(
    lng = ~centroid_lon,
    lat = ~centroid_lat,
    radius = ~sqrt(study_count + 1) * 50000,
    popup = ~paste(
      "<strong>", country_name, "</strong><br>",
      "ISO: ", iso_a3, "<br>",
      "Studies: ", study_count, "<br>",
      ifelse(!is.na(gdp_current_usd), 
             paste("GDP (USD): ", format(gdp_current_usd, big.mark = ","), "<br>"), 
             ""),
      "Continent: ", country_name_world, "<br>"
    ),
    color = ~color_func(study_count_log),
    weight = 2,
    opacity = 0.8,
    fillOpacity = 0.6
  ) %>%
  addLegend(
    pal = color_func,
    values = ~study_count_log,
    title = "Studies per Country<br/>(log10 scale)",
    position = "bottomright",
    opacity = 0.7,
    layerId = "legend"
  ) %>%
  setView(lng = 0, lat = 20, zoom = 3)

htmlwidgets::saveWidget(interactive_map, file = INTERACTIVE_MAP_FILE)
cat("  Saved: ", INTERACTIVE_MAP_FILE, "\n", sep = "")

message("Creating regional heatmap...")

# Create a heatmap of continents vs bias classes
heatmap_data <- world_data %>%
  st_drop_geometry() %>%
  filter(!is.na(continent), continent != "Unknown") %>%
  left_join(
    bias_metrics %>% select(iso_a3, bias_class),
    by = "iso_a3"
  ) %>%
  mutate(bias_class = replace_na(bias_class, "No studies")) %>%
  group_by(continent, bias_class) %>%
  summarise(count = n(), .groups = "drop") %>%
  mutate(
    continent = reorder(continent, desc(continent)),
    bias_class = factor(bias_class, levels = c(
      "Over-studied (top 10%)",
      "Well-studied (top 25%)",
      "Moderate coverage (top 50%)",
      "Under-studied (bottom 50%)",
      "Rare/minimal coverage",
      "No studies"
    ))
  )

heatmap_plot <- ggplot(heatmap_data, aes(x = bias_class, y = continent, fill = count)) +
  geom_tile(color = "white", linewidth = 0.5) +
  geom_text(aes(label = count), size = 3.5, color = "black") +
  scale_fill_gradient(low = "#f7fbff", high = "#08306b", name = "Number of countries") +
  scale_x_discrete(position = "top") +
  labs(
    title = "Geographic Distribution of Research Effort by Continent",
    subtitle = "Countries classified by study concentration",
    x = NULL,
    y = "Continent"
  ) +
  theme_endo_bw(base_size = 11) +
  theme(
    axis.text.x = element_text(angle = 45, hjust = 0, vjust = 1, size = 9),
    axis.text.y = element_text(size = 10),
    legend.position = "right"
  )

ggsave(BIAS_HEATMAP_FILE, heatmap_plot, width = 11, height = 7, dpi = 300)
cat("  Saved: ", BIAS_HEATMAP_FILE, "\n", sep = "")

message("\nGeographic bias mapping complete.")
message("Total studies across all countries: ", total_studies)
message("Countries with >=1 study: ", countries_with_studies, " / ", total_countries)
message("Top 5 countries by study count:")
print(bias_metrics %>% slice_head(n = 5) %>% select(country_name, study_count, bias_class))

message("\nOutput files:")
message("  - Interactive map: ", INTERACTIVE_MAP_FILE)
message("  - Bias metrics: ", BIAS_METRICS_FILE)
message("  - Continental summary: ", CONTINENTAL_FILE)
message("  - Bias heatmap: ", BIAS_HEATMAP_FILE)
