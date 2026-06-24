# BMB 2024-09-22
# Manual step — combines and deduplicates abstract exports from Web of Science,
# Scopus, and PubMed. Not run by the automated pipeline.
# Version: 2.0
#
# Inputs/Outputs: Reads WoS .txt files, Scopus .csv files, and PubMed .csv file from data/raw/All_abstracts_8-14-25/;
# produces intermediate combined files (wos_combined.csv, scopus_combined.csv) and final deduplicated dataset
# (All_abstracts_deduped.csv) in data/processed/
#
# =============================================================================
#'
#' @description This script combines and deduplicates scientific abstracts from multiple bibliographic databases
#' to create a comprehensive dataset for analysis of fungal endophyte research. The script processes data
#' collected in the second pull (2025) using the search query:TITLE-ABS-KEY(
 # (
  #  "fungal endophyte" OR "fungal endophytes" OR "endophytic fungus" OR "endophytic fungi" OR 
  #  "latent fungus" OR "latent fungi" OR "systemic fungus" OR "systemic fungi" OR 
  #  "internal fungi" OR "resident fungi" OR "seed-borne fungi" OR "seed-transmitted fungi" OR 
  #  "dark septate endophyte" OR "dark septate fungi" OR "DSE fungi"
  #)
  #AND
  #(
  #  plant* OR moss* OR bryophyte* OR liverwort* OR hornwort* OR fern* OR lycophyte* OR 
  #  pteridophyte* OR tree* OR forest* OR shrub* OR grass* OR graminoid* OR herb* OR 
  #  crop* OR seedling* OR sapling* OR seed* OR root* OR leaf* OR foliage OR shoot* OR 
  #  stem* OR twig* OR rhizome* OR thallus OR frond* OR algae OR "green alga*" OR macroalga* OR 
  #  "red alga*" OR "brown alga*" OR hydrophyte* OR kelp OR seaweed* OR seagrass* OR 
  #  cyanobacteria OR cyanobiont* OR photobiont* OR lichen*
  #)
