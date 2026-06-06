#!/usr/bin/env Rscript
# =================================================================================
# compare_abs_fulltexts.R
# =================================================================================
# Purpose: Compare abstract-only vs full-text results across core analysis metrics.
# Outputs are written to results/abs_fulltext_comparison/<doc_type>/
# =================================================================================

suppressPackageStartupMessages({
	library(dplyr)
	library(readr)
	library(stringr)
	library(tidyr)
	library(scales)
	library(rnaturalearth)
	library(sf)
})

source("scripts/utils/pipeline_helpers.R")
source("scripts/utils/disputed_territory_parent_iso.R")

INPUT_FINAL <- "data/Ollama_cleaned_synresolved_standardized_final.csv"
INPUT_YEAR <- "data/Ollama_cleaned_synresolved_standardized_year.csv"
COUNTRY_ENRICHED <- "data/country_enriched_data.csv"
GBIF_TAXON_FILE <- "data/Reference_datasets/gbif_backbone/Taxon.tsv"
PBDB_FILE <- "data/Reference_datasets/pbdb_all.csv"
OUTPUT_ROOT <- "results/abs_fulltext_comparison"

resolve_existing_path <- function(candidates) {
	for (p in candidates) {
		if (file.exists(p)) {
			return(p)
		}
	}
	candidates[[1]]
}

GBIF_TAXON_FILE <- resolve_existing_path(c(
	GBIF_TAXON_FILE,
	"../data/Reference_datasets/gbif_backbone/Taxon.tsv",
	"../../data/Reference_datasets/gbif_backbone/Taxon.tsv"
))

PBDB_FILE <- resolve_existing_path(c(
	PBDB_FILE,
	"../data/Reference_datasets/pbdb_all.csv",
	"../../data/Reference_datasets/pbdb_all.csv"
))

dir.create(OUTPUT_ROOT, recursive = TRUE, showWarnings = FALSE)

input_file <- if (file.exists(INPUT_YEAR)) INPUT_YEAR else INPUT_FINAL
if (!file.exists(input_file)) {
	stop("Input file not found: ", input_file)
}
if (!file.exists(COUNTRY_ENRICHED)) {
	stop("Country enriched file not found: ", COUNTRY_ENRICHED)
}
if (!file.exists(GBIF_TAXON_FILE)) {
	stop("GBIF Taxon.tsv file not found: ", GBIF_TAXON_FILE)
}

message("Loading data from: ", input_file)
df <- read_csv(input_file, show_col_types = FALSE)

if (!"paper_id" %in% names(df)) {
	stop("Missing required column: paper_id")
}

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

doc_groups <- c("Abstract", "Full-Text")
if (any(df$doc_type_group == "Unknown")) {
	doc_groups <- c(doc_groups, "Unknown")
}

safe_slug <- function(x) {
	str_replace_all(str_to_lower(x), "[^a-z0-9]+", "_")
}

fast_read_tsv <- function(path, col_select = NULL) {
	if (requireNamespace("vroom", quietly = TRUE)) {
		vroom::vroom(path, delim = "\t", col_select = col_select, progress = FALSE)
	} else {
		readr::read_tsv(path, show_col_types = FALSE, progress = FALSE, col_select = col_select)
	}
}

cache_read_object_local <- function(qs_path, rds_path) {
	if (file.exists(qs_path) && requireNamespace("qs", quietly = TRUE)) {
		return(qs::qread(qs_path))
	}
	if (file.exists(rds_path)) {
		return(readRDS(rds_path))
	}
	NULL
}

cache_write_object_local <- function(object, qs_path, rds_path) {
	if (requireNamespace("qs", quietly = TRUE)) {
		qs::qsave(object, qs_path, preset = "high")
	}
	saveRDS(object, rds_path)
}

resolve_phylum_lookup <- function(taxa_min, parent_lookup, max_iter = 40) {
	resolved_phylum <- setNames(taxa_min$phylum, taxa_min$taxonID)
	unresolved_ids <- names(resolved_phylum)[resolved_phylum == "" | is.na(resolved_phylum)]

	if (length(unresolved_ids) == 0) {
		return(resolved_phylum)
	}

	for (i in seq_len(max_iter)) {
		if (length(unresolved_ids) == 0) {
			break
		}
		parent_ids <- unname(parent_lookup[unresolved_ids])
		parent_phylum <- unname(resolved_phylum[parent_ids])
		fillable <- !is.na(parent_phylum) & parent_phylum != ""
		if (!any(fillable)) {
			break
		}
		resolved_phylum[unresolved_ids[fillable]] <- parent_phylum[fillable]
		unresolved_ids <- names(resolved_phylum)[resolved_phylum == "" | is.na(resolved_phylum)]
	}

	resolved_phylum
}

