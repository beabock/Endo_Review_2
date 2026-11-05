# BMB 2026-09-02
# Canonical extraction schema for the full-text re-extraction (Task 1 Phase 0b).
#
# ONE SOURCE OF TRUTH for:
#   - the JSON schema handed to Ollama (schema-constrained decoding)
#   - the controlled vocabularies (short machine tokens)
#   - the prompt text
#   - the map from the Task 2 human-annotation labels (long phrases in
#     guild_rubric.md / build_groundtruth_sample.py VOCAB) to the same tokens, so
#     score_groundtruth.py can compare model output and human annotation on one axis.
#
# Field names and value sets are LOCKED to the Task 2 workbook (see
# NPH_extraction_schema_design.md, 2026-09-02 update). If you change a vocabulary
# here, change guild_rubric.md + build_groundtruth_sample.py VOCAB in the same commit.

from __future__ import annotations

# --------------------------------------------------------------------------------
# Interaction-level vocabularies (one record = one fungus x host-plant pair)
# --------------------------------------------------------------------------------

TISSUE = [
    "leaf", "root", "stem_wood_bark", "seed", "fruit", "flower",
    "aerial_parts",              # paper says shoots / aerial parts and does not separate them
    "whole_plant", "other", "not_stated",
]

# how the fungus makes its living in this interaction (FungalTraits primary_lifestyle,
# Polme et al. 2020, condensed; the three endophyte types are merged - tissue records
# leaf vs root). v5.3 (2026-10-08): the four saprotroph types and the four mycorrhizal
# types are each merged into one value - no analysis splits them, and rare fine-grained
# categories lower inter-rater agreement. LIFESTYLE_COLLAPSE maps v5.2 output onto v5.3.
FUNGAL_LIFESTYLE = [
    "endophyte",                 # symptomless in living internal tissue
    "latent_pathogen",           # symptomless now, shown/known to turn pathogenic
    "plant_pathogen",            # causing disease in the studied interaction
    "saprotroph",                # dead / senescent plant material (wood, litter, soil, other)
    "mycorrhizal",               # arbuscular / ecto / ericoid / orchid
    "mycoparasite",              # antagonist of other fungi / microbes
    "epiphyte",                  # on the surface only
    "lichenised",
    "context_dependent",         # the paper says the lifestyle itself shifts
    "unclear",
]

LIFESTYLE_COLLAPSE = {           # v5.2 tokens -> v5.3
    "wood_saprotroph": "saprotroph", "litter_saprotroph": "saprotroph",
    "soil_saprotroph": "saprotroph", "other_saprotroph": "saprotroph",
    "arbuscular_mycorrhizal": "mycorrhizal", "ectomycorrhizal": "mycorrhizal",
    "ericoid_mycorrhizal": "mycorrhizal", "orchid_mycorrhizal": "mycorrhizal",
}


def collapse_lifestyle(token):
    return LIFESTYLE_COLLAPSE.get(token, token)

# net outcome for THIS host plant, as the paper reports it. Deliberately a separate
# axis from fungal_lifestyle (a plant_pathogen can occur with no_symptoms_not_tested).
EFFECT_ON_HOST = [
    "not_reported",              # fungus just isolated / detected, effect not addressed
    "no_symptoms_not_tested",    # "symptomless" stated, benefit/harm not tested
    "commensal",                 # plant response tested, no net effect
    "beneficial",
    "harmful",
    "context_dependent",
    "unclear",
]

# basis for fungal_lifestyle + effect_on_host - the anti-circularity field (Referee 3)
EVIDENCE_BASIS = [
    "experimental",              # inoculation / resynthesis / assay in THIS study
    "observational",             # measured / observed here, no manipulation
    "inferred_from_taxon",       # from genus/species reputation or a database
    "asserted",                  # stated in passing, no support
    "not_stated",
]

# --------------------------------------------------------------------------------
# Paper-level vocabularies (Q2-Q11 of the Task 2 workbook)
# --------------------------------------------------------------------------------

