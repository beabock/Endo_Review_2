#!/usr/bin/env Rscript
# =============================================================================
# abs_fulltext_comparison_plots.R
# =============================================================================
# Purpose: Create a comparison table and figures for Abstract vs Full-Text runs.
# Outputs:
#   - results/abs_fulltext_comparison/abs_fulltext_comparison_table.csv
#   - results/abs_fulltext_comparison/figures/abs_fulltext_country_bias_scatter.png
#   - results/abs_fulltext_comparison/figures/abs_fulltext_biome_comparison.png
#   - results/abs_fulltext_comparison/figures/abs_fulltext_relationship_type_percent.png
# Usage:
#   Rscript scripts/05_plotting/abs_fulltext_comparison_plots.R
# =============================================================================

library(dplyr)
library(readr)
library(tidyr)
library(ggplot2)
library(stringr)
library(forcats)
library(scales)

source("scripts/05_plotting/theme_utils.R")

INPUT_DIR <- "results/abs_fulltext_comparison"
ABSTRACT_DIR <- file.path(INPUT_DIR, "abstract")
FULL_DIR <- file.path(INPUT_DIR, "full_text")
FIG_DIR <- file.path(INPUT_DIR, "figures")
dir.create(FIG_DIR, recursive = TRUE, showWarnings = FALSE)

SUMMARY_FILE <- file.path(INPUT_DIR, "comparison_summary.csv")
CORR_FILE <- file.path(INPUT_DIR, "correlation_comparison.csv")
TABLE_FILE <- file.path(INPUT_DIR, "abs_fulltext_comparison_table.csv")

REL_ABS_FILE <- file.path(ABSTRACT_DIR, "relationship_type_counts_by_study.csv")
REL_FULL_FILE <- file.path(FULL_DIR, "relationship_type_counts_by_study.csv")
COUNTRY_ABS_FILE <- file.path(ABSTRACT_DIR, "country_gdp_latitude_summary.csv")
COUNTRY_FULL_FILE <- file.path(FULL_DIR, "country_gdp_latitude_summary.csv")

INPUT_FINAL <- "data/Ollama_cleaned_synresolved_standardized_final.csv"
INPUT_YEAR <- "data/Ollama_cleaned_synresolved_standardized_year.csv"

safe_ratio <- function(num, den) {
	ifelse(is.na(num) | is.na(den) | den == 0, NA_real_, num / den)
}

format_signif <- function(x) {
	if (is.na(x)) {
		return("NA")
	}
	format(signif(x, 3), scientific = TRUE)
}

build_corr_note <- function(corr_df, analysis, stat) {
	p_col <- if (stat == "Pearson r") "pearson_p" else "spearman_p"
	abs_row <- corr_df %>% filter(analysis == !!analysis, doc_type_group == "Abstract")
	full_row <- corr_df %>% filter(analysis == !!analysis, doc_type_group == "Full-Text")
	if (nrow(abs_row) == 0 || nrow(full_row) == 0) {
		return(NA_character_)
	}
	paste0(
		"p_abs=", format_signif(abs_row[[p_col]][1]),
		"; p_full=", format_signif(full_row[[p_col]][1]),
		"; n_abs=", abs_row$n[1],
		"; n_full=", full_row$n[1]
	)
}

normalize_token <- function(x) {
	x %>% as.character() %>% str_to_lower() %>% str_squish()
}

load_set <- function(path, column_name) {
	if (!file.exists(path)) {
		return(character())
	}
	df <- read_csv(path, show_col_types = FALSE)
	if (!column_name %in% names(df)) {
		return(character())
	}
	vec <- df %>%
		pull(.data[[column_name]]) %>%
		normalize_token() %>%
		na.omit() %>%
		unique()
	vec
}

add_overlap_row <- function(label, abs_set, full_set) {
	if (length(abs_set) == 0 || length(full_set) == 0) {
		return(NULL)
	}
	intersect_n <- length(intersect(abs_set, full_set))
	union_n <- length(union(abs_set, full_set))
	jaccard <- ifelse(union_n > 0, intersect_n / union_n, NA_real_)
	tibble(
		metric_group = "Understudied overlap",
		metric = label,
		abstract_value = length(abs_set),
		full_text_value = length(full_set),
		full_minus_abstract = length(full_set) - length(abs_set),
		full_to_abstract_ratio = safe_ratio(length(full_set), length(abs_set)),
		notes = paste0("overlap=", intersect_n, "; jaccard=", round(jaccard, 3))
	)
}