load_plant_reference <- function() {
	gbif_min_qs <- file.path(CACHE_DIR, "gbif_taxa_min.qs")
	gbif_min_rds <- file.path(CACHE_DIR, "gbif_taxa_min.rds")
	gbif_ref_qs <- file.path(CACHE_DIR, "gbif_reference_species.qs")
	gbif_ref_rds <- file.path(CACHE_DIR, "gbif_reference_species.rds")

	gbif_taxa_min <- cache_read_object_local(gbif_min_qs, gbif_min_rds)
	reference_species <- cache_read_object_local(gbif_ref_qs, gbif_ref_rds)

	required_min_cols <- c("taxonID", "parentNameUsageID", "phylum", "taxonomicStatus", "kingdom")
	required_ref_cols <- c("taxonID", "canonicalName", "taxonRank", "taxonomicStatus", "kingdom", "phylum", "family", "genus")

	if (!is.null(gbif_taxa_min) && !all(required_min_cols %in% names(gbif_taxa_min))) {
		message("Cached GBIF Plantae min table missing required columns; rebuilding cache.")
		gbif_taxa_min <- NULL
	}
	if (!is.null(reference_species) && !all(required_ref_cols %in% names(reference_species))) {
		message("Cached GBIF Plantae reference missing required columns; rebuilding cache.")
		reference_species <- NULL
	}

	if (is.null(gbif_taxa_min) || is.null(reference_species)) {
		message("Building GBIF Plantae reference (first run may be slow)...")
		gbif_taxa_min <- fast_read_tsv(
			GBIF_TAXON_FILE,
			col_select = all_of(c("taxonID", "parentNameUsageID", "phylum", "taxonomicStatus", "kingdom"))
		) %>%
			mutate(
				taxonID = as.character(taxonID),
				parentNameUsageID = as.character(parentNameUsageID),
				phylum = as.character(phylum),
				taxonomicStatus = str_to_lower(str_trim(taxonomicStatus)),
				kingdom = str_trim(kingdom)
			) %>%
			filter(
				kingdom == "Plantae",
				taxonomicStatus == "accepted",
				!is.na(taxonID),
				taxonID != ""
			) %>%
			mutate(phylum = if_else(is.na(phylum), "", str_squish(phylum)))

		reference_species <- fast_read_tsv(
			GBIF_TAXON_FILE,
			col_select = all_of(c("taxonID", "canonicalName", "taxonRank", "taxonomicStatus", "kingdom", "phylum", "family", "genus"))
		) %>%
			mutate(
				taxonID = as.character(taxonID),
				taxonRank = str_to_upper(str_trim(taxonRank)),
				taxonomicStatus = str_to_lower(str_trim(taxonomicStatus)),
				kingdom = str_trim(kingdom),
				phylum = if_else(is.na(phylum), "", str_squish(phylum))
			) %>%
			filter(
				kingdom == "Plantae",
				taxonRank == "SPECIES",
				taxonomicStatus == "accepted",
				!is.na(taxonID),
				taxonID != ""
			) %>%
			distinct(taxonID, .keep_all = TRUE)

		try({
			dir.create(CACHE_DIR, recursive = TRUE, showWarnings = FALSE)
			cache_write_object_local(gbif_taxa_min, gbif_min_qs, gbif_min_rds)
			cache_write_object_local(reference_species, gbif_ref_qs, gbif_ref_rds)
		}, silent = TRUE)
	}

	parent_lookup <- setNames(gbif_taxa_min$parentNameUsageID, gbif_taxa_min$taxonID)
	phylum_lookup <- resolve_phylum_lookup(gbif_taxa_min, parent_lookup)

	missing_phylum_before <- sum(is.na(reference_species$phylum) | reference_species$phylum == "")
	if (missing_phylum_before > 0) {
		resolved_values <- unname(phylum_lookup[reference_species$taxonID])
		reference_species <- reference_species %>%
			mutate(phylum = if_else(phylum == "" & !is.na(resolved_values) & resolved_values != "", resolved_values, phylum))
	}
	missing_phylum_after <- sum(is.na(reference_species$phylum) | reference_species$phylum == "")
	phylum_backfilled <- missing_phylum_before - missing_phylum_after

	total_known_raw <- nrow(reference_species)
	pbdb_extinct_species_count <- 0L
	pbdb_extinct_only_species_count <- 0L
	gbif_removed_by_pbdb <- 0L

	if (file.exists(PBDB_FILE)) {
		pbdb_raw <- read_csv(PBDB_FILE, show_col_types = FALSE, skip = 16)
		if (all(c("taxon_rank", "taxon_name", "accepted_rank", "accepted_name", "is_extant") %in% names(pbdb_raw))) {
			pbdb_species_status <- pbdb_raw %>%
				mutate(
					taxon_rank = str_to_lower(str_trim(taxon_rank)),
					accepted_rank = str_to_lower(str_trim(accepted_rank)),
					is_extant = str_to_lower(str_trim(is_extant)),
					taxon_name = str_squish(str_to_lower(taxon_name)),
					accepted_name = str_squish(str_to_lower(accepted_name))
				) %>%
				transmute(
					species_name = case_when(
						taxon_rank == "species" ~ taxon_name,
						accepted_rank == "species" ~ accepted_name,
						TRUE ~ NA_character_
					),
					is_extant
				) %>%
				filter(!is.na(species_name), species_name != "") %>%
				group_by(species_name) %>%
				summarise(
					any_extinct = any(is_extant == "extinct"),
					any_extant = any(is_extant == "extant"),
					.groups = "drop"
				)

			pbdb_extinct_names <- pbdb_species_status %>%
				filter(any_extinct) %>%
				transmute(candidate_name = species_name)

			pbdb_extinct_only_names <- pbdb_species_status %>%
				filter(any_extinct, !any_extant) %>%
				transmute(candidate_name = species_name)

			pbdb_extinct_species_count <- nrow(pbdb_extinct_names)
			pbdb_extinct_only_species_count <- nrow(pbdb_extinct_only_names)

			reference_species <- reference_species %>%
				mutate(canonical_lc = str_squish(str_to_lower(canonicalName))) %>%
				left_join(
					pbdb_extinct_only_names %>% mutate(pbdb_extinct_match = TRUE),
					by = c("canonical_lc" = "candidate_name")
				)

			gbif_removed_by_pbdb <- sum(reference_species$pbdb_extinct_match %in% TRUE, na.rm = TRUE)

			reference_species <- reference_species %>%
				filter(!pbdb_extinct_match %in% TRUE) %>%
				select(-canonical_lc, -pbdb_extinct_match)
		}
	}

	list(
		reference_species = reference_species,
		missing_phylum_before = missing_phylum_before,
		missing_phylum_after = missing_phylum_after,
		phylum_backfilled = phylum_backfilled,
		total_known_raw = total_known_raw,
		pbdb_extinct_species_count = pbdb_extinct_species_count,
		pbdb_extinct_only_species_count = pbdb_extinct_only_species_count,
		gbif_removed_by_pbdb = gbif_removed_by_pbdb
	)
}

