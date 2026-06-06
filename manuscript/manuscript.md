# Manuscript Outline (Structure Only)

## Working Title Options
1. Global Sampling Biases in Fungal Endophyte Research
2. Mapping the Unexplored Spots of Endophyte Ecology Across Biomes, Hosts, and Economies

## Target Journal
New Phytologist

## Central Framing (1-2 sentences for Abstract and Introduction)
- The core focus of this manuscript is to synthesize our current global knowledge of fungal endophyte occurrences, spatial distribution, and research effort.
- Fungal endophytes are frequently assumed to be in all plants in all biomes ("ubiquitous") in the literature [@stone_overview_2000; @arnold_are_2000; @cosner_fungal_2025]. The ubiquity claim analysis serves as evidence to show just how often this statement is uncritically repeated, thereby justifying the need for a global macro-synthesis of actual geographic and taxonomic distribution.
- The key advance is a reproducible evidence-gap analysis linking host taxonomy, geography, and research capacity to define a priority sampling roadmap, mapping where ecological inference is currently credible versus where evidence is missing.
- The broader motivation should still acknowledge the ecological and applied importance of endophytes, including their roles in secondary metabolites, plant stress tolerance, and bioprospecting [@kusari_chemical_2012; @rodriguez_fungal_2009; @strobel_endophytes_2003].

## Core Research Questions
1. Where are studies concentrated geographically, and where are the major spatial knowledge gaps globally?
2. How is sampling distributed across biomes and host plant lineages?
3. How strongly is research effort associated with national economic capacity?
4. How frequently does the literature rely on the assumption of endophyte ubiquity, underscoring the necessity of mapping true sampling coverage?
5. Which host taxa and regions should be prioritized to maximize ecological discovery?

## Novelty Claims to Make Explicit
- Directly evaluates a field-wide, often repeated ubiquity claim with global-scale evidence aggregation, rather than assuming the claim is already settled
- First synthesis in this project space that jointly analyzes geographic, host taxonomic, and macroeconomic bias in fungal endophyte literature at this scale
- Produces actionable priority lists (understudied taxa and countries) rather than only descriptive bibliometrics.
- Extends the prioritization frame by comparing understudied regions and biomes with current biodiversity-estimate priority areas, not future projections.
- Reframes the ecological question from "are endophytes ubiquitous" to "where can we currently test ecological mechanisms with sufficient evidence?"
- Given the reviewer feedback, avoid presenting the manuscript as a mechanism paper; it is stronger as a field-audit and prioritization paper.

## Manuscript Structure

## Abstract (Outline)
- Background: Fungal endophytes are often described as ubiquitous in the literature, yet that repeated claim has not been tested with a truly global synthesis [@stone_overview_2000; @arnold_are_2000; @cosner_fungal_2025].
- Aim: Quantify and integrate geographic, biome, host taxonomic, and GDP-linked sampling bias.
- Methods: Reproducible literature-mining and metadata standardization workflow; bias metrics across country, biome, and host taxonomy.
- Main findings: Strong concentration in a limited set of countries/biomes; study effort tracks national wealth; substantial blind spots remain.
- Ecological implication: Current ecological generalizations are likely conditioned by sampling geography and host coverage.
- Deliverable: Priority roadmap of understudied countries and host taxa for future field and sequencing efforts.

## Introduction (Outline)
1. Why endophyte ecology needs global synthesis now.
2. The ubiquity claim as a central assumption in the literature, and why it needs explicit global testing [@stone_overview_2000; @arnold_are_2000; @cosner_fungal_2025].
2. Problem statement: ecological conclusions are vulnerable to sampling bias.
3. What prior work has done (regional/taxon-specific reviews) and what is still missing [@schulz_endophytic_2005; @uren_host_2012].
4. Gap this manuscript fills: first global test framing + integrated bias analysis + prioritization outputs, but explicitly from mostly abstract-level evidence (CITATION).
5. Study objectives and predictions:
	- Prediction U: Current evidence is insufficiently global to support an unqualified ubiquity claim.
	- Prediction A: Research effort is geographically clustered.
	- Prediction B: Biome and host representation are non-random.
	- Prediction C: Study intensity increases with GDP.
