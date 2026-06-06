---
title: "The Sparsely Sampled Ubiquity of Global Fungal Endophytes"
output:
  word_document:
    fig_caption: true
    df_print: kable
bibliography: Endo_Review_Refs.bib
csl: nature.csl
---

Title: The Sparsely Sampled Ubiquity of Global Fungal Endophytes

Authors: B. M. Bock^1,2^, N. McKay^3^, N.C. Johnson^1, 3^, C.A. Gehring^1,2^

1. Department of Biological Sciences, Northern Arizona University

2. Center for Adaptable Western Landscapes, Northern Arizona University

3. School of Earth and Sustainability, Northern Arizona University


## Abstract
The paradigm that 'all plants harbor fungal endophytes' is a widely accepted axiom in plant ecology, yet this claim has never been systematically tested at a global scale. Here, we use a machine learning pipeline to analyze 21,891 research abstracts spanning nearly a century. We developed a high-sensitivity screening tool to find and manually validate all potential claims of endophyte absence. This comprehensive validation revealed no evidence of a verifiable endophyte-free plant taxon within the entire scientific literature surveyed. This finding confirms that endophyte ubiquity is a robust pattern wherever plants have been studied. However, we show that this "ubiquitous" paradigm is a generalization from an extraordinarily biased sample: only 0.8% of described plant species have been examined for fungal endophytes, with 77% of all research concentrated in the Global North. Our analysis reframes a foundational paradigm, revealing that our understanding of a "global" symbiosis is based on a tiny fraction of biodiversity. This sampling bias represents a critical bottleneck in biodiversity research, limiting our discovery of novel biotechnologies and climate-resilient symbioses in the world's most threatened ecosystems.

## Introduction
Fungal endophytes represent one of the largest and most chemically diverse microbial reservoirs on Earth [@kusari_chemical_2012]. These symbionts, distinguished from mycorrhizal fungi by their ability to inhabit broad plant tissues without forming specific root interfaces [@cosner_fungal_2025] and without causing disease [@brock_fungal_1991], are not merely passive passengers; they actively modulate plant stress tolerance, drive ecosystem productivity, and produce a vast array of bioactive compounds with pharmaceutical and agricultural applications [@rodriguez_fungal_2009; @strobel_endophytes_2003]. Underpinning this functional potential is the foundational paradigm that this symbiosis is ubiquitous. Influential book chapters (e.g., [@stone_overview_2000]) and the introductions of highly cited research articles (e.g., [@arnold_are_2000]) state this claim explicitly. This idea has become a central, defining assumption in ecology, which is restated in contemporary reviews (e.g., [@cosner_fungal_2025]) noting they are "found in nearly all plants," and underpins research on endophyte function, diversity, and transmission.

However, this assumption of ubiquity remains unvalidated, as a comprehensive, systematic evaluation of fungal endophyte distribution across plant taxa and regions is lacking. Previous reviews have been qualitative or focused on specific lineages (e.g., [@schulz_endophytic_2005; @uren_host_2012]), leaving the global pattern untested. Crucially, testing this paradigm requires distinguishing between a "study-level absence" (a failure to detect endophytes in a specific sample or experiment) and a "taxon-level absence" (a plant taxon that always lacks endophytes). While study-level absences are expected due to detection limits and differing methodological approaches, a confirmed taxon-level absence would fundamentally challenge the ubiquity paradigm. Conversely, confirming ubiquity while revealing major sampling gaps would expose a critical bottleneck in our ability to bioprospect this global reservoir for novel functions.

Here, we leverage a novel machine learning pipeline to conduct the first large-scale, quantitative meta-ecology test of endophyte ubiquity. We classify 21,891 abstracts to map the taxonomic and geographic patterns of research and systematically test the claim of ubiquity. Our analysis confirms that endophyte ubiquity is a robust global pattern yet reveals it is founded on a dataset that ignores the vast majority of plant biodiversity.

## Results
Our analysis of 21,891 abstracts confirms that the literature is overwhelmingly a record of presence. Given that 'true absence' is an exceptionally rare event, we designed a high-sensitivity screening pipeline to find and manually validate all potential absence candidates.

To rigorously test for absence, we applied a two-stage machine learning pipeline to the corpus. We first isolated 19,447 relevant primary research articles, excluding secondary literature (e.g., reviews) and studies focused solely on bacterial endophytes. To identify rare negative results within this relevant corpus, we employed a high-sensitivity ensemble classifier designed to prioritize potential absence claims.

This screening tool flagged 89 candidate abstracts. Combined with an independent keyword search (see Methods), this yielded a total of 102 candidates (0.5% of the relevant literature) for manual review. We manually validated 100% of these cases. This comprehensive curation revealed that none represented a true, taxon-level absence. While we identified individual studies that failed to find endophytes (study-level absences), further investigation revealed that other studies published on the same plant taxon reported presence. Consequently, our analysis found no verifiable examples of an endophyte-free plant taxon in the entire 21,891-abstract dataset.

