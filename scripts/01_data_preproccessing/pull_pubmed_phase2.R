# BMB 2026-09-02
# Standalone PubMed re-pull with the AUTHORITATIVE Phase 2 search string
# (docs/SEARCH_STRATEGY.md), to replace pubmed_pull_8-14-25.csv - that file was
# produced with an earlier DRAFT string ("endophyte*" + "latent/systemic fung*"
# wildcards) that pulled ~1,500 clinical-mycology and non-endophyte papers the
# documented strategy excludes. See METHODS_CHANGELOG.md 2026-09-02.
#
# rentrez needs no API key - just a contact email (NCBI etiquette). Run:
#   Rscript scripts/01_data_preproccessing/pull_pubmed_phase2.R your@email
# Output: data/Abstracts/All_abstracts_8-14-25/pubmed_pull_phase2.csv
#         (6 columns: title, authors, doi, year, journal, abstract - the format
#          combine_dedupe_abstracts.R expects)

suppressPackageStartupMessages({
  library(rentrez); library(dplyr); library(tibble); library(purrr); library(xml2)
})

args <- commandArgs(trailingOnly = TRUE)
email <- if (length(args) >= 1) args[[1]] else Sys.getenv("ENTREZ_EMAIL", "")
if (nzchar(email)) options(reutils.email = email)

# --- Phase 2 string (identical concept to WoS/Scopus; PubMed field syntax) ---------
endophyte_terms <- paste(
  '"fungal endophyte" OR "fungal endophytes" OR "endophytic fungus" OR "endophytic fungi" OR',
  '"latent fungus" OR "latent fungi" OR "systemic fungus" OR "systemic fungi" OR',
  '"internal fungi" OR "resident fungi" OR "seed-borne fungi" OR "seed-transmitted fungi" OR',
  '"dark septate endophyte" OR "dark septate fungi" OR "DSE fungi"')
host_terms <- paste(
  "plant*[tiab] OR moss*[tiab] OR bryophyte*[tiab] OR liverwort*[tiab] OR hornwort*[tiab] OR",
  "fern*[tiab] OR lycophyte*[tiab] OR pteridophyte*[tiab] OR tree*[tiab] OR shrub*[tiab] OR",
  "grass*[tiab] OR graminoid*[tiab] OR herb*[tiab] OR crop*[tiab] OR seedling*[tiab] OR",
  "sapling*[tiab] OR seed*[tiab] OR root*[tiab] OR leaf*[tiab] OR foliage[tiab] OR",
  "shoot*[tiab] OR stem*[tiab] OR twig*[tiab] OR rhizome*[tiab] OR thallus[tiab] OR",
  "frond*[tiab] OR algae[tiab] OR macroalga*[tiab] OR cyanobacteria[tiab] OR",
  "cyanobiont*[tiab] OR photobiont*[tiab] OR lichen*[tiab]")
base_search <- sprintf("(%s) AND (%s) AND \"Journal Article\"[Publication Type]",
                       endophyte_terms, host_terms)

year_ranges <- list(c(1700, 1999), c(2000, 2005), c(2006, 2010),
                    c(2011, 2015), c(2016, 2020), c(2021, 2025))

fetch_year <- function(y0, y1, batch = 200) {
  q <- paste0(base_search, " AND (", y0, "/01/01[PDAT] : ", y1, "/12/31[PDAT])")
  s <- entrez_search(db = "pubmed", term = q, retmax = 0, use_history = TRUE)
  message(sprintf("  %d-%d: %d records", y0, y1, s$count))
  if (s$count == 0) return(NULL)
  starts <- seq(0, s$count - 1, by = batch)
  map_dfr(starts, function(st) {
    Sys.sleep(0.34)                                   # <= 3 req/s without a key
    xml <- read_xml(entrez_fetch(db = "pubmed", web_history = s$web_history,
                                 rettype = "xml", retstart = st, retmax = batch))
    arts <- xml_find_all(xml, ".//PubmedArticle")
    tibble(
      title = xml_text(xml_find_first(arts, ".//ArticleTitle")),
      authors = map_chr(arts, function(a) {
        au <- xml_find_all(a, ".//AuthorList/Author")
        if (!length(au)) return(NA_character_)
        paste(map_chr(au, ~paste(xml_text(xml_find_first(.x, ".//LastName")),
                                 xml_text(xml_find_first(.x, ".//Initials")))),
              collapse = "; ")
      }),
      doi = map_chr(arts, function(a) {
        d <- xml_find_first(a, ".//ArticleIdList/ArticleId[@IdType='doi']")
        if (!is.na(d)) tolower(trimws(xml_text(d))) else NA_character_
      }),
      year = xml_text(xml_find_first(arts, ".//PubDate/Year")),
      journal = xml_text(xml_find_first(arts, ".//Journal/Title")),
      abstract = map_chr(arts, ~paste(xml_text(xml_find_all(.x, ".//AbstractText")),
                                      collapse = " "))
    )
  })
}

message("PubMed Phase 2 pull ...")
pm <- map_dfr(year_ranges, ~fetch_year(.x[1], .x[2])) %>%
  filter(!is.na(abstract), abstract != "") %>%
  distinct(title, .keep_all = TRUE)

out <- "data/Abstracts/All_abstracts_8-14-25/pubmed_pull_phase2.csv"
dir.create(dirname(out), showWarnings = FALSE, recursive = TRUE)
write.csv(pm, out, row.names = FALSE)
message(sprintf("\nWrote %d records -> %s", nrow(pm), out))
message("Now set PUBMED_CSV in combine_dedupe_abstracts.R to this file and re-run it.")