load_fungi_reference <- function() {
	cache_qs <- file.path(CACHE_DIR, "gbif_fungi_min.qs")
	cache_rds <- file.path(CACHE_DIR, "gbif_fungi_min.rds")
	fungi_min <- cache_read_object_local(cache_qs, cache_rds)
	required_fungi_cols <- c("taxonID", "parentNameUsageID", "taxonRank", "taxonomicStatus", "kingdom", "phylum", "family", "genus")
	if (!is.null(fungi_min) && !all(required_fungi_cols %in% names(fungi_min))) {
		message("Cached GBIF Fungi reference missing required columns; rebuilding cache.")
		fungi_min <- NULL
	}

	if (is.null(fungi_min)) {
		message("Building GBIF Fungi reference (first run may be slow)...")
		fungi_min <- fast_read_tsv(
			GBIF_TAXON_FILE,
			col_select = all_of(c("taxonID", "parentNameUsageID", "taxonRank", "taxonomicStatus", "kingdom", "phylum", "family", "genus", "canonicalName"))
		) %>%
			mutate(
				taxonID = as.character(taxonID),
				parentNameUsageID = as.character(parentNameUsageID),
				taxonRank = str_to_upper(str_trim(taxonRank)),
				taxonomicStatus = str_to_lower(str_trim(taxonomicStatus)),
				kingdom = str_trim(kingdom),
				phylum = if_else(is.na(phylum), "", str_squish(phylum)),
				family = if_else(is.na(family), "", str_squish(family)),
				genus = if_else(is.na(genus), "", str_squish(genus))
			) %>%
			filter(
				kingdom == "Fungi",
				taxonomicStatus == "accepted",
				!is.na(taxonID),
				taxonID != ""
			)

		parent_lookup <- setNames(fungi_min$parentNameUsageID, fungi_min$taxonID)
		phylum_lookup <- resolve_phylum_lookup(fungi_min, parent_lookup)
		resolved_values <- unname(phylum_lookup[fungi_min$taxonID])
		fungi_min <- fungi_min %>%
			mutate(phylum = if_else(phylum == "" & !is.na(resolved_values) & resolved_values != "", resolved_values, phylum))

		try({
			dir.create(CACHE_DIR, recursive = TRUE, showWarnings = FALSE)
			cache_write_object_local(fungi_min, cache_qs, cache_rds)
		}, silent = TRUE)
	}

	list(
		fungi_min = fungi_min,
		fungi_species = fungi_min %>% filter(taxonRank == "SPECIES"),
		fungi_genus = fungi_min %>% filter(taxonRank == "GENUS"),
		fungi_family = fungi_min %>% filter(taxonRank == "FAMILY")
	)
}

country_base <- read_csv(COUNTRY_ENRICHED, show_col_types = FALSE) %>%
	mutate(
		study_count = as.numeric(study_count),
		centroid_lat = as.numeric(centroid_lat),
		centroid_lon = as.numeric(centroid_lon),
		gdp_current_usd = as.numeric(gdp_current_usd),
		gdp_log10 = ifelse(!is.na(gdp_current_usd) & gdp_current_usd > 0, log10(gdp_current_usd), NA_real_)
	) %>%
	distinct(iso_a3, .keep_all = TRUE)

plant_reference <- load_plant_reference()
fungi_reference <- load_fungi_reference()

compute_doc_summary <- function(df_group) {
	total_rows <- nrow(df_group)
	unique_papers <- n_distinct(df_group$paper_id)
	unique_interactions <- if ("interaction_id" %in% names(df_group)) n_distinct(df_group$interaction_id) else NA_integer_
	unique_countries <- if ("country" %in% names(df_group)) n_distinct(df_group$country) else NA_integer_
	unique_biomes <- if ("biome" %in% names(df_group)) n_distinct(df_group$biome) else NA_integer_
	unique_fungal_ids <- if ("fungal_taxon_accepted_ids" %in% names(df_group)) n_distinct(df_group$fungal_taxon_accepted_ids) else NA_integer_
	unique_plant_ids <- if ("plant_host_accepted_ids" %in% names(df_group)) n_distinct(df_group$plant_host_accepted_ids) else NA_integer_

	tibble(
		total_rows = total_rows,
		unique_papers = unique_papers,
		unique_interactions = unique_interactions,
		unique_countries = unique_countries,
		unique_biomes = unique_biomes,
		unique_fungal_ids = unique_fungal_ids,
		unique_plant_ids = unique_plant_ids
	)
}

