These reviews relate to the old_manuscript.md file.

NPH-MS-2025-54387 - Full Paper -  The Sparsely Sampled Ubiquity of Global Fungal Endophytes
by Bock, Beatrice; McKay, Nicholas; Johnson, Nancy; Gehring, Catherine

Dear Ms Bock,

Thank you for submitting your manuscript to New Phytologist. Your work has now been evaluated by three reviewers, whose comments appear below.While the reviewers recognized the timeliness of your research question and the ambition of applying machine learning to systematically assess gaps in endophyte research, they raised fundamental concerns about the analytical framework that prevent us from accepting this manuscript.

The central methodological issue, noted by all three reviewers, is the reliance on abstract-level text mining. This approach likely results in substantial underrepresentation of the relevant literature for several reasons: many studies do not name specific taxa in abstracts; fungi functioning as endophytes are frequently classified under other functional groups (e.g., mycorrhizal fungi) in databases and literature; and geographic information is often absent from abstracts (as Reviewer 1 notes, Panama appears as "zero studies" despite decades of research at the Smithsonian Tropical Research Institute, including work you cite in the main text).

Reviewer 3 also raised important questions about how your pipeline handles taxonomic and nomenclatural changes—a significant challenge given the shifting classification of major fungal groups—and whether the identification methods reported in source studies (many relying solely on isolation or microscopy) were considered as indicators of data reliability.Beyond the methodological concerns, the reviewers questioned whether the findings advance our understanding of endophyte biology.

As Reviewer 2 observed, the study remains largely technical, focusing on pipeline development and bibliometric patterns rather than functional ecology or plant–fungus interactions. Reviewer 1 noted that the core findings—that most plant species remain unstudied and that research is concentrated in North America and Europe—will not surprise those familiar with the literature.I recognize that addressing these concerns would require substantial additional work, including full-text analysis of a refined dataset and deeper engagement with fungal functional ecology.

I am therefore unable to accept this manuscript for publication.I hope the reviewers' detailed comments prove useful as you develop this work further, whether for resubmission here or elsewhere.

Sincerely,
Francis Martin
Editor, New Phytologist


*****************************************************************
In any correspondence regarding this manuscript, please include the manuscript reference number and copy the correspondence to New Phytologist Central Office (np-managinged@lancaster.ac.uk).

Decision: Reject

Referee: 1

Comments to the Author
This manuscript describes a review that used machine learning to search abstracts of published literature for information about fungal endophyte studies. It is well written and easy to follow the ideas. 
Major comments:
(1)     I think that more of an emphasis should be put on the limitation that only abstracts were searched. I believe that would miss a lot of information in papers that only describe endophyte absence in the main text. It was unclear if the manual check involved going beyond the abstract to read the main text, and that manual check only happened for ~102 papers.
(2)     Most people who know the fungal endophyte literature will not be surprised at all by the results, that we have barely scratched the surface on the host plants and that most studies have been in North America or Europe. Thus, a novel method is used but the findings are not novel.


Minor comments

In Figure 2, Panama is “gray” which equals zero studies. That is wrong, since many studies since the 1990s have occurred at the Smithsonian Tropical Research Institute. This includes studies that the authors cite in the main text (i.e., Arnold & Lutzoni 2007). Thus, many other studies may have been missed because their country was not included in the abstract.


Referee: 2

Comments to the Author
see Attached pdf file and below

