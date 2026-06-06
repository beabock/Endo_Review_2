library(dplyr)
library(rnaturalearth)
library(sf)
library(tidyr)
library(stringr)

source("scripts/utils/disputed_territory_parent_iso.R")

# Optional JSON parser for World Bank API responses
if (!requireNamespace("jsonlite", quietly = TRUE)) {
  stop("Package 'jsonlite' is required for World Bank GDP lookup. Install it before running this script.")
}

# Input/output paths
INPUT_FILE <- "data/standardized_country_data.csv"
OUTPUT_FILE <- "data/country_enriched_data.csv"

# World Bank indicator for current GDP (current US$)
WB_GDP_INDICATOR <- "NY.GDP.MKTP.CD"
WB_GDP_DATE_RANGE <- "1960:2024"

fetch_world_bank_gdp <- function() {
  url <- paste0(
    "https://api.worldbank.org/v2/country/all/indicator/",
    WB_GDP_INDICATOR,
    "?format=json&per_page=20000&date=",
    WB_GDP_DATE_RANGE
  )

  wb_payload <- tryCatch(
    jsonlite::fromJSON(url),
    error = function(e) {
      stop("Failed to download GDP data from the World Bank API: ", e$message)
    }
  )

  if (length(wb_payload) < 2 || is.null(wb_payload[[2]]) || nrow(wb_payload[[2]]) == 0) {
    stop("World Bank GDP request returned no usable data.")
  }

  gdp_data <- wb_payload[[2]] %>%
    as_tibble() %>%
    transmute(
      iso_a3 = countryiso3code,
      gdp_year = as.integer(date),
      gdp_current_usd = as.numeric(value)
    ) %>%
    filter(!is.na(iso_a3), iso_a3 != "", iso_a3 != "-99", !is.na(gdp_current_usd)) %>%
    group_by(iso_a3) %>%
    arrange(desc(gdp_year), desc(gdp_current_usd), .by_group = TRUE) %>%
    summarise(
      gdp_year = first(gdp_year),
      gdp_current_usd = first(gdp_current_usd),
      .groups = "drop"
    )

  gdp_data
}

# Load the standardized country-level dataset
if (!file.exists(INPUT_FILE)) {
  stop("Input file not found: ", INPUT_FILE)
}

standardized_country_data <- read.csv(INPUT_FILE, stringsAsFactors = FALSE)
standardized_country_data <- standardized_country_data %>%
  mutate(iso_a3 = normalize_parent_iso(iso_a3))

if (!all(c("paper_id", "iso_a3") %in% names(standardized_country_data))) {
  stop("Input file must contain paper_id and iso_a3 columns.")
}

# Country-level intensity of research
country_counts <- standardized_country_data %>%
  filter(!is.na(iso_a3), iso_a3 != "", iso_a3 != "-99") %>%
  group_by(iso_a3) %>%
  summarise(
    study_count = n_distinct(paper_id),
    .groups = "drop"
  )

# Load country geometry and compute centroid latitude/longitude
# Define known territory names to exclude (from disputed_territory_parent_iso)
known_territories <- c(
  "Ashmore and Cartier Is.",
  "Indian Ocean Ter.",
  "Kosovo",
  "N. Cyprus",
  "Siachen Glacier",
  "Somaliland"
)

world <- ne_countries(scale = 50, returnclass = "sf") %>%
  apply_disputed_parent_iso_world() %>%
  filter(!is.na(iso_a3), iso_a3 != "-99") %>%
  # Deduplicate by iso_a3: remove known territories, keep primary countries
  filter(!(name %in% known_territories)) %>%
  distinct(iso_a3, .keep_all = TRUE)

world_valid <- suppressWarnings(st_make_valid(world))

safe_country_points <- tryCatch(
  suppressWarnings(st_centroid(world_valid)),
  error = function(e) suppressWarnings(st_point_on_surface(world_valid))
)

world_centroids <- safe_country_points
centroid_coords <- st_coordinates(world_centroids)

country_centroids <- world %>%
  st_drop_geometry() %>%
  mutate(
    centroid_lon = centroid_coords[, 1],
    centroid_lat = centroid_coords[, 2]
  ) %>%
  select(iso_a3, country_name = name, centroid_lon, centroid_lat)

# Pull current GDP from the World Bank and keep the latest available year per country
country_gdp <- fetch_world_bank_gdp()

# Combine everything into one country-level enrichment table.
# Keep all countries/territories from the world map and assign zero studies where absent.
country_enriched <- country_centroids %>%
  left_join(country_counts, by = "iso_a3") %>%
  left_join(country_gdp, by = "iso_a3") %>%
  mutate(study_count = tidyr::replace_na(study_count, 0L)) %>%
  arrange(desc(study_count), country_name)

# Ensure output directory exists
out_dir <- dirname(OUTPUT_FILE)
if (!dir.exists(out_dir)) {
  dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
}

write.csv(country_enriched, OUTPUT_FILE, row.names = FALSE)

cat("Country enrichment complete:\n")
cat("  Input rows: ", nrow(standardized_country_data), "\n", sep = "")
cat("  Countries with studies: ", nrow(country_counts), "\n", sep = "")
cat("  Countries enriched: ", nrow(country_enriched), "\n", sep = "")
cat("  Countries with zero studies: ", sum(country_enriched$study_count == 0), "\n", sep = "")
cat("  Saved to: ", OUTPUT_FILE, "\n", sep = "")
