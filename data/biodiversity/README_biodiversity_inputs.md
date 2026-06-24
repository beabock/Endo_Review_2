# Biodiversity Input Data

Reference datasets for `scripts/04_analyses/08_biodiversity_priority_overlap.R`.

## Country-level CSV schema (`biodiversity_priority_countries.csv`)

- `iso3`: ISO3 country code (e.g., AUS)
- `country_name`: human-readable country name
- `priority_score`: numeric priority metric (higher = higher priority)
- `priority_rank`: optional integer rank
- `source`: source identifier (e.g., `WorldBank_WB_GBIOD_N_SPP_SMALL50XENDEMIC100`)

## Sources

**World Bank** (`World_Bank/`): CSVs use `REF_AREA` (ISO3) and `OBS_VALUE` (numeric).

```r
wb <- read_csv("World_Bank/WB_GBIOD_N_SPP_SMALL50XENDEMIC100.csv")
wb_priority <- wb %>% dplyr::select(iso3 = REF_AREA, priority_score = OBS_VALUE)
write_csv(wb_priority, "biodiversity_priority_countries.csv")
```

**IUCN** (`iucn_5-5-26/`): country tables use country names; convert to ISO3 with `countrycode`.

```r
library(readr); library(dplyr); library(countrycode)
iucn <- read_csv("iucn_5-5-26/Table 6b Plant species (kingdom Plantae) by country - show all.csv")
iucn_out <- iucn %>%
  rename(country_name = Name, threatened = `Subtotal (threatened spp.)`) %>%
  mutate(iso3 = countrycode(country_name, "country.name", "iso3c")) %>%
  transmute(iso3, country_name, priority_score = as.numeric(threatened), source = "IUCN_Table6b")
write_csv(iucn_out, "biodiversity_priority_countries_from_iucn.csv")
```

**EPI 2024** (`EPI_2024/`): raw indicator CSVs from the Yale Environmental Performance Index.
