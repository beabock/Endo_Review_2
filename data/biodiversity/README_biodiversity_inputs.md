Purpose
- Templates and instructions for converting your EPI/IUCN/World Bank files into inputs for `scripts/04_analyses/08_biodiversity_priority_overlap.R`.

Expected country-level CSV schema (recommended file name: `biodiversity_priority_countries.csv`)
- `iso3`: ISO3 country code (e.g., AUS)
- `country_name`: human-readable country name
- `priority_score`: numeric priority metric (higher = higher priority)
- `priority_rank`: optional integer rank
- `source`: source identifier (e.g., `WorldBank_WB_GBIOD_N_SPP_SMALL50XENDEMIC100`)

Expected biome-level CSV schema (recommended file name: `biodiversity_priority_biomes.csv`)
- `biome_id`, `biome_name`, `priority_score`, `units`, `source`

Quick mapping notes
- World Bank CSVs in `World_Bank/` use `REF_AREA` (ISO3) and `OBS_VALUE` (numeric). Example conversion (R):

```r
library(readr)
wb <- read_csv("World_Bank/WB_GBIOD_N_SPP_SMALL50XENDEMIC100.csv")
# keep REF_AREA (iso3) and OBS_VALUE
wb_priority <- wb %>% dplyr::select(iso3 = REF_AREA, priority_score = OBS_VALUE)
write_csv(wb_priority, "biodiversity_priority_countries.csv")
```

- IUCN country tables are by country name; use `countrycode::countrycode()` in R or `country_mapping.py` to get ISO3 codes.

Example IUCN conversion (R):

```r
library(readr); library(dplyr); library(countrycode)
iucn <- read_csv("iucn_5-5-26/Table 6b Plant species (kingdom Plantae) by country - show all.csv")
iucn2 <- iucn %>% rename(country_name = Name, threatened = `Subtotal (threatened spp.)`) %>%
  mutate(iso3 = countrycode(country_name, "country.name", "iso3c"))
# choose metric: threatened or Total
iucn_out <- iucn2 %>% transmute(iso3, country_name, priority_score = as.numeric(threatened), source = "IUCN_Table6b")
write_csv(iucn_out, "biodiversity_priority_countries_from_iucn.csv")
```

Next steps for you
- If you want, I can create converted CSVs from your World Bank files automatically (I already inspected headers). Confirm and I'll generate `biodiversity_priority_countries.csv` using `WB_GBIOD_N_SPP_SMALL50XENDEMIC100.csv` / `WB_GBIOD_N_SPP_TPROB80.csv` / `WB_GBIOD_N_SPP_TOTAL.csv` as separate source rows.
- Or run the R conversion snippets locally and then run `scripts/04_analyses/08_biodiversity_priority_overlap.R` (requires R).

If you'd like me to proceed with automated conversion, reply "Convert WB files" and I'll generate the combined `biodiversity_priority_countries.csv` in the folder.