### A Biased View of Ubiquity
Despite this confirmed ubiquity, our analysis reveals that this conclusion rests on a tiny and deeply biased sample of plant biodiversity. We find that only 0.8% (3,226 of 390,101 species) of described plant species have been examined for endophytes (Figure 1). This sparsity is consistent across all taxonomic ranks: only 6.7% (1,506 of 22,441) of described plant genera (Supp. Fig. 1) and only 28.9% (343 of 1,185) of described plant families have been studied for endophytes (Supp. Fig. 2). The corresponding study of the fungal symbionts has only reached 3.5% of described fungal species (5,064 of 143,957 species).

![Figure 1: Plant species representation by phylum in the analyzed literature. Bars show the percentage of described species within each phylum present in the 21,891-abstract dataset. Overall coverage = 0.8% (3,226 of 390,101 described plant species).](C:/Users/beabo/OneDrive%20-%20Northern%20Arizona%20University/NAU/Endo-Review/plots/main/plantae_species_representation_main_by_phylum_percent.png)

This bias systematically overlooks critical evolutionary lineages. For example, Charophyta (Stoneworts), the closest algal relatives to land plants, have no coverage (0 of 2,012 species) in our dataset. This is a critical knowledge gap, as it leaves the aquatic origins of plant-fungal symbiosis almost completely untested, which is a relationship thought to predate the colonization of land by millions of years [@martin_ancestral_2017; @strulluderrien_origin_2018]. Similarly, Bryophyta (Mosses), representing some of the earliest land plants, have only 0.2% coverage (21 of 10,508 species). This gap obscures our understanding of how these symbioses evolved after plants first colonized land.

Even within the relatively well-studied Tracheophyta (Vascular Plants), which encompasses familiar groups like ferns, conifers, and flowering plants, coverage remains exceptionally low at 0.9% (3,150 of 363,445 species). This demonstrates that our knowledge of endophyte ubiquity is largely derived from a thin sliver of plant diversity.

This taxonomic bias is mirrored by an extreme geographic bias (Figure 2; Supp. Fig. 3). Research is concentrated in high-income countries (the Global North), which account for 77% of all geographically coded studies [@world_bank_world_2025]. This concentration is driven almost entirely by just two regions: North America and Europe alone account for 70.3% of all studies. Conversely, entire nations with unique biodiversity, such as Tonga, have zero studies detected in our dataset. A temporal analysis shows that these geographic and taxonomic biases are not historical artifacts; they have remained largely consistent over the past three decades, even as molecular methods have become standard (used in 36.8% of all studies; Figure 3; Supp. Fig. 4).

![Figure 2: Global geographic bias in fungal endophyte research. The heatmap displays the frequency of studies per country (log10 scale), where darker colors indicate higher research intensity and light gray indicates zero studies detected in the analyzed corpus. The distribution reveals a stark concentration of research in the Global North (e.g., North America and Europe), while vast regions of the Global South, including large portions of Africa and Southeast Asia, remain virtually invisible in the indexed scientific literature.](C:/Users/beabo/OneDrive%20-%20Northern%20Arizona%20University/NAU/Endo-Review/plots/main/world_map_countries_log.png)

Finally, analysis of plant tissues reported in the abstracts shows that research has covered a wide range, with roots, leaves, seeds, stem, shoot, and fruit being the most frequently studied structures (Supp. Fig. 7). This demonstrates thorough sampling across tissue types within the limited taxonomic breadth.

## Discussion
Our analysis provides the first large-scale, data-driven confirmation of the fungal endophyte ubiquity paradigm. By demonstrating that there is no evidence for a single endophyte-free plant taxon in the literature, we confirm that ubiquity is a robust pattern wherever plants have been studied.

However, the central finding of this paper is the stark contradiction between this observed ubiquity and the severe sampling biases that define the field. The 0.8% of plant species and 77% concentration in the Global North are not minor gaps; they are systematic biases that fundamentally limit our understanding. Our "ubiquitous" paradigm is a generalization from a non-random sample shaped largely by research infrastructure and funding availability rather than biological priority.

Our data strongly suggest that the true biodiversity of fungal endophytes is severely underestimated, a conclusion reinforced by both biological and methodological constraints. First, standard definitions of 'endophyte' exclude obligate symbionts such as Glomeromycota (Arbuscular Mycorrhizal Fungi); thus, our dataset represents a conservative lower bound of plant-associated fungal diversity. Second, despite analyzing 21,891 abstracts, we found evidence for only 3.5% of described fungal species (5,064 of 143,957) and 16.5% of fungal genera.

