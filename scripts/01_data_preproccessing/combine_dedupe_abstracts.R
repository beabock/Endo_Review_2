# BMB 2024-09-22, revised 2026-09-02
# Manual step - combines and deduplicates abstract exports from Web of Science,
# Scopus, and PubMed. Not run by the automated pipeline.
#
# Search: the SAME boolean string was used in all three databases, reformatted for each
# platform's syntax. The PubMed form is recorded in api_pull_abstracts.R (`base_search`);
# WoS and Scopus were run through their web interfaces and the exact platform-formatted
# strings should be pasted into the Methods / SI. Search date: 2025-08-14. Year span
# 1700-2025. Document types restricted to journal articles (see the doc-type filter below).
#
# 2026-09-02 revision (NPH resubmission - tighten + make every stage auditable):
#   - DOIs normalised (case, doi.org/ prefix, whitespace) BEFORE the DOI-dedup, so
#     format-variant duplicates actually collapse.
#   - within a DOI, keep the record with the longest abstract (after WoS>Scopus>PubMed).
#   - abstract-text dedup now reported split by DOI-bearing vs DOI-less.
#   - document-type filter matches any "article"-flavoured type (incl. "Article;
#     Proceedings Paper", "Article in Press") instead of the literal string "Article";
#     full before/after Document.Type breakdown is printed.
#   - every stage writes rows-in / rows-out / removed to results/outputs/dedup_stage_counts.csv,
#     and the records removed at the abstract and title stages are saved for eyeballing.

library(readr)
library(dplyr)
library(tidyr)
library(stringr)
library(digest)

library(here)
setwd(here())

# Raw search exports (gitignored - large). Structure:
#   <RAW_DIR>/WoS/*.txt                    tab-separated WoS "savedrecs" exports
#   <RAW_DIR>/Scopus/*.csv                 Scopus CSV exports
#   <RAW_DIR>/search_string.txt            the exact WoS/Scopus boolean string (for the SI)
RAW_DIR <- "data/Abstracts/All_abstracts_8-14-25"

# PubMed source. pubmed_pull_8-14-25.csv was pulled with a DRAFT string (see
# METHODS_CHANGELOG.md) - it carries ~1,500 clinical-mycology / non-endophyte papers.
# Re-pull with scripts/01_data_preproccessing/pull_pubmed_phase2.R, then point this at
# pubmed_pull_phase2.csv. Falls back to the old file with a loud warning.
PUBMED_CSV <- file.path(RAW_DIR, "pubmed_pull_phase2.csv")
if (!file.exists(PUBMED_CSV)) {
  PUBMED_CSV <- file.path(RAW_DIR, "pubmed_pull_8-14-25.csv")
  warning("Using the DRAFT-string PubMed pull (", PUBMED_CSV, "). Re-pull with ",
          "pull_pubmed_phase2.R for a corpus that matches docs/SEARCH_STRATEGY.md.",
          immediate. = TRUE)
}

dir.create("results/outputs", showWarnings = FALSE, recursive = TRUE)
dir.create("data/processed", showWarnings = FALSE, recursive = TRUE)
# Redirect output to txt file
sink("results/outputs/abstracts_pull_summary.txt")

wos_folder <- file.path(RAW_DIR, "WoS")

# List all .txt files in the folder (adjust pattern if needed)
wos_files <- list.files(path = wos_folder, pattern = "\\.txt$", full.names = TRUE)

wos_list <- lapply(wos_files, function(f) {
  df <- read_tsv(f, show_col_types = FALSE)
  df[] <- lapply(df, as.character)
  df
})

wos <- bind_rows(wos_list)

cat("Number of WoS files read:", length(wos_files), "\n")
cat("Total rows after binding:", nrow(wos), "\n")


write.csv(wos, "data/processed/wos_combined.csv", row.names = FALSE)

# Read and bind all Scopus files in the specified folder

scopus_folder <- file.path(RAW_DIR, "Scopus")

# List all .csv files in the folder (adjust pattern if needed)
scopus_files <- list.files(path = scopus_folder, pattern = "\\.csv$", full.names = TRUE)

