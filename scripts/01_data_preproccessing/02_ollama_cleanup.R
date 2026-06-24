# BMB 2026-06-05
# Cleans up taxon names in the Ollama extraction output — strips AI-generated
# prefixes, filters non-plant hosts, and standardizes values for the rest of the pipeline.

library(tidyverse)
library(stringr)
library(jsonlite)

message("Loading perfectly structured Python dataset...")
# 1. Load the Python-healed file natively
ds <- read_csv("data/Ollama_python_healed.csv", show_col_types = FALSE)

# 2. Define the exact same biological rules for the taxon column
config_path <- file.path("scripts", "utils", "taxon_mapping_config.json")
fallback_null_words <- c("endophytic", "endophyte", "intercellular fungal endophyte", 
                          "anaerobic microbes", "unspecified", "not explicitly mentioned", 
                          "unknown", "none", "n/a", "fungus", "fungi", 
                          "endophytic fungus", "endophytes", "fungal endophytes", 
                          "various", "primary guild", "multiple endophytic", "medicinal plants", 
                          "latin name", "ectomycorrhizal fungi", "common name")

if (file.exists(config_path)) {
    config <- jsonlite::fromJSON(config_path)
    null_words <- unique(tolower(c(config$suppress_non_taxon_phrases, config$na_tokens)))
} else {
    null_words <- fallback_null_words
}

                
clean_taxon <- function(x) {
    if(!is.character(x)) return(x)
    
    x <- x %>%
        # Strip JSON, HTML, and technical wrappers
        str_replace_all("<.*?>", " ") %>%
        str_remove_all("\\{'scientific_name'\\: ?|'tissue'\\: ?'.*?'") %>%
        str_remove_all("[\\{\\}\\[\\]\\']") %>%
        # Strip parenthetical content 
        str_remove_all("\\(.*?\\)") %>%
        # Strip AI prefixes
        str_remove_all("^(taxon|phylum|class|order|family|genus|species|name|role)\\s*:?\\s*") %>%
        str_squish() %>%
        str_to_lower()
    
    # NA-ing non-biological noise
    x[x %in% null_words] <- NA_character_
    
    # Enforce Word Count and Length limits
    word_counts <- str_count(x, "\\w+")
    x[word_counts > 6] <- NA_character_
    x[str_length(x) > 60] <- NA_character_
    
    return(x)
}

message("Scrubbing AI prefixes and non-plant hosts...")
# 3. Apply the cleaning
ds_final <- ds %>%
    mutate(across(where(is.character), ~ str_squish(str_to_lower(.x)))) %>%
    mutate(fungal_taxon = clean_taxon(fungal_taxon)) %>%
    
    # Filter out Clinical/Human hosts
    filter(is.na(plant_host) | !str_detect(plant_host, "homo sapiens|human|carcinoma|patient|infant|clinical")) %>%
    
    # Standardize categoricals
    mutate(
        relevance = ifelse(str_detect(relevance, "relev") & !str_detect(relevance, "not"), "Relevant", "Uncertain"),
        doc_type_ai_clean = ifelse(str_detect(doc_type_ai, "full-text|full text"), "Full-Text", "Abstract")
    )

# 4. Save the final dataset
write.csv(ds_final, "data/Ollama_cleaned.csv", row.names = FALSE)
message(sprintf("Complete! %d rows ready for GBIF.", nrow(ds_final)))