Given that we have sampled only 0.8% of global plant diversity, the 'missing' fungal biodiversity likely resides within the 99.2% of known plant species that remain unexplored. This sampling gap has fundamental implications for estimates of global fungal richness, which rely heavily on extrapolations of plant-to-fungus ratios [@hawksworth_fungal_2017]. Our data suggest that current ratios, derived largely from the depauperate endophyte communities of well-studied, temperate crops, likely fail to capture the hyperdiversity of the tropical and arid hosts that dominate the global flora. Current estimates of global fungal richness may therefore require significant upward revision as we expand sampling beyond the few dominant plant hosts currently represented in the literature. 

![Figure 3: Temporal trends in methods reported for detecting fungal endophytes across the 21,891-abstract corpus. Molecular approaches were negligible before the 1990s and rose sharply after 2000; overall, 36.8% of studies in the corpus report molecular methods.](C:/Users/beabo/OneDrive%20-%20Northern%20Arizona%20University/NAU/Endo-Review/plots/supplementary/temporal_method_trends.png)

### From "Study-Level Negatives" to "Taxon-Level Ubiquity"
A key challenge in testing ubiquity is the interpretation of "absence" reports. Our screening pipeline flagged 102 abstracts that indicated absence. Manual validation clarified that these were either irrelevant (40), simple false positives (i.e., abstracts incorrectly classified as 'Absence' by the model; 46), or reports of mixed results (15) where endophytes were found in some tissues but not others or in some plant individuals but not others.

We identified only a single genuine "study-level absence" in the literature: a study reporting no fungal endophytes in *Phragmites australis* [@lambert_no_2006]. However, this absence is contradicted by numerous other studies that confirm diverse fungal endophyte communities in the same host species [@wirsel_genetic_2001; @angelini_endophytic_2012; @clay_diversity_2016]. This specific case perfectly illustrates our core distinction: while individual studies may fail to detect endophytes ("study-level negatives"), "taxon-level ubiquity" holds true. We found no evidence of a plant taxon that is consistently free of fungal endophytes.

### Limitations of Scope
Our analysis relies on metadata and claims extracted from scientific abstracts. While this approach enables a scale of analysis impossible with manual full-text review, it inherently produces a conservative dataset, as abstracts may not explicitly list every host species or collection site. However, even if full-text mining significantly increased species recovery, the vast majority of global plant biodiversity would remain verifyingly unexplored.

We also consider the role of publication bias, or the 'file drawer problem' [@rosenthal_file_1979]. In the context of the ubiquity paradigm, this bias is likely circular: failure to detect endophytes is often attributed to methodological error rather than biological absence, discouraging the publication of negative results. Thus, our 'zero verifiable absence' finding reflects the consensus of the published record, which is itself shaped by the assumption of ubiquity.

Finally, our restriction to English-language abstracts imposes a linguistic filter on the map of knowledge. Consequently, the 'zero' counts observed in many nations in the Global South (e.g., across substantial portions of Africa) likely reflect a dual failure: a genuine scarcity of funded biodiversity monitoring, compounded by an indexing bias that excludes regional or non-English journals from global databases.

### Conclusions
This concentration of research has profound practical consequences. By prioritizing the Global North, we are effectively ignoring the tropical and arid biodiversity hotspots of the Global South [@myers_biodiversity_2000], regions where plants face some of the most extreme environmental pressures [@seneviratne_weather_2023]. This geographic skew is particularly critical given the contrasting biogeography of fungal guilds. While the diversity of key soil guilds, particularly ectomycorrhizal fungi (definitionally excluded from being endophytes), peaks in temperate and boreal zones [@tedersoo_global_2014], foliar endophytes appear to follow the canonical latitudinal diversity gradient, reaching peak richness in the tropics [@arnold_are_2000]. By concentrating 77% of research in the Global North, the field has inadvertently aligned its sampling effort with the diversity centers of mycorrhizae, while systematically ignoring the hyperdiverse centers of endophytic life.

This reframes the research bias from a simple academic gap to a significant bottleneck in global bioprospecting ([@newman_natural_2012]; [@strobel_endophytes_2003]). The cost of this omission is illustrated by recent successes in under-sampled, extreme environments; for instance, endophytes from the Antarctic angiosperm *Colobanthus quitensis* have yielded unique metabolic pathways with potential applications in neurodegenerative disease treatment [@bertini_biodiversity_2022]. Such discoveries confirm that the 99% of plant hosts currently excluded from our limited, sampling biased toward the Global North represent a vast, untapped reservoir of functional biology.

Beyond quantifying this bias, our analysis provides a corrective tool: a data-driven roadmap of the plant taxa and geographic regions that define the 'missing' majority of the literature. Provided in the Supplementary Information, this resource identifies priority targets, such as the phyla Charophyta and Bryophyta and nations like Tonga, where directed sampling is most likely to maximize novelty. Having established the global ubiquity of fungal endophytes, the field must now pivot from verifying their presence to exploring their function. By redirecting research toward these neglected lineages and regions, we can unlock the next generation of climate-resilient symbioses and biotechnologies hidden within the world's most threatened ecosystems.