PRIMARY_AIM = [            # Q2
    "endophyte_ecology",              # ecology / diversity / community
    "endophyte_function_growth",      # growth, nutrition, stress tolerance
    "endophyte_function_biocontrol",  # disease protection / biocontrol
    "natural_products",              # secondary metabolites / bioprospecting
    "plant_pathology",               # the fungus studied as a pathogen
    "fungal_taxonomy",               # systematics / new species
    "genomics_methods",              # genomics / transcriptomics / methods
    "other",
]

SAMPLING_APPROACH = [     # Q3
    "few_isolates",          # one or a few named isolates
    "culture_survey",        # many isolates, named
    "metabarcoding",         # community NGS - OTU / ASV table
    "direct_observation",    # microscopy / histology only, no isolation or sequencing
    "mixed",                 # note which in interaction_notes / community_summary
    "review",               # synthesis / secondary compilation - no new fungi here
    "other",
    "unclear",
]

LANGUAGE = [              # Q4 - answer for the text actually analysed on this row
    "english",
    "non_english",
    "bilingual",            # bilingual abstract, or English abstract + non-English body
    "unclear",
]

# Q8 (2026-09-22: merged with the short-lived separate Q7a/location_source field - Bea Bock,
# "I think simplifying could be a good idea". One question now answers both "how specific is
# the location" AND "where does the text keep it", instead of two overlapping dropdowns that
# nothing enforced agreement between.)
SAMPLING_LOCATION_STATUS = [
    "explicit",             # sampling location explicitly stated in the main text
    "inferable",            # inferable from a named field site / region in the main text
    "supplement",           # the main text says location details are in a supplement
    "cited_work",           # the main text says location details are in another cited study
    "affiliation_only",     # only the authors' institutional country is given
    "none",                 # no geographic information at all
]

STRAIN_VARIATION = [      # Q6
    "yes", "no", "single_strain",
]

# WWF terrestrial biomes (Olson et al. 2001), matching the Task 4 realm choice. Q9.
BIOME = [
    "tropical_moist_forest", "tropical_dry_forest",
    "temperate_boreal_forest", "forest_unspecified", "mediterranean_scrub",
    "tropical_grassland_savanna", "temperate_grassland_steppe",
    "montane_grassland_alpine", "desert_xeric",
    "wetland_flooded_grassland", "mangrove", "tundra_polar", "marine_coastal",
    "agriculture_cultivated", "urban_garden", "greenhouse_growthchamber",
    "other", "not_stated",
]

STERILISATION_CHECKED = [   # workbook Q10 (was Q11)
    "yes_control",          # final rinse plated / tissue imprint / similar control
    "no_check",             # standard sterilisation, no check described
    "not_culture_based",
    "not_applicable_external",  # no plant tissue processed here (e.g. culture-collection strains)
    "not_sterilised",           # v5.4: tissue processed without surface sterilisation
    "cannot_tell",
]

# Workbook Q2 (2026-10-08): where the fungi came from. Separates natural host records from
# inoculations of strains obtained elsewhere (artificial associations) and from strains merely
# re-used from a collection. v5.4: also extracted by the model (fungus_source).
FUNGUS_SOURCE = [
    "from_study_plants",        # isolated / detected from plants sampled in this study
    "external",                 # culture collection or another study, then put onto plants here
    "external_not_inoculated",  # culture collection or another study, not put onto plants here
    "both",                     # a mix of these
    "not_stated",
]

# endophytism-demonstration methods - MULTI-select (Referee 3 QC). Task 2 method ticks.
DETECTION_METHODS = [
    "culture_sterilised",       # surface-sterilised tissue plated, fungi grown out
    "microscopy_in_tissue",     # hyphae shown inside tissue (staining / sectioning / TEM)
    "direct_sequencing",        # DNA sequenced straight from tissue (metabarcoding)
    "isolate_id_sequencing",    # cultured isolates barcoded to identify them
    "resynthesis_inoculation",  # sterile plant re-inoculated and fungus re-isolated
    "not_stated",
]

YES_NO_UNCLEAR = ["yes", "no", "unclear"]   # Q1 relevance, Q5 uncultured-taxa flag

# --------------------------------------------------------------------------------
# JSON schema for Ollama schema-constrained decoding (format=<schema>).
# One call returns the paper-level block + a list of interaction records.
# --------------------------------------------------------------------------------