# Read and coerce all columns to character for each file
scopus_list <- lapply(scopus_files, function(f) {
  df <- read_csv(f, show_col_types = FALSE)
  df[] <- lapply(df, as.character)
  df
})

scopus <- bind_rows(scopus_list)

cat("Number of Scopus files read:", length(scopus_files), "\n")
cat("Total rows after binding:", nrow(scopus), "\n")

write.csv(scopus, "data/processed/scopus_combined.csv", row.names = FALSE)


pubmed <- read_csv(PUBMED_CSV, show_col_types = FALSE)
cat("PubMed source:", PUBMED_CSV, "\n")
cat("Number of PubMed files read:", length(pubmed), "\n")
cat("Total rows after binding:", nrow(pubmed), "\n")


# Data Overview
cat("WoS columns:", length(colnames(wos)), "\n")
cat("Scopus columns:", length(colnames(scopus)), "\n") 
cat("PubMed columns:", length(colnames(pubmed)), "\n")

# Create a mapping of acronyms to full names
colname_mapping <- c(
  PT = "Document.Abb",
  AU = "Authors",
  BA = "Book.Authors",
  BE = "Editors",
  GP = "Group.Authors",
  AF = "Author.full.names",
  BF = "Book.Full.Names",
  CA = "Conference.Authors",
  TI = "Title",
  SO = "Source.title",
  SE = "Series.Title",
  BS = "Book.Series",
  LA = "Language.of.Original.Document",
  DT = "Document.Type",
  CT = "Conference.name",
  CY = "Conference.date",
  CL = "Conference.location",
  SP = "Sponsors",
  HO = "Host",
  DE = "Author.Keywords",
  ID = "Index.Keywords",
  AB = "Abstract",
  C1 = "Affiliations",
  C3 = "Authors.with.affiliations",
  RP = "Correspondence.Address",
  EM = "Email.Address",
  RI = "Researcher.IDs",
  OI = "ORCID.IDs",
  FU = "Funding.Details",
  FP = "Funding.Programs",
  FX = "Funding.Texts",
  CR = "References",
  NR = "Cited.References",
  TC = "Times.Cited",
  Z9 = "Total.Times.Cited",
  U1 = "Usage.Count.180.Days",
  U2 = "Usage.Count.Since.2013",
  PU = "Publisher",
  PI = "Publisher.City",
  PA = "Publisher.Address",
  SN = "ISSN",
  EI = "eISSN",
  BN = "ISBN",
  J9 = "Abbreviated.Source.Title",
  JI = "Journal.ISO",
  PD = "Publication.Date",
  PY = "Year",
  VL = "Volume",
  IS = "Issue",
  PN = "Art..No.",
  SU = "Supplement",
  SI = "Special.Issue",
  MA = "Meeting.Abstract",
  BP = "Page.start",
  EP = "Page.end",
  AR = "Art..No.",
  DI = "DOI",
  DL = "DOI.Link",
  D2 = "Secondary.DOI",
  EA = "Early.Access.Date",
  PG = "Page.count",
  WC = "Web.of.Science.Categories",
  WE = "Research.Areas",
  SC = "Subject.Categories",
  GA = "Document.Delivery.Number",
  PM = "PubMed.ID",
  OA = "Open.Access",
  HC = "Highly.Cited.Paper",
  HP = "Hot.Paper",
  DA = "Date",
  UT = "WOS_ID"
)

unmapped_cols <- setdiff(colnames(wos), names(colname_mapping))


# Rename columns in wos
colnames(wos) <- ifelse(colnames(wos) %in% names(colname_mapping), 
                        colname_mapping[colnames(wos)], 
                        colnames(wos))


wos <- wos %>%
  select(
    -Art..No.
  )

# View the updated column names
cat("WoS standardized columns:", length(colnames(wos)), "\n")

cat("Wos earliest year:", min(as.numeric(wos$Year), na.rm = TRUE), "\n")