## Methods
Our methodology followed a three-phase computational workflow. Phase 1: High-Sensitivity Screening. We developed a two-stage machine learning pipeline to first isolate relevant primary research (n=19,447) and then classify these abstracts for potential absence claims. Phase 2: Human Validation. We manually reviewed all abstracts flagged as potential absences (n=102) to verify the 'zero absence' finding. Phase 3: Extraction & Mapping. We applied a validated extraction pipeline to the relevant corpus. To ensure our bias analysis focused strictly on endophytes, we excluded abstracts focused solely on mycorrhizal fungi, resulting in a final analytical dataset of 19,199 abstracts for taxonomic and geographic mapping.

### 1. Machine Learning Classification as a High-Sensitivity Screen
For phase 1 of our workflow, we developed a two-stage machine learning pipeline. The first stage screened for relevance, resulting in the 19,447 abstract dataset. The second stage classified relevant abstracts as either indicating presence or absence of fungal endophytes in the studied plants. For this classification, we faced an extreme imbalanced class problem: our manually curated 876-abstract training dataset contained 346 'Presence' examples but only a single 'Absence' example (0.11%). To address this scarcity, we employed data augmentation techniques, generating synthetic abstracts representing plausible absence claims (both manually and using large language models; see Supplementary Methods). These synthetic data were used solely to define the linguistic boundaries during training and were not part of the analyzed dataset.

To design a high-sensitivity screening tool, we used a weighted ensemble of two machine learning models: a Support Vector Machine (a model that finds the optimal boundary separating two groups) and a regularized logistic regression (a model that automatically selects the most important predictive words). As documented in our model testing, we intentionally weighted the model to prioritize absence detection, creating a screen that would flag all potential candidates for manual review.

### 2. Pipeline Validation: Absence and Manual Review
We implemented a rigorous, multi-step process to validate all potential "Absence" classifications. First, our Machine Learning (ML) screen flagged 89 candidates. Second, an independent rule-based string detection algorithm flagged 12 additional unique candidates. Combined with the inclusion of our single positive control from the training set, this created a final set of 102 abstracts for manual validation.

We manually reviewed all of these 102 abstracts. The results, detailed in the Supplementary Methods, confirmed that zero represented a true, taxon-level absence.

### 3. Data Extraction Pipeline and Validation
We built a modular data extraction pipeline to parse taxonomic, geographic, and methodological information. The robustness of every component, from species name extraction to geographic coordinate parsing, was verified using a comprehensive, automated test suite. This suite evaluated core functionality, accuracy, synonym resolution, and error handling, ensuring high fidelity in the extracted data. After taxonomic information was attached to taxon names in the abstracts, any taxa listed as mycorrhizal in FungalTraits [@polme_fungaltraits_2020] and any taxa with the phylum Glomeromycota were removed. Although mycorrhizal fungi inhabit plant tissues, they represent a distinct, well-characterized functional guild separate from the general "endophyte" paradigm tested here [@cosner_fungal_2025]; therefore, abstracts focusing exclusively on mycorrhizal fungi were excluded to avoid confounding the results on endophytic fungi (which include root endophytes).


### 4. Data Aggregation
Taxonomic names were standardized and synonyms were resolved against the Global Biodiversity Information Facility (GBIF) backbone [@registry-migrationgbiforg_gbif_2023] to ensure accurate aggregation of species counts. Geographic information was aggregated at the country and region level. For regional analysis, countries were classified as 'Global North' or 'Global South' based on the World Bank's income group classifications (e.g., 'High income' vs. 'Low/Middle income') [@world_bank_world_2025].



## References
Kusari, S., Hertweck, C. & Spiteller, M. Chemical ecology of endophytic fungi: origins of secondary metabolites. Chem. Biol. 19, 792–798 (2012).

Cosner, J. et al. Fungal endophytes. Curr. Biol. 35, R904–R910 (2025).

Petrini, O. Fungal endophytes of tree leaves. in Microbial Ecology of Leaves (eds Andrews, J. H. & Hirano, S. S.) 179–197 (Springer, 1991).

Rodriguez, R. J., White, J. F., Arnold, A. E. & Redman, R. S. Fungal endophytes: diversity and functional roles. New Phytol. 182, 314–330 (2009).

Strobel, G. A. Endophytes as sources of bioactive products. Microbes Infect. 5, 535–544 (2003).

Stone, J. K., Bacon, C. W. & White, F. An overview of endophytic microbes: endophytism defined. in Microbial Endophytes 1–28 (CRC Press, 2000).

