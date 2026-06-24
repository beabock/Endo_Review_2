# BMB 2026-06-24
# Plots tissue/plant-part sampling bias — raw term counts, country and family
# heatmaps, co-occurrence matrix, biome breakdown, and trends over time.

library(dplyr)
library(ggplot2)
library(readr)
library(stringr)
library(tidyr)
library(forcats)
library(viridis)
library(scales)
library(purrr)

source("scripts/05_plotting/theme_utils.R")

# Use the year-enriched file if available, fallback to final
INPUT_FILE <- "data/Ollama_cleaned_synresolved_standardized_year.csv"
if (!file.exists(INPUT_FILE)) {
  INPUT_FILE <- "data/Ollama_cleaned_synresolved_standardized_final.csv"
}

OUTPUT_DIR <- "results/tissue_analysis"
RAW_COUNTS_FILE <- file.path(OUTPUT_DIR, "tissue_counts_by_study_raw.csv")
PLANT_COUNTS_FILE <- file.path(OUTPUT_DIR, "tissue_counts_by_study_plant_parts.csv")
RAW_PLOT_FILE <- file.path(OUTPUT_DIR, "top_tissue_terms_by_study_raw.png")
PLANT_PLOT_FILE <- file.path(OUTPUT_DIR, "top_tissue_parts_by_study.png")

if (!file.exists(INPUT_FILE)) {
	stop("Input file not found: ", INPUT_FILE)
}

if (!dir.exists(OUTPUT_DIR)) {
	dir.create(OUTPUT_DIR, recursive = TRUE, showWarnings = FALSE)
}

df <- read_csv(INPUT_FILE, show_col_types = FALSE)

required_cols <- c("paper_id", "tissue")
missing_cols <- setdiff(required_cols, names(df))
if (length(missing_cols) > 0) {
	stop("Missing required columns: ", paste(missing_cols, collapse = ", "))
}

clean_tissue_value <- function(x) {
	x %>%
		str_to_lower() %>%
		str_replace_all("[\"'`]+", "") %>%
		str_replace_all("\\s+", " ") %>%
		str_trim()
}

is_missing_tissue <- function(x) {
	x %in% c("", "na", "n/a", "none", "unknown", "not specified", "not-specified", "not_mentioned")
}

split_tissues <- function(x) {
	# Support common multi-value separators used in extracted metadata.
	str_split(x, "\\s*(?:/|\\band\\b|&)\\s*")
}

# Build one row per paper_id x tissue token, then deduplicate.
paper_tissue <- df %>%
	transmute(
		paper_id = as.character(paper_id),
		tissue_raw = clean_tissue_value(as.character(tissue))
	) %>%
	filter(!is.na(paper_id), paper_id != "", !is.na(tissue_raw), !is_missing_tissue(tissue_raw)) %>%
	mutate(tissue_tokens = split_tissues(tissue_raw)) %>%
	unnest_longer(tissue_tokens) %>%
	mutate(
		tissue_token = tissue_tokens %>%
			str_squish() %>%
			str_replace_all("[^a-z0-9\\s-]", "")
	) %>%
	filter(!is.na(tissue_token), tissue_token != "", !is_missing_tissue(tissue_token)) %>%
	distinct(paper_id, tissue_token)

raw_counts <- paper_tissue %>%
	count(tissue_token, name = "study_count", sort = TRUE)

write_csv(raw_counts, RAW_COUNTS_FILE)

# Canonical plant tissue-part categories.
paper_tissue_plant <- paper_tissue %>%
	mutate(
		tissue_part = case_when(
			str_detect(tissue_token, "leaf|foliar|foliage|needle|phylloplane") ~ "Leaf",
			str_detect(tissue_token, "root|rhizosphere|rhizoplane") ~ "Root",
			str_detect(tissue_token, "stem|wood|bark|caulosphere|phloem|cambial") ~ "Stem/Wood/Bark",
			str_detect(tissue_token, "seed") ~ "Seed",
			str_detect(tissue_token, "fruit") ~ "Fruit",
			str_detect(tissue_token, "flower|inflorescence|reproductive") ~ "Flower/Reproductive",
			str_detect(tissue_token, "tuber") ~ "Tuber",
			str_detect(tissue_token, "rhizome") ~ "Rhizome",
			str_detect(tissue_token, "nodule") ~ "Nodule",
			TRUE ~ NA_character_
		)
	) %>%
	filter(!is.na(tissue_part)) %>%
	distinct(paper_id, tissue_part)

