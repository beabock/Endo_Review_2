# BMB 2026-06-05
# Static geographic maps (Robinson projection) showing study density by country
# and top-ranked countries.

library(rnaturalearth)
library(sf)
library(ggplot2)
library(readr)
library(ggrepel)
library(dplyr)
library(forcats)
library(grid)
library(ggnewscale)
library(viridisLite)

source("scripts/utils/disputed_territory_parent_iso.R")
source("scripts/05_plotting/theme_utils.R")

# Load the enriched country-level data
country_papers <- read.csv("data/country_enriched_data.csv") %>%
  mutate(
    study_count = as.numeric(study_count),
    study_count_plot = log10(study_count + 1)
  ) %>%
  distinct(iso_a3, .keep_all = TRUE)

# Load world map
world <- ne_countries(scale = 50, returnclass = "sf") %>%
  apply_disputed_parent_iso_world() %>%
  filter(!is.na(iso_a3), iso_a3 != "-99")

world_lookup <- world %>%
  st_drop_geometry() %>%
  distinct(iso_a3, .keep_all = TRUE) %>%
  select(iso_a3, name)

# Join study counts with world map data
world_data <- world %>%
  left_join(country_papers, by = c("iso_a3" = "iso_a3"), relationship = "many-to-one")

# Build explicit status labels for countries in the world map.
country_status <- world_lookup %>%
  left_join(country_papers %>% select(iso_a3, study_count), by = "iso_a3", relationship = "many-to-one") %>%
  mutate(
    data_status = case_when(
      is.na(study_count) ~ "NA",
      study_count == 0 ~ "0",
      study_count > 0 ~ ">0"
    )
  )

# Transform to Robinson projection
robinson_proj <- "+proj=robin"
world_robinson <- st_transform(world_data, robinson_proj)

# Create the map with a smooth gradient while compressing extreme outliers
legend_breaks <- c(0, 1, 2, 5, 10, 25, 50, 100, 250, 500, 1000)
legend_breaks <- legend_breaks[legend_breaks <= max(world_robinson$study_count, na.rm = TRUE)]

map <- ggplot() +
  # draw all countries with continuous gradient (viridisLite palette)
  geom_sf(data = world_robinson, aes(fill = study_count_plot), color = "white", linewidth = 0.2) +
  scale_fill_gradientn(
    colours = viridisLite::viridis(256, option = "mako", direction = -1),
    name = "Studies per country",
    breaks = log10(legend_breaks + 1),
    labels = scales::label_number(accuracy = 1)(legend_breaks),
    na.value = "#EEEEEE",
    oob = scales::squish
  ) +
  guides(fill = guide_colorbar(barwidth = unit(12, "cm"), barheight = unit(0.45, "cm"), title.position = "top", label.position = "bottom", order = 1)) +
  theme_endo_bw(base_size = 12) +
  theme(
    axis.title = element_blank(),
    axis.text = element_blank(),
    axis.ticks = element_blank(),
    panel.grid = element_blank(),
    panel.border = element_blank(),
    legend.position = "bottom",
    legend.title = element_text(size = 11),
    legend.text = element_text(size = 10),
    legend.key.width = unit(3, "cm"),
    legend.key.height = unit(0.45, "cm"),
    plot.title = element_text(size = 12, hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5),
    plot.margin = margin(10, 10, 10, 10)
  ) +
  labs(
    title = "Number of Fungal Endophyte Studies by Country"
  )

# Save the continuous map
ggsave("results/study_count_by_country_robinson.png", map, width = 6.5, height = 5, dpi = 300)

# Create ranked bar chart of top countries
top_countries <- country_papers %>%
  filter(study_count > 0) %>%
  arrange(desc(study_count)) %>%
  slice_head(n = 20) %>%
  mutate(country_name = if_else(is.na(country_name), iso_a3, country_name)) %>%
  mutate(country_name = factor(country_name, levels = country_name))

ranked_bar <- ggplot(top_countries, aes(x = study_count, y = fct_rev(country_name))) +
  geom_col(fill = "#0072B2", width = 0.7) +
  geom_text(
    aes(label = paste0(study_count, " studies")),
    hjust = -0.1,
    size = 3,
    color = "#000000", face = "bold"
  ) +
  scale_x_continuous(
    expand = expansion(mult = c(0, 0.1)),
    labels = scales::comma
  ) +
  theme_endo_bw() +
  theme(
    axis.title.y = element_blank(),
    plot.title = element_text(size = 13, hjust = 0.5, face = "bold")
  ) +
  labs(
    title = "Top 20 Countries by Number of Endophyte Studies",
    x = "Number of Studies"
  )

ggsave("results/top_countries_ranked.png", ranked_bar, width = 6.5, height = 5, dpi = 300)


# Print summary stats
cat("Summary of studies by country:\n")
# Joining with country names for a more readable summary
summary_data <- country_papers %>%
  left_join(world_lookup, by = "iso_a3", relationship = "many-to-one") %>%
  select(country_name = name, iso_a3, study_count) %>%
  arrange(desc(study_count))
print(summary_data)


