# BMB 2026-08-27
# Biogeographic realm helpers (Olson et al. 2001 / WWF terrestrial realms).
# Replaces the political EU / Global North-South groupings for the
# NPH-MS-2026-57711 resubmission (Referee 3).
#
# Source of truth: data/Reference_datasets/country_biogeographic_realm.csv
# (authored; built by scripts/utils/build_biogeographic_realm_table.py).
#
# source() this file, then use load_realm_table() / add_realm().

suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
})

REALM_LEVELS <- c(
  "Palearctic", "Nearctic", "Neotropic", "Afrotropic",
  "Indomalaya", "Australasia", "Oceania", "Antarctic", "Unknown"
)

load_realm_table <- function() {
  candidates <- c(
    "scripts/utils/country_biogeographic_realm.csv",
    "../scripts/utils/country_biogeographic_realm.csv",
    "utils/country_biogeographic_realm.csv"
  )
  path <- candidates[file.exists(candidates)][1]
  if (is.na(path)) {
    stop("country_biogeographic_realm.csv not found. Run ",
         "python scripts/utils/build_biogeographic_realm_table.py")
  }
  read_csv(path, show_col_types = FALSE) %>%
    mutate(
      iso_a3 = as.character(iso_a3),
      realm = as.character(realm),
      realm_secondary = as.character(realm_secondary)
    )
}

# Add realm / realm_sensitivity columns to a data frame that has an ISO3 column.
# realm_sensitivity uses the secondary realm for trans-realm countries (primary
# elsewhere) so an analysis can be re-run to check robustness.
add_realm <- function(df, iso_col = "country") {
  realm_tbl <- load_realm_table()
  lookup_primary <- setNames(realm_tbl$realm, realm_tbl$iso_a3)
  lookup_secondary <- setNames(
    ifelse(is.na(realm_tbl$realm_secondary) | realm_tbl$realm_secondary == "",
           realm_tbl$realm, realm_tbl$realm_secondary),
    realm_tbl$iso_a3
  )
  iso <- as.character(df[[iso_col]])
  df$realm <- unname(lookup_primary[iso])
  df$realm[is.na(df$realm)] <- "Unknown"
  df$realm_sensitivity <- unname(lookup_secondary[iso])
  df$realm_sensitivity[is.na(df$realm_sensitivity)] <- "Unknown"
  df$realm <- factor(df$realm, levels = REALM_LEVELS)
  df$realm_sensitivity <- factor(df$realm_sensitivity, levels = REALM_LEVELS)
  df
}