plant_counts <- paper_tissue_plant %>%
	count(tissue_part, name = "study_count", sort = TRUE)

write_csv(plant_counts, PLANT_COUNTS_FILE)

top_n_raw <- 20
raw_plot_data <- raw_counts %>%
	slice_head(n = top_n_raw) %>%
	mutate(tissue_token = fct_reorder(tissue_token, study_count))

raw_plot <- ggplot(raw_plot_data, aes(x = tissue_token, y = study_count)) +
	geom_col(fill = endo_palette_discrete[1], width = 0.8) +
	geom_text(aes(label = study_count), hjust = -0.1, size = 3.2) +
	coord_flip(clip = "off") +
	theme_endo_bw(base_size = 12) +
	theme(
		plot.title = element_text(face = "bold")
	) +
	labs(
		title = "Top tissue terms by number of studies",
		subtitle = "Each study contributes at most one count per tissue term",
		x = "Tissue term",
		y = "Number of studies"
	)

ggsave(RAW_PLOT_FILE, raw_plot, width = 6.5, height = 6, dpi = 300)

plant_plot_data <- plant_counts %>%
	mutate(tissue_part = fct_reorder(tissue_part, study_count))

plant_plot <- ggplot(plant_plot_data, aes(x = tissue_part, y = study_count)) +
	geom_col(fill = endo_palette_discrete[2], width = 0.8) +
	geom_text(aes(label = study_count), hjust = -0.1, size = 3.5) +
	coord_flip(clip = "off") +
	theme_endo_bw(base_size = 12) +
	theme(
		plot.title = element_text(face = "bold")
	) +
	labs(
		title = "Most frequent plant tissues studied for endophytes",
		subtitle = "Each study contributes at most one count per tissue",
		x = "Plant tissue",
		y = "Number of studies"
	)

ggsave(PLANT_PLOT_FILE, plant_plot, width = 6.5, height = 6, dpi = 300)

cat("Tissue plotting complete:\n")
cat("  Input rows: ", nrow(df), "\n", sep = "")
cat("  Unique paper x tissue tokens: ", nrow(paper_tissue), "\n", sep = "")
cat("  Raw tissue terms saved to: ", RAW_COUNTS_FILE, "\n", sep = "")
cat("  Plant tissue parts saved to: ", PLANT_COUNTS_FILE, "\n", sep = "")
cat("  Raw plot saved to: ", RAW_PLOT_FILE, "\n", sep = "")
cat("  Plant tissue-part plot saved to: ", PLANT_PLOT_FILE, "\n", sep = "")

# ============================================================================
# VISUALIZATION 1: Tissue × Country Heatmap (Geographic bias in tissue choice)
# ============================================================================
tissue_country <- df %>%
	transmute(
		paper_id = as.character(paper_id),
		country = as.character(country),
		tissue_raw = clean_tissue_value(as.character(tissue))
	) %>%
	filter(!is.na(country), country != "", !is.na(tissue_raw), !is_missing_tissue(tissue_raw)) %>%
	mutate(tissue_tokens = split_tissues(tissue_raw)) %>%
	unnest_longer(tissue_tokens) %>%
	mutate(
		tissue_token = tissue_tokens %>%
			str_squish() %>%
			str_replace_all("[^a-z0-9\\s-]", "")
	) %>%
	filter(!is.na(tissue_token), tissue_token != "", !is_missing_tissue(tissue_token)) %>%
	distinct(paper_id, country, tissue_token) %>%
	count(country, tissue_token, name = "study_count", sort = TRUE)

# Top 15 tissues and top 15 countries for readability
top_tissues_hm <- paper_tissue %>%
	count(tissue_token, name = "n", sort = TRUE) %>%
	slice_head(n = 15) %>%
	pull(tissue_token)

top_countries_hm <- tissue_country %>%
	group_by(country) %>%
	summarise(total = sum(study_count), .groups = "drop") %>%
	slice_head(n = 15) %>%
	pull(country)

tissue_country_filtered <- tissue_country %>%
	filter(tissue_token %in% top_tissues_hm, country %in% top_countries_hm) %>%
	complete(country, tissue_token, fill = list(study_count = 0))