cat("\nTotal countries with studies:", nrow(country_papers), "\n")
cat("Total studies across all countries:", sum(country_papers$study_count), "\n")

# Show countries NOT represented in the dataset
all_countries <- world_lookup %>% pull(iso_a3) %>% unique() %>% sort()
countries_with_data <- country_papers %>% filter(study_count > 0) %>% pull(iso_a3) %>% unique() %>% sort()
countries_without_data <- setdiff(all_countries, countries_with_data)

cat("\n\nCountries/territories NOT represented in dataset (", length(countries_without_data), " total):\n", sep="")
# Get country names from world map for display
world_names <- world_lookup %>%
  filter(iso_a3 %in% countries_without_data) %>%
  arrange(name)
cat(paste(world_names$name, collapse = ", "), "\n")


# Explicit NA vs 0 reporting
na_countries <- country_status %>%
  filter(data_status == "NA") %>%
  arrange(name)

zero_countries <- country_status %>%
  filter(data_status == "0") %>%
  arrange(name)

cat("\nCountries with NA study_count (no match or missing value): ", nrow(na_countries), "\n", sep = "")
cat(paste(na_countries$name, collapse = ", "), "\n")

cat("\nCountries with study_count == 0: ", nrow(zero_countries), "\n", sep = "")
cat(paste(zero_countries$name, collapse = ", "), "\n")

write.csv(na_countries, "results/countries_study_count_NA.csv", row.names = FALSE)
write.csv(zero_countries, "results/countries_study_count_zero.csv", row.names = FALSE)


# Time series: top countries over time
cat("\nGenerating time series plot for top countries...\n")

TIME_SERIES_INPUT_FILE <- "data/Ollama_cleaned_synresolved_standardized_year.csv"
if (file.exists(TIME_SERIES_INPUT_FILE)) {

  time_df <- read_csv(TIME_SERIES_INPUT_FILE, show_col_types = FALSE)

  # Get top 8 country names for plot clarity
  top_8_country_names <- top_countries %>%
    slice_head(n = 8) %>%
    pull(country_name) %>%
    as.character()
  
  # Map full country names back to iso_a3 for filtering
  top_8_iso <- country_papers %>%
    filter(country_name %in% top_8_country_names) %>%
    pull(iso_a3)

  # Process data
  country_time_data <- time_df %>%
    filter(
      !is.na(publication_year),
      publication_year >= 1990,
      publication_year <= 2024,
      country %in% top_8_iso
    ) %>%
    # Add full names for plotting
    left_join(country_papers %>% select(iso_a3, country_name) %>% distinct(iso_a3, .keep_all=TRUE), by = c("country" = "iso_a3")) %>%
    filter(!is.na(country_name), country_name %in% top_8_country_names) %>%
    count(publication_year, country_name)

  p_country_time <- ggplot(country_time_data, aes(x = publication_year, y = n, color = country_name)) +
    geom_line(linewidth = 1, alpha = 0.8) +
    geom_point(size = 1.5) +
    scale_color_manual(values = endo_palette_discrete, name = "Country") +
    theme_endo_bw() +
    labs(
      title = "Trends in Endophyte Research Over Time by Country",
      subtitle = "Annual study counts for the top 8 countries (1990-2024)",
      x = "Publication Year",
      y = "Number of Studies"
    )

  ggsave("results/country_trends_over_time.png", p_country_time, width = 6.5, height = 4.5, dpi = 300)
  cat("Saved country time series plot to results/country_trends_over_time.png\n")

} else {
  cat("Skipping time series plot: year-enriched data file not found at", TIME_SERIES_INPUT_FILE, "\n")
}


# Scatter plots: GDP and latitude

# Load analysis data for scatter plots
analysis_data <- country_papers %>%
  filter(!is.na(study_count), !is.na(centroid_lat)) %>%
  mutate(
    centroid_lat = as.numeric(centroid_lat),
    gdp_current_usd = as.numeric(gdp_current_usd),
    gdp_log10 = ifelse(!is.na(gdp_current_usd) & gdp_current_usd > 0, log10(gdp_current_usd), NA_real_)
  )

# Load correlation statistics from analysis output
corr_stats <- read.csv("results/country_analysis/country_gdp_latitude_correlations.csv")

# Prepare data for GDP plot
gdp_data <- analysis_data %>% 
  filter(!is.na(gdp_log10), !is.na(study_count)) %>%
  mutate(
    x_value = gdp_log10,
    y_value = log10(study_count + 1)
  ) %>%
  select(x_value, y_value, study_count, country_name, iso_a3)

gdp_stats <- corr_stats %>%
  filter(analysis == "study_count_vs_log10_gdp") %>%
  mutate(
    label = paste0(
      "Pearson r = ", round(pearson_r, 3), " (p ", 
      if_else(pearson_p < 0.001, "< 0.001", paste0("= ", round(pearson_p, 3))), ")\n",
      "Spearman ρ = ", round(spearman_rho, 3), " (p ",
      if_else(spearman_p < 0.001, "< 0.001", paste0("= ", round(spearman_p, 3))), ")"
    )
  )

