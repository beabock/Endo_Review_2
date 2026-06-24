# BMB 2026-06-05
# Maps free-text location mentions to ISO codes. Handles ambiguous terms
# (regions, biomes, etc.) and flags anything that couldn't be resolved.

library(rnaturalearth)
library(sf)
library(ggplot2)
library(dplyr)
library(tidyr)
library(stringr)

# Load data
ds <- read.csv("data/Ollama_cleaned_synresolved_filtered.csv")

# Source country mapping from utils
source("scripts/utils/country_mapping.R")
source("scripts/utils/disputed_territory_parent_iso.R")

# Define a list of terms to exclude
exclude_list <- c(
  "africa", "asia", "europe", "north america", "south america", "world", 
  "worldwide", "global", "earth", "unspecified", "various", "multiple", 
  "several", "many", "various countries", "multiple countries", "several countries", 
  "many countries", "not specified", "not applicable", "na", "n/a", "none", "unknown",
  "neotropics", "paleotropics", "holarctic", "afrotropics", "indomalayan", 
  "australasian", "oceanian", "nearctic", "palearctic",
  "tropical", "subtropical", "temperate", "arctic", "boreal", "polar",
  "forest", "desert", "mountain", "river", "ocean", "sea", "island", "archipelago", "peninsula", "continent",
  "eastern", "western", "northern", "southern", "central", "andean", "atacama desert", 
  "americas", "eurasia", "middle east", "north africa", "sub-saharan africa", "latin america", 
  "caribbean", "scandinavia", "balkans", "mediterranean",
  "biodiversity hotspot", "conservation international", "iucn", "wwf",
  "in vitro", "ex situ", "laboratory", "greenhouse", "experimental", "field",
  "cretaceous", "jurassic", "triassic", "permian", "carboniferous", "devonian", 
  "silurian", "ordovician", "cambrian", "precambrian",
  "eocene", "oligocene", "miocene", "pliocene", "pleistocene", "holocene",
  "mesozoic", "cenozoic", "paleozoic",
  "biogeographic region", "ecozone", "ecoregion",
  "and", "or", "et al", "sensu lato", "sensu stricto",
  "not-specified-in-text", "notprovided", "notspecified", "not specified", "not specific",
  "not specifically mentioned", "unavailable", "none specified", "not_mentioned_in_text",
  "not_specific_in_text", "not-mentioned-specifically", "not_mentioned_specifically_in_text",
  "not_specificied_in_text", "not_mentioned",
  "iberian",
  "patagonia",
  "el-haourane canton", "central europe", "central america",
  "ipswich","south asia",
  "northern europe", "western north america", "eastern north america", "east asia",
  "high arctic", "indian subcontinent", "middle eastern countries",
  "abroad", "african countries", "asia pacific regions", "asian", "australasia",
  "banana-exporting countries", "carpathian", "circum mediterranean countries",
  "circum-mediterranean", "cooler regions west", "eastern africa", "eastern pre-pyrenees",
  "eleven african countries", "fildes", "five regions of rice seed production", "flooding pampa",
  "foreign countries", "geographically diverse", "grows widely in eurasia", "high andes",
  "indo-pacific", "introduced range", "nine countries across six continents",
  "non-eu europe", "northeastern", "northeastern america", "northeastern north america",
  "northern africa", "northern hemisphere", "occurrences on six continents",
  "of the alps", "of the pennines", "other asian countries",
  "other developed countries with intensive agriculture", "other east asian countries",
  "other mediterranean countries", "pacific northwest", "pampa", 
  "possibly india or other himalayan countries", "pubmed databases", "pyrenees mountains",
  "southeastern asian countries", "southern africa", "southern baltics", "southern cone",
  "southern europe", "spanning eight countries on five continents",
  "subarctic", "temperate asia", "temperate regions", "temperate zone",
  "the americas", "tropical africa", "tropical america", "tropical atlantic", "tropical countries",
  "western amazonia", "western asia", "western world", "wide geographic sampling",
  "aiton", "alar", "arabian", "cisural", "coast", "data collected from web of science",
  "du an county", "early agricultural sites",  "linneus", "loess plateau",
  "many parts of the world", "mediterranean basin", "monoculture areas from indigenous mapuche communities",
  "multiple countries across africa", "multiple countries in sub-saharan africa",
  "nearby areas", "neolithic", "obispo", "origin in south america",
  "t&uuml", "tak",  "three production areas", "vic", "viraria", "wetter",
  "south", "west", "east", "north", "central",
  "north-east", "north-west", "south-east", "south-west",
  "northeast", "northwest", "southeast", "southwest",
  "northern", "southern", "eastern", "western",
  "eurasian", "gondwana", "laurasia", "pangaea", "rodinia", "columbia", "kenorland", "vaalbara", "ur",
  "neoarchean", "mesoarchean", "paleoarchean", "eoarchean", "hadean", "proterozoic", "phanerozoic", "archean",
  "doggerland", "atlantis", "lemuria", "mu", "thule", "hyperborea", "avalon", "camelot", "el dorado",
  "shangri-la", "zion", "eden", "paradise", "heaven", "hell", "underworld", "olympus", "asgard", "valhalla",
  "nirvana", "arcadia", "utopia", "dystopia", "narnia", "middle-earth", "westeros", "essos", "oz", "neverland",
  "wonderland", "hogwarts", "gotham", "metropolis", "atlantis",
  "pacific", "atlantic", "indian", "arctic", "southern", "ocean", "sea", "gulf", "bay", "strait", "channel",
  "sound", "fjord", "inlet", "cove", "lagoon", "estuary", "delta", "continental shelf", "abyssal plain",
  "mid-ocean ridge", "seamount", "guyot", "trench", "hydrothermal vent", "cold seep", "coral reef",
  "kelp forest", "mangrove", "salt marsh", "seagrass bed", "intertidal zone", "subtidal zone", "neritic zone",
  "oceanic zone", "epipelagic zone", "mesopelagic zone", "bathypelagic zone", "abyssopelagic zone",
  "hadopelagic zone", "photic zone", "aphotic zone", "benthic", "pelagic", "demersal", "littoral",
  "offshore", "onshore", "coastal", "marine", "aquatic", "terrestrial", "freshwater", "brackish", "saline",
  "hypersaline", "endemic", "native", "indigenous", "exotic", "invasive", "introduced", "naturalized",
  "cosmopolitan", "widespread", "regional", "local", "global", "holarctic", "neotropical", "afrotropical",
  "indomalayan", "australasian", "oceanian", "nearctic", "palearctic", "saharo-arabian", "guineo-congolian",
  "ir-tur", "mediterranean", "euro-siberian", "alps", "pyrenees", "carpathian mountains","scandinavian mountains",
  "caucasus mountains", "great rift valley", "andes", "others", "georgia to the leonie",
  # Additional geographic and regional terms to exclude
  "east africa", "south east asia", "west africa", "west asia",
  "lagotellerie island", "mediterranean island",
  "north of the pennines", "north temperate zone", "south of the alps",
  "north temperate", "temperate zone", "devon", "nordic countries", "northern fennoscandia"
)