def _enum(values, *, nullable=False):
    t = {"type": "string", "enum": list(values)}
    return {"anyOf": [t, {"type": "null"}]} if nullable else t


INTERACTION_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "fungus": {"type": "string"},          # verbatim, as the authors name it
        "host_plant": {"type": "string"},      # verbatim
        "tissue": {"type": "array", "items": _enum(TISSUE)},
        "fungal_lifestyle": _enum(FUNGAL_LIFESTYLE),
        "effect_on_host": _enum(EFFECT_ON_HOST),
        "evidence_basis": _enum(EVIDENCE_BASIS),
        "interaction_notes": {"type": "string"},
    },
    "required": ["fungus", "host_plant", "tissue", "fungal_lifestyle",
                 "effect_on_host", "evidence_basis"],
}

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "is_fungus_in_plant_study": _enum(YES_NO_UNCLEAR),      # Q1
        "primary_aim": _enum(PRIMARY_AIM),                       # Q2
        "sampling_approach": _enum(SAMPLING_APPROACH),           # Q3
        "language": _enum(LANGUAGE),                             # Q4
        "uncultured_taxa": _enum(YES_NO_UNCLEAR),                # Q5
        "strain_variation": _enum(STRAIN_VARIATION),             # Q6
        "sampling_country": {"type": "string"},                  # Q7a country/countries, "not stated"
        "sampling_location": {"type": "string"},                 # Q7b site / locality, free text
        "coordinates_given": _enum(["yes", "no"]),               # Q7c coordinates in the paper?
        "sampling_location_status": _enum(SAMPLING_LOCATION_STATUS),  # Q8 (specificity + where it's kept)
        "biome": {"type": "array", "items": _enum(BIOME)},       # Q9
        "n_distinct_pairs": {"type": "integer"},                 # Q10
        "sterilisation_checked": _enum(STERILISATION_CHECKED),   # Q11
        "fungus_source": _enum(FUNGUS_SOURCE),                   # workbook Q2 (v5.4)
        "detection_methods": {"type": "array", "items": _enum(DETECTION_METHODS)},
        "community_summary": {"type": "string"},   # for metabarcoding: richness, dominant taxa
        "interactions": {"type": "array", "items": INTERACTION_ITEM_SCHEMA},
    },
    "required": ["is_fungus_in_plant_study", "primary_aim", "sampling_approach",
                 "language", "sampling_country", "sampling_location",
                 "coordinates_given", "sampling_location_status",
                 "biome", "sterilisation_checked", "fungus_source", "detection_methods",
                 "interactions"],
}

# Flat CSV columns written by monsoon_extract.py (v5). Paper-level fields are repeated
# on every interaction row of that paper; a paper with zero interactions gets one row
# with the interaction columns blank. Legacy columns (fungal_taxon, plant_host,
# primary_guild, country, data_source, doc_type_ai, presence_absence, source_file) are
# kept populated for backward compatibility with 02_ollama_cleanup.R / merge_final_data.py.
CSV_COLUMNS = [
    # identity
    "paper_id", "doi", "source_file", "data_source", "doc_type_ai", "n_pages",
    "model", "schema_version", "n_chunks", "malformed_chunks",
    # paper-level
    "is_fungus_in_plant_study", "primary_aim", "sampling_approach", "language",
    "uncultured_taxa", "strain_variation", "sampling_country", "sampling_location",
    "coordinates_given", "sampling_location_status", "biome", "n_distinct_pairs", "sterilisation_checked",
    "fungus_source",
    "detection_methods", "community_summary",
    # interaction-level (new names)
    "fungus", "host_plant", "tissue", "fungal_lifestyle", "effect_on_host",
    "evidence_basis", "interaction_notes",
    # legacy aliases (populated for back-compat)
    "fungal_taxon", "plant_host", "primary_guild", "country", "presence_absence",
]

SCHEMA_VERSION = "v5.4"   # v5.4 (2026-10-08): fungus_source field; not_sterilised;
# forest_unspecified biome; relabelled workbook options mapped.
# v5.3: saprotroph / mycorrhizal merged; not_applicable_external
# sterilisation value. v5.2: dropped location_source, merged into sampling_location_status