p_tissue_country <- ggplot(tissue_country_filtered, aes(x = tissue_token, y = fct_reorder(country, study_count, .fun = max), fill = study_count)) +
	geom_tile(color = "white", linewidth = 0.3) +
	scale_fill_viridis(option = "mako", begin = 0.1, end = 0.95, name = "Studies", direction = -1) +
	theme_endo_bw(base_size = 11) +
	theme(
		axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1),
		plot.title = element_text(face = "bold")
	) +
	labs(
		title = "Tissue studied by country (top 15 of each)",
		subtitle = "Heatmap intensity shows number of studies examining each tissue-country combination",
		x = "Tissue term",
		y = "Country"
	)

tissue_country_file <- file.path(OUTPUT_DIR, "tissue_country_heatmap.png")
ggsave(tissue_country_file, p_tissue_country, width = 6.5, height = 6, dpi = 300)

# ============================================================================
# VISUALIZATION 2: Tissue × Plant Family Heatmap (Host-tissue specialization)
# ============================================================================
tissue_family <- df %>%
	transmute(
		paper_id = as.character(paper_id),
		plant_host = as.character(plant_host),
		tissue_raw = clean_tissue_value(as.character(tissue))
	) %>%
	filter(!is.na(plant_host), plant_host != "", !is.na(tissue_raw), !is_missing_tissue(tissue_raw)) %>%
	mutate(tissue_tokens = split_tissues(tissue_raw)) %>%
	unnest_longer(tissue_tokens) %>%
	mutate(
		tissue_token = tissue_tokens %>%
			str_squish() %>%
			str_replace_all("[^a-z0-9\\s-]", "")
	) %>%
	filter(!is.na(tissue_token), tissue_token != "", !is_missing_tissue(tissue_token)) %>%
	distinct(paper_id, plant_host, tissue_token) %>%
	count(plant_host, tissue_token, name = "study_count", sort = TRUE)

# Top 12 tissues and families
top_tissues_fam <- paper_tissue %>%
	count(tissue_token, name = "n", sort = TRUE) %>%
	slice_head(n = 12) %>%
	pull(tissue_token)

top_families <- tissue_family %>%
	group_by(plant_host) %>%
	summarise(total = sum(study_count), .groups = "drop") %>%
	slice_head(n = 12) %>%
	pull(plant_host)

tissue_family_filtered <- tissue_family %>%
	filter(tissue_token %in% top_tissues_fam, plant_host %in% top_families) %>%
	complete(plant_host, tissue_token, fill = list(study_count = 0))

p_tissue_family <- ggplot(tissue_family_filtered, aes(x = tissue_token, y = fct_reorder(plant_host, study_count, .fun = max), fill = study_count)) +
	geom_tile(color = "white", linewidth = 0.3) +
	scale_fill_viridis(option = "viridis", begin = 0.1, end = 0.95, name = "Studies") +
	theme_endo_bw(base_size = 11) +
	theme(
		axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1),
		plot.title = element_text(face = "bold")
	) +
	labs(
		title = "Tissue specialization by plant family (top 12 of each)",
		subtitle = "Shows which plant families are studied for which tissues",
		x = "Tissue term",
		y = "Plant family"
	)

tissue_family_file <- file.path(OUTPUT_DIR, "tissue_family_heatmap.png")
ggsave(tissue_family_file, p_tissue_family, width = 6.5, height = 6, dpi = 300)

# ============================================================================
# VISUALIZATION 3: Tissue Co-occurrence Network (shared tissues in papers)
# ============================================================================
tissue_cooccurrence <- paper_tissue %>%
	group_by(paper_id) %>%
	filter(n() > 1) %>%
	ungroup() %>%
	arrange(paper_id, tissue_token) %>%
	group_by(paper_id) %>%
	summarise(tissues = list(tissue_token), .groups = "drop") %>%
	mutate(tissue_pairs = map(tissues, function(x) {
		if (length(x) <= 1) return(data.frame(tissue1 = character(), tissue2 = character()))
		t(combn(sort(x), 2)) %>%
			as.data.frame(stringsAsFactors = FALSE) %>%
			setNames(c("tissue1", "tissue2"))
	})) %>%
	unnest(tissue_pairs) %>%
	count(tissue1, tissue2, name = "co_count", sort = TRUE) %>%
	slice_head(n = 30)