6. Defense of the evidence base: Over 80% of endophyte research remains behind paywalls, meaning global synthesis currently must rely heavily on abstract-led mining. We explicitly frame this limitation as yielding a conservative underestimate of sampling diversity—if a region or taxon is globally sampled, it should be visible in the abstract record [CITATION].

## Methods (Outline)

### Main Methods
1. Corpus assembly and scope
	- Abstracts were consolidated from Web of Science, Scopus, and PubMed, deduplicated, and filtered to a final analysis corpus [CITATION].
	- Describe the retrieval of open-access full texts (n=3,068) versus paywalled abstract-only records (n=15,682 from a total 18,750).
	- Explicitly defend the method: because comprehensive full-text mining is blocked by access barriers, this study is an abstract-led field audit. Acknowledge that while abstracts omit some geographic and taxonomic minutiae, they capture the primary focus of the work, meaning our detected major gaps represent true thematic blind spots in the literature [CITATION].
2. Taxonomic resolution and synonym handling
	- Detailed GBIF matching workflow and manual review of unresolved taxa [@registry-migrationgbiforg_gbif_2023]. Include explicit rules for how the pipeline mapped shifting taxonomic bounds over time (e.g., changes in fungal phyla and misclassifications) to ensure robust lineage-level counts [CITATION].
3. Core analyses
	- Geographic concentration and country-level bias [CITATION].
	- GDP and latitude relationships [CITATION].
	- Host taxonomic coverage and understudied-taxa prioritization [CITATION].
	- Interaction / relationship-type summaries.
	- Ubiquity-claim detection in the full-text/abstract evidence base [CITATION].
4. Reproducibility and validation
	- Brief statement that the pipeline is script-based, versioned, and checkpointed [CITATION].
	- Brief statement that ambiguous records and unusual metadata were manually reviewed where needed.
	- Detailed explanation of how historical taxonomic shifts (e.g., traditional isolation vs. molecular OTUs) were reconciled: our custom scripts algorithmically mapped and resolved obsolete or changing nomenclature to their current valid taxonomies using the GBIF backbone, harmonizing decades of data (e.g., moving specific species definitions or higher-level phyla) to rigorously calculate biological coverage.

### Supplementary Methods
1. Corpus assembly details
	- Exact search strings, database export rules, deduplication sequence, document-type filters, and row counts at each stage.
	- Scripts: [01_csv_cleanup.py](scripts/01_data_preproccessing/01_csv_cleanup.py), [api_pull_abstracts.R](scripts/01_data_preproccessing/api_pull_abstracts.R), [Combo_abstracts_pull2.R](scripts/01_data_preproccessing/Combo_abstracts_pull2.R), [merge_final_data.py](scripts/01_data_preproccessing/merge_final_data.py), [download_pdfs.py](scripts/01_data_preproccessing/download_pdfs.py), [monsoon_extract.py](scripts/01_data_preproccessing/monsoon_extract.py).
2. Taxonomic resolution and synonym handling
	- Detailed GBIF matching workflow, manual review of unresolved taxa, and the rules used to standardize plant and fungal names.
	- Scripts: [taxa_synonym_resolution.py](scripts/02_taxa_resolution/taxa_synonym_resolution.py), [taxon_mapping.py](scripts/utils/taxon_mapping.py).