# --------------------------------------------------------------------------------
# legacy primary_guild <- fungal_lifestyle (keeps the old standardisation working)
# --------------------------------------------------------------------------------

LIFESTYLE_TO_LEGACY_GUILD = {
    "endophyte": "endophyte", "latent_pathogen": "pathogen",
    "plant_pathogen": "pathogen", "wood_saprotroph": "saprotroph",
    "litter_saprotroph": "saprotroph", "soil_saprotroph": "saprotroph",
    "other_saprotroph": "saprotroph", "arbuscular_mycorrhizal": "mycorrhiza",
    "ectomycorrhizal": "mycorrhiza", "ericoid_mycorrhizal": "mycorrhiza",
    "orchid_mycorrhizal": "mycorrhiza", "mycoparasite": "biocontrol",
    "saprotroph": "saprotroph", "mycorrhizal": "mycorrhiza",          # v5.3 merged values
    "epiphyte": "epiphyte", "lichenised": "lichen",
    "context_dependent": "Unknown", "unclear": "Unknown", None: "Unknown",
}

# --------------------------------------------------------------------------------
# Task 2 human-label -> token maps (for score_groundtruth.py). Keys are the exact
# strings in build_groundtruth_sample.py VOCAB / the workbook dropdowns.
# --------------------------------------------------------------------------------

HUMAN_TO_TOKEN = {
    "tissue": {
        "leaf": "leaf", "root": "root", "stem / wood / bark": "stem_wood_bark",
        "seed": "seed", "fruit": "fruit", "flower / reproductive": "flower",
        "aerial parts / shoots (not separated)": "aerial_parts",
        "whole plant": "whole_plant", "other (type it)": "other",
        "not stated": "not_stated",
    },
    "fungal_lifestyle": {
        "endophyte (any plant tissue; symptomless in living tissue)": "endophyte",
        "latent pathogen / hemibiotroph": "latent_pathogen",
        "plant pathogen": "plant_pathogen",
        "wood saprotroph": "wood_saprotroph",
        "litter saprotroph": "litter_saprotroph",
        "soil saprotroph": "soil_saprotroph",
        "unspecified / other saprotroph": "other_saprotroph",
        "arbuscular mycorrhizal": "arbuscular_mycorrhizal",
        "ectomycorrhizal": "ectomycorrhizal",
        "ericoid mycorrhizal": "ericoid_mycorrhizal",
        "orchid mycorrhizal": "orchid_mycorrhizal",
        "mycoparasite / antagonist of other microbes": "mycoparasite",
        "epiphyte (surface only)": "epiphyte",
        "lichenised": "lichenised",
        "context-dependent (varies by host / environment / strain)": "context_dependent",
        "not clear from the text": "unclear",
    },
    "effect_on_host": {
        "not reported (fungus just isolated / detected)": "not_reported",
        "no visible symptoms; benefit or harm not tested": "no_symptoms_not_tested",
        "neutral / commensal (plant response tested; no net effect)": "commensal",
        "beneficial to the plant": "beneficial",
        "harmful to the plant (disease / reduced fitness)": "harmful",
        "context-dependent (varies by host / environment / strain)": "context_dependent",
        "unclear": "unclear",
    },
    "evidence_basis": {
        "experimentally tested in this study": "experimental",
        "observed / measured in this study (no manipulation)": "observational",
        "inferred from what the fungus usually does (taxon reputation / database)": "inferred_from_taxon",
        "asserted with no support": "asserted",
        "not stated": "not_stated",
    },
    "primary_aim": {
        "endophyte ecology / diversity / community": "endophyte_ecology",
        "endophyte function: growth, nutrition, or stress tolerance": "endophyte_function_growth",
        "endophyte function: disease protection / biocontrol": "endophyte_function_biocontrol",
        "natural products / secondary metabolites / bioprospecting": "natural_products",
        "plant pathology (the fungus studied as a pathogen)": "plant_pathology",
        "fungal taxonomy / systematics / new species": "fungal_taxonomy",
        "genomics / transcriptomics / methods development": "genomics_methods",
        "other (type it)": "other",
    },
    "sampling_approach": {
        "one or a few isolates (named)": "few_isolates",
        "culture survey (many isolates, named)": "culture_survey",
        "community metabarcoding / NGS (OTU or ASV table)": "metabarcoding",
        "direct observation only (microscopy / histology, no isolation or sequencing)": "direct_observation",
        "mixed methods (type which)": "mixed",
        "review / synthesis / secondary compilation - no new fungi obtained here": "review",
        "other (type it)": "other", "unclear": "unclear",
    },
    "language": {
        "English": "english", "non-English (type which)": "non_english",
        "English + non-English (bilingual abstract, or English abstract + non-English body)": "bilingual",
        "unclear": "unclear",
    },
    "sampling_location_status": {
        "sampling location is explicitly stated": "explicit",
        "sampling location is inferable from a named field site / region": "inferable",
        "the main text says location details are in a supplement": "supplement",
        "the main text says location details are in another cited study": "cited_work",
        "no sampling location - only the authors' institutional country is given": "affiliation_only",
        "no geographic information at all": "none",
    },
    "strain_variation": {
        "yes - noted": "yes", "no - not noted": "no",
        "only one strain / isolate studied": "single_strain",
    },
    "biome": {
        "tropical / subtropical moist forest": "tropical_moist_forest",
        "tropical / subtropical dry forest": "tropical_dry_forest",
        "temperate or boreal forest": "temperate_boreal_forest",
        "Mediterranean forest / woodland / scrub": "mediterranean_scrub",
        "tropical grassland / savanna / shrubland": "tropical_grassland_savanna",
        "temperate grassland / steppe / prairie": "temperate_grassland_steppe",
        "montane grassland / alpine": "montane_grassland_alpine",
        "desert / xeric shrubland": "desert_xeric",
        "wetland / flooded grassland / bog": "wetland_flooded_grassland",
        "mangrove": "mangrove", "tundra / polar": "tundra_polar",
        "marine / coastal": "marine_coastal",
        "agriculture / cultivated (crop, orchard, plantation, sown pasture)": "agriculture_cultivated",
        "urban / garden / botanical collection": "urban_garden",
        "greenhouse / growth chamber": "greenhouse_growthchamber",
        "other (type it)": "other", "not stated": "not_stated",
    },
    "sterilisation_checked": {
        "yes - a control was done (final rinse plated, tissue imprints, or similar)": "yes_control",
        "no - standard sterilisation, no check described": "no_check",
        "not a culture-based study": "not_culture_based",
        "cannot tell from the text": "cannot_tell",
    },
}