# -----------------------------------------------------------------------------
# 1) Comparison table
# -----------------------------------------------------------------------------
if (!file.exists(SUMMARY_FILE)) {
	stop("Missing input file: ", SUMMARY_FILE)
}

summary_df <- read_csv(SUMMARY_FILE, show_col_types = FALSE)

metric_info <- tibble(
	metric = c(
		"total_rows",
		"unique_papers",
		"unique_interactions",
		"unique_countries",
		"unique_biomes",
		"unique_fungal_ids",
		"unique_plant_ids",
		"plant_coverage_percent",
		"fungal_coverage_percent"
	),
	metric_label = c(
		"Total rows",
		"Unique papers",
		"Unique interactions",
		"Countries",
		"Biomes",
		"Fungal IDs",
		"Plant IDs",
		"Plant coverage (%)",
		"Fungal coverage (%)"
	),
	metric_group = c(
		rep("Scale", 7),
		rep("Coverage", 2)
	)
)

summary_long <- summary_df %>%
	select(doc_type_group, all_of(metric_info$metric)) %>%
	pivot_longer(-doc_type_group, names_to = "metric", values_to = "value") %>%
	left_join(metric_info, by = "metric")

summary_wide <- summary_long %>%
	pivot_wider(names_from = doc_type_group, values_from = value)

if (!all(c("Abstract", "Full-Text") %in% names(summary_wide))) {
	stop("comparison_summary.csv must include Abstract and Full-Text rows.")
}

summary_table <- summary_wide %>%
	transmute(
		metric_group,
		metric = metric_label,
		abstract_value = Abstract,
		full_text_value = `Full-Text`,
		full_minus_abstract = full_text_value - abstract_value,
		full_to_abstract_ratio = safe_ratio(full_text_value, abstract_value),
		notes = NA_character_
	)

corr_table <- tibble()
if (file.exists(CORR_FILE)) {
	corr_df <- read_csv(CORR_FILE, show_col_types = FALSE)
	if (nrow(corr_df) > 0) {
		corr_long <- corr_df %>%
			select(analysis, doc_type_group, pearson_r, pearson_p, spearman_rho, spearman_p, n) %>%
			pivot_longer(
				cols = c(pearson_r, spearman_rho),
				names_to = "stat",
				values_to = "value"
			) %>%
			mutate(
				stat = recode(stat, pearson_r = "Pearson r", spearman_rho = "Spearman rho"),
				metric_group = "Correlation",
				metric = paste(analysis, stat, sep = " - ")
			)

		corr_wide <- corr_long %>%
			pivot_wider(names_from = doc_type_group, values_from = value)

		corr_wide$notes <- mapply(
			function(analysis, stat) build_corr_note(corr_df, analysis, stat),
			corr_wide$analysis,
			corr_wide$stat,
			USE.NAMES = FALSE
		)

		corr_table <- corr_wide %>%
			transmute(
				metric_group,
				metric,
				abstract_value = Abstract,
				full_text_value = `Full-Text`,
				full_minus_abstract = full_text_value - abstract_value,
				full_to_abstract_ratio = safe_ratio(full_text_value, abstract_value),
				notes
			)
	}
}

overlap_rows <- list(
	add_overlap_row(
		"Understudied countries (count)",
		load_set(file.path(ABSTRACT_DIR, "unstudied_countries.csv"), "iso_a3"),
		load_set(file.path(FULL_DIR, "unstudied_countries.csv"), "iso_a3")
	),
	add_overlap_row(
		"Understudied plant families (count)",
		load_set(file.path(ABSTRACT_DIR, "unstudied_plant_families.csv"), "family"),
		load_set(file.path(FULL_DIR, "unstudied_plant_families.csv"), "family")
	),
	add_overlap_row(
		"Understudied plant genera (count)",
		load_set(file.path(ABSTRACT_DIR, "unstudied_plant_genera.csv"), "genus"),
		load_set(file.path(FULL_DIR, "unstudied_plant_genera.csv"), "genus")
	),
	add_overlap_row(
		"Understudied plant species (count)",
		load_set(file.path(ABSTRACT_DIR, "unstudied_plant_species.csv"), "species"),
		load_set(file.path(FULL_DIR, "unstudied_plant_species.csv"), "species")
	)
)