compute_country_metrics <- function(df_group, output_dir) {
	if (!"country" %in% names(df_group)) {
		return(list(country_summary = tibble(), correlations = tibble()))
	}

	country_counts <- df_group %>%
		filter(!is.na(country), country != "") %>%
		distinct(paper_id, country) %>%
		count(country, name = "study_count")

	country_summary <- country_base %>%
		select(-study_count) %>%
		left_join(country_counts, by = c("iso_a3" = "country")) %>%
		mutate(study_count = replace_na(study_count, 0L)) %>%
		arrange(desc(study_count), country_name)

	write_csv(country_summary, file.path(output_dir, "country_gdp_latitude_summary.csv"))

	analysis_data <- country_summary %>%
		filter(!is.na(study_count), !is.na(centroid_lat))

	corr_pairs <- list(
		list(x = "gdp_log10", y = "study_count", label = "study_count_vs_log10_gdp"),
		list(x = "centroid_lat", y = "study_count", label = "study_count_vs_latitude")
	)

	correlations <- lapply(corr_pairs, function(spec) {
		subset_data <- analysis_data %>%
			filter(!is.na(.data[[spec$x]]), !is.na(.data[[spec$y]]))

		if (nrow(subset_data) < 3) {
			return(tibble(
				analysis = spec$label,
				n = nrow(subset_data),
				pearson_r = NA_real_,
				pearson_p = NA_real_,
				spearman_rho = NA_real_,
				spearman_p = NA_real_
			))
		}

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

	write_csv(correlations, file.path(output_dir, "country_gdp_latitude_correlations.csv"))

	list(country_summary = country_summary, correlations = correlations)
}

compute_geographic_bias <- function(country_summary, output_dir) {
	if (nrow(country_summary) == 0) {
		return(invisible(NULL))
	}

	world <- ne_countries(scale = 50, returnclass = "sf")

	world_data <- world %>%
		left_join(
			country_summary %>% select(iso_a3, country_name, study_count, gdp_current_usd, gdp_log10),
			by = c("iso_a3" = "iso_a3")
		) %>%
		mutate(
			study_count = replace_na(study_count, 0),
			continent = ifelse(is.na(continent), "Unknown", as.character(continent))
		)

	p75 <- quantile(country_summary$study_count, 0.75, na.rm = TRUE)
	p90 <- quantile(country_summary$study_count, 0.90, na.rm = TRUE)
	p25 <- quantile(country_summary$study_count, 0.25, na.rm = TRUE)

	bias_metrics <- country_summary %>%
		mutate(
			study_count_percentile = percent_rank(study_count),
			bias_class = case_when(
				study_count == 0 ~ "No studies",
				study_count_percentile >= 0.90 ~ "Over-studied (top 10%)",
				study_count_percentile >= 0.75 ~ "Well-studied (top 25%)",
				study_count_percentile >= 0.50 ~ "Moderate coverage (top 50%)",
				study_count_percentile >= 0.25 ~ "Under-studied (bottom 50%)",
				TRUE ~ "Rare/minimal coverage"
			),
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

	write_csv(bias_metrics, file.path(output_dir, "geographic_bias_metrics.csv"))

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

	write_csv(continental_data, file.path(output_dir, "continental_breakdown.csv"))
}

compute_relationship_summary <- function(df_group, output_dir) {
	required_cols <- c("paper_id", "country", "primary_guild", "interaction_notes", "fungal_taxon", "presence_absence")
	if (!all(required_cols %in% names(df_group))) {
		return(invisible(NULL))
	}

	`%||%` <- function(x, y) ifelse(is.na(x), y, x)

	classify_relationship <- function(primary_guild, interaction_notes, fungal_taxon, presence_absence) {
		txt <- str_to_lower(str_squish(paste(
			primary_guild %||% "",
			interaction_notes %||% "",
			fungal_taxon %||% "",
			presence_absence %||% ""
		)))

		if (str_detect(txt, "pathogen|pathogenic|disease|blight|wilt|anthracnose|lesion|necrosis|rot")) return("Pathogenic")
		if (str_detect(txt, "mycorrhiz|amf|arbuscular|ectomycorrhiz|endomycorrhiz|glomer")) return("Mycorrhizal")
		if (str_detect(txt, "antagonist|biocontrol|biological control|inhibit|suppres")) return("Antagonistic/Biocontrol")
		if (str_detect(txt, "mutual|beneficial symbio")) return("Mutualistic")
		if (str_detect(txt, "saprotroph|saprophy|decomposer")) return("Saprotrophic")
		if (str_detect(txt, "commensal")) return("Commensal")
		if (str_detect(txt, "endophyt|latent fungus|internal fungus|resident fungi|dse")) return("Endophytic")
		if (str_detect(txt, "absence|none found|not detected|no evidence")) return("Absence/Negative")
		"Unknown/Other"
	}

	summary_df <- df_group %>%
		mutate(
			relationship_type = mapply(
				classify_relationship,
				primary_guild,
				interaction_notes,
				fungal_taxon,
				presence_absence,
				USE.NAMES = FALSE
			),
			country = if_else(is.na(country) | country == "", "Unknown", country)
		)

	by_interaction <- summary_df %>%
		count(relationship_type, sort = TRUE, name = "interaction_count") %>%
		mutate(percent_of_interactions = round(100 * interaction_count / sum(interaction_count), 2))

	by_study <- summary_df %>%
		filter(!is.na(paper_id), paper_id != "") %>%
		distinct(paper_id, relationship_type) %>%
		count(relationship_type, sort = TRUE, name = "study_count") %>%
		mutate(percent_of_studies = round(100 * study_count / sum(study_count), 2))

	by_country <- summary_df %>%
		filter(country != "Unknown") %>%
		distinct(paper_id, country, relationship_type) %>%
		count(country, relationship_type, sort = TRUE, name = "study_count")

	write_csv(by_interaction, file.path(output_dir, "relationship_type_counts_by_interaction.csv"))
	write_csv(by_study, file.path(output_dir, "relationship_type_counts_by_study.csv"))
	write_csv(by_country, file.path(output_dir, "relationship_type_counts_by_country.csv"))

	if ("publication_year" %in% names(summary_df)) {
		by_year <- summary_df %>%
			filter(!is.na(publication_year)) %>%
			distinct(paper_id, publication_year, relationship_type) %>%
			count(publication_year, relationship_type, sort = TRUE, name = "study_count")
		write_csv(by_year, file.path(output_dir, "relationship_type_counts_by_year.csv"))
	}
}

compute_interaction_bias <- function(df_group, output_dir) {
	required_cols <- c("paper_id", "fungal_taxon_accepted_ids", "plant_host_accepted_ids", "country", "tissue")
	if (!all(required_cols %in% names(df_group))) {
		return(invisible(NULL))
	}

	gbif_all_qs <- file.path(CACHE_DIR, "gbif_taxa_min_all.qs")
	gbif_all_rds <- file.path(CACHE_DIR, "gbif_taxa_min_all.rds")
	gbif_min <- cache_read_object_local(gbif_all_qs, gbif_all_rds)
	if (!is.null(gbif_min) && !all(c("taxonID", "kingdom", "phylum", "taxonomicStatus") %in% names(gbif_min))) {
		message("Cached GBIF min-all table missing required columns; rebuilding cache.")
		gbif_min <- NULL
	}

	if (is.null(gbif_min)) {
		gbif_min <- fast_read_tsv(
			GBIF_TAXON_FILE,
			col_select = all_of(c("taxonID", "kingdom", "phylum", "taxonomicStatus"))
		) %>%
			mutate(
				taxonID = as.character(taxonID),
				kingdom = str_trim(kingdom),
				phylum = if_else(is.na(phylum) | phylum == "", "Unassigned", str_squish(phylum)),
				taxonomicStatus = str_to_lower(str_trim(taxonomicStatus))
			) %>%
			filter(
				kingdom %in% c("Fungi", "Plantae"),
				taxonomicStatus == "accepted",
				!is.na(taxonID),
				taxonID != ""
			)

		try({
			dir.create(CACHE_DIR, recursive = TRUE, showWarnings = FALSE)
			cache_write_object_local(gbif_min, gbif_all_qs, gbif_all_rds)
		}, silent = TRUE)
	}

	continent_lookup <- ne_countries(scale = 110, returnclass = "sf") %>%
		sf::st_drop_geometry() %>%
		select(iso_a3, continent) %>%
		distinct(iso_a3, .keep_all = TRUE)

	df_clean <- df_group %>%
		mutate(
			fungal_id = str_extract(fungal_taxon_accepted_ids, "^[^;]+"),
			plant_id = str_extract(plant_host_accepted_ids, "^[^;]+")
		) %>%
		left_join(gbif_min %>% rename(fungal_phylum = phylum, f_king = kingdom), by = c("fungal_id" = "taxonID")) %>%
		left_join(gbif_min %>% rename(plant_phylum = phylum, p_king = kingdom), by = c("plant_id" = "taxonID")) %>%
		left_join(continent_lookup, by = c("country" = "iso_a3")) %>%
		mutate(
			fungal_phylum = replace_na(fungal_phylum, "Unknown Fungi"),
			plant_phylum = replace_na(plant_phylum, "Unknown Plant"),
			continent = replace_na(continent, "Unknown"),
			tissue = replace_na(tissue, "Unknown")
		)

	fungal_continent <- df_clean %>%
		filter(!is.na(paper_id), fungal_phylum != "Unknown Fungi", continent != "Unknown") %>%
		distinct(paper_id, fungal_phylum, continent) %>%
		count(fungal_phylum, continent, name = "study_count")

	write_csv(fungal_continent, file.path(output_dir, "fungal_phylum_vs_continent.csv"))

	df_clean <- df_clean %>%
		mutate(tissue_group = case_when(
			str_detect(tolower(tissue), "leaf|foliar") ~ "Leaf",
			str_detect(tolower(tissue), "root|rhizo") ~ "Root",
			str_detect(tolower(tissue), "stem|wood|bark|shoot") ~ "Stem/Wood",
			str_detect(tolower(tissue), "seed") ~ "Seed",
			TRUE ~ "Other/Unknown"
		))

	fungal_tissue <- df_clean %>%
		filter(!is.na(paper_id), fungal_phylum != "Unknown Fungi", tissue_group != "Other/Unknown") %>%
		distinct(paper_id, fungal_phylum, tissue_group) %>%
		count(fungal_phylum, tissue_group, name = "study_count")

	write_csv(fungal_tissue, file.path(output_dir, "fungal_phylum_vs_tissue.csv"))

	top_fungal <- fungal_continent %>%
		group_by(fungal_phylum) %>%
		summarise(total = sum(study_count), .groups = "drop") %>%
		arrange(desc(total)) %>%
		slice_head(n = 5) %>%
		pull(fungal_phylum)

	fc_analysis_data <- df_clean %>%
		filter(fungal_phylum %in% top_fungal, continent != "Unknown")

	if (nrow(fc_analysis_data) > 0 && n_distinct(fc_analysis_data$fungal_phylum) > 1 && n_distinct(fc_analysis_data$continent) > 1) {
		fc_table <- table(fc_analysis_data$fungal_phylum, fc_analysis_data$continent)
		if (all(dim(fc_table) > 1)) {
			fc_chi <- chisq.test(fc_table, simulate.p.value = TRUE, B = 2000)
			fc_stats <- tibble(
				test = "Chi-Square: Fungal Phylum x Continent",
				statistic = fc_chi$statistic,
				p_value = fc_chi$p.value,
				method = fc_chi$method,
				interpretation = ifelse(fc_chi$p.value < 0.05,
					"Significant bias: Fungal phyla are not studied equally across continents.",
					"No significant bias detected."
				)
			)
		} else {
			fc_stats <- tibble(test = "Chi-Square: Fungal Phylum x Continent", interpretation = "Skipped: Not enough data diversity for test.")
		}
	} else {
		fc_stats <- tibble(test = "Chi-Square: Fungal Phylum x Continent", interpretation = "Skipped: Not enough data to create contingency table.")
	}

	ft_analysis_data <- df_clean %>%
		filter(fungal_phylum %in% top_fungal, tissue_group != "Other/Unknown")

	if (nrow(ft_analysis_data) > 0 && n_distinct(ft_analysis_data$fungal_phylum) > 1 && n_distinct(ft_analysis_data$tissue_group) > 1) {
		ft_table <- table(ft_analysis_data$fungal_phylum, ft_analysis_data$tissue_group)
		if (all(dim(ft_table) > 1)) {
			ft_chi <- chisq.test(ft_table, simulate.p.value = TRUE, B = 2000)
			ft_stats <- tibble(
				test = "Chi-Square: Fungal Phylum x Tissue Category",
				statistic = ft_chi$statistic,
				p_value = ft_chi$p.value,
				method = ft_chi$method,
				interpretation = ifelse(ft_chi$p.value < 0.05,
					"Significant bias: Fungal phyla are not studied equally across plant tissues.",
					"No significant bias detected."
				)
			)
		} else {
			ft_stats <- tibble(test = "Chi-Square: Fungal Phylum x Tissue Category", interpretation = "Skipped: Not enough data diversity for test.")
		}
	} else {
		ft_stats <- tibble(test = "Chi-Square: Fungal Phylum x Tissue Category", interpretation = "Skipped: Not enough data to create contingency table.")
	}

	all_stats <- bind_rows(fc_stats, ft_stats)
	write_csv(all_stats, file.path(output_dir, "interaction_statistical_tests.csv"))
}

compute_plant_taxonomy <- function(df_group, output_dir) {
	required_cols <- c("paper_id", "plant_host_resolved", "plant_host_accepted_ids")
	if (!all(required_cols %in% names(df_group))) {
		return(list(summary = tibble()))
	}

	reference_species <- plant_reference$reference_species

	study_species_links <- df_group %>%
		mutate(
			paper_id = as.character(paper_id),
			plant_host_accepted_ids = as.character(plant_host_accepted_ids),
			plant_host_resolved = as.character(plant_host_resolved)
		) %>%
		filter(
			!is.na(paper_id),
			paper_id != "",
			!is.na(plant_host_accepted_ids),
			plant_host_accepted_ids != ""
		) %>%
		mutate(accepted_id = str_split(plant_host_accepted_ids, "\\s*;\\s*")) %>%
		unnest_longer(accepted_id) %>%
		mutate(accepted_id = str_squish(accepted_id)) %>%
		filter(!is.na(accepted_id), accepted_id != "") %>%
		distinct(paper_id, plant_host_resolved, accepted_id)

	study_species_matched <- study_species_links %>%
		inner_join(reference_species, by = c("accepted_id" = "taxonID"))

	studied_species <- study_species_matched %>%
		distinct(accepted_id, canonicalName, phylum, family, genus)

	studied_species_count <- nrow(studied_species)
	total_known <- nrow(reference_species)
	coverage_pct <- if (total_known > 0) 100 * studied_species_count / total_known else NA_real_

	coverage_summary <- tibble(
		dataset_rows = nrow(df_group),
		rows_with_plantae_host = sum(!is.na(df_group$plant_host_accepted_ids) & df_group$plant_host_accepted_ids != "", na.rm = TRUE),
		unique_papers_with_plantae_host_ids = n_distinct(study_species_links$paper_id),
		unique_plantae_accepted_ids_in_dataset = n_distinct(study_species_links$accepted_id),
		unique_plantae_species_matched_to_gbif = studied_species_count,
		gbif_species_missing_phylum_before_backfill = plant_reference$missing_phylum_before,
		gbif_species_missing_phylum_after_backfill = plant_reference$missing_phylum_after,
		gbif_species_phylum_backfilled_from_lineage = plant_reference$phylum_backfilled,
		total_known_plant_species_gbif_raw = plant_reference$total_known_raw,
		pbdb_extinct_species_name_count = plant_reference$pbdb_extinct_species_count,
		pbdb_extinct_only_species_name_count = plant_reference$pbdb_extinct_only_species_count,
		gbif_species_removed_by_pbdb_extinct_filter = plant_reference$gbif_removed_by_pbdb,
		total_known_plant_species_gbif = total_known,
		coverage_percent = coverage_pct
	)

	write_csv(coverage_summary, file.path(output_dir, "plant_species_coverage_summary.csv"))

	known_by_phylum <- reference_species %>%
		mutate(phylum = if_else(is.na(phylum) | phylum == "", "Unassigned", phylum)) %>%
		count(phylum, name = "known_species")

	studied_by_phylum <- studied_species %>%
		mutate(phylum = if_else(is.na(phylum) | phylum == "", "Unassigned", phylum)) %>%
		count(phylum, name = "studied_species")

	coverage_by_phylum <- known_by_phylum %>%
		left_join(studied_by_phylum, by = "phylum") %>%
		mutate(
			studied_species = replace_na(studied_species, 0L),
			coverage_percent = 100 * studied_species / known_species
		) %>%
		arrange(desc(known_species))

	write_csv(coverage_by_phylum, file.path(output_dir, "plant_species_coverage_by_phylum.csv"))

	known_genera_by_phylum <- reference_species %>%
		filter(!is.na(genus), genus != "") %>%
		mutate(phylum = if_else(is.na(phylum) | phylum == "", "Unassigned", phylum)) %>%
		distinct(phylum, genus) %>%
		count(phylum, name = "known_genera")

	studied_genera_by_phylum <- studied_species %>%
		filter(!is.na(genus), genus != "") %>%
		mutate(phylum = if_else(is.na(phylum) | phylum == "", "Unassigned", phylum)) %>%
		distinct(phylum, genus) %>%
		count(phylum, name = "studied_genera")

	genus_coverage_by_phylum <- known_genera_by_phylum %>%
		left_join(studied_genera_by_phylum, by = "phylum") %>%
		mutate(
			studied_genera = replace_na(studied_genera, 0L),
			coverage_percent = 100 * studied_genera / known_genera
		) %>%
		arrange(desc(known_genera))

	write_csv(genus_coverage_by_phylum, file.path(output_dir, "plant_genus_coverage_by_phylum.csv"))

	known_families_by_phylum <- reference_species %>%
		filter(!is.na(family), family != "") %>%
		mutate(phylum = if_else(is.na(phylum) | phylum == "", "Unassigned", phylum)) %>%
		distinct(phylum, family) %>%
		count(phylum, name = "known_families")

	studied_families_by_phylum <- studied_species %>%
		filter(!is.na(family), family != "") %>%
		mutate(phylum = if_else(is.na(phylum) | phylum == "", "Unassigned", phylum)) %>%
		distinct(phylum, family) %>%
		count(phylum, name = "studied_families")

	family_coverage_by_phylum <- known_families_by_phylum %>%
		left_join(studied_families_by_phylum, by = "phylum") %>%
		mutate(
			studied_families = replace_na(studied_families, 0L),
			coverage_percent = 100 * studied_families / known_families
		) %>%
		arrange(desc(known_families))

	write_csv(family_coverage_by_phylum, file.path(output_dir, "plant_family_coverage_by_phylum.csv"))

	top_studied_species <- study_species_matched %>%
		distinct(paper_id, accepted_id, canonicalName, phylum, family, genus) %>%
		count(accepted_id, canonicalName, phylum, family, genus, name = "study_count", sort = TRUE) %>%
		slice_head(n = 100)

	write_csv(top_studied_species, file.path(output_dir, "top_studied_plant_species.csv"))

	list(
		summary = coverage_summary,
		studied_species = studied_species,
		study_species_links = study_species_links
	)
}

compute_understudied_taxa <- function(plant_results, output_dir) {
	if (nrow(plant_results$summary) == 0) {
		return(invisible(NULL))
	}

	normalize_name <- function(x) {
		x %>% as.character() %>% str_to_lower() %>% str_squish()
	}

	all_known_taxa <- plant_reference$reference_species %>%
		select(canonicalName, genus, family) %>%
		distinct()

	known_species_df <- all_known_taxa %>%
		filter(!is.na(canonicalName), canonicalName != "") %>%
		transmute(label = canonicalName, key = normalize_name(canonicalName)) %>%
		filter(!is.na(key), key != "") %>%
		distinct(key, .keep_all = TRUE)

	known_genera_df <- all_known_taxa %>%
		filter(!is.na(genus), genus != "") %>%
		transmute(label = genus, key = normalize_name(genus)) %>%
		filter(!is.na(key), key != "") %>%
		distinct(key, .keep_all = TRUE)

	known_families_df <- all_known_taxa %>%
		filter(!is.na(family), family != "") %>%
		transmute(label = family, key = normalize_name(family)) %>%
		filter(!is.na(key), key != "") %>%
		distinct(key, .keep_all = TRUE)

	studied_species_keys <- plant_results$studied_species %>%
		filter(!is.na(canonicalName), canonicalName != "") %>%
		transmute(key = normalize_name(canonicalName)) %>%
		distinct() %>%
		pull(key)

	studied_genera_keys <- plant_results$studied_species %>%
		filter(!is.na(genus), genus != "") %>%
		transmute(key = normalize_name(genus)) %>%
		distinct() %>%
		pull(key)

	studied_families_keys <- plant_results$studied_species %>%
		filter(!is.na(family), family != "") %>%
		transmute(key = normalize_name(family)) %>%
		distinct() %>%
		pull(key)

	unstudied_families <- known_families_df %>%
		filter(!key %in% studied_families_keys) %>%
		transmute(family = label) %>%
		arrange(family)

	unstudied_genera <- known_genera_df %>%
		filter(!key %in% studied_genera_keys) %>%
		transmute(genus = label) %>%
		arrange(genus)

	unstudied_species <- known_species_df %>%
		filter(!key %in% studied_species_keys) %>%
		transmute(species = label) %>%
		arrange(species)

	write_csv(unstudied_families, file.path(output_dir, "unstudied_plant_families.csv"))
	write_csv(unstudied_genera, file.path(output_dir, "unstudied_plant_genera.csv"))
	write_csv(unstudied_species, file.path(output_dir, "unstudied_plant_species.csv"))
}

compute_understudied_countries <- function(country_summary, output_dir) {
	if (nrow(country_summary) == 0) {
		return(invisible(NULL))
	}

	world <- ne_countries(scale = 110, returnclass = "sf") %>%
		select(iso_a3, name) %>%
		apply_disputed_parent_iso_world() %>%
		st_drop_geometry() %>%
		filter(iso_a3 != "-99") %>%
		distinct(iso_a3, name)

	studied_iso <- country_summary %>%
		filter(study_count > 0) %>%
		distinct(iso_a3) %>%
		pull(iso_a3)

	unstudied_countries <- world %>%
		filter(!iso_a3 %in% studied_iso)

	write_csv(unstudied_countries, file.path(output_dir, "unstudied_countries.csv"))
}

compute_fungal_taxonomy <- function(df_group, plant_summary, output_dir) {
	required_cols <- c("paper_id", "fungal_taxon_resolved", "fungal_taxon_accepted_ids")
	if (!all(required_cols %in% names(df_group))) {
		return(tibble())
	}

	fungi_species <- fungi_reference$fungi_species
	fungi_genus <- fungi_reference$fungi_genus
	fungi_family <- fungi_reference$fungi_family

	study_fungi_links <- df_group %>%
		mutate(
			paper_id = as.character(paper_id),
			fungal_taxon_accepted_ids = as.character(fungal_taxon_accepted_ids),
			fungal_taxon_resolved = as.character(fungal_taxon_resolved)
		) %>%
		filter(
			!is.na(paper_id),
			paper_id != "",
			!is.na(fungal_taxon_accepted_ids),
			fungal_taxon_accepted_ids != ""
		) %>%
		mutate(accepted_id = str_split(fungal_taxon_accepted_ids, "\\s*;\\s*")) %>%
		unnest_longer(accepted_id) %>%
		mutate(accepted_id = str_squish(accepted_id)) %>%
		filter(!is.na(accepted_id), accepted_id != "") %>%
		distinct(paper_id, fungal_taxon_resolved, accepted_id)

	matched_taxa <- study_fungi_links %>%
		inner_join(fungi_species, by = c("accepted_id" = "taxonID"))
	if (!"taxonID" %in% names(matched_taxa)) {
		matched_taxa <- matched_taxa %>%
			mutate(taxonID = accepted_id)
	}

	unique_studied <- matched_taxa %>%
		distinct(taxonID, phylum, family, genus)

	known_by_phylum <- fungi_species %>%
		mutate(phylum = if_else(is.na(phylum) | phylum == "", "Unassigned", phylum)) %>%
		count(phylum, name = "known_species")

	studied_by_phylum <- unique_studied %>%
		mutate(phylum = if_else(is.na(phylum) | phylum == "", "Unassigned", phylum)) %>%
		count(phylum, name = "studied_species")

	coverage_phylum <- known_by_phylum %>%
		left_join(studied_by_phylum, by = "phylum") %>%
		mutate(
			studied_species = replace_na(studied_species, 0L),
			coverage_percent = 100 * studied_species / known_species
		) %>%
		arrange(desc(known_species))

	write_csv(coverage_phylum, file.path(output_dir, "fungal_phylum_coverage.csv"))

	known_genera <- fungi_genus %>%
		filter(genus != "") %>%
		distinct(phylum, genus) %>%
		count(phylum, name = "known_genera")

	studied_genera <- matched_taxa %>%
		filter(genus != "") %>%
		distinct(phylum, genus) %>%
		count(phylum, name = "studied_genera")

	coverage_genus <- known_genera %>%
		left_join(studied_genera, by = "phylum") %>%
		mutate(
			studied_genera = replace_na(studied_genera, 0L),
			coverage_percent = 100 * studied_genera / known_genera
		) %>%
		arrange(desc(known_genera))

	write_csv(coverage_genus, file.path(output_dir, "fungal_genus_coverage.csv"))

	known_families <- fungi_family %>%
		filter(family != "") %>%
		distinct(phylum, family) %>%
		count(phylum, name = "known_families")

	studied_families <- matched_taxa %>%
		filter(family != "") %>%
		distinct(phylum, family) %>%
		count(phylum, name = "studied_families")

	coverage_family <- known_families %>%
		left_join(studied_families, by = "phylum") %>%
		mutate(
			studied_families = replace_na(studied_families, 0L),
			coverage_percent = 100 * studied_families / known_families
		) %>%
		arrange(desc(known_families))

	write_csv(coverage_family, file.path(output_dir, "fungal_family_coverage.csv"))

	top_genera <- matched_taxa %>%
		filter(genus != "") %>%
		distinct(paper_id, taxonID, genus, phylum, family) %>%
		count(genus, phylum, family, name = "study_count", sort = TRUE) %>%
		slice_head(n = 100)

	write_csv(top_genera, file.path(output_dir, "top_studied_fungal_genera.csv"))

	fungal_summary <- tibble(
		dataset_rows = nrow(df_group),
		rows_with_fungi_records = sum(!is.na(df_group$fungal_taxon_accepted_ids) & df_group$fungal_taxon_accepted_ids != "", na.rm = TRUE),
		unique_papers_with_fungi = n_distinct(study_fungi_links$paper_id),
		unique_fungi_accepted_ids = n_distinct(study_fungi_links$accepted_id),
		unique_fungi_species_matched_to_gbif = nrow(unique_studied),
		total_known_fungi_species_gbif = nrow(fungi_species),
		coverage_percent = if (nrow(fungi_species) > 0) 100 * nrow(unique_studied) / nrow(fungi_species) else NA_real_,
		phyla_represented = nrow(coverage_phylum),
		phyla_with_studies = sum(coverage_phylum$studied_species > 0, na.rm = TRUE)
	)

	plant_values <- lapply(names(fungal_summary), function(metric) {
		if (nrow(plant_summary) > 0 && metric %in% names(plant_summary)) {
			plant_summary[[metric]][1]
		} else {
			NA
		}
	})

	comparison <- tibble(
		Metric = names(fungal_summary),
		Fungi = as.list(fungal_summary[1, names(fungal_summary)]),
		Plants = plant_values
	)

	write_csv(comparison, file.path(output_dir, "fungal_vs_plant_comparison.csv"))

	mycorrhizal_keywords <- c(
		"mycorrhiz", "amf", "arbuscular", "ectomycorrhiz",
		"endomycorrhiz", "ery", "glomerales", "glomeromycota"
	)

	myco_pattern <- paste(mycorrhizal_keywords, collapse = "|")
	mycorrhizal_summary <- df_group %>%
		filter(str_detect(str_to_lower(coalesce(fungal_taxon_resolved, "")), myco_pattern)) %>%
		select(paper_id, fungal_taxon_resolved) %>%
		distinct()

	write_csv(mycorrhizal_summary, file.path(output_dir, "mycorrhizal_annotation.csv"))

	fungal_summary
}

compute_biodiversity_overlap <- function(df_group, country_summary, unstudied_countries, output_dir) {
	priority_countries_path <- "data/biodiversity_priority_countries.csv"
	priority_biomes_path <- "data/biodiversity_priority_biomes.csv"

	if (!file.exists(priority_countries_path) && !file.exists(priority_biomes_path)) {
		return(invisible(NULL))
	}

	normalize_text <- function(x) {
		x %>% as.character() %>% str_to_lower() %>% str_squish()
	}

	normalize_country <- function(x) normalize_text(x)

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
		if (!file.exists(path)) return(NULL)
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
		if (!file.exists(path)) return(NULL)
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

	country_priority <- prepare_priority_country_file(priority_countries_path)
	biome_priority <- prepare_priority_biome_file(priority_biomes_path)

	unstudied_countries <- unstudied_countries %>%
		mutate(
			country_name = if ("country_name" %in% names(.)) as.character(country_name) else if ("name" %in% names(.)) as.character(name) else NA_character_,
			country_key = normalize_country(country_name),
			iso_a3 = if ("iso_a3" %in% names(.)) as.character(iso_a3) else NA_character_
		)

	country_summary <- country_summary %>%
		mutate(country_key = normalize_country(country_name))

	if (!is.null(country_priority)) {
		country_priority <- country_priority %>%
			mutate(country_key = normalize_country(country_name))
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

		write_csv(overlap_by_country, file.path(output_dir, "overlap_by_country.csv"))
	}

	biome_counts <- collect_endophyte_biomes(df_group)
	summary_metrics$value[summary_metrics$metric == "endophyte_biomes_total"] <- nrow(biome_counts)
	summary_metrics$value[summary_metrics$metric == "endophyte_biomes_studied"] <- sum(biome_counts$study_count > 0, na.rm = TRUE)

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

		write_csv(overlap_by_biome, file.path(output_dir, "overlap_by_biome.csv"))
	}

	write_csv(summary_metrics, file.path(output_dir, "summary_metrics.csv"))
}

doc_type_counts <- df %>%
	distinct(paper_id, doc_type_group) %>%
	count(doc_type_group, name = "paper_count") %>%
	arrange(desc(paper_count))
write_csv(doc_type_counts, file.path(OUTPUT_ROOT, "doc_type_counts.csv"))

comparison_rows <- list()
correlation_rows <- list()

for (group in doc_groups) {
	message("\n=== Processing: ", group, " ===")
	group_dir <- file.path(OUTPUT_ROOT, safe_slug(group))
	dir.create(group_dir, recursive = TRUE, showWarnings = FALSE)

	df_group <- df %>% filter(doc_type_group == group)

	summary_row <- compute_doc_summary(df_group)
	write_csv(summary_row, file.path(group_dir, "summary_overview.csv"))

	country_results <- compute_country_metrics(df_group, group_dir)
	compute_geographic_bias(country_results$country_summary, group_dir)

	compute_relationship_summary(df_group, group_dir)
	compute_interaction_bias(df_group, group_dir)

	plant_results <- compute_plant_taxonomy(df_group, group_dir)
	compute_understudied_taxa(plant_results, group_dir)
	compute_understudied_countries(country_results$country_summary, group_dir)

	fungal_summary <- compute_fungal_taxonomy(df_group, plant_results$summary, group_dir)

	unstudied_countries_path <- file.path(group_dir, "unstudied_countries.csv")
	if (file.exists(unstudied_countries_path)) {
		unstudied_countries <- read_csv(unstudied_countries_path, show_col_types = FALSE)
		compute_biodiversity_overlap(df_group, country_results$country_summary, unstudied_countries, group_dir)
	}

	summary_row <- summary_row %>%
		mutate(
			doc_type_group = group,
			plant_coverage_percent = if (nrow(plant_results$summary) > 0) plant_results$summary$coverage_percent else NA_real_,
			fungal_coverage_percent = if (nrow(fungal_summary) > 0) fungal_summary$coverage_percent else NA_real_
		)

	comparison_rows[[group]] <- summary_row

	if (nrow(country_results$correlations) > 0) {
		corr_with_group <- country_results$correlations %>%
			mutate(doc_type_group = group)
		correlation_rows[[group]] <- corr_with_group
	}
}

comparison_summary <- bind_rows(comparison_rows)
write_csv(comparison_summary, file.path(OUTPUT_ROOT, "comparison_summary.csv"))

correlation_summary <- bind_rows(correlation_rows)
if (nrow(correlation_summary) > 0) {
	write_csv(correlation_summary, file.path(OUTPUT_ROOT, "correlation_comparison.csv"))
}

message("\nComparison outputs saved under: ", OUTPUT_ROOT)
