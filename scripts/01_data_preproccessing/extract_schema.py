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
    "whole_plant", "other", "not_stated",
]

# how the fungus makes its living in this interaction (FungalTraits primary_lifestyle,
# Polme et al. 2020, condensed; the three endophyte types are merged - tissue records
# leaf vs root; the four mycorrhizal types are kept separate).
FUNGAL_LIFESTYLE = [
    "endophyte",                 # symptomless in living internal tissue
    "latent_pathogen",           # symptomless now, shown/known to turn pathogenic
    "plant_pathogen",            # causing disease in the studied interaction
    "wood_saprotroph",
    "litter_saprotroph",
    "soil_saprotroph",
    "other_saprotroph",          # dead/senescent tissue, type unspecified
    "arbuscular_mycorrhizal",
    "ectomycorrhizal",
    "ericoid_mycorrhizal",
    "orchid_mycorrhizal",
    "mycoparasite",              # antagonist of other fungi / microbes
    "epiphyte",                  # on the surface only
    "lichenised",
    "context_dependent",         # the paper says the lifestyle itself shifts
    "unclear",
]

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

SAMPLING_LOCATION_STATUS = [   # Q8
    "explicit",             # sampling location explicitly stated
    "inferable",            # inferable from a named field site / region
    "affiliation_only",     # only the authors' institutional country is given
    "none",                # no geographic information at all
]

STRAIN_VARIATION = [      # Q6
    "yes", "no", "single_strain",
]

# WWF terrestrial biomes (Olson et al. 2001), matching the Task 4 realm choice. Q9.
BIOME = [
    "tropical_moist_forest", "tropical_dry_forest",
    "temperate_boreal_forest", "mediterranean_scrub",
    "tropical_grassland_savanna", "temperate_grassland_steppe",
    "montane_grassland_alpine", "desert_xeric",
    "wetland_flooded_grassland", "mangrove", "tundra_polar", "marine_coastal",
    "agriculture_cultivated", "urban_garden", "greenhouse_growthchamber",
    "other", "not_stated",
]

STERILISATION_CHECKED = [   # Q11
    "yes_control",          # final rinse plated / tissue imprint / similar control
    "no_check",             # standard sterilisation, no check described
    "not_culture_based",
    "cannot_tell",
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
        "sampling_location": {"type": "string"},                 # Q7 free text / "not stated"
        "sampling_location_status": _enum(SAMPLING_LOCATION_STATUS),  # Q8
        "biome": {"type": "array", "items": _enum(BIOME)},       # Q9
        "n_distinct_pairs": {"type": "integer"},                 # Q10
        "sterilisation_checked": _enum(STERILISATION_CHECKED),   # Q11
        "detection_methods": {"type": "array", "items": _enum(DETECTION_METHODS)},
        "community_summary": {"type": "string"},   # for metabarcoding: richness, dominant taxa
        "interactions": {"type": "array", "items": INTERACTION_ITEM_SCHEMA},
    },
    "required": ["is_fungus_in_plant_study", "primary_aim", "sampling_approach",
                 "language", "sampling_location", "sampling_location_status",
                 "biome", "sterilisation_checked", "detection_methods", "interactions"],
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
    "uncultured_taxa", "strain_variation", "sampling_location",
    "sampling_location_status", "biome", "n_distinct_pairs", "sterilisation_checked",
    "detection_methods", "community_summary",
    # interaction-level (new names)
    "fungus", "host_plant", "tissue", "fungal_lifestyle", "effect_on_host",
    "evidence_basis", "interaction_notes",
    # legacy aliases (populated for back-compat)
    "fungal_taxon", "plant_host", "primary_guild", "country", "presence_absence",
]

SCHEMA_VERSION = "v5.0"

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
        "whole plant": "whole_plant", "other (type it)": "other",
        "not stated": "not_stated",
    },
    "fungal_lifestyle": {
        "endophyte (foliar, root, or dark-septate; symptomless in living tissue)": "endophyte",
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
        "not clear from the paper": "unclear",
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

# Task 2 method-tick column header -> DETECTION_METHODS token
METHOD_COL_TO_TOKEN = {
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
- sampling_location: where the PLANT was sampled (free text; "not stated" if only the
  authors' institution is given - never put an institution here).
- sampling_location_status: how that location is known.
- biome: WWF terrestrial biome(s) of the sampling site.
- n_distinct_pairs: number of distinct fungus x host-plant pairs the paper names.
- sterilisation_checked: was surface-sterilisation verified with a control?
- detection_methods: every method used to show the fungus was inside the plant.
- community_summary: for metabarcoding, one line - host, tissue, richness (e.g. "142
  OTUs / 38 genera"), dominant taxa. Empty otherwise.

INTERACTIONS - one object per DISTINCT fungus x host-plant pair the paper NAMES:
- fungus, host_plant: VERBATIM as the authors write them (do not update old names).
- tissue: list every plant part this pair was found in.
- fungal_lifestyle: how the fungus lives in this interaction (trophic mode). This is a
  SEPARATE question from effect_on_host - a plant_pathogen can be present with
  no_symptoms_not_tested.
- effect_on_host: net outcome for THIS plant, as the paper reports it.
- evidence_basis: was the lifestyle+effect experimentally tested here, observed here,
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
                 "sterilisation_checked": STERILISATION_CHECKED}[fld]
        bad = set(m.values()) - set(canon)
        assert not bad, f"{fld}: {bad}"
    print("schema self-check OK")
    print(f"schema version {SCHEMA_VERSION}, {len(EXTRACTION_SCHEMA['properties'])} paper fields")
    print(_json.dumps(EXTRACTION_SCHEMA, indent=2)[:400], "...")