3. Metadata extraction and standardization rules
	- Country normalization, disputed-territory handling, geographic centroids, GDP linkage, biome assignment, tissue mapping, guild mapping, and publication-year enrichment.
	- Scripts: [01_standardize_metadata.py](scripts/03_standardize_metadata/01_standardize_metadata.py), [01a_enrich_publication_year.py](scripts/03_standardize_metadata/01a_enrich_publication_year.py), [02_dataset_filtering.py](scripts/03_standardize_metadata/02_dataset_filtering.py), [03_geographic_standardizing.R](scripts/03_standardize_metadata/03_geographic_standardizing.R), [04_country_enrichment.R](scripts/03_standardize_metadata/04_country_enrichment.R), [05_dataset_summary.py](scripts/03_standardize_metadata/05_dataset_summary.py), [06_preanalysis_check.py](scripts/03_standardize_metadata/06_preanalysis_check.py), [country_mapping.py](scripts/utils/country_mapping.py), [country_mapping.R](scripts/utils/country_mapping.R), [disputed_territory_parent_iso.R](scripts/utils/disputed_territory_parent_iso.R).
4. Relationship and bias classification rules
	- Full rules for relationship classification (endophytic, pathogenic, mycorrhizal, antagonistic, mutualistic, saprotrophic, commensal, absence/negative, unknown).
	- Scripts: [07_relationship_type_summary.R](scripts/04_analyses/07_relationship_type_summary.R), [04_interaction_bias.R](scripts/04_analyses/04_interaction_bias.R), [03_fungal_taxonomic_bias.py](scripts/04_analyses/03_fungal_taxonomic_bias.py).
5. Biodiversity priority overlap analysis
	- Compare understudied endophyte countries to World Bank biodiversity metrics (endemic species counts, threatened species probabilities).
	- Assess overlap between research gaps and conservation priorities across multiple priority thresholds.
	- Scripts: [convert_wb_biodiversity.py](scripts/04_analyses/convert_wb_biodiversity.py), [08_biodiversity_priority_overlap.R](scripts/04_analyses/08_biodiversity_priority_overlap.R), [09_biodiversity_priority_robustness.py](scripts/04_analyses/09_biodiversity_priority_robustness.py), [biodiversity_priority_overlap_plot.R](scripts/05_plotting/biodiversity_priority_overlap_plot.R).
6. Ubiquity detection and full-text screening
	- Ollama model choice, prompt structure, sharding, checkpointing, timeout behavior, and positive-call criteria.
	- Scripts: [06_detect_ubiquity_claims_ollama.py](scripts/04_analyses/06_detect_ubiquity_claims_ollama.py), [merge_ubiquity_shards.py](scripts/04_analyses/merge_ubiquity_shards.py), [submit_ubiquity_shards.sh](scripts/04_analyses/submit_ubiquity_shards.sh), [run_06_ubiquity_claims_ollama.sbatch](scripts/04_analyses/run_06_ubiquity_claims_ollama.sbatch), [check_ollama_models.sh](scripts/utils/check_ollama_models.sh).
7. Validation and sensitivity checks
	- Training/test splits, manual validation of absence candidates, and checks for the effect of abstract-only vs full-text access.
	- Scripts: [05_manuscript_summary.py](scripts/04_analyses/05_manuscript_summary.py), [03_identify_understudied_taxa.R](scripts/04_analyses/03_identify_understudied_taxa.R), [01_country_gdp_latitude_analysis.R](scripts/04_analyses/01_country_gdp_latitude_analysis.R), [02_taxonomy.R](scripts/04_analyses/02_taxonomy.R), [03_geographic_bias_mapping.R](scripts/04_analyses/03_geographic_bias_mapping.R).
8. Figure generation and presentation
	- Plotting choices and publication-ready outputs.
	- Scripts: [geographic_plotting.R](scripts/05_plotting/geographic_plotting.R), [biome_plots.R](scripts/05_plotting/biome_plots.R), [relationship_type_plots.R](scripts/05_plotting/relationship_type_plots.R), [taxonomy_representation.R](scripts/05_plotting/taxonomy_representation.R), [tissue_plots.R](scripts/05_plotting/tissue_plots.R), [theme_utils.R](scripts/05_plotting/theme_utils.R), [biodiversity_priority_overlap_plot.R](scripts/05_plotting/biodiversity_priority_overlap_plot.R).

