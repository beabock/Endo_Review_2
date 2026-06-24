#!/usr/bin/env Rscript
# BMB 2026-06-05
# Tallies plant-fungal relationship types (endophytic, pathogenic, mycorrhizal, etc.)
# by study, country, and year.

library(dplyr)
library(readr)
library(stringr)

INPUT_YEAR <- "data/Ollama_cleaned_synresolved_standardized_year.csv"
INPUT_FINAL <- "data/Ollama_cleaned_synresolved_standardized_final.csv"
OUTPUT_DIR <- "results/interaction_analysis"

dir.create(OUTPUT_DIR, recursive = TRUE, showWarnings = FALSE)

input_file <- if (file.exists(INPUT_YEAR)) INPUT_YEAR else INPUT_FINAL
if (!file.exists(input_file)) {
  stop("Input file not found: ", input_file)
}

message("Loading data from: ", input_file)
df <- read_csv(input_file, show_col_types = FALSE)

classify_relationship <- function(primary_guild, interaction_notes, fungal_taxon, presence_absence) {
  txt <- str_to_lower(str_squish(paste(
    primary_guild %||% "",
    interaction_notes %||% "",
    fungal_taxon %||% "",
    presence_absence %||% ""
  )))

  if (str_detect(txt, "pathogen|pathogenic|disease|blight|wilt|anthracnose|lesion|necrosis|rot")) {
    return("Pathogenic")
  }
  if (str_detect(txt, "mycorrhiz|amf|arbuscular|ectomycorrhiz|endomycorrhiz|glomer")) {
    return("Mycorrhizal")
  }
  if (str_detect(txt, "antagonist|biocontrol|biological control|inhibit|suppres")) {
    return("Antagonistic/Biocontrol")
  }
  if (str_detect(txt, "mutual|beneficial symbio")) {
    return("Mutualistic")
  }
  if (str_detect(txt, "saprotroph|saprophy|decomposer")) {
    return("Saprotrophic")
  }
  if (str_detect(txt, "commensal")) {
    return("Commensal")
  }
  if (str_detect(txt, "endophyt|latent fungus|internal fungus|resident fungi|dse")) {
    return("Endophytic")
  }
  if (str_detect(txt, "absence|none found|not detected|no evidence")) {
    return("Absence/Negative")
  }

  return("Unknown/Other")
}

# Lightweight null-coalescing helper for base vectors.
`%||%` <- function(x, y) ifelse(is.na(x), y, x)

required_cols <- c("paper_id", "country", "primary_guild", "interaction_notes", "fungal_taxon", "presence_absence")
missing_cols <- setdiff(required_cols, names(df))
if (length(missing_cols) > 0) {
  stop("Missing required columns: ", paste(missing_cols, collapse = ", "))
}

summary_df <- df %>%
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

# 1) By interaction row
by_interaction <- summary_df %>%
  count(relationship_type, sort = TRUE, name = "interaction_count") %>%
  mutate(percent_of_interactions = round(100 * interaction_count / sum(interaction_count), 2))

# 2) By study (distinct paper_id)
by_study <- summary_df %>%
  filter(!is.na(paper_id), paper_id != "") %>%
  distinct(paper_id, relationship_type) %>%
  count(relationship_type, sort = TRUE, name = "study_count") %>%
  mutate(percent_of_studies = round(100 * study_count / sum(study_count), 2))

# 3) By country
by_country <- summary_df %>%
  filter(country != "Unknown") %>%
  distinct(paper_id, country, relationship_type) %>%
  count(country, relationship_type, sort = TRUE, name = "study_count")

write_csv(by_interaction, file.path(OUTPUT_DIR, "relationship_type_counts_by_interaction.csv"))
write_csv(by_study, file.path(OUTPUT_DIR, "relationship_type_counts_by_study.csv"))
write_csv(by_country, file.path(OUTPUT_DIR, "relationship_type_counts_by_country.csv"))

# 4) By year (if publication_year exists)
if ("publication_year" %in% names(summary_df)) {
  by_year <- summary_df %>%
    filter(!is.na(publication_year)) %>%
    distinct(paper_id, publication_year, relationship_type) %>%
    count(publication_year, relationship_type, sort = TRUE, name = "study_count")

  write_csv(by_year, file.path(OUTPUT_DIR, "relationship_type_counts_by_year.csv"))
  message("Saved yearly relationship summary.")
} else {
  message("No publication_year column found; skipped yearly summary.")
}

message("Saved relationship summaries to: ", OUTPUT_DIR)
