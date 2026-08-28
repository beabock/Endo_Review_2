# Rubric — how to fill the judgement columns

Keep this open beside the workbook. Always record **what the paper reports at the reading
stage you're on** (abstract, or full text), not what you know about the taxon in general.

Dropdowns are suggestions — if the right answer isn't listed, **type it into the cell**
(Excel warns but keeps it).

---

## `paper_reviewed` — set this when you finish a row; it decides what else you fill

| value | when | then fill… |
|---|---|---|
| **complete** | the paper reports its own primary fungus-from-plant data | the whole row |
| **could not access the paper (full text needed)** | a `full text` row where you couldn't get the PDF | nothing else — stop there |
| **review or secondary compilation — no primary data of its own** | a review, opinion, methods commentary, meta-analysis, or database paper that discusses endophytes but reports no fungus the authors themselves found | **Q1 = no · Q3 = review · Q4 (language)**. Leave Q2, Q5–Q11, the method ticks, and every interaction block **blank**. (Optionally note the review's topic in the summary column.) |
| **not a fungus-in-plant study** | wrong topic entirely — no plant, wrong organism, etc. | **Q1 = no**. Leave everything else blank. |

**A blank `paper_reviewed` = you have not done that row yet.**
For a `complete` row, use the "not stated" / "unclear" option where a paper is silent —
only leave a cell truly blank in unused interaction blocks.

Why reviews and compilations get flagged rather than filled: the software *did* pull
taxa and hosts out of them (they cite plenty), so they're likely **false positives** for
the extraction. Flagging them is exactly the measurement we want.

---

## The paper-level questions

**Q1 — does this paper report a fungus coming from a plant?**
`yes` if the paper isolated, detected, or observed at least one fungus *in or on* a living
plant. `no` if it's the wrong organism, there is no plant host, or no fungus–plant
association is reported at all. `unclear` as a last resort.
- A natural-products paper that isolates compounds *from* an endophyte is still `yes` (its
  purpose goes in Q2).
- A **review / compilation** that discusses endophytes but reports no fungus the authors
  found themselves → `no`; set `paper_reviewed = review or secondary compilation` and
  follow that row of the table above.

**Q2 — paper's main purpose** (single choice; pick the one the abstract leads with)
| value | e.g. |
|---|---|
| endophyte ecology / diversity / community | isolating/surveying endophytes of a host or region, community composition, biogeography, temporal change |
| endophyte function: growth, nutrition, or stress tolerance | inoculation studies of biomass, yield, drought/salt/metal/heat tolerance, nutrient uptake, hormones |
| endophyte function: disease protection / biocontrol | endophyte-mediated resistance to pathogens or pests; developing a biocontrol agent |
| natural products / secondary metabolites / bioprospecting | screening endophyte extracts for bioactive / antimicrobial / anticancer compounds, enzymes |
| plant pathology (the fungus studied as a pathogen) | the paper is about disease caused by the fungus |
| fungal taxonomy / systematics / new species | describing / revising taxa, phylogeny |
| genomics / transcriptomics / methods development | a genome/transcriptome paper, or a new isolation/detection method |
| other (type it) | anything else — type it |

**Q3 — how were the fungi obtained in this paper?** (single choice)
one or a few isolates (named) · culture survey (many isolates, named) · community
metabarcoding/NGS (OTU/ASV table) · direct observation only (microscopy/histology, no
isolation or sequencing) · **mixed methods (type which)** — after choosing this, type the
combination, e.g. "mixed: culture + metabarcoding" ·
**review / synthesis / secondary compilation — no new fungi obtained here** (set
`paper_reviewed` to match — see the table above) · other (type it) · unclear.
The method tick columns (`m_`) record the detail for the non-review cases.

**Q4 — language of the text you are reading on this row.** Answer for the reading stage.
- English abstract of a French paper → `English` on the `abstract` row, `French` on the
  `full text` row.
- **Bilingual abstract** (e.g. given in both English and Spanish) → `English + non-English`
  on the `abstract` row.
- English abstract but the paper body is another language → `English + non-English` on the
  `full text` row (and note the body language).
Type the specific language after choosing `non-English (type which)`.

**Q5 — any sequence-only (uncultured) taxa?** `yes` if any reported fungi were detected
**only by DNA sequencing, never cultured** (OTUs, ASVs, clone sequences).

**Q6 — strain-level variation noted?** `yes - noted` if the paper says different
strains/isolates of one species behaved differently. `only one strain / isolate studied`
if there was nothing to compare. `no - not noted` otherwise.

**Q7 — where was the plant SAMPLED?** The place the plant material was **collected** —
country, plus state/province/region if the paper gives it (don't go hunting). If the paper
does not say where sampling was done, write **"not stated"**.
**Never put the authors' institution / affiliation country here.** Q7 is *only* the
sampling location.

**Q8 — what geographic information does the paper contain?**
- `sampling location is explicitly stated` — Q7 has a real answer from the text
- `sampling location is inferable from a named field site / region` — e.g. a named forest
  or reserve you can place on a map
- `no sampling location - only the authors' institutional country is given` — the paper
  only tells you where the authors are (this is the case Referee 2 is worried about)
- `no geographic information at all`

If Q7 = "not stated" and you can see the authors' affiliations, that is
`no sampling location - only the authors' institutional country is given` — do **not**
move the affiliation into Q7.

**Q9 — biome (WWF category).** Best match for where the plant was growing / was sampled,
from the WWF terrestrial biome scheme (Olson et al. 2001). If a study spans more than one,
list them comma-separated. Guidance:
- **cultivated grassland** (sown pasture, hayfield, managed lawn) → `agriculture / cultivated`.
  Natural / semi-natural grassland, steppe, prairie → `temperate grassland / steppe / prairie`.
- **forest** — pick by climate, not tree density: tropical/subtropical humid →
  `tropical / subtropical moist forest`; temperate, boreal, or a plantation →
  `temperate or boreal forest`; seasonally dry tropical → `tropical / subtropical dry forest`.
- **estuary / salt marsh** (not mangrove) → `wetland / flooded grassland / bog` or `marine / coastal`.
- greenhouse / pot experiment with no field component → `greenhouse / growth chamber`.
- none fit → `other (type it)` and type it.

**Q10 — how many distinct fungus-host pairs?** A number, including any you summarise in
the NGS column.

**Q11 — was the surface-sterilisation checked?** The classic endophyte QC (Referee 3):
did the paper *verify* that surface fungi were removed, e.g. by plating the final rinse
water, pressing sterilised tissue onto agar (tissue imprint), or a similar control?
- `yes - a control was done`
- `no - standard sterilisation, no check described`
- `not a culture-based study` — e.g. metabarcoding-only, or microscopy-only
- `cannot tell from the text`
(Whether the fungus was also confirmed *inside* by microscopy or resynthesis is already
captured by the "microscopy in tissue" / "resynthesis / re-inoculation" method ticks.)

---

## Method tick columns (the purple block) — put `yes` in every one that applies

| column header | tick `yes` when the paper… |
|---|---|
| `culture from sterilised tissue` | surface-sterilised tissue, plated it, grew fungi out |
| `microscopy in tissue` | showed hyphae *inside* tissue by staining / sectioning / confocal / TEM (covers "histology") |
| `direct sequencing from tissue` | sequenced fungal DNA straight from tissue — metabarcoding, clone libraries (no culturing step) |
| `isolate ID by sequencing` | Sanger / ITS-sequenced the *cultured isolates* to identify them |
| `resynthesis / re-inoculation` | re-inoculated a sterile plant with an isolate and re-isolated it |
| `method not stated` | the paper doesn't say how endophytism was shown |

Whether the sterilisation was *checked with a control* goes in Q11, not here.

---

## Interaction blocks — one per DISTINCT fungus × host-plant pair the paper NAMES

Each block: `fungus` · `host_plant` · `tissue` · `fungal_lifestyle` · `effect_on_host` ·
`evidence_basis`.

- Fill blocks only for taxa the paper **names**. For a metabarcoding community, name the
  dominant few and summarise the rest in `extra_pairs_or_NGS_community_summary`.
- **`fungus` / `host_plant` — copy the name exactly as the authors write it**, genus +
  species where they give it. If you happen to know the taxon has since been renamed,
  **still record the authors' name, not the current one.** Synonym resolution to current
  taxonomy is done programmatically afterwards; changing names by hand would corrupt that
  step. (Spelling fixes for obvious typos are fine.)
- **tissue** — if one fungus + host was found in more than one tissue, put them all in the
  one cell, comma-separated: `leaf, root`. Don't make a separate block per tissue. If the
  paper only says "shoots" / "aerial parts" without separating, record `leaf, stem`; only
  type `aerial parts (not separated)` if the tissues genuinely can't be told apart.

### `fungal_lifestyle` — how the fungus makes its living (trophic mode)

Values follow **FungalTraits `primary_lifestyle`** (Põlme et al. 2020, *Fungal Diversity*
105:1–16). FungalTraits' full plant-relevant list is: *foliar endophyte, root endophyte,
root endophyte-dark septate, plant pathogen, plant pathogen-biotroph/-hemibiotroph/
-necrotroph, arbuscular mycorrhizal, ectomycorrhizal, ericoid mycorrhizal, orchid
mycorrhizal, wood saprotroph, litter saprotroph, soil saprotroph, plant/unspecified
saprotroph, nectar/tap saprotroph, epiphyte, sooty mould, mycoparasite, lichenised,
lichen parasite.* We collapse the three endophyte types into one "endophyte" value (the
`tissue` column already records leaf vs root); the four mycorrhizal types are kept
**separate** (arbuscular / ecto / ericoid / orchid).

| value | use when the fungus is… |
|---|---|
| **endophyte (foliar, root, or dark-septate)** | living inside healthy tissue, no disease — the default for this literature |
| **latent pathogen / hemibiotroph** | symptomless now but the paper shows/states it turns pathogenic (later, under stress, on other hosts) |
| **plant pathogen** | causing disease in the studied interaction |
| **wood saprotroph** | decaying woody tissue |
| **litter saprotroph** | on fallen leaves / needle litter |
| **soil saprotroph** | free-living in soil (recovered from the root zone but not the plant) |
| **unspecified / other saprotroph** | dead/senescent plant tissue, type not specified |
| **arbuscular mycorrhizal** | an AM (Glomeromycota) root symbiont |
| **ectomycorrhizal** | an ECM root symbiont (sheath / Hartig net; e.g. *Russula*, *Cortinarius*, *Tuber*) |
| **ericoid mycorrhizal** | an ericoid symbiont of Ericaceae hair roots (e.g. *Rhizoscyphus ericae*) |
| **orchid mycorrhizal** | a symbiont of orchid roots / protocorms (e.g. *Tulasnella*, *Ceratobasidium*) |
| **mycoparasite / antagonist of other microbes** | attacking / suppressing other fungi or microbes |
| **epiphyte (surface only)** | on the plant surface, not inside |
| **lichenised** | part of a lichen |
| **context-dependent** | the paper says the lifestyle itself shifts with host/environment/strain |
| **not clear from the paper** | |

### `effect_on_host` — the net outcome for THIS host plant, as the paper reports it

| value | use when the paper… |
|---|---|
| **harmful to the plant** | reports disease, symptoms, reduced growth or fitness |
| **beneficial to the plant** | reports a **measured or clearly stated** benefit — growth, stress tolerance, defence, nutrition |
| **neutral / commensal** | **tested the plant's response** (growth, fitness, stress, defence) **and found no net effect** |
| **no visible symptoms; benefit or harm not tested** | says the plant looked healthy / "symptomless", but did not test for benefit or harm |
| **not reported** | says **nothing** about effect — just isolated / detected the fungus |
| **context-dependent** | outcome varies by host genotype / environment / strain |
| **unclear** | you genuinely cannot tell |

**Why lifestyle and effect are separate columns:** the same fungus can appear as a
`plant pathogen` lifestyle with `no visible symptoms` effect (a latent infection), or an
`endophyte` lifestyle that turns out `harmful`. Keeping them apart is the whole point of
the study — "endophytism is a location, not a fixed function."

The three "not obviously harmful" effects differ by **how much the paper checked**:

| | mentioned symptoms? | measured the plant's response? |
|---|---|---|
| **not reported** | no | no — "endophytic fungi were isolated from leaves" |
| **no visible symptoms, not tested** | yes ("symptomless endophyte") | no |
| **neutral / commensal** | usually | **yes** — and the effect was ~zero |

### `evidence_basis` — how the lifestyle AND effect you recorded were established

| value | use when… |
|---|---|
| **experimentally tested in this study** | inoculation / re-synthesis / knockout / a controlled assay |
| **observed / measured in this study (no manipulation)** | co-occurrence, community stats, expression, field observation of symptoms |
| **inferred from what the fungus usually does** | assigned from the genus/species name or a database, not data in this paper |
| **asserted with no support** | stated in passing, no evidence |
| **not stated** | |

---

## Worked examples

**1 — abstract, nothing tested.** *"Endophytic fungi were isolated from surface-sterilised
leaves of Espeletia; dominant taxa Xylaria sp. and Nigrospora sphaerica."*
→ Q1 yes · Q2 endophyte ecology · Q3 culture survey · Q7 Colombia · Q8 explicitly stated ·
Q9 montane grassland / alpine · Q11 no-check · tick `culture from sterilised tissue` ·
2 blocks, each: tissue leaf / lifestyle `endophyte` / effect `not reported` /
evidence `inferred from what the fungus usually does`.

**2 — full text, benefit tested.** Wheat inoculated with *Epichloë*, +22% biomass under drought.
→ Q3 one/few isolates · Q11 yes-check · tick `resynthesis / re-inoculation` · block 1:
*Epichloë* sp. / *Triticum aestivum* / whole plant / lifestyle `endophyte` /
effect `beneficial to the plant` / evidence `experimentally tested in this study`.

**3 — latent pathogen.** *"Diplodia sapinea recovered asymptomatically from Pinus shoots;
water-stressed inoculated seedlings developed shoot blight."*
→ block 1: *Diplodia sapinea* / *Pinus* sp. / stem-wood-bark /
lifestyle `latent pathogen / hemibiotroph` /
effect `no visible symptoms; benefit or harm not tested` (at sampling) /
evidence `experimentally tested in this study`. Note the stress result in the summary column.

**4 — metabarcoding.** *"ITS metabarcoding of Quercus robur leaves recovered 142 fungal
OTUs (38 genera); most abundant Cladosporium, Aureobasidium."*
→ Q3 community metabarcoding · Q5 yes · Q11 no-check · tick `direct sequencing from tissue` ·
block 1: *Cladosporium* / *Quercus robur* / leaf / lifestyle `endophyte` /
effect `not reported` / evidence `inferred...` · block 2: *Aureobasidium* / … ·
summary: *"142 OTUs / 38 genera from Q. robur leaves; asymptomatic foliar endophyte
community; no effect tested."*