# Prepare data for latitude plot
lat_data <- analysis_data %>% 
  filter(!is.na(centroid_lat), !is.na(study_count)) %>%
  mutate(
    x_value = centroid_lat,
    y_value = log10(study_count + 1)
  ) %>%
  select(x_value, y_value, study_count, country_name, iso_a3)

lat_stats <- corr_stats %>%
  filter(analysis == "study_count_vs_latitude") %>%
  mutate(
    label = paste0(
      "Pearson r = ", round(pearson_r, 3), " (p ", 
      if_else(pearson_p < 0.001, "< 0.001", paste0("= ", round(pearson_p, 3))), ")\n",
      "Spearman ρ = ", round(spearman_rho, 3), " (p ",
      if_else(spearman_p < 0.001, "< 0.001", paste0("= ", round(spearman_p, 3))), ")"
    )
  )

# Get top 10 countries for labeling
top_countries_gdp <- gdp_data %>%
  arrange(desc(study_count)) %>%
  slice_head(n = 10)

# GDP scatter plot
scatter_plot_gdp <- ggplot(gdp_data, aes(x = x_value, y = y_value)) +
  geom_point(alpha = 0.5, size = 2.3, color = "#2b8cbe") +
  geom_smooth(method = "lm", se = TRUE, color = "#d7301f", linewidth = 0.8, alpha = 0.2) +
  ggrepel::geom_text_repel(
    data = top_countries_gdp,
    mapping = aes(x = x_value, y = y_value, label = iso_a3),
    size = 3,
    color = "#000000",
    max.overlaps = 15,
    inherit.aes = FALSE
  ) +
  geom_text(
    data = data.frame(
      x = min(gdp_data$x_value, na.rm = TRUE) + 0.05 * (max(gdp_data$x_value, na.rm = TRUE) - min(gdp_data$x_value, na.rm = TRUE)),
      y = max(gdp_data$y_value, na.rm = TRUE) - 0.05 * (max(gdp_data$y_value, na.rm = TRUE) - min(gdp_data$y_value, na.rm = TRUE)),
      label = gdp_stats$label
    ),
    aes(x = x, y = y, label = label),
    hjust = 0, vjust = 1,
    size = 3, color = "#000000",
    inherit.aes = FALSE
  ) +
  theme_endo_bw(base_size = 12) +
  theme(
    plot.title = element_text(size = 14, hjust = 0.5, face = "bold"),
    axis.title = element_text(face = "bold")
  ) +
  labs(
    title = "Study Count vs log10(GDP)",
    x = "log10(Current GDP, USD)",
    y = "log10(Study count + 1)"
  )

# Get top 10 countries for labeling
top_countries_lat <- lat_data %>%
  arrange(desc(study_count)) %>%
  slice_head(n = 10)

# Latitude scatter plot
scatter_plot_lat <- ggplot(lat_data, aes(x = x_value, y = y_value)) +
  geom_point(alpha = 0.5, size = 2.3, color = "#2b8cbe") +
  geom_smooth(method = "lm", se = TRUE, color = "#d7301f", linewidth = 0.8, alpha = 0.2) +
  ggrepel::geom_text_repel(
    data = top_countries_lat,
    mapping = aes(x = x_value, y = y_value, label = iso_a3),
    size = 3,
    color = "#000000",
    max.overlaps = 15,
    inherit.aes = FALSE
  ) +
  geom_text(
    data = data.frame(
      x = min(lat_data$x_value, na.rm = TRUE) + 0.05 * (max(lat_data$x_value, na.rm = TRUE) - min(lat_data$x_value, na.rm = TRUE)),
      y = max(lat_data$y_value, na.rm = TRUE) - 0.05 * (max(lat_data$y_value, na.rm = TRUE) - min(lat_data$y_value, na.rm = TRUE)),
      label = lat_stats$label
    ),
    aes(x = x, y = y, label = label),
    hjust = 0, vjust = 1,
    size = 3, color = "#555555",
    inherit.aes = FALSE
  ) +
  theme_endo_bw(base_size = 12) +
  theme(
    plot.title = element_text(size = 14, hjust = 0.5, face = "bold"),
    axis.title = element_text(face = "bold")
  ) +
  labs(
    title = "Study Count vs Latitude",
    x = "Country centroid latitude",
    y = "log10(Study count + 1)"
  )

ggsave("results/country_analysis/country_study_count_vs_gdp.png", scatter_plot_gdp, width = 4.5, height = 4.5, dpi = 300)
ggsave("results/country_analysis/country_study_count_vs_latitude.png", scatter_plot_lat, width = 6.5, height = 5.5, dpi = 300)

cat("\nGeographic plots saved to:\n")
cat("  - results/study_count_by_country_robinson.png (continuous scale)\n")
cat("  - results/study_count_by_country_robinson_binned.png (binned scale)\n")
cat("  - results/top_countries_ranked.png (ranked bar chart)\n")
cat("  - results/country_analysis/country_study_count_vs_gdp.png (scatter + labels)\n")
cat("  - results/country_analysis/country_study_count_vs_latitude.png (scatter + labels)\n")