# Standardize Scopus column names
# Rename Scopus columns to match WoS standardized names
scopus <- scopus %>%
  rename(
    Title = `Title`,
    Authors = `Authors`, 
    Abstract = `Abstract`,
    DOI = `DOI`,
    Year = `Year`,
    Source.title = `Source title`,
    Affiliations = `Affiliations`,
    Author.Keywords = `Author Keywords`,
    Index.Keywords = `Index Keywords`,
    Publisher = `Publisher`,
    ISSN = `ISSN`,
    Volume = `Volume`,
    Issue = `Issue`,
    Page.start = `Page start`,
    Page.end = `Page end`,
    Times.Cited = `Cited by`,
    Document.Type = `Document Type`,
    Language.of.Original.Document = `Language of Original Document`
  )

cat("Scopus earliest year:", min(scopus$Year, na.rm = TRUE), "\n")

# Standardize PubMed column names
# Rename PubMed columns to match WoS standardized names  
pubmed <- pubmed %>%
  rename(
    Title = `title`,
    Authors = `authors`,
    Abstract = `abstract`, 
    DOI = `doi`,
    Year = `year`,
    Source.title = `journal`
  )

cat("PubMed earliest year:", min(pubmed$Year, na.rm = TRUE), "\n")

# Add source column to track origin
wos$Source <- "WoS"
scopus$Source <- "Scopus" 
pubmed$Source <- "PubMed"

# Combine all three datasets
# Get common columns across all datasets
common_cols <- intersect(intersect(colnames(wos), colnames(scopus)), colnames(pubmed))
cat("Common columns:", length(common_cols), "\n")

# Get all unique columns
all_cols <- unique(c(colnames(wos), colnames(scopus), colnames(pubmed)))

# Add missing columns to each dataset (fill with NA)
for(col in all_cols) {
  if(!col %in% colnames(wos)) wos[[col]] <- NA
  if(!col %in% colnames(scopus)) scopus[[col]] <- NA  
  if(!col %in% colnames(pubmed)) pubmed[[col]] <- NA
}

# Reorder columns to match
wos <- wos[, all_cols]
scopus <- scopus[, all_cols]
pubmed <- pubmed[, all_cols]

wos$Year <- as.numeric(wos$Year)
scopus$Year <- as.numeric(scopus$Year)
pubmed$Year <- as.numeric(pubmed$Year)

# ============================================================================
# Combine + deduplicate
# ============================================================================

MISSING_ABSTRACT <- c("[No abstract available]", "No abstract available",
                      "Abstract not available", "[Abstract not available]", "")

ds <- bind_rows(wos, scopus, pubmed) %>%
  mutate(Abstract = str_squish(Abstract)) %>%
  filter(!is.na(Abstract), !(Abstract %in% MISSING_ABSTRACT))

combined_n <- nrow(ds)
cat("Combined rows with a usable abstract:", combined_n,
    "(WoS/Scopus/PubMed:", sum(ds$Source == "WoS"), "/",
    sum(ds$Source == "Scopus"), "/", sum(ds$Source == "PubMed"), ")\n")
write.csv(ds, "data/processed/intermediate_after_combined.csv", row.names = FALSE)

# --- stage-count ledger (writes the Methods table for us) --------------------
stage_rows <- list()
log_stage <- function(name, n_in, n_out, note = "") {
  stage_rows[[length(stage_rows) + 1]] <<- data.frame(
    stage = name, rows_in = n_in, rows_out = n_out,
    removed = n_in - n_out, note = note, stringsAsFactors = FALSE)
  cat(sprintf("  %-32s %7d -> %7d  (-%d)  %s\n", name, n_in, n_out, n_in - n_out, note))
}

# --- helpers ---------------------------------------------------------------
normalize_text <- function(x) {
  x <- tolower(x)
  x <- gsub("\\s+", " ", x)
  x <- gsub("[[:punct:]]", "", x)
  stringr::str_trim(x)
}
normalize_doi <- function(x) {
  x <- tolower(trimws(as.character(x)))
  x <- sub("^https?://(dx\\.)?doi\\.org/", "", x)
  x <- sub("^doi:\\s*", "", x)
  x <- sub("[.,;]+$", "", x)             # trailing punctuation from some exports
  x[x %in% c("", "na", "null")] <- NA_character_
  trimws(x)
}

dir.create("data/processed", showWarnings = FALSE, recursive = TRUE)
dir.create("results/outputs", showWarnings = FALSE, recursive = TRUE)

