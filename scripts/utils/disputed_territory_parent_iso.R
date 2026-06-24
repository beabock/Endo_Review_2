# BMB 2026-06-05
# Maps disputed territories and non-sovereign geometries to their parent ISO code
# for stable country joins across the pipeline.

# Name-based mapping for world geometries that lack ISO A3 codes in rnaturalearth.
disputed_territory_parent_iso <- dplyr::tribble(
  ~name, ~iso_a3_parent,
  "Ashmore and Cartier Is.", "AUS",
  "Indian Ocean Ter.", "GBR",
  "Kosovo", "SRB",
  "N. Cyprus", "CYP",
  "Siachen Glacier", "IND",
  "Somaliland", "SOM"
)

# ISO recoding for extracted country mentions before aggregation.
# Example: XKX (Kosovo) rolls up to SRB to match parent-country geometry usage.
disputed_iso_parent_recode <- c(
  "XKX" = "SRB"
)

normalize_parent_iso <- function(iso_values) {
  dplyr::recode(iso_values, !!!as.list(disputed_iso_parent_recode), .default = iso_values)
}

apply_disputed_parent_iso_world <- function(world_sf) {
  world_sf %>%
    dplyr::left_join(disputed_territory_parent_iso, by = "name") %>%
    dplyr::mutate(iso_a3 = dplyr::coalesce(iso_a3, iso_a3_parent)) %>%
    dplyr::select(-iso_a3_parent)
}