Arnold, A. E., Maynard, Z., Gilbert, G. S., Coley, P. D. & Kursar, T. A. Are tropical fungal endophytes hyperdiverse? Ecol. Lett. 3, 267–274 (2000).

Schulz, B. & Boyle, C. The endophytic continuum. Mycol. Res. 109, 661–686 (2005).

U’Ren, J. M., Lutzoni, F., Miadlikowska, J., Laetsch, A. D. & Arnold, A. E. Host and geographic structure of endophytic and endolichenic fungi at a continental scale. Am. J. Bot. 99, 898–914 (2012).

Martin, F. M., Uroz, S. & Barker, D. G. Ancestral alliances: plant mutualistic symbioses with fungi and bacteria. Science 356, eaad4501 (2017).

Strullu-Derrien, C., Selosse, M.-A., Kenrick, P. & Martin, F. M. The origin and evolution of mycorrhizal symbioses: from palaeomycology to phylogenomics. New Phytol. 220, 1012–1030 (2018).

World Bank. World Bank Country and Lending Groups https://datahelpdesk.worldbank.org/knowledgebase/articles/906519 (2025).

Hawksworth, D. L. & Lücking, R. Fungal diversity revisited: 2.2 to 3.8 million species. Microbiol. Spectr. 5, 79–95 (2017).

Lambert, A. & Casagrande, R. No evidence of fungal endophytes in native and exotic Phragmites australis. Northeast. Nat. 13, 561–568 (2006).

Wirsel, S. G. R., Leibinger, W., Ernst, M. & Mendgen, K. Genetic diversity of fungi closely associated with common reed. New Phytol. 149, 589–598 (2001).

Angelini, P. et al. The endophytic fungal communities associated with the leaves and roots of the common reed (Phragmites australis) in Lake Trasimeno (Perugia, Italy) in declining and healthy stands. Fungal Ecol. 5, 683–693 (2012).

Clay, K., Shearin, Z., Bourke, K., Bickford, W. & Kowalski, K. Diversity of fungal endophytes in non-native Phragmites australis in the Great Lakes. Biol. Invasions 18, 2703–2716 (2016).

Rosenthal, R. The “file drawer problem” and tolerance for null results. Psychol. Bull. 86, 638–641 (1979).

Myers, N., Mittermeier, R. A., Mittermeier, C. G., da Fonseca, G. A. & Kent, J. Biodiversity hotspots for conservation priorities. Nature 403, 853–858 (2000).

Seneviratne, S. I. et al. Weather and climate extreme events in a changing climate. in Climate Change 2021: The Physical Science Basis (eds Masson-Delmotte, V. et al.) 1513–1766 (Cambridge Univ. Press, 2021).

Tedersoo, L. et al. Global diversity and geography of soil fungi. Science 346, 1256688 (2014).

Newman, D. J. & Cragg, G. M. Natural products as sources of new drugs over the 30 years from 1981 to 2010. J. Nat. Prod. 75, 311–335 (2012).

Bertini, L. et al. Biodiversity and bioprospecting of fungal endophytes from the Antarctic plant Colobanthus quitensis. J. Fungi 8, 979 (2022).

Põlme, S. et al. FungalTraits: a user-friendly traits database of fungi and fungus-like stramenopiles. Fungal Divers. 105, 1–16 (2020).

GBIF. GBIF Home Page https://www.gbif.org (2025).

Raasveldt, M. & Mühleisen, H. DuckDB: an embeddable analytical database. in Proc. 2019 Int. Conf. Manag. Data 1981–1984 (ACM, 2019).

R Core Team. R: A language and environment for statistical computing https://www.R-project.org/ (2021).

Wickham, H. ggplot2: Elegant Graphics for Data Analysis (Springer, 2016).


## Author Contributions
B.B. conceived the study, designed the methodology, performed the data analysis and machine learning, and wrote the manuscript. N.M., N.C.J. and C.A.G. contributed to the final manuscript text. All authors read and approved the final manuscript.

## Competing Interests
The authors declare no competing interests.

## Funding Statement
This work was supported by National Science Foundation (NSF)  MacroSystems grant DEB-1340852 (C.A.G.), US Department of Energy program in Systems Biology Research to Advance Sustainable Bioenergy Crop Development (DE-FOA-0002214)(N.C.J.), the Lucking Family Professorship (C.A.G.), the ARCS Foundation (B.M.B.), the Presidential Fellowship Program at NAU (B.M.B.), the Arizona Mushroom Society (B.M.B.), the Support for Graduate Students program at NAU (B.M.B.), and the American Association of University Women’s American Dissertation Fellowship (B.M.B.).

## Data and Code Availability
The full code for the data analysis pipeline, including all R scripts used for machine learning, validation, and figure generation, is available at [GitHub/Zenodo DOI]. The final abstract dataset and model outputs generated during this study are available at [Zenodo/Dryad DOI].