#)
#AND (DOCTYPE(ar))
#'
#' @details
#' ## Overview
#' This data processing pipeline creates a unified dataset of abstracts from Web of Science (WoS),
#' Scopus, and PubMed databases. The workflow involves reading raw data files, standardizing column
#' names across databases, combining datasets, filtering for quality and relevance, and performing
#' multi-stage deduplication to ensure data integrity.
#'
#' ## Data Sources
#' - **Web of Science (WoS)**: Multiple tab-separated value (.txt) files exported in batches of 1000 records
#'   each due to export limitations. Data collected on 11/18/24 by BB.
#' - **Scopus**: Multiple comma-separated value (.csv) files containing bibliographic records.
#' - **PubMed**: Single comma-separated value (.csv) file with publication metadata.
#'
#' All source data is located in the `data/raw/All_abstracts_8-14-25/` directory structure.
#'
#' ## Processing Workflow
#'
#' ### 1. Data Loading
#' - Read all WoS files from `data/raw/All_abstracts_8-14-25/WoS/` directory
#' - Read all Scopus files from `data/raw/All_abstracts_8-14-25/Scopus/` directory
#' - Read PubMed file: `data/raw/All_abstracts_8-14-25/pubmed_pull_8-14-25.csv`
#' - Convert all columns to character type for consistent handling
#' - Generate intermediate combined files for each source
#'
#' ### 2. Column Standardization
#' - Map WoS abbreviated column names to descriptive full names using predefined mapping
#' - Rename Scopus and PubMed columns to match WoS standardized names
#' - Add 'Source' column to track original database for each record
#' - Align column structures across all datasets by adding missing columns with NA values
#'
#' ### 3. Data Integration
#' - Combine all three datasets into single dataframe
#' - Filter out records with missing, empty, or unavailable abstracts
#' - Prioritize records by metadata richness (WoS > Scopus > PubMed)
#'
#' ### 4. Deduplication Process
#'
#' #### Methods and Criteria
#' Deduplication occurs in multiple stages with increasing stringency:
#'
#' - **Stage 1: DOI-based deduplication**
#'   - Exact matching on Digital Object Identifier (DOI) field
#'   - Preserves NA/missing DOI records separately to avoid false matches
#'   - Most reliable method for identifying true duplicates
#'
#' - **Stage 2: Abstract-based deduplication**
#'   - Text normalization: convert to lowercase, remove punctuation, collapse whitespace
#'   - Exact matching on normalized abstract content
#'   - Applied after DOI deduplication to catch records without DOIs
#'
#' - **Stage 3: Document type filtering**
#'   - Restrict to "Article" document types only
#'   - Removes conference abstracts, reviews, and other non-article content
#'
#' - **Stage 4: Title-based deduplication**
#'   - Text normalization: convert to lowercase, remove punctuation, collapse whitespace
#'   - Exact matching on normalized titles
#'   - Final cleanup for remaining duplicates
#'
#' ### 5. Data Cleaning and Filtering
#' - Remove temporary normalized text columns
#' - Reorder columns for consistency and readability
#' - Relocate key columns (Title, Authors, Year, Source.title, Abstract, DOI) to front
#'
#' ## Output Description
#' The final deduplicated dataset is saved as `data/processed/All_abstracts_deduped.csv` with the following structure:
#' - Columns: Title, Authors, Year, Source.title, Abstract, DOI, and additional standardized metadata fields
#' - Row count: Deduplicated records only (varies based on input data)
#' - Format: Comma-separated values (.csv) without row names
#' - Encoding: UTF-8 (default R behavior)
#'
#' ## Specific Parameters and Settings
#' - **Search Query**: ("fungal endophyte" OR "fungal endophytes" OR "endophytic fungus" OR "endophytic fungi" OR "latent fungus" OR "latent fungi" OR "systemic fungus" OR "systemic fungi" OR "internal fungi" OR "resident fungi" OR "seed-borne fungi" OR "seed-transmitted fungi" OR "dark septate endophyte" OR "dark septate fungi" OR "DSE fungi") AND (plant* OR moss* OR bryophyte* OR liverwort* OR hornwort* OR fern* OR lycophyte* OR pteridophyte* OR tree* OR forest* OR shrub* OR grass* OR graminoid* OR herb* OR crop* OR seedling* OR sapling* OR seed* OR root* OR leaf* OR foliage OR shoot* OR stem* OR twig* OR rhizome* OR thallus OR frond* OR algae OR "green alga*" OR macroalga* OR "red alga*" OR "brown alga*" OR hydrophyte* OR kelp OR seaweed* OR seagrass* OR cyanobacteria OR cyanobiont* OR photobiont* OR lichen*) AND DOCTYPE(ar)
#' - **Document Types**: Restricted to "Article" only
#' - **Abstract Filtering**: Removes records with "[No abstract available]", NA, or empty abstracts
#' - **Text Normalization**: Removes punctuation, converts to lowercase, trims whitespace
#' - **Source Prioritization**: WoS > Scopus > PubMed for duplicate resolution
#'
#' ## Reproducibility Notes
#' - **Data Collection Date**: Final search performed on 8/14/25
#' - **Data Pull Version**: Pull 2, completed in 2025
#' - **Random Seeds**: None used (deterministic text processing)
#' - **Package Versions**: Uses tidyverse ecosystem (dplyr, tidyr, stringr, readr)
#' - **R Version**: Tested with R 4.3.0 (backward compatible)
#' - **Dependencies**: readr, dplyr, tidyr, stringr, digest, here
#' - **File Paths**: Relative to project root using `here()` package
#' - **Intermediate Files**: WoS and Scopus combined files saved for verification
#'
#' @author BB (Primary data collector and processor)
#' @date 2025-01-08 (Script creation), 2025-08-14 (Data processing)
#' @keywords data processing, bibliographic databases, deduplication, fungal endophytes
#'
#' @section Dependencies:
#' Requires the following R packages:
#' - readr: for reading CSV/TSV files
#' - dplyr: for data manipulation
#' - tidyr: for data tidying
#' - stringr: for string operations
#' - digest: for hashing (not actively used in this script)
#' - here: for relative path management
#'
#' @section File Inputs:
#' - data/raw/All_abstracts_8-14-25/WoS/*.txt (multiple WoS export files)
#' - data/raw/All_abstracts_8-14-25/Scopus/*.csv (multiple Scopus export files)
#' - data/raw/All_abstracts_8-14-25/pubmed_pull_8-14-25.csv (single PubMed file)
#'
#' @section File Outputs:
#' - data/processed/wos_combined.csv (intermediate WoS combined file)
#' - data/processed/scopus_combined.csv (intermediate Scopus combined file)
#' - data/processed/All_abstracts_deduped.csv (final deduplicated dataset)

library(readr)
library(dplyr)
library(tidyr)
library(stringr)
library(digest)

library(here)
setwd(here())
# Redirect output to txt file
sink("results/outputs/abstracts_pull_summary.txt")


wos_folder <- "data/raw/All_abstracts_8-14-25/WoS"

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

# --- Read and bind all Scopus files in the specified folder ---