# 2026-10-08 workbook relabel: the new dropdown text -> the same tokens. The older labels
# above are kept so a workbook filled before the relabel still scores.
HUMAN_TO_TOKEN["fungal_lifestyle"] = {k: collapse_lifestyle(v)
                                      for k, v in HUMAN_TO_TOKEN["fungal_lifestyle"].items()}
HUMAN_TO_TOKEN["fungal_lifestyle"].update({
    "endophyte (inside healthy tissue, no disease)": "endophyte",
    "endophyte (lives inside plant tissue)": "endophyte",          # 2026-10-08 v2 label
    "latent pathogen (no symptoms now, causes disease later)": "latent_pathogen",
    "plant pathogen (causing disease)": "plant_pathogen",
    "saprotroph (on dead or dying plant material)": "saprotroph",
    "mycorrhizal (any type)": "mycorrhizal",
})
HUMAN_TO_TOKEN["tissue"]["other (type over this cell, e.g. other: rhizosphere soil)"] = "other"
HUMAN_TO_TOKEN["primary_aim"]["other (type over this cell with your own answer)"] = "other"
HUMAN_TO_TOKEN["language"].update({
    "non-English (type over this cell, e.g. non-English: French)": "non_english",
    "English + non-English (type over this cell, e.g. English + French)": "bilingual",
})
HUMAN_TO_TOKEN["sampling_location_status"].update({
    "explicitly stated (country, place, or coordinates)": "explicit",
    "inferable from a named site / region": "inferable",
    "the text says it is in a supplement": "supplement",
    "the text says it is in another cited study": "cited_work",
    "only the authors' institution country is given": "affiliation_only",
})
HUMAN_TO_TOKEN["biome"].update({
    "greenhouse / growth chamber / lab": "greenhouse_growthchamber",
    "other (type over this cell with your own answer)": "other",
})
HUMAN_TO_TOKEN["sterilisation_checked"].update({
    "yes - a check was done (e.g. final rinse water plated)": "yes_control",
    "no - sterilised, but no check described": "no_check",
    "not applicable - fungi came from a culture collection": "not_applicable_external",
    "yes - a check was done (e.g. final rinse water plated or sequenced)": "yes_control",
    "no - tissue was not surface-sterilised": "not_sterilised",
    "not applicable - no plant tissue processed in this study": "not_applicable_external",
    "unclear": "cannot_tell",
})
HUMAN_TO_TOKEN["fungus_source"] = {
    "isolated or detected from plants sampled in this study": "from_study_plants",
    "from a culture collection or another study, then put onto plants here": "external",
    "from a culture collection or another study (not put onto plants here)": "external_not_inoculated",
    "both": "both", "a mix of these": "both", "not stated": "not_stated",
}

