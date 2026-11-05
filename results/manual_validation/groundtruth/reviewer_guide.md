# Reviewer Guide: Fungal Endophyte Paper Check

Keep this guide beside you while you work. It explains every column in your Excel file. Words that may be unfamiliar are explained in the **glossary at the end** (section 11).

If anything is unclear, **ask Bea before guessing**. A question is always better than a guess.

---

## 1. What you are doing

We used a computer program to read thousands of papers about fungi living in plants. You are checking that program by reading some of the same papers yourself.

You will **not** see the program's answers. You just read each paper and record what it says. Your answers become the "correct answers" we compare the program against.

**The one rule that matters most:**

> **Record what the text says, not what you know.**
>
> If a paper only says "Espeletia", do not fill in a country because you know where Espeletia grows. If a paper calls a fungus an endophyte, record "endophyte" even if you know the genus has pathogens. If the text says "wheat", write "wheat", not the Latin name.

---

## 2. What you need

1. **Your Excel file.** Work in the **Review** tab.
2. **The folder of PDFs** (link in Bea's email). Each PDF has the same name as a row in your sheet. Row `K001b` goes with file `K001b.pdf`.
3. **This guide.**

**Work on your own.** Please don't discuss the papers with the other reviewers until everyone is finished. That is what makes the comparison fair.

---

## 3. How to do one row

Each row is one paper, read one way. Work left to right.

**Step 1. Look at column D (`text_type`).** It tells you what to read.

| text_type | What to read |
|---|---|
| **abstract** | Read **only** the title (column I) and the abstract (column J). **Do not open the PDF.** It is normal to answer "not stated" a lot. |
| **full text** | Open the PDF with the same name as the row. Read the whole paper, including its tables and figures. Do not open supplementary files or look up other papers. |

Most papers have **two rows next to each other**: first the abstract row (ends in `a`), then the full text row (ends in `b`). Always do the abstract row first.

On the full text row you may copy your abstract answers across, then correct and add to them. **Copy only from column K to the right.** Columns A and D to J hold the paper details. They are locked so they can't be changed by accident. If Excel says a cell is protected, you are in one of those columns.

**Step 2. Answer Q1 to Q11** (section 5).

**Step 3. Fill in the purple Methods columns** (section 6).

**Step 4. Fill in one interaction block for each fungus and plant pair** (section 7).

**Step 5. Set column B (`text_reviewed`)** (section 4). Then type today's date in column C.

**Dropdowns:** click a cell and pick from the list. If the right answer is not in the list, type your own. Excel will warn you. Click **Yes** to keep what you typed.

**Typing your own answer:** some options say *"type over this cell"*. Choose that option, then click the cell and type your answer over it, for example `other: rhizosphere soil`. Do **not** type quotation marks.

---

## 4. Column B: `text_reviewed`

Set this when you finish a row. It also tells you how much of the row to fill.

| Choose | When | Then |
|---|---|---|
| **in progress** | You started the row but have not finished | Come back to it later |
| **complete** | The authors report fungi they found in, grew from, or put onto plants (see below) | Fill the whole row |
| **could not access the text (missing or unreadable)** | The PDF will not open or is missing, or the abstract is empty or garbled | Stop. Leave the rest blank. Tell Bea. |
| **review or secondary compilation - no primary data of its own** | A review or opinion piece, or a paper that only analyses other people's published results | Answer **Q3 (language) only**. Leave everything else blank. |
| **not a fungus-in-plant study** | No fungus living in or on a plant is involved (examples below) | Leave everything else blank |

A blank `text_reviewed` means "not done yet".

**These count as complete:**

* Plant disease papers.
* Chemistry or genome papers about a fungus the authors call an endophyte of a plant, even if the plant isn't named.
* Fungi living in seaweeds, algae, lichens, mosses or ferns. Treat the seaweed, alga or lichen as the "plant".

**These are "not a fungus-in-plant study":**

* Only bacteria, not fungi. Yeasts **are** fungi.
* Fungicide or chemical residue studies with no fungus examined.
* Fungi grown in the lab on dead plant material used as food, such as autoclaved grain or plant extracts, with no living plant.
* Studies of plant extracts only.
* Fungi from soil, buildings or animals, with no plant.

**Retracted papers:** if the paper is marked as retracted, review it as normal and write `retracted` in the last column.

---

## 5. The questions (Q1 to Q11)

### Q1. Paper's main purpose

Pick **one**: the purpose the paper leads with.

| Option | For example |
|---|---|
| endophyte ecology / diversity / community | Surveying which fungi live in a plant or place |
| endophyte function: growth, nutrition, or stress tolerance | Does the fungus help the plant grow or survive drought, salt, heat |
| endophyte function: disease protection / biocontrol | Does the fungus protect the plant from pests or disease |
| natural products / secondary metabolites / bioprospecting | Finding chemicals or drugs made by the fungus |
| plant pathology (the fungus studied as a pathogen) | The paper is about a disease the fungus causes |
| fungal taxonomy / systematics / new species | Naming or describing fungi |
| genomics / transcriptomics / methods development | A genome paper, or a new lab method |
| other | Type over the cell, e.g. `other: plant extract activity` |

### Q2. Where did the fungi come from?

| Option | When |
|---|---|
| isolated or detected from plants sampled in this study | The authors took the fungi out of plants they collected for this study, or found them there by DNA or microscope. This still applies if they later put those fungi back onto plants. |
| from a culture collection or another study, then put onto plants here | The fungi came from a culture collection, a company, or an earlier study, and were put onto plants in this study |
| from a culture collection or another study (not put onto plants here) | The fungi came from a culture collection or an earlier study and were only grown in the lab, e.g. for chemistry. A collection code in the name (such as ATCC, BCRC, CBS) is a clue. |
| a mix of these | Some fungi of more than one kind above |
| not stated | The text doesn't say |

### Q3. Language of the text you are reading

Answer for **this row only**. An English abstract of a French paper is `English` on the abstract row and `non-English` on the full text row.

| Option | When |
|---|---|
| English | |
| non-English | Type over the cell with the language, e.g. `non-English: French` |
| English + non-English | Two languages, e.g. an abstract given in English and French. Type over the cell, e.g. `English + French` |
| unclear | |

Language is filled in as `English` to save time. **Check it**, and change it if it's wrong.

### Q4. Any sequence-only (uncultured) taxa?

**yes** if the text reports any fungi found **only by DNA sequencing and never grown in culture** (often called OTUs, ASVs, clones or phylotypes). **no** if it doesn't mention any. Use **unclear** only as a last resort.

### Q5. Strain-level variation noted?

| Option | When |
|---|---|
| yes - noted | The text says different strains or isolates of the **same species** differed in some way, e.g. in their effect on the plant, their chemistry or their activity. Count it even if the text is citing another study. |
| no - not noted | The text doesn't say this |
| only one strain / isolate studied | The paper works with a single isolate, e.g. one strain for a chemistry or genome study |

### Q6a. COUNTRY where the plant was sampled

* The country where the **plant was collected**.
* Only use a country **the text names**. Never look one up.
* A country adjective counts: "Taiwanese plants" = `Taiwan`, "Brazilian forest" = `Brazil`.
* A state, province or region **without** its country (Yunnan, Washington, Minas Gerais) does **not** count. Choose `not stated`, and Q7 will be `inferable from a named site / region`.
* **Never** use the country of the authors' university or institute.
* Several countries: pick one from the list, then type them all in the cell separated by a semicolon, e.g. `Brazil; Peru`.
* If the text uses an **old country name** (USSR, Yugoslavia, Zaire, Czechoslovakia), type it **exactly as written**.
* Tables and figures in the full text count.
* If the text doesn't name a country, choose `not stated`.

### Q6b. Does the text give GPS coordinates for where the plant was sampled?

**yes** or **no**. Latitude and longitude in any format count, e.g. `4°35'N, 74°04'W` or `4.59, -74.07`, including in a table.

### Q7. What geographic information does the text contain?

| Option | When |
|---|---|
| explicitly stated (country or coordinates) | The text names the country where the plant was collected, or gives coordinates |
| inferable from a named site / region | The text names a place (a forest, reserve, island, state or region) but no country and no coordinates |
| the text says it is in a supplement | The text says the locations are in supplementary material, and gives nothing itself |
| the text says it is in another cited study | e.g. "sites as described in Smith et al. 2015", and gives nothing itself |
| only the authors' institution country is given | The only location in the text is where the authors work |
| no geographic information at all | |

Do **not** open supplements or look up cited papers. Just record that the text points there.

### Q8. Biome where the plant was sampled

Only answer from **what the text describes**: a habitat word like "rainforest", "páramo" or "wheat field". **Do not guess a biome from the plant or the country.** If the text doesn't describe the habitat, choose `not stated`.

| If the text says | Choose |
|---|---|
| rainforest, cloud forest, tropical forest | tropical / subtropical moist forest |
| dry forest, deciduous tropical forest | tropical / subtropical dry forest |
| temperate forest, boreal forest, taiga, conifer forest, plantation forest | temperate or boreal forest |
| just "forest" or "woodland", with no type | forest - type not stated |
| fynbos, chaparral, maquis, Mediterranean | Mediterranean forest / woodland / scrub |
| savanna, cerrado | tropical grassland / savanna / shrubland |
| prairie, steppe, natural grassland | temperate grassland / steppe / prairie |
| páramo, puna, alpine, mountain meadow | montane grassland / alpine |
| desert, semi-arid scrub | desert / xeric shrubland |
| marsh, bog, wetland, flooded grassland | wetland / flooded grassland / bog |
| mangrove | mangrove |
| tundra, arctic, Antarctic, polar | tundra / polar |
| sea, coast, beach, seaweed | marine / coastal |
| crop, field, orchard, plantation, sown pasture | agriculture / cultivated |
| garden, park, botanical garden, campus, city | urban / garden / botanical collection |
| only greenhouse, pots or lab | greenhouse / growth chamber / lab |

If plants were **collected in the field and then tested in a greenhouse**, give the field habitat. If the study covers several biomes, pick one, then type them all in the cell separated by commas. If nothing fits, choose `other` and type over the cell.

### Q9. How many distinct fungus-host pairs does the text name?

Type **one whole number**, never a range like 3-5.

* Count each **named fungus**, once for **each plant the text links it to**.
* Count **kinds** of fungi and plants, not isolates and not individual plants.
* Only count fungi the text **names** (section 7 explains what counts as a name). Never estimate.
* Different names count separately, even if they may be the same fungus (`Fusarium sp.` and `Fusarium oxysporum` = 2).
* If a fungus is named but its plant is not, still count it, and write `not stated` in the host_plant cell.
* On full text rows, fungi named in **tables** count too. If the authors give their own total (e.g. "38 genera were identified"), you may use that number instead of counting a long table.

| The text says | Q9 |
|---|---|
| "*Xylaria* and *Nigrospora* were isolated from oak leaves" | **2** |
| "32 isolates from 9 oak trees, belonging to *Xylaria*, *Nigrospora* and *Alternaria*" | **3** |
| "*Xylaria* was found on oak and on pine" | **2** (one fungus, two plants) |
| "*Xylaria* and *Nigrospora* were isolated from oak and pine" (doesn't say which from which) | **2**. Use one block per fungus and write both plants in the host cell: `oak, pine`. |
| "32 isolates belonging to 14 species" (no names given) | **0**. Write `32 isolates, 14 species, not named` in the summary column. |
| "*Aspergillus terreus*, an endophyte of a medicinal plant" (plant not named) | **1**. Host_plant: `not stated`. |

There is room for **5** pairs. If there are more, write the **true total** in Q9 and fill 5 blocks with, in this order: fungi named in the title, then in the abstract, then the most common or most discussed. Then write a short note in the summary column (section 8).

### Q10. Was the surface-sterilisation checked?

Fungi on the **outside** of a plant can be mistaken for fungi **inside** it. Scientists wash the plant surface to kill outside fungi ("surface sterilisation"). This question asks whether they **checked** that the washing worked. It applies whether they then grew fungi or sequenced DNA.

A check is a separate step, such as plating or sequencing the last rinse water, or pressing the washed tissue onto a plate before cutting it. These should show nothing.

| Option | When |
|---|---|
| yes - a check was done (e.g. final rinse water plated or sequenced) | The text describes a check like the ones above |
| no - sterilised, but no check described | The text says the tissue was washed or sterilised, but describes no check. This is the usual answer on abstract rows that mention sterilising. |
| no - tissue was not surface-sterilised | Plant tissue was used, but the text says it was not sterilised, or clearly describes the method without any sterilising |
| not applicable - no plant tissue processed in this study | Nothing was taken out of plant tissue in this study, e.g. fungi from a culture collection, or a plant disease field trial |
| unclear | The text says nothing about how the tissue was handled. Common on abstract rows. |

**Example.** "Leaves were washed in 70% ethanol and 2% bleach, then plated" → **no - sterilised, but no check described**. Add "the final rinse water was plated and showed no growth" → **yes - a check was done**.

### Q11. Does the text state that endophytes are found in all or nearly all plants?

**yes** only if the text **says** this, for example:

* "endophytes are ubiquitous"
* "endophytes occur in virtually all plants"
* "every plant species examined to date hosts endophytes"

**no** otherwise. "All", "nearly all", "virtually all", "every" or "ubiquitous" mean **yes**. "Most", "many", "common", "diverse" or "widespread" are **not** enough. Don't count your own knowledge or what the authors might assume.

On a full text row, read the paper as usual. Statements like this are most often in the **first paragraph of the introduction**, so check there carefully.

---

## 6. The purple Methods columns

Fill **every** Methods column on a complete row.

| Answer | Means |
|---|---|
| **yes** | The text says this method was used |
| **no** | The text describes its methods, and this one is **not** among them (full text rows) |
| **not stated** | The text doesn't describe its methods. This is the usual answer on abstract rows. |

| Column | "yes" when the text... |
|---|---|
| Methods: cultured fungi from surface-sterilised tissue | washed plant tissue, put it on plates, and grew fungi out |
| Methods: performed microscopy on tissue | showed fungus **inside** plant tissue with a microscope |
| Methods: molecular (DNA) sequencing from tissue | sequenced fungal DNA straight from plant tissue, without growing it first |
| Methods: isolate ID by sequencing | grew the fungi, then used DNA to identify them |

**Methods: fungus inoculated onto a plant** has four options:

| Option | When |
|---|---|
| yes - inoculated, and confirmed inside the plant (re-isolated or seen in tissue) | The fungus was put onto a living plant **and** later grown back out of washed tissue, or seen inside the tissue with a microscope |
| yes - inoculated, but not confirmed inside the plant | The fungus was put onto a living plant, but nobody checked it got inside |
| no | Nothing was put onto a living plant (full text rows) |
| not stated | You can't tell |

---

## 7. The interaction blocks (one per fungus and plant pair)

There are 5 blocks, coloured alternately blue and green. Use one block for each pair you counted in Q9, up to 5. Each block has six cells.

**If you fill a block, answer all six cells.** Where the text doesn't say, use the option that means that: `not stated` (tissue, evidence), `not clear from the text` (lifestyle), or `not reported` (effect). **Leave unused blocks completely empty.**

### fungus: what counts as a name

* **Write the name exactly as the authors do.** Don't correct it, update it or add anything to it. If the text says "Epichloë", write `Epichloë`, not `Epichloë sp.`.
* The most precise name given is best: `Colletotrichum tropicale`, or just `Xylaria sp.` if that is what the text says.
* A family or other higher group name counts if it is the only name, e.g. `Xylariaceae` or `Hypocreales`.
* Names with a qualifier count. Write them as given: `Cryptococcus cf. laurentii`, `Phoma sp. 1`, `phylotype closest to Cryptococcus foliicola`.
* **Leave out strain and collection codes**: `Penicillium sclerotiorum PSU-A13` → `Penicillium sclerotiorum`. If a code is the only name but a group is given ("isolate KLAR 5, order Hypocreales"), write the group: `Hypocreales`.
* **These are NOT names. Don't make a block for them.** Describe them in the summary column instead.
  * group words: "dark septate endophytes", "AM fungi", "mycorrhizal fungi", "endophytic fungi"
  * DNA codes: "OTU 12", "uncultured fungus"
* **Fungi only.** Yeasts are fungi. Bacteria are not: names such as *Bacillus*, *Pseudomonas*, *Streptomyces*, *Rahnella* or *Pantoea* are bacteria, so leave them out. **If you're not sure whether a name is a fungus, record it** and write `not sure if fungus` in the last column.

### host_plant

The plant's name, **exactly as the authors write it**: `wheat`, `Quercus robur` or `Ericaceae`. Family names count. If the text doesn't name the plant, write `not stated`. A seaweed, alga or lichen counts as the host.

### tissue

Which part of the plant. If the fungus was in several parts, put them all in **one cell**: `leaf, root`.

| If the text says | Choose |
|---|---|
| needles, petioles, leaf blades | leaf |
| twigs, branches, bark, wood, trunk | stem / wood / bark |
| blooms, inflorescences, flowers | flower / reproductive |
| seedlings, whole plants | whole plant |
| "shoots" or "aerial parts" without saying which | aerial parts / shoots (not separated) |
| anything else (rhizome, tuber, thallus...) | `other: ` plus the text's word, e.g. `other: rhizome` |
| nothing | not stated |

### fungal_lifestyle: how does the fungus live?

Record what the **text** says about the fungus. Choose **not clear from the text** if the text doesn't describe its lifestyle at all.

| Option | When the text describes the fungus as... |
|---|---|
| endophyte (lives inside plant tissue) | living inside the plant, including when the text simply calls it "endophytic". Whether it harms the plant goes in effect_on_host, not here. |
| latent pathogen (no symptoms now, causes disease later) | harmless now, but the text shows or says it becomes a disease later or under stress |
| plant pathogen (causing disease) | causing disease in this plant |
| saprotroph (on dead or dying plant material) | living on dead wood, fallen leaves or dying tissue |
| mycorrhizal (any type) | a root partner fungus of any mycorrhizal type |
| mycoparasite / antagonist of other microbes | attacking or suppressing other fungi or microbes |
| epiphyte (surface only) | on the plant surface, not inside |
| lichenised | part of a lichen |
| context-dependent | the text says its lifestyle changes with host, place or strain |
| not clear from the text | the text doesn't say |

### effect_on_host: what happened to the plant?

This is a **different question** from lifestyle. A plant pathogen can be present with no symptoms.

| Option | When the text... |
|---|---|
| not reported (fungus just isolated / detected) | says nothing about the plant's health or any effect on it |
| no visible symptoms; benefit or harm not tested | says the plants were **healthy, asymptomatic or symptomless**, but didn't test for benefit or harm |
| neutral / commensal (plant response tested; no net effect) | **measured** the plant's growth or health and found no effect |
| beneficial to the plant | reports a measured or clearly stated benefit |
| harmful to the plant (disease / reduced fitness) | reports disease, symptoms or poorer growth |
| context-dependent | the effect changes with host, place or strain |
| unclear | you can't tell |

### evidence_basis: how was it shown?

**The rule:** record how the **effect** was shown. If the effect is **not reported**, record how the **lifestyle** was shown instead.

| Option | When |
|---|---|
| experimentally tested in this study | the authors did an experiment, e.g. put the fungus onto plants and measured them |
| observed / measured in this study (no manipulation) | the authors saw or measured it themselves without an experiment, e.g. grew the fungus out of a plant they sampled, or saw disease in the field |
| from other studies or the fungus's reputation (not shown in this paper) | the text cites earlier work, or the label comes from what the fungus is known for |
| asserted with no support | the text just says it, with no evidence and no citation |
| not stated | |

**The three most common cases.** Please follow these exactly.

| What the text says | evidence_basis |
|---|---|
| The fungus was isolated or detected from a plant **in this study** | observed / measured in this study |
| The fungus is only **called** "an endophytic fungus" (common in chemistry and genome papers) | asserted with no support |
| The text says it is an endophyte **and cites an earlier study** for it | from other studies or the fungus's reputation |

---

## 8. The last two columns

**extra_pairs_or_NGS_community_summary.** Only needed when there are more than 5 pairs, when fungi are described without names, or for DNA community studies. Write a count and a few words. **No need to list names.**

* `9 more named pairs, all from oak leaves`
* `142 OTUs / 38 genera from oak leaves; most common Cladosporium, Aureobasidium`
* `dark septate endophytes and AM fungi in roots of 66 plant species`

**anything_you_were_unsure_about.** Write anything that made you hesitate. This helps us a lot.

**DNA community papers (metabarcoding / NGS):** don't list every OTU. Make blocks only for fungi the text **names**, usually the few most common ones. Describe the rest in the summary column.

---

## 9. Worked examples

### Example 1. Abstract row, fungi isolated, nothing tested

*"Endophytic fungi were isolated from surface-sterilised leaves of Espeletia in the páramo of Chingaza, Colombia. The dominant taxa were Xylaria sp. and Nigrospora sphaerica."*

| Column | Answer |
|---|---|
| text_reviewed | complete |
| Q1 | endophyte ecology / diversity / community |
| Q2 | isolated or detected from plants sampled in this study |
| Q3 | English |
| Q4 | no |
| Q5 | no - not noted |
| Q6a | Colombia |
| Q6b | no |
| Q7 | explicitly stated (country or coordinates) |
| Q8 | montane grassland / alpine ("páramo" is the text's own habitat word) |
| Q9 | 2 |
| Q10 | no - sterilised, but no check described |
| Q11 | no |
| Methods | cultured fungi from surface-sterilised tissue: **yes**. All others: **not stated**. |
| Blocks 1 and 2 | `Xylaria sp.` and `Nigrospora sphaerica` / `Espeletia` / leaf / endophyte / not reported / observed / measured in this study |

Effect is **not reported** because the abstract says nothing about the plants' health. If it had said "healthy leaves", effect would be **no visible symptoms; benefit or harm not tested**.

If the abstract had said only "Espeletia" with no place: Q6a `not stated`, Q7 `no geographic information at all`, Q8 `not stated`.

### Example 2. Full text row, benefit tested

*"Wheat seedlings were inoculated with Epichloë. Inoculated plants grew 22% more under drought."*

| Column | Answer |
|---|---|
| Q1 | endophyte function: growth, nutrition, or stress tolerance |
| Q2 | not stated (unless the text says where the strain came from) |
| Q10 | as the text reports; `not applicable` if no plant tissue was processed |
| Methods: fungus inoculated | yes - inoculated, but not confirmed inside the plant (the text never checks) |
| Block 1 | `Epichloë` / `wheat` / whole plant (seedlings) / the lifestyle the text gives, or `not clear from the text` / beneficial to the plant / experimentally tested in this study |

### Example 3. Latent pathogen

*"Diplodia sapinea was recovered from healthy-looking Pinus shoots. Inoculated seedlings under water stress developed shoot blight."*

Block 1: `Diplodia sapinea` / `Pinus` / aerial parts / shoots (not separated) / **latent pathogen** / **harmful to the plant** / **experimentally tested in this study**. Write "harmful only under water stress" in the last column.

### Example 4. DNA community study (metabarcoding)

*"ITS metabarcoding of Quercus robur leaves recovered 142 fungal OTUs (38 genera); the most abundant were Cladosporium and Aureobasidium."*

| Column | Answer |
|---|---|
| Q4 | yes |
| Q9 | 2 on the abstract row (only two are named). On the full text row, count the genera named in the tables, or use the authors' total of 38. |
| Q10 | unclear (abstract row); on the full text row, as the methods describe |
| Methods | molecular (DNA) sequencing from tissue: **yes** |
| Blocks 1 and 2 | `Cladosporium` and `Aureobasidium` / `Quercus robur` / leaf / endophyte / not reported / observed / measured in this study |
| Summary | `142 OTUs / 38 genera from Q. robur leaves; no effect tested` |

### Example 5. Fungi from a culture collection, put onto plants

*"Three fungal strains from a culture collection were grown on plates and applied to tomato plants. Plant growth was measured."*

| Column | If the fungi were later found inside the plant | If nobody checked |
|---|---|---|
| text_reviewed | complete | complete |
| Q2 | from a culture collection or another study, then put onto plants here | same |
| Q9 | 3 | 3 |
| Q10 | as the text reports for the step where fungi were grown back out of washed tissue | not applicable - no plant tissue processed in this study |
| Methods: fungus inoculated | yes - inoculated, and confirmed inside the plant | yes - inoculated, but not confirmed inside the plant |
| Blocks 1 to 3 | lifestyle as the text gives it / effect as measured / experimentally tested in this study | same |

This is **not** a review. Mark it **complete**.

### Example 6. Chemistry paper about a named endophyte

*"Two new compounds were isolated from the endophytic fungus Penicillium sclerotiorum PSU-A13."*

| Column | Answer |
|---|---|
| text_reviewed | complete |
| Q1 | natural products / secondary metabolites / bioprospecting |
| Q2 | not stated |
| Q5 | only one strain / isolate studied |
| Q9 | 1 |
| Q10 | unclear |
| Block 1 | `Penicillium sclerotiorum` / not stated / not stated / endophyte / not reported / **asserted with no support** |

---

## 10. Before you mark a row complete

* [ ] I read only what `text_type` told me to read.
* [ ] Every question Q1 to Q11 has an answer.
* [ ] Every purple Methods column has yes, no, or not stated.
* [ ] I filled one block for each pair I counted in Q9 (up to 5), with all six cells answered.
* [ ] I used the authors' names exactly as written, without strain codes.
* [ ] I recorded fungi only, not bacteria.
* [ ] I did not add anything I know but the text doesn't say.
* [ ] Column B says **complete**, and today's date is in column C.

---

## 11. Glossary

| Word | Meaning |
|---|---|
| **endophyte** | A fungus living inside a plant |
| **epiphyte** | A fungus living on the plant's surface |
| **pathogen** | A fungus that causes disease |
| **latent pathogen** | A fungus that causes no symptoms now but can cause disease later |
| **saprotroph** | A fungus that feeds on dead material |
| **mycorrhizal** | A fungus that partners with roots and trades nutrients with the plant |
| **mycoparasite / antagonist** | A fungus that attacks or holds back other fungi or microbes |
| **lichenised** | Part of a lichen, a partnership between a fungus and an alga |
| **commensal** | Lives with the plant with no measurable benefit or harm |
| **isolate / strain** | One culture of a fungus grown from one source |
| **isolated** | Grown out of plant tissue onto a plate |
| **plated** | Put onto a dish of growth medium (agar) |
| **inoculated** | Fungus deliberately put onto or into a plant |
| **re-isolated** | Grown back out of the plant after inoculation, showing it got inside |
| **surface-sterilised** | Plant tissue washed (e.g. with ethanol and bleach) to kill fungi on the outside |
| **culture collection** | A bank of stored fungal cultures. Codes like ATCC, CBS or BCRC in a name come from one. |
| **sequencing / DNA barcoding** | Reading a fungus's DNA to identify it |
| **metabarcoding / NGS** | Sequencing all the fungal DNA in a sample at once to list many fungi together |
| **OTU / ASV / phylotype / clone** | A DNA sequence group used in place of a species name |
| **uncultured** | Known only from DNA, never grown |
| **taxon / taxa** | A named group of organisms, such as a species or genus (plural: taxa) |
| **genus / species** | In *Fusarium oxysporum*, *Fusarium* is the genus and *oxysporum* the species |
| **secondary metabolites / natural products** | Chemicals made by the fungus, often studied as possible drugs |
| **genomics / transcriptomics** | Studies of all of an organism's genes, or of which genes are switched on |
| **systematics / taxonomy** | Naming and classifying organisms |
| **biome** | A large type of habitat, such as tropical rainforest or desert |

**Questions? Ask Bea.**
