# Data Processing Directory

This directory contains scripts for initial data acquisition, processing, and consolidation of scientific literature abstracts for the Endo-Review project.

## Scripts Overview

### `api_pull_abstracts.R` - Literature Database API Queries
Primary data acquisition script that retrieves abstracts from major academic databases:
- **PubMed**: NIH biomedical literature database
- **Scopus**: Elsevier's comprehensive abstract database
- **Web of Science**: Clarivate's multidisciplinary citation database

**Features:**
- Batch processing with configurable date ranges
- XML parsing for structured data extraction
- Duplicate handling across sources
- Comprehensive metadata collection (title, authors, DOI, journal, abstract text)

### `Combo_abstracts_pull2.R` - Data Consolidation and Cleaning
Data integration and quality assurance script that combines and cleans abstract collections:
- **Multi-source Integration**: Merges data from PubMed, Scopus, and Web of Science
- **Deduplication**: Advanced duplicate detection using DOI, title, and content similarity
- **Quality Filtering**: Removes non-journal articles and applies language filters
- **Metadata Standardization**: Harmonizes column names and formats across sources

## Data Processing Pipeline

### Stage 1: Data Acquisition
```r
# Retrieve abstracts from all sources
source("scripts/01_data_preproccessing/api_pull_abstracts.R")
```

### Stage 2: Consolidation
```r
# Combine and clean datasets
source("scripts/01_data_preproccessing/Combo_abstracts_pull2.R")
```

## Output Files

- **Raw Data**: Individual source files (`pubmed_pull_*.csv`, `scopus_results.csv`, `wos_results.csv`)
- **Consolidated Data**: `results/consolidated_dataset.csv` (main analysis input)
- **Processing Logs**: Deduplication statistics and quality metrics

## Dependencies

- **API Access**: Requires API keys for Scopus and Web of Science
- **R Packages**: `rentrez`, `rscopus`, `wosr`, `dplyr`, `tibble`, `purrr`, `xml2`
- **External Data**: FUNGuild database (`funtothefun.csv`) for mycorrhizal classification

## Configuration

Settings are controlled through `scripts/config/pipeline_config.R`:
- API credentials and endpoints
- Date ranges and batch sizes
- Search query parameters
- Output file paths

## Quality Assurance

### Deduplication Process
1. **DOI Matching**: Exact DOI comparison (most reliable)
2. **Title Normalization**: Fuzzy matching of normalized titles
3. **Content Similarity**: Abstract text comparison for final validation
4. **Document Type Filtering**: Restricts to "Journal Article" publications

### Data Validation
- Completeness checks for required fields
- Encoding validation for special characters
- Language detection and filtering
- Metadata consistency verification

## Performance Considerations

- **Batch Processing**: Large queries processed in configurable batches
- **Memory Management**: Chunked processing for datasets >100K abstracts
- **Rate Limiting**: Respects API rate limits with automatic retry logic
- **Error Recovery**: Robust error handling with partial result preservation

## Usage Notes

### API Requirements
- PubMed: Free API access (no key required)
- Scopus: Institutional API key required
- Web of Science: Institutional subscription and API credentials

### Data Volume
- Typical run processes 20,000-40,000 abstracts
- Processing time: 30 minutes to several hours depending on date ranges
- Output size: ~500MB consolidated dataset

### Maintenance
- Monitor API key validity and rate limits
- Update search queries for new research terms
- Archive raw data files for reproducibility
- Document any API changes or outages

This data processing pipeline forms the foundation of the Endo-Review analysis by ensuring high-quality, comprehensive literature data for downstream analysis.