## Results (Outline)
1. Evidence base for evaluating the ubiquity claim
	- Quantify scope and coverage limits of the globally aggregated record.
	- Report how many abstracts/papers explicitly or near-explicitly state ubiquity claims, because this directly shows that the claim is repeated in the literature. The Ollama screen flagged 586 positive claims in the 21,891-abstract corpus (334 explicit and 252 qualified; all from abstracts), which is about 2.7% of the corpus.
	- Position the rest of the Results as tests of where the literature makes this claim and where sampling remains sparse.

### Estimated prevalence of explicit ubiquity claims in the sampled literature

1. Global geography of study effort
	- Show strong spatial concentration and zero/near-zero regions.
	- Figure: `study_count_by_country_robinson.png` (Figure 1)
	- Add a caveat about country-level zeros because reviewers flagged that abstracts often omit location metadata, so zeros are not literal absence [@uren_host_2012; CITATION] but definitely flag underrepresented areas.

2. Biome-by-country imbalance
	- Show that study effort is not only geographically clustered, but biome-skewed within and across countries.
	- Figure: `biome_country_heatmap.png` (Figure 2)
	- Keep this secondary unless biome metadata coverage is strong enough to survive reviewer scrutiny; reviewers explicitly worried that abstract-only mining misses contextual details like habitat and location (CITATION).

3. Economic gradient in research intensity
	- Quantify association between GDP and number of studies.
	- Figure: `country_study_count_vs_gdp.png` (Figure 3)

4. Host taxonomy representation gaps
	- Identify concentrated sampling of certain host groups and missing branches.
	- Figure: `13_compound_taxonomy_heatmap.png` (Figure 4)
	- Tie this back to the old manuscript's species/genera/family coverage statistics and the GBIF-backed taxonomy standardization approach [@registry-migrationgbiforg_gbif_2023]. Use updated statistics from ANALYSIS_SUMMARY.md though.

5. Priority outputs for future sampling
	- Summarize top understudied countries and host taxa from pipeline outputs.
	- Tables: unstudied species/genera/families and unstudied countries.
	- This is the place to include the old manuscript's priority framing around Charophyta, Bryophyta, and similarly sparse regions like Tonga (CITATION), but again referring to the actual numbers from ANALYSIS_SUMMARY.md instead.
	- Add a short overlap analysis that compares understudied regions/biomes with current biodiversity-estimate priority areas (e.g., hotspots or richness layers) rather than future projections.

### Overlap with biodiversity conservation priorities

- A country's economic status is the primary predictor of endophyte research effort. Multiple regression models show that a country's GDP is the strongest, most consistent predictor of its study count, far outweighing the influence of biodiversity.
- While biodiversity is also a statistically significant predictor, its effect is much smaller than that of GDP. This indicates that while there is a tendency for research to occur in more biodiverse countries, this effort is overwhelmingly concentrated in high-GDP nations.
- This creates a critical knowledge gap: high-biodiversity, low-GDP countries are systematically under-represented in the current body of endophyte research. These regions are likely to harbor a vast, undiscovered diversity of endophytic fungi.
- **Implication**: The global distribution of endophyte research is more a map of economic privilege than it is a map of biodiversity. To achieve a truly global understanding of endophyte diversity and ecology, future research must prioritize sampling in these high-biodiversity, low-GDP regions.
- Figures: `modeling_results.png`, `correlation_heatmap.png`

## Discussion (Outline)
1. Main interpretation
	- The ubiquity claim may be plausible in sampled systems, but current evidence is too uneven for a strong global generalization [CITATION].
	- Make clear that the paper evaluates evidence coverage, not endophyte function, colonization mechanisms, or universal biological truth.

2. Ecological meaning (address this directly)
	- Biased sampling limits inference on host specificity, biome filtering, and broad functional claims [CITATION].
	- Overrepresented geographies may inflate confidence in generality.
	- This is the place to respond directly to the reviewer critique that the current manuscript is technical; the solution is to connect sampling bias to what ecological claims can legitimately be made, not to overstate mechanism.