## Supplementary Methods

### 1. Data Sourcing and Deduplication
The initial abstract corpus was generated by querying three major bibliographic databases: Web of Science (WoS), Scopus, and PubMed on August 14, 2025.

Final Search Query: The search string was designed to capture fungal endophyte research broadly. The exact Boolean query used was:
`TITLE-ABS-KEY(("fungal endophyte" OR "fungal endophytes" OR "endophytic fungus" OR "endophytic fungi" OR "latent fungus" OR "latent fungi" OR "systemic fungus" OR "systemic fungi" OR "internal fungi" OR "resident fungi" OR "seed-borne fungi" OR "seed-transmitted fungi" OR "dark septate endophyte" OR "dark septate fungi" OR "DSE fungi") AND (plant* OR moss* OR bryophyte* OR liverwort* OR hornwort* OR fern* OR lycophyte* OR pteridophyte* OR tree* OR forest* OR shrub* OR grass* OR graminoid* OR herb* OR crop* OR seedling* OR sapling* OR seed* OR root* OR leaf* OR foliage OR shoot* OR stem* OR twig* OR rhizome* OR thallus OR frond* OR algae OR "green alga*" OR macroalga* OR "red alga*" OR "brown alga*" OR hydrophyte* OR kelp OR seaweed* OR seagrass* OR cyanobacteria OR cyanobiont* OR photobiont* OR lichen*)) AND DOCTYPE(ar)`

This process yielded a combined dataset of 41,154 abstracts from the three sources (WoS: 14,855; Scopus: 15,426; PubMed: 10,873). This corpus was subjected to a rigorous, multi-stage deduplication pipeline:

1.  Standardization of column names (e.g., Title, Abstract, DOI) across sources.

2.  Deduplication by DOI, reducing the set to 23,321 abstracts.

3.  Deduplication by normalized (to lowercase) abstract text, reducing the set to 23,007 abstracts.

4.  Filtering to include "Article" document types only, reducing the set to 22,587 abstracts.

5.  Final deduplication by normalized (to lowercase) title, resulting in the 21,891 abstract dataset that was fed into the ML pipeline. To ensure our training data was representative of this full corpus, we compared the publication year distributions of the manually curated training set against the full dataset (Supp. Fig. 5). This confirmed that our training data was not temporally biased.

Corpus Assembly Statistics:

| Curation Stage | Initial Records ($N$) | Final Records ($N$) | Records Removed ($\Delta N$) | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| 1. Initial Combination & Abstract Filter | 41,154 (WoS: 14,855; Scopus: 15,426; PubMed: 10,873) | 40,776 | 378 | Removed records with missing or empty abstracts. |
| 2. DOI Deduplication | 40,776 | 23,321 | 17,455 | Most stringent match; prioritized WoS/Scopus/PubMed record. |
| 3. Abstract Text Deduplication | 23,321 | 23,007 | 314 | Normalized text match for records without DOIs. |
| 4. Document Type Filter | 23,007 | 22,587 | 420 | Restricted analysis to Article types only. |
| 5. Title Deduplication (Final Corpus) | 22,587 | 21,891 | 696 | Final check using normalized title text. |

### 2. ML Classification Pipeline
The 21,891 abstracts were processed by a two-stage machine learning pipeline. To ensure the models could distinguish true biological claims from ambiguous statements, this training set included not only clear 'Presence' and 'Absence' examples, but also 'Both' (mixed results, n=117) and 'Other' (irrelevant/ambiguous, n=180) classes. We employed synthetic data augmentation to balance these classes and compensate for the extreme rarity of 'Absence' claims in the literature.

* Relevance Classification: The first stage classifier filtered the corpus for scope. We rigorously defined 'Irrelevant' as any abstract that failed to meet our inclusion criteria for primary fungal endophyte ecology. Specifically, the 'Irrelevant' class included: (1) secondary literature (reviews, perspectives, book chapters); (2) studies focused exclusively on bacterial, viral, or insect symbionts; (3) research on mycorrhizae lacking a distinct endophyte component; and (4) purely agronomic or chemical studies (e.g., bioprospecting assays) that did not report host or fungal taxonomic data. 

The initial relevance classification stage used a regularized logistic regression (glmnet) to filter the corpus of 21,891 abstracts for primary literature relevant to fungal endophytes. Using 5-fold cross-validation on the manually curated training set, the model achieved an Overall Accuracy of 0.895 and a Sensitivity (Recall) for the 'Relevant' class of 0.976. This high sensitivity was critical to ensure the first filter retained the vast majority of true endophyte-focused studies, preventing the loss of relevant data from the corpus before the final analysis. The Specificity (correctly identifying 'Irrelevant' abstracts) was 0.674, which is an acceptable trade-off for maximizing the recall of the primary, 'Relevant' literature. An irrelevant abstract was defined as a non-primary literature article that did not discuss fungal endophytes. Common examples were abstracts that discussed only bacterial endophytes or review papers. This step resulted in 19,447 abstracts classified as relevant.