overlap_table <- bind_rows(overlap_rows)

comparison_table <- bind_rows(summary_table, corr_table, overlap_table) %>%
	arrange(metric_group, metric)

write_csv(comparison_table, TABLE_FILE)
message("Saved comparison table to: ", TABLE_FILE)

# -----------------------------------------------------------------------------
# 2) Geographic bias scatter (country study counts)
# -----------------------------------------------------------------------------
if (file.exists(COUNTRY_ABS_FILE) && file.exists(COUNTRY_FULL_FILE)) {
	abs_country <- read_csv(COUNTRY_ABS_FILE, show_col_types = FALSE) %>%
		select(iso_a3, study_count)
	full_country <- read_csv(COUNTRY_FULL_FILE, show_col_types = FALSE) %>%
		select(iso_a3, study_count)

	country_plot_df <- full_join(abs_country, full_country, by = "iso_a3", suffix = c("_abstract", "_full_text")) %>%
		mutate(
			study_count_abstract = replace_na(study_count_abstract, 0L),
			study_count_full_text = replace_na(study_count_full_text, 0L)
		)

	p_country <- ggplot(country_plot_df, aes(x = study_count_abstract, y = study_count_full_text)) +
		geom_abline(slope = 1, intercept = 0, linetype = "dashed", color = "#999999") +
		geom_point(alpha = 0.55, size = 2.2, color = endo_palette_discrete[1]) +
		scale_x_continuous(trans = pseudo_log_trans(base = 10), labels = comma) +
		scale_y_continuous(trans = pseudo_log_trans(base = 10), labels = comma) +
		theme_endo_bw(base_size = 11) +
		labs(
			title = "Geographic bias comparison",
			subtitle = "Country-level study counts: Abstract vs Full-Text",
			x = "Abstract-only study count (pseudo-log)",
			y = "Full-text study count (pseudo-log)"
		)

	ggsave(
		file.path(FIG_DIR, "abs_fulltext_country_bias_scatter.png"),
		p_country,
		width = 6.5,
		height = 5,
		dpi = 300
	)
} else {
	message("Skipping country scatter: missing country_gdp_latitude_summary.csv files.")
}

# -----------------------------------------------------------------------------
# 3) Relationship type distribution (percent of studies)
# -----------------------------------------------------------------------------
if (file.exists(REL_ABS_FILE) && file.exists(REL_FULL_FILE)) {
	rel_abs <- read_csv(REL_ABS_FILE, show_col_types = FALSE) %>%
		mutate(doc_type_group = "Abstract")
	rel_full <- read_csv(REL_FULL_FILE, show_col_types = FALSE) %>%
		mutate(doc_type_group = "Full-Text")

	rel_df <- bind_rows(rel_abs, rel_full) %>%
		group_by(doc_type_group) %>%
		mutate(share = study_count / sum(study_count)) %>%
		ungroup()

	rel_colors <- c(
		"Endophytic" = "#0072B2",
		"Pathogenic" = "#D55E00",
		"Mycorrhizal" = "#009E73",
		"Antagonistic/Biocontrol" = "#E69F00",
		"Mutualistic" = "#CC79A7",
		"Saprotrophic" = "#56B4E9",
		"Commensal" = "#F0E442",
		"Absence/Negative" = "#666666",
		"Unknown/Other" = "#999999"
	)

	p_relationship <- ggplot(rel_df, aes(x = doc_type_group, y = share, fill = relationship_type)) +
		geom_col(width = 0.7, color = "white", linewidth = 0.2) +
		scale_y_continuous(labels = percent_format(accuracy = 1)) +
		scale_fill_manual(values = rel_colors) +
		theme_endo_bw(base_size = 11) +
		labs(
			title = "Relationship-type composition by doc type",
			x = NULL,
			y = "Share of studies",
			fill = "Relationship type"
		) +
		theme(legend.position = "bottom")

	ggsave(
		file.path(FIG_DIR, "abs_fulltext_relationship_type_percent.png"),
		p_relationship,
		width = 6.5,
		height = 5,
		dpi = 300
	)
} else {
	message("Skipping relationship-type plot: missing input files.")
}