cat("\nDeduplication (normalise: lowercase, collapse whitespace, strip punctuation):\n")

# --- Stage 1: DOI -----------------------------------------------------------
# normalise first so 10.1/ABC, 10.1/abc and https://doi.org/10.1/abc collapse.
# Within one DOI keep the source-priority record, tie-broken by the longest
# abstract (the most complete copy). src_rank/abs_len are helper columns, dropped
# before the final write.
ds <- ds %>%
  mutate(DOI_norm  = normalize_doi(DOI),
         src_rank  = match(Source, c("WoS", "Scopus", "PubMed")),
         abs_len   = nchar(Abstract)) %>%
  arrange(src_rank, desc(abs_len))        # global priority order, used by every stage

ds_doi   <- ds %>% filter(!is.na(DOI_norm))
ds_nodoi <- ds %>% filter(is.na(DOI_norm))

dedup <- ds_doi %>%
  distinct(DOI_norm, .keep_all = TRUE) %>%
  bind_rows(ds_nodoi)                     # DOI-less rows carried through untouched here
log_stage("DOI dedup", combined_n, nrow(dedup),
          sprintf("%d had a DOI, %d did not", nrow(ds_doi), nrow(ds_nodoi)))
write.csv(dedup, "data/processed/intermediate_after_doi_dedup.csv", row.names = FALSE)

# --- Stage 2: normalized abstract --------------------------------------------
n_before <- nrow(dedup)
dedup <- dedup %>%
  arrange(src_rank, desc(abs_len)) %>%    # re-assert order after the bind_rows
  mutate(Abstract_norm = normalize_text(Abstract),
         Title_norm     = normalize_text(Title),
         Authors_norm   = normalize_text(Authors))

# records that will be dropped (2nd+ copy of each normalized abstract)
abs_removed <- dedup %>%
  group_by(Abstract_norm) %>% filter(n() > 1) %>% slice(-1) %>% ungroup()
write.csv(abs_removed %>% select(Source, DOI, DOI_norm, Title, Year, Source.title),
          "data/processed/dedup_removed_by_abstract.csv", row.names = FALSE)

dedup <- dedup %>% distinct(Abstract_norm, .keep_all = TRUE)
log_stage("Abstract-text dedup", n_before, nrow(dedup),
          sprintf("%d of the removed had a DOI, %d did not",
                  sum(!is.na(abs_removed$DOI_norm)), sum(is.na(abs_removed$DOI_norm))))
write.csv(dedup, "data/processed/intermediate_after_abstract_dedup.csv", row.names = FALSE)

# --- Stage 3: document-type filter -------------------------------------
# Keep anything whose type contains "article" (covers "Article",
# "Article; Proceedings Paper", "Article; Early Access", "Article in Press") plus
# NA (PubMed rows - already limited to Journal Article at search time). This DROPS
# Review, Editorial, Meeting Abstract, Letter, Note, Correction, Book Chapter, etc.
# -- reviews carry no primary occurrence records, consistent with a research-effort study.
cat("\n  Document.Type BEFORE the filter:\n")
print(sort(table(dedup$Document.Type, useNA = "ifany"), decreasing = TRUE))

n_before <- nrow(dedup)
is_article <- grepl("article", tolower(dedup$Document.Type)) | is.na(dedup$Document.Type)
dropped_types <- dedup %>% filter(!is_article)
write.csv(dropped_types %>% select(Source, DOI, Title, Year, Document.Type),
          "data/processed/dedup_removed_by_doctype.csv", row.names = FALSE)
dedup <- dedup %>% filter(is_article)
log_stage("Document-type filter", n_before, nrow(dedup),
          "kept *article* + NA; dropped review/editorial/etc.")
cat("  Document.Type AFTER the filter:\n")
print(sort(table(dedup$Document.Type, useNA = "ifany"), decreasing = TRUE))
write.csv(dedup, "data/processed/intermediate_after_articles_filter.csv", row.names = FALSE)

# --- Stage 4: normalized title ---------------------------------------------
# Titles < 15 normalized chars are left alone (generic short titles like "new
# species" would collide spuriously).
n_before <- nrow(dedup)
dedup <- dedup %>% arrange(src_rank, desc(abs_len))