p_cooccurrence <- ggplot(tissue_cooccurrence, aes(x = tissue1, y = tissue2, size = co_count, color = co_count)) +
	geom_point(alpha = 0.7) +
	geom_label(aes(label = co_count), size = 2.5, alpha = 0.8, label.padding = unit(0.2, "lines")) +
	scale_color_viridis(option = "plasma", name = "Co-occurrences") +
	scale_size_continuous(range = c(3, 8), name = "Co-occurrences") +
	theme_endo_bw(base_size = 11) +
	theme(
		axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1),
		plot.title = element_text(face = "bold"),
		legend.position = "bottom"
	) +
	labs(
		title = "Tissue co-occurrence in same studies (top 30 pairs)",
		subtitle = "Shows which tissues are commonly studied together",
		x = "Tissue 1",
		y = "Tissue 2"
	)

cooccurrence_file <- file.path(OUTPUT_DIR, "tissue_cooccurrence_plot.png")
ggsave(cooccurrence_file, p_cooccurrence, width = 6.5, height = 6, dpi = 300)

# ============================================================================
# VISUALIZATION 4: Tissue Data Completeness (Sankey-style waterfall)
# ============================================================================
completeness_summary <- df %>%
	transmute(
		has_tissue = !is.na(tissue) & tissue != "" & !is_missing_tissue(clean_tissue_value(tissue)),
		has_plant = !is.na(plant_host) & plant_host != "",
		has_country = !is.na(country) & country != "",
		has_fungal = !is.na(fungal_taxon_resolved) & fungal_taxon_resolved != ""
	) %>%
	summarise(
		Total = n(),
		"Has tissue" = sum(has_tissue),
		"Has host plant" = sum(has_plant),
		"Has country" = sum(has_country),
		"Has fungal ID" = sum(has_fungal),
		"Has all four" = sum(has_tissue & has_plant & has_country & has_fungal)
	)

total_obs <- completeness_summary$Total[1]

completeness_stats <- completeness_summary %>%
	pivot_longer(cols = everything(), names_to = "category", values_to = "count") %>%
	mutate(
		category = fct_inorder(category),
		pct = count / total_obs * 100
	)

p_completeness <- ggplot(completeness_stats, aes(x = category, y = count, fill = category)) +
	geom_col(width = 0.7, show.legend = FALSE) +
	geom_text(aes(label = paste0(count, "\n(", round(pct, 1), "%)")), vjust = -0.2, size = 3.2, fontface = "bold") +
	scale_fill_endo_discrete() +
	theme_endo_bw(base_size = 11) +
	theme(
		axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1),
		plot.title = element_text(face = "bold")
	) +
	labs(
		title = "Data completeness across key fields",
		subtitle = "Shows availability of tissue, host plant, location, and fungal identification",
		x = "Data field",
		y = "Number of observations"
	) +
	coord_cartesian(clip = "off")

completeness_file <- file.path(OUTPUT_DIR, "tissue_data_completeness.png")
ggsave(completeness_file, p_completeness, width = 6.5, height = 5, dpi = 300)

# ============================================================================
# VISUALIZATION 5: Tissue by Biome (Faceted bar chart)
# ============================================================================
tissue_biome <- df %>%
	transmute(
		paper_id = as.character(paper_id),
		biome = as.character(biome),
		tissue_raw = clean_tissue_value(as.character(tissue))
	) %>%
	filter(!is.na(biome), biome != "", !is.na(tissue_raw), !is_missing_tissue(tissue_raw)) %>%
	mutate(tissue_tokens = split_tissues(tissue_raw)) %>%
	unnest_longer(tissue_tokens) %>%
	mutate(
		tissue_token = tissue_tokens %>%
			str_squish() %>%
			str_replace_all("[^a-z0-9\\s-]", "")
	) %>%
	filter(!is.na(tissue_token), tissue_token != "", !is_missing_tissue(tissue_token)) %>%
	distinct(paper_id, biome, tissue_token)

# For clarity, show top 10 tissues per biome
top_tissues_biome <- tissue_biome %>%
	count(tissue_token, name = "n", sort = TRUE) %>%
	slice_head(n = 10) %>%
	pull(tissue_token)