The study by Bock et al. is timely, as there is a substantial publication gap in endophytic fungal research, particularly regarding their ecological roles. The authors hypothesis contrasting the Global South and Global North is very interesting and effectively highlights geographic disparities in endophyte research, as well as the striking estimate that 99.2% of plant species remain unexplored for endophytic fungi. However, the analytical framework underlying this conclusion is problematic. The authors pipeline relies predominantly on abstract-level text mining, which is an oversimplified approach for endophytic research. Endophytic fungi cannot be reliably identified or distinguished based on terminology used in abstracts alone. A substantial proportion of fungi that function as endophytes are frequently classified in the literature and in global fungal databases as mycorrhizal fungi or other functional groups. By restricting the analysis to studies that explicitly use the term “endophyte” in the abstract, the authors likely exclude a large body of relevant literature, leading to a systematic underrepresentation of endophytic diversity and function. While I understand that resolving fungal misclassification and functional overlap is a complex and time-consuming task, the current approach does not adequately engage with this challenge. As a consequence, the study remains largely technical, focusing on pipeline development and bibliometric patterns rather than on biological meaning. The reliance on abstracts severely limits the authors ability to draw robust conclusions about the ecological roles, functional traits, or plant associated significance of endophytic fungi. Importantly, neither the results nor the discussion provides fundamental new knowledge  into the biological functions of endophytic fungi in a plant context. Given the scope and audience of New Phytologist, the lack of functional interpretation significantly weakens the manuscript. Without a deeper integration of fungal biology, functional ecology, and plant–fungus interactions, the study falls short of advancing conceptual understanding of endophytism, despite its ambitious global framing.

Referee: 3

Comments to the Author
The main goals of the manuscript are to study whether endophytic fungi are ubiquitous and, to test this, the Authors developed a machine-learning pipeline to screen abstracts of scientific papers. A comprehensive analysis of the literature on endophytes might help us better understand their presence and the potential phylogenetic bias of endophyte colonization.
While reading the manuscript (ms), I found some fundamental issues that are not clear in its present form:
Plant microbiomes generally and commonly harbor fungal members; in the absence of symptoms, these could be considered endophytes. The study attempts to identify papers, based on their abstracts, that consider these endophytic fungi, aiming to study and identify these partners. Thus, it relies on the existence, spread, and interpretation of the term “endophyte”.
If I understood correctly, the screening focused solely on abstracts, which is extremely limited. The Authors also emphasize that, because of the methods applied, the findings should naturally be underestimations. Nevertheless, since abstracts in many cases do not list taxa (or all taxa screened/identified), there might be differences of even an order of magnitude at the species level. For example, the seminal paper of Arnold and Lutzoni (2007) mentioned only one taxonomic group in its abstract (Ascomycota). I agree with the Authors (L222–225) that it is almost certain that the vast majority of land plants have not been studied.
The main aims are to study the taxonomic and geographic distribution of reports on endophytic fungi. Regarding the former, the Authors focus on both plant/host and fungal taxonomy. Nevertheless, it is not entirely clear how this was carried out. Besides the problem mentioned above, how did the pipeline and data extraction handle significant changes in taxonomy and nomenclature? How were the data treated? A species can be assigned to higher taxonomic ranks; however, this does not work in the reverse direction. This is probably less problematic in the case of plants, as many papers or case studies focus on one or a few plant species. However, it might be a serious issue in the case of fungi. Just one example—which is from mycorrhizal research but illustrates the question—and how the study handled this group: fungi forming arbuscular mycorrhizae are grouped in a distinct taxonomic group. This group once belonged to Zygomycota, Glomales/Glomerales, later Glomeromycota, and now Mucoromycota (Glomeromycotina) according to many studies. Were these problems considered, and if so, how?
It is a very interesting part of the study when the applied methods are filtered. Nevertheless, were these data used for quality control, as indicators of data reliability? For example, studies using solely isolation and/or microscopy (a large proportion according to the figures) cannot be considered reliable sources of fungal species-level data. Fungal species identification (and in many cases even higher taxonomic ranks) based on culture characteristics should be treated with extreme caution.
Although the study aims to screen the ubiquitous nature of endophyte presence, it does not discuss whether there are possible differences in colonization of a given plant species across different habitats.
The study discusses overall fungal diversity and missing fungal species. Nevertheless, there is no correction of species estimates specifically for endophytes. I understand that one of the reasons is unstudied plant diversity and/or geographic regions; however, the discussion in Lines L197–205 is slightly misleading if only plant species numbers are used. There is no calculation assessing whether there is a change (and/or difference between North and South) in plant-to-fungal ratios, which was a key figure in some estimates. It seems that there may be a degree of specificity (see, e.g., Rodriguez et al. 2009) regarding which plant organs are colonized. Did the Authors examine whether increasing the number of plant species studied increases the number of fungal species colonizing a given organ? Without such analyses, increasing the number of plant species studied would inevitably increase the number of fungal species if species specificity exists, which does not appear to be a general rule for endophytes.
L125–126: What is the rationale or justification for applying this grouping?
L172: Why were countries used (also at L259)? How can a country be considered a sampling unit instead of a geographic, biogeographic, regional, and/or habitat-based unit? I understand that this is a practical way to filter studies; nevertheless, it could be misleading, especially when large countries representing very different biomes are considered. Habitats or biomes are more commonly used when sampling is planned than countries.
L226–231: This is an extremely important point; our overall bias toward positive results would deserve a deeper discussion.
L242: What are “soil guilds”?
L245: This is one factor; however, plant genotype has a major influence on endophyte diversity (see, e.g., Bálint et al. 2013, PLoS One). This is an extremely important point when a taxon-based discussion attempts to understand endophyte diversity.
L253: It is not clear why bioactivity is mentioned here—it has no ecological meaning. It may highlight the potential usefulness of metabolites from hidden fungal diversity; nevertheless, there are comprehensive papers on this topic.
SuppL93–94: Was it tested whether introductions discussed ubiquity?
SuppL114–115: How were fungal taxa linked to mycorrhizal status, especially in the case of ericoid and orchid fungi?
SuppL121: See above regarding the problems of taxonomic assignments.
SuppL124–126: How were shoots handled (stem + leaves)?
SuppL164–165, 167–168: Strong representation, but this might be misleading when taxa with orders-of-magnitude differences are presented. In the case of fungi, see the comments above on taxonomic identification.
SuppL177–178: See the comments above regarding identification methods.
Overall, the idea of applying a machine-learning pipeline to screen and filter a massive dataset of scientific literature is interesting. Presenting geographic and plant taxon biases could be valuable, as could a structured critical analysis of the methods applied and the diversity found. Applying quality control (see above) and using full-text searches on a narrowed dataset would help to avoid most of the problems listed above. I also recommend discussing the general literature on fungal endophytes in more detail, particularly regarding their diversity and distribution.