* Presence/Absence Classification: The training dataset for the second stage consisted of 505 relevant abstracts (80% split). The class distribution for the "Absence" category was initially critically low (n=1 verified true absence). To enable model training, we first performed text-based data augmentation by generating synthetic abstracts representing plausible absence claims (manually and via large language models), raising the "Absence" class count to 94.

Despite this augmentation, the dataset remained imbalanced (Presence: 411, Absence: 94). To fully mitigate classification bias toward the dominant Presence class, we subsequently applied the Synthetic Minority Oversampling Technique (SMOTE) to the feature vectors (Document-Term Matrix). This resulted in a final, perfectly balanced training set of 822 abstracts (411 for each class).

The models were trained on a Document-Term Matrix (DTM) composed of 7,492 unique features (Unigrams and Bigrams) extracted from the abstract text. The large-scale application to the full corpus involved creating a sparse DTM with 120,245 features, which was processed in 1,000-document chunks and employed sparse matrix techniques (e.g., unigram sparsity of 99.1%) for memory efficiency.

This corpus was classified using a custom-weighted ensemble of a `glmnet` model and a linear-kernel Support Vector Machine (`svmLinear`). As documented in our model testing, this ensemble allowed us to prioritize absence detection. The final model applied a weight of 0.6 to the SVM's "Presence" prediction and 0.8 to the `glmnet` "Absence" prediction. All models were validated using 5-fold cross-validation. Two distinct models were trained and cross-validated on the balanced dataset: Support Vector Machine with a Linear Kernel (svmLinear) and Regularized Logistic Regression (glmnet). The svmLinear model demonstrated superior ability to detect studies reporting fungal presence, achieving a Presence Recall of 0.980 (Sensitivity). Conversely, the glmnet model achieved a superior Absence Recall of 0.913 (Specificity). To optimize performance for the rare Absence class while retaining high confidence in Presence classification, we implemented a weighted probability ensemble. This strategy combines the prediction probabilities of the two models using the following weights:
  
  Weight for svmLinear Presence prediction: 0.6

  Weight for glmnet Absence prediction: 0.8

This approach ensures that a high probability of Absence from the glmnet model, which excels at this detection, is strongly favored, thus creating a high-confidence screening tool for our critical class of interest. The optimized threshold for the combined ensemble achieved an Overall Accuracy of 0.872 with a Presence Recall of 0.882 and an Absence Recall of 0.826 on the test set (at a threshold of 0.7).

### 3. Ubiquity Statement Analysis
To quantify the status of the 'ubiquity paradigm,' we computationally screened the 19,447 relevant abstracts for explicit statements of ubiquity (e.g., 'endophytes are ubiquitous'). This analysis found that only 38 abstracts (0.2%) contained such a claim. This scarcity confirms that ubiquity functions as a silent axiom in the primary literature: it is almost never treated as a novel result to be reported in an abstract, but rather as an established premise typically reserved for the introduction sections of full texts.

### 4. Computational Optimization & Pipeline
The pipeline was engineered for high-throughput and robust processing of large text datasets.

* Error Handling: The pipeline featured a robust error handling system, including "safe execution wrappers" and data recovery from backups, to prevent catastrophic failures during long-running processes.

* Memory Optimization: We employed memory-efficient techniques, such as chunked processing of large files (1,000-document batches), data structure optimization (e.g., converting strings to factors), and aggressive garbage collection, to ensure the pipeline could run on standard hardware.

* Optimized Lookups: We used hash-table optimization and pre-computed lookup tables for O(1) (instant) lookups of species names.

* Bloom Filters: We implemented DuckDB-based bloom filters for probabilistic pre-filtering [@raasveldt_duckdb_2019], which allowed the pipeline to instantly reject 80-90% of non-matching taxonomic strings, dramatically reducing expensive validation queries.

### 5. Modular Extraction Pipeline
The data extraction pipeline was built as a series of modular, independent components.

The extraction components demonstrated high fidelity, successfully detecting plant and fungal species in 82.2% (15,940) of the 19,447 relevant abstracts and plant tissue information in 75.5% of abstracts.

1.  Species & Mycorrhizal Extraction: The first component extracted all plant and fungal taxonomic names and classified fungi for mycorrhizal status (Supp. Fig. 6).

2.  Mycorrhizal-Only Filtering: A dedicated script assessed abstracts and flagged those containing *only* mycorrhizal fungi for exclusion. Starting with 19,447 unique abstracts (the full relevant corpus input into the P/A DTM creation), we systematically removed abstracts that reported mycorrhizal associations to avoid confounding the endophytic signal. This involved a multi-step filter targeting rows classified as `is_mycorrhizal` or belonging to the phylum Glomeromycota. This rigorous filtering resulted in the final corpus of 19,199 relevant, abstracts excluding those solely focused on mycorrhizae used for all subsequent analyses.

