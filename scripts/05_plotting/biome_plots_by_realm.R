# BMB 2026-08-27
# Biome x biogeographic-realm heatmap (replaces biome_plots_eu_grouped.R - the
# EU grouping was political, Referee 3, NPH-MS-2026-57711). Realm scheme:
# Olson et al. 2001 / WWF. Pairs with 03c_biogeographic_bias_mapping.R.

suppressPackageStartupMessages({
  library(dplyr)
  library(ggplot2)
  library(readr)
  library(stringr)
  library(tidyr)
  library(forcats)
  library(viridis)
  library(scales)
})

source("scripts/05_plotting/theme_utils.R")
source("scripts/utils/biogeographic_mapping.R")

INPUT_FILE <- "data/Ollama_cleaned_synresolved_standardized_year.csv"
if (!file.exists(INPUT_FILE)) {
  INPUT_FILE <- "data/Ollama_cleaned_synresolved_standardized_final.csv"
}

OUTPUT_DIR <- "results/biome_analysis"
dir.create(OUTPUT_DIR, recursive = TRUE, showWarnings = FALSE)

cat("Loading data from:", INPUT_FILE, "\n")
df <- read_csv(INPUT_FILE, show_col_types = FALSE)

standardize_biome <- function(x) {
  x <- str_to_lower(x)
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

paper_biome <- df %>%
  mutate(
    paper_id = as.character(paper_id),
    biome_clean = standardize_biome(as.character(biome))
  ) %>%
  filter(!is.na(paper_id), !is.na(biome_clean), biome_clean != "Other/Specific") %>%
  add_realm(iso_col = "country") %>%
  filter(!is.na(realm), realm != "Unknown") %>%
  mutate(realm = forcats::fct_drop(realm)) %>%
  distinct(paper_id, biome_clean, realm, .keep_all = TRUE)

# Overall biome distribution
biome_counts <- paper_biome %>%
  count(biome_clean, name = "study_count", sort = TRUE)
write_csv(biome_counts, file.path(OUTPUT_DIR, "biome_counts.csv"))

top_biomes <- biome_counts %>% slice_head(n = 10) %>% pull(biome_clean)

biome_realm <- paper_biome %>%
  filter(biome_clean %in% top_biomes) %>%
  count(biome_clean, realm, name = "study_count") %>%
  complete(biome_clean, realm, fill = list(study_count = 0))

write_csv(biome_realm, file.path(OUTPUT_DIR, "biome_by_realm.csv"))

p <- ggplot(biome_realm,
            aes(x = biome_clean,
                y = fct_reorder(realm, study_count, .fun = sum),
                fill = study_count)) +
  geom_tile(color = "white") +
  geom_text(aes(label = ifelse(study_count > 0, study_count, "")), size = 3, colour = "grey15") +
  scale_fill_viridis(option = "rocket", name = "Studies", begin = 0.1, direction = -1) +
  theme_endo_bw(base_size = 11) +
  theme(axis.text.x = element_text(angle = 45, hjust = 1)) +
  labs(
    title = "Biome research effort by biogeographic realm",
    subtitle = "Studies per biome x realm (top 10 biomes; Olson et al. 2001 realms)",
    x = "Biome", y = "Biogeographic realm"
  )

ggsave(file.path(OUTPUT_DIR, "biome_realm_heatmap.png"), p, width = 7.5, height = 5, dpi = 300)

cat("Biome x realm analysis complete. Outputs in:", OUTPUT_DIR, "\n")