3. Why this is needed even if broad bias is expected
	- Quantification, explicit testing of a core field assumption, integration, and prioritization are the contribution, not merely noting bias exists.
	- Converts an intuitive claim into a testable resource for future work [CITATION].
    - Something about how we can't just make claims that everyone agrees on and never test them. We need to actually test the claims that people make. Or something.
	- This is also where the old draft's file-drawer argument belongs, because it explains why negative findings are underreported [@rosenthal_file_1979].

4. Reliability and scope limits
	- The Open Access bottleneck: Address the necessity of abstract-level mining. Since only ~16% of the corpus (3,068 / 18,750 records) had accessible full text, systematic global reviews are artificially constrained. This serves as a broader critique of how paywalled science impedes macroecological synthesis [CITATION].
	- Confronting the abstract caveat: Acknowledge the reviewer point that abstracts frequently omit precise coordinates or secondary taxa [@uren_host_2012]. Argue that this makes our reported gaps highly conservative—even if full texts added some undocumented coverage, the structural skew towards high-GDP countries and narrow host lineages is far too massive to be an artifact of abstract writing styles.
	- Taxonomic and nomenclatural harmonization: Detail how the GBIF backbone pipeline handled historical classification shifts (e.g., moving arbuscular mycorrhizae to Glomeromycota/Mucoromycotina), directly answering concerns about the reliability of fungal taxonomic counts [CITATION].
	- Country-level aggregation caveat and biome context as partial remedy.
	- If you keep the old ecological context, note the contrast between endophyte biogeography and mycorrhizal biogeography using the existing references [@martin_ancestral_2017; @strulluderrien_origin_2018; @tedersoo_global_2014]. 

5. Practical roadmap
	- Propose targeted sampling design: underrepresented countries x underrepresented host lineages x under-sampled biomes.
	- Suggest minimum metadata standards for future synthesis-ready studies.
	- Keep the roadmap concrete and table-driven so it reads as a contribution, not just a critique.
	- **Key advantage**: The drivers of sampling bias are not random. Our models show that a country's GDP is the strongest predictor of endophyte research effort, far outweighing the influence of biodiversity. This means that our current understanding of endophyte diversity is strongly biased towards the fungi of high-GDP nations. Targeted sampling in high-biodiversity, low-GDP countries is therefore essential for a truly global understanding of endophyte ecology and for discovering novel fungal biodiversity.
	- Frame as conservation-research synergy: strategic endophyte field efforts can simultaneously address research gaps and protect global biodiversity hotspots.
	- Keep the bioprospecting angle only if it is tied to concrete under-sampled biodiversity and not used as a separate claim [@newman_natural_2012; @bertini_biodiversity_2022].

6. Conclusion
	- Endophyte ecology needs strategic expansion of sampling domains before stronger global ecological generalizations are made.
	- End with a restrained, reviewer-resistant claim: the paper identifies where evidence is missing and what should be sampled next, rather than claiming to settle endophyte ecology.

## Figure Plan (Main)
1. `study_count_by_country_robinson.png`
	- Role: Global baseline map of where evidence exists.
2. `biome_country_heatmap.png`
	- Role: Demonstrates ecological context imbalance beyond country counts.
3. `country_study_count_vs_gdp.png`
	- Role: Quantifies structural inequity in knowledge production.
4. `13_compound_taxonomy_heatmap.png`
	- Role: Shows host lineage concentration and missing taxonomic space.

## Figure Plan (Supplementary)
- `correlation_heatmap.png`: Correlation heatmap of GDP, biodiversity, and study count.
- `biome_trends_over_time.png`: temporal shifts in biome focus.
- `biome_family_heatmap.png`: family-level concentration within biomes.
- `14_family_trends_over_time.png`: temporal taxonomic dynamics.
- `tissue_trends_over_time.png`: changing tissue emphasis through time.
- `top_tissue_parts_by_study.png`: dominant tissue categories.
- `top_countries_ranked.png`: ranked concentration summary.

## Figure Captions

**Figure 1: `study_count_by_country_robinson.png`**
**Caption:** Global distribution of fungal endophyte research effort. The map shows the number of studies per country from a corpus of 18,750 publications. Of the 234 countries and territories in our analysis, 80 had zero studies. The concentration of studies in a few high-GDP countries is evident, with large regions of the world, particularly in Africa and Central Asia, showing little to no research effort.