HUMAN_TO_TOKEN["evidence_basis"]["from other studies or the fungus's reputation (not shown in this paper)"] = "inferred_from_taxon"
HUMAN_TO_TOKEN["sampling_location_status"]["explicitly stated (country or coordinates)"] = "explicit"
HUMAN_TO_TOKEN["biome"]["forest - type not stated"] = "forest_unspecified"

# Task 2 method-tick column header -> DETECTION_METHODS token
METHOD_COL_TO_TOKEN = {
    "Methods: cultured fungi from surface-sterilised tissue": "culture_sterilised",   # 2026-10-08
    "Methods: performed microscopy on tissue": "microscopy_in_tissue",
    "Methods: molecular (DNA) sequencing from tissue": "direct_sequencing",
    "Methods: isolate ID by sequencing": "isolate_id_sequencing",
    "Methods: fungus inoculated onto a plant": "resynthesis_inoculation",
    "culture from sterilised tissue": "culture_sterilised",
    "microscopy in tissue": "microscopy_in_tissue",
    "direct sequencing from tissue": "direct_sequencing",
    "isolate ID by sequencing": "isolate_id_sequencing",
    "resynthesis / re-inoculation": "resynthesis_inoculation",
    "method not stated": "not_stated",
}
# NOTE: DETECTION_METHODS uses "microscopy_in_tissue" here but the schema list above
# says "microscopy_in_tissue" - keep these identical. (self-check in tests below)


def human_token(field: str, label) -> str | None:
    """Map a Task 2 workbook cell value to the canonical token (for scoring)."""
    if label is None:
        return None
    s = str(label).strip()
    if not s:
        return None
    return HUMAN_TO_TOKEN.get(field, {}).get(s, s)   # fall through: typed custom value


# --------------------------------------------------------------------------------
# Prompt
# --------------------------------------------------------------------------------