The study by Bock et al. is timely, as there is a substantial publication gap in endophytic fungal
research, particularly regarding their ecological roles. The authors hypothesis contrasting the
Global South and Global North is very interesting and effectively highlights geographic disparities
in endophyte research, as well as the striking estimate that 99.2% of plant species remain
unexplored for endophytic fungi.
However, the analytical framework underlying this conclusion is problematic. The authors pipeline
relies predominantly on abstract-level text mining, which is an oversimplified approach for
endophytic research. Endophytic fungi cannot be reliably identified or distinguished based on
terminology used in abstracts alone. A substantial proportion of fungi that function as endophytes
are frequently classified in the literature and in global fungal databases as mycorrhizal fungi or
other functional groups. By restricting the analysis to studies that explicitly use the term
“endophyte” in the abstract, the authors likely exclude a large body of relevant literature, leading
to a systematic underrepresentation of endophytic diversity and function.
While I understand that resolving fungal misclassification and functional overlap is a complex and
time-consuming task, the current approach does not adequately engage with this challenge. As a
consequence, the study remains largely technical, focusing on pipeline development and
bibliometric patterns rather than on biological meaning. The reliance on abstracts severely limits

the authors ability to draw robust conclusions about the ecological roles, functional traits, or plant-
associated significance of endophytic fungi.

Importantly, neither the results nor the discussion provides fundamental new knowledge into the
biological functions of endophytic fungi in a plant context. Given the scope and audience of New
Phytologist, the lack of functional interpretation significantly weakens the manuscript. Without a
deeper integration of fungal biology, functional ecology, and plant–fungus interactions, the study
falls short of advancing conceptual understanding of endophytism, despite its ambitious global
framing.