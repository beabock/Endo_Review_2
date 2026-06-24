# BMB 2024-09-22
# Manual step - pulls abstracts from PubMed, Scopus, and Web of Science APIs.
# Needs credentials; run interactively, not part of the automated pipeline.

library(rentrez)       # PubMed
library(rscopus)       # Scopus
library(wosr)          # Web of Science
library(dplyr)
library(tibble)
library(purrr)
library(xml2)

# 1. Define search string

base_search <- paste(
  "( (endophyte* AND (fungus OR fungi OR fungal OR mycota))",
  'OR "latent fung*" OR "systemic fung*" OR "internal fung*" OR "resident fung*"',
  'OR "fungal endophyte*" OR "endophytic fung*" OR "dark septate endophyte*"',
  'OR "dark septate fung*" OR "seed-borne fung*" OR "seed-transmitted fung*"',
  'OR "symptomless fung*" OR "asymptomatic fung*" OR "quiescent fung*" )',
  "AND",
  "( plant* OR moss* OR bryophyt* OR liverwort* OR hornwort* OR fern*",
  "OR lycophyte* OR pteridophyte* OR tree* OR forest* OR shrub* OR grass*",
  "OR graminoid* OR herb* OR crop* OR seedling* OR sapling* OR seed*",
  "OR root* OR leaf* OR foliage OR shoot* OR stem* OR twig* OR rhizome*",
  "OR thallus OR frond* OR hydrophyte* OR seagrass* OR alga* OR gymnosperm*",
  "OR angiosperm* OR macroalga* OR spermatophyte* OR phanerogam* OR monocot*",
  "OR dicot* OR charophyt* OR chlorophyt* OR anthocerotophyt* OR glaucophyt*",
  "OR langiophytophyt* OR langiophytopsid* OR marchantiophyt* OR rhodophyt*",
  "OR tracheophyt* OR vine* OR epiphyt* OR cultivar* OR xylem OR phloem )",
  "AND \"Journal Article\"[Publication Type]",
  collapse = " "
)

# 2. Define year ranges
year_ranges <- list(
  c(1700, 1999),
  c(2000, 2005),
  c(2006, 2010),
  c(2011, 2015),
  c(2016, 2020),
  c(2021, 2025)
)

# 3. Function to fetch and parse a year chunk
fetch_parse_pubmed <- function(year_start, year_end, batch_size = 200) {
  search_string <- paste0(
    base_search,
    " AND (", year_start, "/01/01[PDAT] : ", year_end, "/12/31[PDAT])"
  )
  
  search_res <- entrez_search(db = "pubmed", term = search_string,
                              retmax = 0, use_history = TRUE)
  total <- search_res$count
  web_hist <- search_res$web_history
  
  if (total == 0) return(NULL)
  
  batches <- seq(0, min(total - 1, 9998), by = batch_size)  # never exceed 9999
  
  xml_list <- map(batches, function(start) {
    message("PubMed: Fetching records ", start + 1, " to ", min(start + batch_size, total),
            " for years ", year_start, "-", year_end)
    records_xml <- entrez_fetch(db = "pubmed",
                                web_history = web_hist,
                                rettype = "xml",
                                retstart = start,
                                retmax = batch_size)
    read_xml(records_xml)
  })
  
  # Parse XML
  map_dfr(xml_list, function(xml_doc) {
    articles <- xml_find_all(xml_doc, ".//PubmedArticle")
    
    tibble(
      title = xml_text(xml_find_first(articles, ".//ArticleTitle")),
      authors = map_chr(articles, function(article) {
        author_nodes <- xml_find_all(article, ".//AuthorList/Author")
        if (length(author_nodes) == 0) return(NA_character_)
        paste(map_chr(author_nodes, function(a) {
          paste(
            xml_text(xml_find_first(a, ".//LastName")),
            xml_text(xml_find_first(a, ".//Initials"))
          )
        }), collapse = "; ")
      }),
      doi = map_chr(articles, function(article) {
        doi_node <- xml_find_first(article, ".//ArticleIdList/ArticleId[@IdType='doi']")
        if (!is.na(doi_node)) xml_text(doi_node) else NA_character_
      }),
      year = xml_text(xml_find_first(articles, ".//PubDate/Year")),
      journal = xml_text(xml_find_first(articles, ".//Journal/Title")),
      abstract = map_chr(articles, function(article) {
        txt <- xml_find_all(article, ".//AbstractText")
        paste(xml_text(txt), collapse = " ")
      })
    )
  })
}

# Fetch all PubMed
pubmed_df <- map_dfr(year_ranges, ~fetch_parse_pubmed(.x[1], .x[2]))

# 5. Inspect and save
View(pubmed_df[1:30,])
write.csv(pubmed_df, "data/raw/pubmed_pull_8-14-25.csv", row.names = FALSE)
# 3. Scopus
# Note: Requires API key. Set environment variable or input directly.

# Set API key
set_api_key("") # replace with your Scopus key

# Search Scopus
fetch_parse_scopus <- function(query, batch_size = 200) {
  # First, get the total number of results
  initial <- scopus_search(query = query, view = "STANDARD", count = 0)
  total_results <- initial$totalResults %>% as.numeric()
  message("Total Scopus results: ", total_results)
  
  results <- list()
  start_record <- 0
  
  while (start_record < total_results) {
    message("Fetching Scopus records ", start_record + 1, " to ", 
            min(start_record + batch_size, total_results))
    
    batch <- scopus_search(query = query, view = "STANDARD", 
                           start = start_record, count = batch_size)
    
    if (length(batch$entries) == 0) break
    
    df <- batch$entries %>% as_tibble() %>%
      transmute(
        title = title,
        authors = map_chr(authors, ~paste(.x$`surname`, .x$`given-name`, collapse = "; ")),
        doi = doi,
        year = str_sub(coverDate, 1, 4),
        journal = publicationName,
        abstract = description
      )
    
    results[[length(results) + 1]] <- df
    start_record <- start_record + nrow(df)
  }
  
  bind_rows(results)
}

# Example usage
scopus_df <- fetch_parse_scopus(base_search)

write.csv(scopus_df, "scopus_results.csv", row.names = FALSE)

# 4. Web of Science (WoS)
# Note: Requires institutional subscription and API key

# Set API credentials
wos_auth(username = "YOUR_USERNAME", password = "YOUR_PASSWORD", insttoken = "YOUR_INST_TOKEN")

fetch_parse_wos <- function(query, batch_size = 100) {
  results <- list()
  start_record <- 1
  repeat {
    batch <- wos_search(query = query, count = batch_size, firstRecord = start_record)
    if (length(batch$records) == 0) break
    
    df <- map_df(batch$records, ~tibble(
      title = .x$`title` %||% NA_character_,
      authors = .x$`authors` %||% NA_character_,
      doi = .x$`doi` %||% NA_character_,
      year = .x$`pubinfo` %||% NA_character_,
      journal = .x$`source` %||% NA_character_,
      abstract = .x$`abstract` %||% NA_character_
    ))
    
    results[[length(results) + 1]] <- df
    start_record <- start_record + batch_size
  }
  bind_rows(results)
}

wos_df <- fetch_parse_wos(base_search, batch_size = 100)

write.csv(wos_df, "wos_results.csv", row.names = FALSE)