PROMPT_HEADER = """You are an expert mycologist extracting structured data from ONE
research paper (or a text segment from it). Report ONLY what THIS text says - never what
you know about a taxon in general. If the text does not say something, use the "not
stated" / "unclear" / "not_reported" option, do not guess.

Return a single JSON object matching the schema. Field guide:

PAPER-LEVEL
- is_fungus_in_plant_study: does the text report a fungus obtained from / detected in a
  plant? "no" for reviews with no primary data and for non-plant-fungus studies.
- primary_aim: the paper's main purpose (one value).
- sampling_approach: how the fungi in THIS paper were obtained.
- language: language of the text you are reading.
- uncultured_taxa: does it report sequence-only (OTU/ASV, uncultured) taxa?
- strain_variation: does it note functional differences among strains/isolates of one species?
- sampling_country: the country (or countries, separated by "; ") where the PLANT was
  sampled, as a standard English country name, ONLY if the paper names it. If the paper
  gives only coordinates, use "not stated" (put the coordinates in sampling_location; do
  not work out the country). "not stated" if the paper doesn't say - never use the
  authors' institution's country.
- sampling_location: the site / locality where the PLANT was sampled, followed by the
  coordinates as written if the paper gives them (free text; "not
  stated" if not given - never put an institution here).
- coordinates_given: does the paper itself report latitude/longitude for the sampling site?
- sampling_location_status: explicit (stated directly) / inferable (from a named field site
  or region) / supplement (paper says location details are in supplementary material) /
  cited_work (paper says location details are in another cited study) / affiliation_only
  (only the authors' institution is given) / none (no geographic information at all).
- biome: WWF terrestrial biome(s) of the sampling site.
- n_distinct_pairs: number of distinct fungus x host-plant pairs the paper names.
- sterilisation_checked: if plant tissue was surface-sterilised (culture OR DNA work), was the
  sterilisation verified with a control (e.g. final rinse water plated or sequenced)?
  not_sterilised if tissue was processed without sterilisation; not_applicable_external if no
  plant tissue was processed in this study.
- fungus_source: where the fungi came from - from_study_plants (isolated / detected from plants
  sampled in this study), external (culture collection or another study, then put onto plants
  here), external_not_inoculated (culture collection or another study, not put onto plants),
  both, or not_stated.
- detection_methods: every method used to show the fungus was inside the plant.
- community_summary: for metabarcoding, one line - host, tissue, richness (e.g. "142
  OTUs / 38 genera"), dominant taxa. Empty otherwise.

INTERACTIONS - one object per DISTINCT fungus x host-plant pair the paper NAMES:
- fungus, host_plant: VERBATIM as the authors write them (do not update old names).
- tissue: list every plant part this pair was found in. If the paper only says "shoots" or
  "aerial parts" without separating them, use aerial_parts (do not guess leaf / stem).
- fungal_lifestyle: how the fungus lives in this interaction (trophic mode). This is a
  SEPARATE question from effect_on_host - a plant_pathogen can be present with
  no_symptoms_not_tested.
- effect_on_host: net outcome for THIS plant, as the paper reports it.
- evidence_basis: how effect_on_host was established (if effect_on_host is not_reported,
  how the fungal_lifestyle was established): experimentally tested here, observed here,
  inferred from the taxon's reputation, or just asserted?
For a metabarcoding community, name only the dominant few taxa and put the rest in
community_summary.
"""


def build_prompt(segment_text: str, *, doc_type: str, doi: str = "") -> str:
    stage = ("You are reading the FULL TEXT (or a segment of it)."
             if doc_type == "fulltext"
             else "You are reading ONLY an abstract. Expect to answer 'not stated' often.")
    return (f"{PROMPT_HEADER}\n{stage}\nPaper DOI: {doi or 'unknown'}\n\n"
            f"TEXT TO ANALYSE:\n\"\"\"\n{segment_text}\n\"\"\"\n")


if __name__ == "__main__":
    # self-checks
    import json as _json
    assert set(METHOD_COL_TO_TOKEN.values()) <= set(DETECTION_METHODS), (
        set(METHOD_COL_TO_TOKEN.values()) - set(DETECTION_METHODS))
    for fld, m in HUMAN_TO_TOKEN.items():
        canon = {"tissue": TISSUE, "fungal_lifestyle": FUNGAL_LIFESTYLE,
                 "effect_on_host": EFFECT_ON_HOST, "evidence_basis": EVIDENCE_BASIS,
                 "primary_aim": PRIMARY_AIM, "sampling_approach": SAMPLING_APPROACH,
                 "language": LANGUAGE, "sampling_location_status": SAMPLING_LOCATION_STATUS,
                 "strain_variation": STRAIN_VARIATION, "biome": BIOME,
                 "sterilisation_checked": STERILISATION_CHECKED,
                 "fungus_source": FUNGUS_SOURCE}[fld]
        bad = set(m.values()) - set(canon)
        assert not bad, f"{fld}: {bad}"
    print("schema self-check OK")
    print(f"schema version {SCHEMA_VERSION}, {len(EXTRACTION_SCHEMA['properties'])} paper fields")
    print(_json.dumps(EXTRACTION_SCHEMA, indent=2)[:400], "...")