title_removed <- dedup %>%
  filter(nchar(Title_norm) >= 15) %>%
  group_by(Title_norm) %>% filter(n() > 1) %>% slice(-1) %>% ungroup()
write.csv(title_removed %>% select(Source, DOI, DOI_norm, Title, Year, Source.title),
          "data/processed/dedup_removed_by_title.csv", row.names = FALSE)

dedup_short <- dedup %>% filter(nchar(Title_norm) < 15)
dedup_long  <- dedup %>% filter(nchar(Title_norm) >= 15) %>%
  distinct(Title_norm, .keep_all = TRUE)
dedup <- bind_rows(dedup_long, dedup_short)
log_stage("Title dedup", n_before, nrow(dedup),
          sprintf("normalized-title match on titles >= 15 chars; %d short titles kept as-is",
                  nrow(dedup_short)))
write.csv(dedup, "data/processed/intermediate_after_title_dedup.csv", row.names = FALSE)

# ============================================================================
# Output
# ============================================================================

# Publication-year sanity: a handful of source rows carry the volume number or a
# stray value in the year field (e.g. "13", "109", "4"). Null those (keep the row).
this_year <- as.integer(format(Sys.Date(), "%Y"))
yr <- suppressWarnings(as.numeric(dedup$Year))
bad_year <- !is.na(yr) & (yr < 1850 | yr > this_year + 1)
cat("\nImplausible publication years set to NA:", sum(bad_year), "\n")
if (any(bad_year)) print(dedup[bad_year, c("Title", "Year", "DOI")])
dedup$Year[bad_year] <- NA

final_data <- dedup %>%
  select(-Abstract_norm, -Title_norm, -Authors_norm,
         -DOI_norm, -src_rank, -abs_len) %>%
  relocate(Title, Authors, Year, Source.title, Abstract, DOI)

stage_counts <- do.call(rbind, stage_rows)
stage_counts <- rbind(
  data.frame(stage = "Combined (usable abstract)", rows_in = NA, rows_out = combined_n,
             removed = NA, note = "WoS + Scopus + PubMed", stringsAsFactors = FALSE),
  stage_counts)
write.csv(stage_counts, "results/outputs/dedup_stage_counts.csv", row.names = FALSE)

cat("\n==== FINAL ====\n")
cat("Final dataset rows:", nrow(final_data), "\n")
cat("  with DOI:", sum(!is.na(normalize_doi(final_data$DOI))), "\n")
cat("  no DOI  :", sum(is.na(normalize_doi(final_data$DOI))), "\n")
cat("  missing Title:", sum(is.na(final_data$Title)),
    "| missing Abstract:", sum(is.na(final_data$Abstract)), "\n")
cat("  year range:", suppressWarnings(min(as.numeric(final_data$Year), na.rm = TRUE)),
    "-", suppressWarnings(max(as.numeric(final_data$Year), na.rm = TRUE)), "\n")

# canonical outputs live in data/Abstracts/ (gitignored - too big for the repo):
#   All_abstracts_deduped.csv  - full record, all bibliographic columns
#   Abstracts_for_Monsoon.csv  - 6-column slim projection fed to the LLM / retrieval
dir.create("data/Abstracts", showWarnings = FALSE, recursive = TRUE)
write.csv(final_data, "data/Abstracts/All_abstracts_deduped.csv", row.names = FALSE)

monsoon_slim <- final_data %>%
  select(Title, Authors, Year, Source.title, Abstract, DOI)
write.csv(monsoon_slim, "data/Abstracts/Abstracts_for_Monsoon.csv", row.names = FALSE)

cat("\nWritten:\n")
cat("  data/Abstracts/All_abstracts_deduped.csv  (", nrow(final_data), "rows )\n")
cat("  data/Abstracts/Abstracts_for_Monsoon.csv  (slim projection)\n")
cat("  results/outputs/dedup_stage_counts.csv    (Methods table)\n")
cat("  data/processed/dedup_removed_by_{abstract,doctype,title}.csv  (audit)\n")

sink()