tissue_biome_plot <- tissue_biome %>%
	filter(tissue_token %in% top_tissues_biome) %>%
	count(biome, tissue_token, name = "study_count") %>%
	mutate(tissue_token = fct_reorder(tissue_token, study_count, .fun = sum))

p_biome <- ggplot(tissue_biome_plot, aes(x = tissue_token, y = study_count, fill = biome)) +
	geom_col(position = "stack") +
	scale_fill_viridis(option = "turbo", discrete = TRUE, name = "Biome") +
	coord_flip() +
	theme_endo_bw(base_size = 11) +
	theme(
		plot.title = element_text(face = "bold"),
		legend.position = "bottom"
	) +
	labs(
		title = "Tissue research across biomes",
		subtitle = "Stacked bar chart showing biome distribution for top 10 tissues studied",
		y = "Number of studies",
		x = "Tissue term"
	)

biome_file <- file.path(OUTPUT_DIR, "tissue_by_biome_stacked.png")
ggsave(biome_file, p_biome, width = 6.5, height = 6, dpi = 300)

# ============================================================================
# VISUALIZATION 6: Tissue Richness per Study (Distribution)
# ============================================================================
tissue_richness <- paper_tissue %>%
	group_by(paper_id) %>%
	summarise(n_tissues = n(), .groups = "drop")

p_richness <- ggplot(tissue_richness, aes(x = n_tissues)) +
	geom_histogram(binwidth = 1, fill = endo_palette_discrete[1], color = "white", alpha = 0.85) +
	geom_vline(aes(xintercept = median(n_tissues)), color = endo_palette_discrete[2], linetype = "dashed", linewidth = 1) +
	geom_vline(aes(xintercept = mean(n_tissues)), color = endo_palette_discrete[3], linetype = "dotted", linewidth = 1) +
	theme_endo_bw(base_size = 11) +
	theme(
		plot.title = element_text(face = "bold")
	) +
	labs(
		title = "Tissue research breadth per study",
		subtitle = "Distribution of number of distinct tissues examined per paper (dashed = median, dotted = mean)",
		x = "Number of distinct tissues per study",
		y = "Number of studies"
	) +
	annotate("text", x = Inf, y = Inf, label = paste0("Median: ", median(tissue_richness$n_tissues), "\nMean: ", round(mean(tissue_richness$n_tissues), 2)),
		hjust = 1.05, vjust = 1.2, size = 3.5, fontface = "bold", color = endo_palette_discrete[2])

richness_file <- file.path(OUTPUT_DIR, "tissue_richness_distribution.png")
ggsave(richness_file, p_richness, width = 6.5, height = 5, dpi = 300)

# ============================================================================
# VISUALIZATION 7: Top Tissue × Top Plant Family Tile Plot (Focused cross-tab)
# ============================================================================
top_tissue_x_family <- tissue_family %>%
	filter(tissue_token %in% top_tissues_fam, plant_host %in% top_families) %>%
	complete(plant_host, tissue_token, fill = list(study_count = 0)) %>%
	mutate(
		tissue_token = fct_reorder(tissue_token, study_count, .fun = max),
		plant_host = fct_reorder(plant_host, study_count, .fun = max)
	)

p_tile <- ggplot(top_tissue_x_family, aes(x = tissue_token, y = plant_host, fill = study_count)) +
	geom_tile(color = "white", linewidth = 0.5) +
	geom_text(aes(label = if_else(study_count > 0, as.character(study_count), "")), 
		size = 3, fontface = "bold", color = "white") +
	scale_fill_viridis(option = "cividis", name = "Studies") +
	theme_endo_bw(base_size = 11) +
	theme(
		axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1),
		plot.title = element_text(face = "bold"),
		panel.grid = element_blank()
	) +
	labs(
		title = "Top tissue-plant family interactions",
		subtitle = "Detailed cross-tabulation of 12 most-studied tissues vs. plant families",
		x = "Tissue term",
		y = "Plant family"
	)

tile_file <- file.path(OUTPUT_DIR, "tissue_family_tile_plot.png")
ggsave(tile_file, p_tile, width = 6.5, height = 6, dpi = 300)