# -----------------------------------------------------------------------------
# 4) Biome comparison (top biomes)
# -----------------------------------------------------------------------------
input_file <- if (file.exists(INPUT_YEAR)) INPUT_YEAR else INPUT_FINAL
if (file.exists(input_file)) {
	df <- read_csv(input_file, show_col_types = FALSE)

	normalize_doc_type <- function(doc_type_clean, doc_type_raw, data_source) {
		doc_raw <- ifelse(!is.na(doc_type_clean) & doc_type_clean != "", doc_type_clean,
			ifelse(!is.na(doc_type_raw) & doc_type_raw != "", doc_type_raw, data_source)
		)
		doc_raw <- str_to_lower(str_squish(coalesce(doc_raw, "")))

		case_when(
			str_detect(doc_raw, "full") ~ "Full-Text",
			str_detect(doc_raw, "abstract") ~ "Abstract",
			TRUE ~ "Unknown"
		)
	}

	df <- df %>%
		mutate(
			doc_type_group_row = normalize_doc_type(
				if ("doc_type_ai_clean" %in% names(df)) doc_type_ai_clean else NA_character_,
				if ("doc_type_ai" %in% names(df)) doc_type_ai else NA_character_,
				if ("data_source" %in% names(df)) data_source else NA_character_
			)
		)

	paper_doc_types <- df %>%
		filter(!is.na(paper_id), paper_id != "") %>%
		group_by(paper_id) %>%
		summarise(
			doc_type_group = case_when(
				any(doc_type_group_row == "Full-Text") ~ "Full-Text",
				any(doc_type_group_row == "Abstract") ~ "Abstract",
				TRUE ~ "Unknown"
			),
			.groups = "drop"
		)

	df <- df %>%
		left_join(paper_doc_types, by = "paper_id") %>%
		mutate(doc_type_group = replace_na(doc_type_group, "Unknown"))

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

	if ("biome" %in% names(df)) {
		paper_biome <- df %>%
			filter(doc_type_group %in% c("Abstract", "Full-Text")) %>%
			mutate(
				paper_id = as.character(paper_id),
				biome_clean = standardize_biome(biome)
			) %>%
			filter(!is.na(paper_id), paper_id != "", !is.na(biome_clean), biome_clean != "Other/Specific") %>%
			distinct(paper_id, doc_type_group, biome_clean)

		biome_counts <- paper_biome %>%
			count(doc_type_group, biome_clean, name = "study_count")

		top_biomes <- biome_counts %>%
			group_by(biome_clean) %>%
			summarise(total = sum(study_count), .groups = "drop") %>%
			arrange(desc(total)) %>%
			slice_head(n = 10) %>%
			pull(biome_clean)

		biome_plot_df <- biome_counts %>%
			filter(biome_clean %in% top_biomes) %>%
			group_by(doc_type_group) %>%
			mutate(share = study_count / sum(study_count)) %>%
			ungroup() %>%
			mutate(biome_clean = fct_reorder(biome_clean, study_count, .fun = sum, .desc = TRUE))

		p_biome <- ggplot(biome_plot_df, aes(x = biome_clean, y = share, fill = doc_type_group)) +
			geom_col(position = position_dodge(width = 0.7), width = 0.65) +
			scale_y_continuous(labels = percent_format(accuracy = 1)) +
			scale_fill_manual(values = c(
				"Abstract" = endo_palette_discrete[1],
				"Full-Text" = endo_palette_discrete[2]
			)) +
			coord_flip() +
			theme_endo_bw(base_size = 11) +
			labs(
				title = "Biome distribution by document type",
				subtitle = "Top 10 biomes by study count (percent of studies)",
				x = NULL,
				y = "Share of studies",
				fill = "Document type"
			)

		ggsave(
			file.path(FIG_DIR, "abs_fulltext_biome_comparison.png"),
			p_biome,
			width = 6.5,
			height = 5,
			dpi = 300
		)
	} else {
		message("Skipping biome comparison: biome column not found in input file.")
	}
} else {
	message("Skipping biome comparison: input dataset not found.")
}

message("Abstract vs Full-Text comparison plotting complete.")