# Function to extract and clean country strings
extract_countries <- function(country_str, exclude_list) {
  if (is.na(country_str) || country_str == "" || tolower(country_str) %in% c("na", "not-specified", "not_mentioned")) {
    return(NA_character_)
  }

  # Remove brackets and quotes
  country_str <- gsub("\\[", "", country_str)
  country_str <- gsub("\\]", "", country_str)
  country_str <- gsub("'", "", country_str)  # Regular apostrophe
  country_str <- gsub("'", "", country_str)  # Right single quotation mark
  country_str <- gsub("´", "", country_str)  # Acute accent
  country_str <- gsub("`", "", country_str)  # Backtick
  country_str <- gsub('"', "", country_str)  # Double quotes
  country_str <- gsub(" - ", " ", country_str)  # Replace dashes with spaces
  country_str <- gsub("\\.", "", country_str)  # Remove periods from abbreviations

  # Split by both comma AND "and" for multi-country entries
  countries <- str_split(tolower(country_str), "[,;]|\\band\\b")[[1]]
  countries <- str_trim(countries)

  # Strip common suffixes that shouldn't be part of the country name
  countries <- gsub(" province$| province,", "", countries)
  countries <- gsub(" region$| region,", "", countries)
  countries <- gsub(" district$| district,", "", countries)
  countries <- gsub(" reserve$| reserve,", "", countries)
  countries <- gsub(" natural.*$", "", countries)  # Remove "natural reserve", "natural area", etc.
  countries <- gsub(" peninsula$", "", countries)
  countries <- gsub(" hills$", "", countries)
  countries <- str_trim(countries)
  countries <- gsub("^(northeast|northwest|southeast|southwest) ", "", countries)  # Remove directional prefixes
  countries <- str_trim(countries)

  # Remove non-country entries from the exclude list
  countries <- countries[!countries %in% exclude_list]

  # Remove entries containing numbers or common non-country text patterns
  countries <- countries[!grepl("\\d+|sea|ocean|bay|lake|river|marine|coastal|wetland|properties|traits|symptoms|activities|infection|habitat|parameter|growth|hormone|enzyme|lipid|herbivore|fungal|symptom|tissue", countries)]

  # Remove very short entries that are likely errors
  countries <- countries[nchar(countries) > 2]

  return(if (length(countries) == 0) NA_character_ else countries)
}

# Extract all countries mentioned in each paper (one row per country-paper combo)
paper_countries <- ds %>%
  filter(!is.na(country)) %>%
  select(paper_id, country) %>%
  distinct() %>%
  mutate(
    countries = sapply(country, extract_countries, exclude_list = exclude_list, USE.NAMES = FALSE)
  ) %>%
  filter(!is.na(countries)) %>%
  unnest_longer(countries) %>%
  select(paper_id, countries) %>%
  distinct() %>%
  rename(country_clean = countries)

# Check what's not being matched
unmatched <- paper_countries %>%
  left_join(country_iso_mapping, by = "country_clean", relationship = "many-to-one") %>%
  filter(is.na(iso_a3)) %>%
  group_by(country_clean) %>%
  summarise(count = n(), .groups = 'drop') %>%
  arrange(desc(count))

# Save unmatched countries for review
if (nrow(unmatched) > 0) {
  cat("Found", nrow(unmatched), "unmatched country terms. Saving to results/unmatched_countries.csv\n")
  write.csv(unmatched, "results/unmatched_countries.csv", row.names = FALSE)
} else {
  cat("All country terms were successfully matched or excluded.\n")
  # Create an empty file if it doesn't exist, or clear it if it does
  file.create("results/unmatched_countries.csv")
}

# Create the final standardized dataset
standardized_country_data <- paper_countries %>%
  left_join(country_iso_mapping, by = "country_clean", relationship = "many-to-one") %>%
  mutate(iso_a3 = normalize_parent_iso(iso_a3)) %>%
  filter(!is.na(iso_a3)) %>%
  select(paper_id, iso_a3) %>%
  distinct()

# Save the standardized data
write.csv(standardized_country_data, "data/standardized_country_data.csv", row.names = FALSE)

cat("Standardized country data saved to data/standardized_country_data.csv\n")