# ============================================================================
# VISUALIZATION 8: Cumulative Coverage Curve (Ranked coverage threshold)
# ============================================================================
tissue_coverage <- paper_tissue %>%
	count(tissue_token, name = "study_count", sort = TRUE) %>%
	mutate(
		rank = row_number(),
		cumulative_studies = cumsum(study_count),
		total_studies = max(cumsum(study_count)),
		pct_coverage = cumulative_studies / total_studies * 100
	) %>%
	filter(rank <= 50)

p_coverage <- ggplot(tissue_coverage, aes(x = rank, y = pct_coverage)) +
	geom_line(size = 1, color = endo_palette_discrete[1]) +
	geom_point(size = 2, color = endo_palette_discrete[1]) +
	geom_hline(aes(yintercept = 80), linetype = "dashed", color = endo_palette_discrete[2], alpha = 0.7) +
	geom_hline(aes(yintercept = 50), linetype = "dotted", color = endo_palette_discrete[3], alpha = 0.7) +
	scale_y_continuous(limits = c(0, 105), labels = label_percent(scale = 1)) +
	annotate("text", x = 45, y = 82, label = "80% coverage", size = 3.2, fontface = "bold", color = endo_palette_discrete[2]) +
	annotate("text", x = 45, y = 52, label = "50% coverage", size = 3.2, fontface = "bold", color = endo_palette_discrete[3]) +
	theme_endo_bw(base_size = 11) +
	theme(
		plot.title = element_text(face = "bold")
	) +
	labs(
		title = "Cumulative tissue coverage curve",
		subtitle = "How many tissues are needed to cover different percentages of the literature?",
		x = "Number of tissues (ranked by frequency)",
		y = "% of literature covered"
	)

coverage_file <- file.path(OUTPUT_DIR, "tissue_cumulative_coverage.png")
ggsave(coverage_file, p_coverage, width = 6.5, height = 5, dpi = 300)

# ============================================================================
# Summary output
# ============================================================================

# ============================================================================
# VISUALIZATION 9: Tissue Research Over Time
# ============================================================================
if ("publication_year" %in% names(df)) {
  
  # Get top 8 tissue parts for clarity in the plot
  top_tissues_time <- plant_counts %>%
    slice_head(n = 8) %>%
    pull(tissue_part)

  # Join year info back to the paper_tissue_plant data
  tissue_time_data <- paper_tissue_plant %>%
    left_join(df %>% select(paper_id, publication_year) %>% distinct(), by = "paper_id") %>%
    filter(
      !is.na(publication_year),
      publication_year >= 1990,
      publication_year <= 2024,
      tissue_part %in% top_tissues_time
    ) %>%
    count(publication_year, tissue_part)

  p_tissue_time <- ggplot(tissue_time_data, aes(x = publication_year, y = n, color = tissue_part)) +
    geom_line(linewidth = 1, alpha = 0.8) +
    geom_point(size = 1.5) +
    scale_color_manual(values = endo_palette_discrete, name = "Tissue") +
    theme_endo_bw(base_size = 11) +
    labs(
      title = "Trends in Tissue Research Over Time",
      subtitle = "Annual study counts for the top 8 standardized tissue (1990-2024)",
      x = "Publication Year",
      y = "Number of Studies"
    )

  tissue_time_file <- file.path(OUTPUT_DIR, "tissue_trends_over_time.png")
  ggsave(tissue_time_file, p_tissue_time, width = 11, height = 7, dpi = 300)
  
} else {
  tissue_time_file <- "skipped (no publication_year column found)"
}

cat("\n=== EXTENDED TISSUE VISUALIZATIONS ===\n")
cat("  1. Tissue × Country Heatmap: ", tissue_country_file, "\n", sep = "")
cat("  2. Tissue × Plant Family Heatmap: ", tissue_family_file, "\n", sep = "")
cat("  3. Tissue Co-occurrence Network: ", cooccurrence_file, "\n", sep = "")
cat("  4. Data Completeness Waterfall: ", completeness_file, "\n", sep = "")
cat("  5. Tissue by Biome (Stacked): ", biome_file, "\n", sep = "")
cat("  6. Tissue Richness Distribution: ", richness_file, "\n", sep = "")
cat("  7. Top Tissue × Family Tile: ", tile_file, "\n", sep = "")
cat("  8. Cumulative Coverage Curve: ", coverage_file, "\n", sep = "")
cat("  9. Tissue Trends Over Time: ", tissue_time_file, "\n", sep = "")
