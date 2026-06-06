library(dplyr)
library(readr)
library(stringr)
library(tidyr)
library(scales)

source("scripts/utils/pipeline_helpers.R")

INPUT_FILE <- "data/Ollama_cleaned_synresolved_standardized_final.csv"
GBIF_TAXON_FILE <- "data/Reference_datasets/gbif_backbone/Taxon.tsv"
PBDB_FILE <- "data/Reference_datasets/pbdb_all.csv"
OUTPUT_DIR <- "results/taxonomy_analysis"

resolve_existing_path <- function(candidates) {
	for (p in candidates) {
		if (file.exists(p)) {
			return(p)
		}
	}
	return(candidates[[1]])
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

# Use centrally defined cache paths
GBIF_MIN_RDS <- file.path(CACHE_DIR, "gbif_taxa_min.rds")
GBIF_REF_RDS <- file.path(CACHE_DIR, "gbif_reference_species.rds")
GBIF_MIN_QS <- file.path(CACHE_DIR, "gbif_taxa_min.qs")
GBIF_REF_QS <- file.path(CACHE_DIR, "gbif_reference_species.qs")

# The step_time, cache_read_object, and cache_write_object functions
# are now defined in pipeline_helpers.R and sourced above.
# The fast_read_tsv function remains local to this script.

step_time <- function(label, expr) {
	message(label)
	t0 <- proc.time()
	result <- force(expr)
	elapsed <- proc.time() - t0
	message(sprintf("%s completed in %.2f sec", label, as.numeric(elapsed[["elapsed"]])))
	result
}

cache_read_object <- function(preferred_path, fallback_path = NULL) {
	if (!is.null(preferred_path) && file.exists(preferred_path)) {
		if (requireNamespace("qs", quietly = TRUE)) {
			return(qs::qread(preferred_path))
		}
	}
	if (!is.null(fallback_path) && file.exists(fallback_path)) {
		return(readRDS(fallback_path))
	}
	stop("No cache file found for: ", preferred_path)
}

cache_write_object <- function(object, qs_path, rds_path) {
	if (requireNamespace("qs", quietly = TRUE)) {
		qs::qsave(object, qs_path, preset = "high")
	}
	saveRDS(object, rds_path)
}

# fast reader wrapper: prefer vroom when available
fast_read_tsv <- function(path, col_select = NULL) {
	if (requireNamespace("vroom", quietly = TRUE)) {
		vroom::vroom(path, delim = "\t", col_select = col_select, progress = FALSE)
	} else {
		readr::read_tsv(path, show_col_types = FALSE, progress = FALSE, col_select = col_select)
	}
}

SUMMARY_FILE <- file.path(OUTPUT_DIR, "plant_species_coverage_summary.csv")
PHYLUM_FILE <- file.path(OUTPUT_DIR, "plant_species_coverage_by_phylum.csv")
GENUS_PHYLUM_FILE <- file.path(OUTPUT_DIR, "plant_genus_coverage_by_phylum.csv")
FAMILY_PHYLUM_FILE <- file.path(OUTPUT_DIR, "plant_family_coverage_by_phylum.csv")
TOP_SPECIES_FILE <- file.path(OUTPUT_DIR, "top_studied_plant_species.csv")

if (!file.exists(INPUT_FILE)) {
	stop("Input file not found: ", INPUT_FILE)
}

if (!file.exists(GBIF_TAXON_FILE)) {
	stop("GBIF Taxon.tsv file not found: ", GBIF_TAXON_FILE)
}

if (!dir.exists(OUTPUT_DIR)) {
	dir.create(OUTPUT_DIR, recursive = TRUE, showWarnings = FALSE)
}

message("Loading study-level host data...")
study_data <- read_csv(
	INPUT_FILE,
	show_col_types = FALSE,
	col_select = all_of(c(
		"paper_id",
		"plant_host_resolved",
		"plant_host_status",
		"plant_host_accepted_ids"
	))
)

required_cols <- c("paper_id", "plant_host_resolved", "plant_host_accepted_ids")
missing_cols <- setdiff(required_cols, names(study_data))
if (length(missing_cols) > 0) {
	stop("Missing required columns in input data: ", paste(missing_cols, collapse = ", "))
}

message("Loading GBIF backbone reference species (with caching)...")

# Define phylum resolution function (needed for both cache build and load)
resolve_phylum_from_lineage <- function(start_taxon_id, parent_map, phylum_map, max_steps = 40) {
	current <- start_taxon_id
	steps <- 0
	while (!is.na(current) && current != "" && steps < max_steps) {
		p <- unname(phylum_map[current])
		if (length(p) > 0 && !is.na(p) && p != "") {
			return(p)
		}
		next_id <- unname(parent_map[current])
		if (length(next_id) == 0 || is.na(next_id) || next_id == "" || identical(next_id, current)) {
			break
		}
		current <- next_id
		steps <- steps + 1
	}
	""
}

resolve_phylum_lookup <- function(gbif_taxa_min, parent_lookup, max_iter = 40) {
	resolved_phylum <- setNames(gbif_taxa_min$phylum, gbif_taxa_min$taxonID)
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

if (file.exists(GBIF_MIN_RDS) && file.exists(GBIF_REF_RDS)) {
	message("Loading cached GBIF objects...")
	gbif_taxa_min <- step_time(
		"Loading cached GBIF minimal taxonomy cache",
		cache_read_object(GBIF_MIN_QS, GBIF_MIN_RDS)
	)
	reference_species <- step_time(
		"Loading cached GBIF reference species cache",
		cache_read_object(GBIF_REF_QS, GBIF_REF_RDS)
	)
	
	# Rebuild lookup tables from cached data
	parent_lookup <- step_time(
		"Rebuilding GBIF parent/phylum lookup tables",
		setNames(gbif_taxa_min$parentNameUsageID, gbif_taxa_min$taxonID)
	)
	phylum_lookup <- step_time(
		"Resolving GBIF phylum lookup from lineage",
		resolve_phylum_lookup(gbif_taxa_min, parent_lookup)
	)
} else {
	# Build a minimal accepted Plantae taxonomy index for lineage-based phylum backfill.
	gbif_taxa_min <- step_time(
		"Building minimal GBIF taxonomy cache",
		fast_read_tsv(
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
	)

	parent_lookup <- setNames(gbif_taxa_min$parentNameUsageID, gbif_taxa_min$taxonID)
	phylum_lookup <- setNames(gbif_taxa_min$phylum, gbif_taxa_min$taxonID)

	reference_species <- step_time(
		"Building GBIF reference species cache",
		fast_read_tsv(
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
	)

	# Save caches for future runs
	try({
		cache_write_object(gbif_taxa_min, GBIF_MIN_QS, GBIF_MIN_RDS)
		cache_write_object(reference_species, GBIF_REF_QS, GBIF_REF_RDS)
		message("Saved GBIF caches to QS and RDS files.")
	}, silent = TRUE)

	# Ensure parent/phylum lookups exist in this branch
	parent_lookup <- setNames(gbif_taxa_min$parentNameUsageID, gbif_taxa_min$taxonID)
	phylum_lookup <- step_time(
		"Resolving GBIF phylum lookup from lineage",
		resolve_phylum_lookup(gbif_taxa_min, parent_lookup)
	)
}

missing_phylum_before_backfill <- sum(is.na(reference_species$phylum) | reference_species$phylum == "")

if (missing_phylum_before_backfill > 0) {
	reference_species <- step_time(
		"Backfilling missing phylum values from GBIF lineage",
		{
			resolved_values <- unname(phylum_lookup[reference_species$taxonID])
			reference_species %>%
				mutate(phylum = if_else(phylum == "" & !is.na(resolved_values) & resolved_values != "", resolved_values, phylum))
		}
	)
}

missing_phylum_after_backfill <- sum(is.na(reference_species$phylum) | reference_species$phylum == "")
phylum_backfilled_count <- missing_phylum_before_backfill - missing_phylum_after_backfill

total_known_plant_species_raw <- nrow(reference_species)

# Exclude extinct species from denominator using PBDB when available.
pbdb_extinct_species_count <- 0L
pbdb_extinct_only_species_count <- 0L
gbif_species_removed_by_pbdb <- 0L

if (file.exists(PBDB_FILE)) {
	pbdb_raw <- step_time(
		"Loading PBDB extinct taxa to exclude extinct plant species from denominator",
		read_csv(PBDB_FILE, show_col_types = FALSE, skip = 16)
	)

	if (all(c("taxon_rank", "taxon_name", "accepted_rank", "accepted_name", "is_extant") %in% names(pbdb_raw))) {
		pbdb_species_status <- step_time(
			"Summarizing PBDB extant/extinct species",
			pbdb_raw %>%
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

		gbif_species_removed_by_pbdb <- sum(reference_species$pbdb_extinct_match %in% TRUE, na.rm = TRUE)

		reference_species <- reference_species %>%
			filter(!pbdb_extinct_match %in% TRUE) %>%
			select(-canonical_lc, -pbdb_extinct_match)
	} else {
		warning("PBDB file found but expected columns are missing. Extinct-species filtering was skipped.")
	}
} else {
	message("PBDB file not found; denominator uses GBIF accepted species without extinct filtering.")
}

total_known_plant_species <- nrow(reference_species)

message("Extracting studied plant species IDs...")
study_species_links <- study_data %>%
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
coverage_pct <- if (total_known_plant_species > 0) {
	100 * studied_species_count / total_known_plant_species
} else {
	NA_real_
}

coverage_summary <- tibble(
	dataset_rows = nrow(study_data),
	rows_with_plantae_host = sum(!is.na(study_data$plant_host_accepted_ids) & study_data$plant_host_accepted_ids != "", na.rm = TRUE),
	unique_papers_with_plantae_host_ids = n_distinct(study_species_links$paper_id),
	unique_plantae_accepted_ids_in_dataset = n_distinct(study_species_links$accepted_id),
	unique_plantae_species_matched_to_gbif = studied_species_count,
	gbif_species_missing_phylum_before_backfill = missing_phylum_before_backfill,
	gbif_species_missing_phylum_after_backfill = missing_phylum_after_backfill,
	gbif_species_phylum_backfilled_from_lineage = phylum_backfilled_count,
	total_known_plant_species_gbif_raw = total_known_plant_species_raw,
	pbdb_extinct_species_name_count = pbdb_extinct_species_count,
	pbdb_extinct_only_species_name_count = pbdb_extinct_only_species_count,
	gbif_species_removed_by_pbdb_extinct_filter = gbif_species_removed_by_pbdb,
	total_known_plant_species_gbif = total_known_plant_species,
	coverage_percent = coverage_pct
)

write_csv(coverage_summary, SUMMARY_FILE)

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

write_csv(coverage_by_phylum, PHYLUM_FILE)

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

write_csv(genus_coverage_by_phylum, GENUS_PHYLUM_FILE)

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

write_csv(family_coverage_by_phylum, FAMILY_PHYLUM_FILE)

top_studied_species <- study_species_matched %>%
	distinct(paper_id, accepted_id, canonicalName, phylum, family, genus) %>%
	count(accepted_id, canonicalName, phylum, family, genus, name = "study_count", sort = TRUE) %>%
	slice_head(n = 100)

write_csv(top_studied_species, TOP_SPECIES_FILE)

message("Taxonomy coverage analysis complete:")
message("  GBIF species missing phylum before lineage backfill: ", comma(missing_phylum_before_backfill))
message("  GBIF species phylum backfilled from lineage: ", comma(phylum_backfilled_count))
message("  GBIF species still missing phylum after backfill: ", comma(missing_phylum_after_backfill))
message("  Known plant species (GBIF accepted, raw): ", comma(total_known_plant_species_raw))
message("  PBDB extinct species names (all extinct records): ", comma(pbdb_extinct_species_count))
message("  PBDB extinct-only species names (not also marked extant): ", comma(pbdb_extinct_only_species_count))
message("  Species removed by PBDB extinct filter: ", comma(gbif_species_removed_by_pbdb))
message("  Known plant species (post-filter denominator): ", comma(total_known_plant_species))
message("  Studied plant species (matched by accepted ID): ", comma(studied_species_count))
message("  Coverage: ", percent(coverage_pct / 100, accuracy = 0.01))
message("  Summary file: ", SUMMARY_FILE)
message("  Phylum table: ", PHYLUM_FILE)
message("  Genus phylum table: ", GENUS_PHYLUM_FILE)
message("  Family phylum table: ", FAMILY_PHYLUM_FILE)
message("  Top species table: ", TOP_SPECIES_FILE)
message("  Plotting moved to scripts/05_plotting/taxonomy_representation.R")