**Figure 2: `biome_country_heatmap.png`**
**Caption:** Heatmap of study counts by biome and country. This figure reveals that research effort is not only geographically clustered, but also heavily skewed towards certain biomes within those countries. For example, temperate forests and agricultural biomes are heavily overrepresented, while other biomes, such as tropical and subtropical grasslands, savannas, and shrublands, are underrepresented, even in well-studied countries.

**Figure 3: `country_study_count_vs_gdp.png`**
**Caption:** Relationship between a country's economic status (GDP) and its endophyte research effort. There is a strong, positive correlation between a country's log10(GDP) and its log10(study count) (Spearman's ρ = 0.56, p < 0.001), indicating that wealthier countries are studied more. The line represents a loess-smoothed fit, with the shaded area showing the 95% confidence interval.

**Figure 4: `13_compound_taxonomy_heatmap.png`**
**Caption:** Heatmap showing the distribution of studies across host plant families and orders. The color intensity represents the number of studies. This figure highlights the strong taxonomic bias in endophyte research, with a few host families (e.g., Poaceae, Fabaceae) receiving a disproportionate amount of research attention, while many others are completely unstudied.

## Supplementary Figure Captions

**Figure S1: `correlation_heatmap.png`**
**Caption:** Correlation heatmap of GDP, biodiversity, and study count. This figure shows the Spearman correlation coefficients between log10(GDP), log10(study count), and the three raw biodiversity metrics from the World Bank. The strong positive correlation between GDP and study count is clearly visible across all three biodiversity metrics, and is consistently stronger than the correlation between biodiversity and study count.

## Optional Web Supplement
- `interactive_study_density.html`
  - Keep as online supplementary exploration tool, not a core figure.
  - Mention briefly in Data/Code Availability and Supplementary Methods.

## Reviewer-Facing Positioning Notes (for cover letter and Discussion)
- Explicitly state that this is a bias-and-prioritization synthesis, not a full ecological mechanism paper.
- Emphasize conservative interpretation: outputs identify evidence distribution and missingness.
- Add a short paragraph on how future full-text and non-English expansion can refine estimates.
- Acknowledge the reviewer concern that abstract-only mining likely misses geographic and taxonomic information, and make that limitation part of the paper's framing rather than a buried caveat.

## Writing Guardrails for Drafting
- Avoid overclaims such as "global ubiquity is proven" from sparse host coverage.
- Prefer language like "evidence-supported in sampled domains" and "currently untested domains."
- Tie each major claim to one figure and one concrete quantitative result.
- Ensure citations are used for any statement requiring one. Use the specific citations provided in the outline text whenever possible. If a statement requires a citation that is not explicitly provided in the outline or attached data, you must not invent one. Instead, insert a descriptive, uppercase placeholder so I can add it manually later (e.g., [CITE: NEED REFERENCE FOR ENDOPHYTE DEFINITION])
- Do not use em-dashes (--)
- Do not randomly quote or bold things.
- Strictly adhere to accepted biological nomenclature. Always italicize genus and species names (e.g., *Lolium perenne*). Do not refer to bacteria (e.g., Streptomyces) or oomycetes (e.g., *Phytophthora*) as fungi. Rely on the cleaned taxonomic data standard.
- Maintain strict distinctions between ecological guilds. When discussing the ubiquity of endophytes, do not use examples or data that explicitly refer to transient pathogens or obligate mycorrhizae unless specifically drawing a contrast.
- When discussing ubiquity claims, clearly distinguish between primary empirical findings and inherited statements. Attribute foundational claims to their original authors rather than treating them as undisputed scientific consensus.
- Use the active voice where possible to improve clarity. Use the past tense when describing the methods and results of our data extraction pipeline (e.g., 'we extracted,' 'the model identified'), and use the present tense when discussing established scientific facts or the contents of a cited paper.