scopus_folder <- "data/raw/All_abstracts_8-14-25/Scopus"

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


pubmed <- read_csv("data/raw/All_abstracts_8-14-25/pubmed_pull_8-14-25.csv", show_col_types = FALSE)
cat("Number of PubMed files read:", length(pubmed), "\n")
cat("Total rows after binding:", nrow(pubmed), "\n")


# --- Data Overview ---
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

# --- Standardize Scopus column names ---
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

# --- Standardize PubMed column names ---
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

# --- Add source column to track origin ---
wos$Source <- "WoS"
scopus$Source <- "Scopus" 
pubmed$Source <- "PubMed"

# --- Combine all three datasets ---
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

# Combine all datasets (prioritize WoS > Scopus > PubMed when deduplicating)
ds <- bind_rows(wos, scopus, pubmed) %>%
  filter(Abstract != "[No abstract available]", #Can't do anything with missing abstracts
         !is.na(Abstract),
         Abstract != "") %>%
  arrange(factor(Source, levels = c("WoS", "Scopus", "PubMed")))  # Prioritize by metadata richness

cat("Combined dataset rows:", nrow(ds), "\n")
write.csv(ds, "data/processed/intermediate_after_combined.csv", row.names = FALSE)

# --- Deduplication Process ---
normalize_text <- function(x) {
  x <- tolower(x)
  x <- gsub("\\s+", " ", x)          # collapse whitespace
  x <- gsub("[[:punct:]]", "", x)    # remove punctuation
  x <- stringr::str_trim(x)          # trim leading/trailing spaces
  return(x)
}

cat("Deduplication: to lowercase, collapse whitespace, remove punctuation, trim spaces\n")

# Step 1: Deduplicate by DOI (preserving NA DOIs)
ds_no_na <- ds %>% filter(!is.na(DOI) & DOI != "")
cat("Rows with non-missing DOIs:", nrow(ds_no_na), "\n")
ds_na <- ds %>% filter(is.na(DOI) | DOI == "")
cat("Rows with missing DOIs:", nrow(ds_na), "\n")
deduplicated <- ds_no_na %>% distinct(DOI, .keep_all = TRUE)
cat("After DOI deduplication (non-missing DOIs):", nrow(deduplicated), "\n")
deduplicated <- bind_rows(deduplicated, ds_na)
cat("After DOI deduplication:", nrow(deduplicated), "\n")
write.csv(deduplicated, "data/processed/intermediate_after_doi_dedup.csv", row.names = FALSE)

# Step 2: Create normalized text columns for further deduplication
deduplicated <- deduplicated %>%
  mutate(Abstract_norm = normalize_text(Abstract),
         Title_norm = normalize_text(Title),
         Authors_norm = normalize_text(Authors))
cat("Normalized text columns (abstract, title, authors) created.\n")

# Step 3: Deduplicate by abstract
deduplicated <- deduplicated %>%
  distinct(Abstract_norm, .keep_all = TRUE)
cat("After abstract deduplication:", nrow(deduplicated), "\n")
write.csv(deduplicated, "data/processed/intermediate_after_abstract_dedup.csv", row.names = FALSE)

# Step 4: Filter to articles only
deduplicated <- deduplicated %>%
  filter(Document.Type %in% c("Article", NA))
cat("After filtering to articles:", nrow(deduplicated), "\n")
write.csv(deduplicated, "data/processed/intermediate_after_articles_filter.csv", row.names = FALSE)

# Step 5: Final deduplication by title
deduplicated <- deduplicated %>%
  distinct(Title_norm, .keep_all = TRUE)
cat("After title deduplication:", nrow(deduplicated), "\n")
write.csv(deduplicated, "data/processed/intermediate_after_title_dedup.csv", row.names = FALSE)


# --- Final cleanup and output ---
final_data <- deduplicated %>%
  select(-Abstract_norm, -Title_norm, -Authors_norm) %>%
  relocate(Title, Authors, Year, Source.title, Abstract, DOI)

cat("Final dataset rows:", nrow(final_data), "\n")
cat("Missing DOIs:", sum(is.na(final_data$DOI)), "\n")
cat("Missing Authors:", sum(is.na(final_data$Authors)), "\n")
cat("Missing Titles:", sum(is.na(final_data$Title)), "\n")
cat("Missing Abstracts:", sum(is.na(final_data$Abstract)), "\n")


write.csv(final_data, "data/processed/All_abstracts_deduped.csv", row.names = FALSE)
cat("Data written to: data/processed/All_abstracts_deduped.csv\n")

# Close the output redirection
sink()