3.  Component Extraction: Subsequent components ran on the filtered abstract list to extract research methods (e.g., culture, molecular), plant tissues (e.g., stem, leaf, bark, root) (Supp. Fig. 7), and geographic locations.

4.  Final Aggregation: A final script merged the outputs from all components into a single comprehensive dataset.

### 6. Pipeline Performance and Visualization

* Profiling: The pipeline's performance was comprehensively profiled, confirming a high throughput of ~100-500 abstracts/second.

* Visualization: All data visualizations were generated in R using `ggplot2`, employing custom, colorblind-friendly palettes and themes to ensure accessibility and consistency ([@r_core_team_r_2023]; [@wickham_ggplot2_2016]).

### 7. Code Reproducibility
The codebase includes a comprehensive framework to ensure validation and reproducibility, including scripts to generate representative test subsets and "quick start" test scripts to automatically execute the entire pipeline on these subsets.

### 8. Detailed Validation Protocols

* Extraction Validation Suite: The data extraction components were validated using a comprehensive, automated test suite (`test_extract_species.R`) that evaluated "core functionality, accuracy, performance, and robustness." The pipeline achieved a weighted "Overall score" of 91.4%, passing all 10 test categories.

* Manual Classification Validation: We validated our ML classification in two ways. First, we reviewed 100% of all 'Absence' candidates. Second, to estimate the 'Absence' False Negative Rate (i.e., 'Absence' abstracts misclassified as 'Presence'), we manually reviewed a stratified random sample of 77 abstracts that the model had classified as 'Presence'. This review confirmed that 0 of the 77 abstracts were genuine 'Absence' cases, supporting the robustness of our primary finding.

### 9. Detailed Absence Validation Results
The high-sensitivity screening pipeline identified 102 candidate abstracts for manual validation (89 from the ML model, 12 from the string search, 1 from training). Manual expert review of these 102 abstracts yielded the following:

* 46 'Presence': Simple false positives (the abstract only reported presence but was incorrectly flagged as 'Absence' by the model).

* 15 'Both': Abstracts that reported mixed results (e.g., presence in leaves, absence in roots). These are considered 'Presence' at the taxon level.

* 40 'Irrelevant': Abstracts irrelevant to this study (e.g., bacterial endophytes).

* 1 'Absence': A single study-level report of non-detection (Lambert & Casagrande, 2006).
This validation confirmed zero verifiable taxon-level absences in the corpus.

## Supplementary Figures

![Supp. Fig. 1: Genus representation by plant phylum. Proportion of described genera represented in the corpus, broken down by plant phylum.](C:/Users/beabo/OneDrive%20-%20Northern%20Arizona%20University/NAU/Endo-Review/plots/main/plantae_genus_representation_main_by_phylum_percent.png)

![Supp. Fig. 2: Family representation by phylum (plants). Proportion of described families represented in the corpus, by plant phylum.](C:/Users/beabo/OneDrive%20-%20Northern%20Arizona%20University/NAU/Endo-Review/plots/main/plantae_family_representation_main_by_phylum_percent.png)

![Supp. Fig. 3: Top countries by study count. Bar plot of the top 20 countries by number of geographically coded studies; United States, China, South Africa, India, and Brazil are highest.](C:/Users/beabo/OneDrive%20-%20Northern%20Arizona%20University/NAU/Endo-Review/plots/main/top_countries.png)

![Supp. Fig. 4: Combined detection methods overview. Relative and absolute counts of method types (molecular, culture-based, microscopy/visual) across studies that reported methods.](C:/Users/beabo/OneDrive%20-%20Northern%20Arizona%20University/NAU/Endo-Review/plots/main/methods_combined_core.png)

![Supp. Fig. 5: Distribution of publication years in the training dataset.](C:/Users/beabo/OneDrive%20-%20Northern%20Arizona%20University/NAU/Endo-Review/plots/training_publication_years.png)

![Supp. Fig. 6: Fungal species representation by phylum. Percent of described fungal species represented in the dataset by fungal phylum.](C:/Users/beabo/OneDrive%20-%20Northern%20Arizona%20University/NAU/Endo-Review/plots/main/fungi_species_representation_main_by_phylum_percent.png)

![Supp. Fig. 7: Plant tissue frequency in the dataset. Frequency distribution of plant parts (leaf, root, stem, etc.) reported across the 19,447 relevant-abstract corpus.](C:/Users/beabo/OneDrive%20-%20Northern%20Arizona%20University/NAU/Endo-Review/plots/main/plant_parts_frequency.png)