#!/usr/bin/env python3
# BMB 2026-11-05 (Thread B). PROOF-OF-CONCEPT runner for the v6 staged extraction design
# (NPH_extraction_v6_design.md). Local models only: talks to a vLLM OpenAI-compatible server
# (`vllm serve`) or to Ollama - nothing hosted. Written for <= ~50 papers; it is deliberately
# NOT the production pipeline (no sharding, no PDF/OCR cache, no WWF biome lookup yet).
#
# STATUS: plumbing is unit-tested with `--backend mock` only. It has NOT been run against a
# real vLLM/Ollama server - the first real run is the proof of concept itself (needs Bea's OK
# for the GPU job; see NPH_v6_poc_plan.md).
#
# Stages (per paper):
#   0  deterministic: coordinate regex, language guess, candidate-name regex, section split
#   1  paper-level pass  -> "paper card" (Q1-Q11 equivalents, methods, study hosts)
#   2  entity pass per chunk -> fungus x host x tissue + verbatim evidence quote; union + dedup
#   3  per-pair classification (lifestyle / effect / evidence basis) from that pair's evidence
#   4  verification: every judgment quote must be a verbatim substring of the text the model
#      saw (normalised); optional quote-only re-derivation; consistency flags
#
# Field names and vocabularies are IMPORTED from extract_schema.py (locked to the reviewer
# workbook). Two things the workbook has that extract_schema.py v5.4 lacks are emitted here as
# PROPOSED additions and are flagged in the design doc, not silently adopted:
#   - evidence_basis split into evidence_basis_effect / evidence_basis_lifestyle (workbook has two
#     columns per block; extract_schema.py has one)
#   - ubiquity_claim (workbook Q11) and inoculation (4-level), methods as yes/no/not_stated
#
# Usage (see run_v6_poc.sbatch):
#   python extract_v6_poc.py --mode fulltext --input dev_set_selected.csv --pdf-dir ~/dev_pdfs \
#       --prefix 25 --backend openai --base-url http://127.0.0.1:8000/v1 --model <served-name> \
#       --concurrency 16 --out-dir results/v6_poc/qwen32b_vllm

from __future__ import annotations

import argparse
import concurrent.futures as cf
import gzip
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import threading
import time
import unicodedata
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_schema as S          # noqa: E402  (vocabularies are LOCKED here)

try:
    import requests                 # noqa: E402
except Exception:                   # pragma: no cover
    requests = None

PIPELINE_VERSION = "v6-poc-0.1"
TIMEOUT_EXC = requests.exceptions.Timeout if requests else TimeoutError

# ============================================================================ vocab (additions)

METHOD_STATUS = ["yes", "no", "not_stated"]
INOCULATION = ["yes_confirmed_inside", "yes_not_confirmed", "no", "not_stated"]
TEXT_STATUS = ["complete", "review_or_compilation", "not_fungus_in_plant_study"]
ABSENCE_LABELS = {"not_stated", "no", "not_reported", "unclear", "none", "not_applicable_external",
                  "cannot_tell", "not_sterilised", "single_strain", "not_clear", "no_check"}

# ============================================================================ schema builders


def _enum(vals):
    return {"type": "string", "enum": list(vals)}


def judged(props: dict, req: list, name: str, vals) -> None:
    """quote FIRST, label second: with constrained decoding the property order is the
    generation order, so the model must produce the evidence before it commits to a label."""
    props[f"{name}_quote"] = {"type": "string"}
    props[name] = _enum(vals)
    req += [f"{name}_quote", name]


def stage1_schema() -> dict:
    p, r = {}, []
    judged(p, r, "text_status", TEXT_STATUS)
    judged(p, r, "primary_aim", S.PRIMARY_AIM)
    judged(p, r, "fungus_source", S.FUNGUS_SOURCE)
    judged(p, r, "sampling_approach", S.SAMPLING_APPROACH)
    judged(p, r, "uncultured_taxa", S.YES_NO_UNCLEAR)
    judged(p, r, "strain_variation", S.STRAIN_VARIATION)
    judged(p, r, "location_status", S.SAMPLING_LOCATION_STATUS)
    judged(p, r, "sterilisation_checked", S.STERILISATION_CHECKED)
    judged(p, r, "ubiquity_claim", ["yes", "no"])
    judged(p, r, "inoculation", INOCULATION)
    for m in ("culture_sterilised", "microscopy_in_tissue", "direct_sequencing", "isolate_id_sequencing"):
        judged(p, r, f"method_{m}", METHOD_STATUS)
    p["country_quote"] = {"type": "string"}
    p["country_named"] = {"type": "string"}          # as the text names it, else "not stated"
    p["coordinates_quote"] = {"type": "string"}
    p["coordinates_text"] = {"type": "string"}       # verbatim, "" if none
    p["habitat_quote"] = {"type": "string"}
    p["habitat_text"] = {"type": "string"}           # verbatim habitat words, "not stated" if none
    p["biome_text"] = {"type": "array", "items": _enum(S.BIOME)}
    p["study_hosts"] = {"type": "array", "items": {"type": "string"}}
    p["community_summary"] = {"type": "string"}
    r += ["country_quote", "country_named", "coordinates_quote", "coordinates_text",
          "habitat_quote", "habitat_text", "biome_text", "study_hosts", "community_summary"]
    return {"type": "object", "properties": p, "required": r}


def stage2_schema() -> dict:
    item = {"type": "object", "properties": {
        "evidence_quote": {"type": "string"},        # sentence / table row naming the fungus
        "fungus": {"type": "string"}, "host_plant": {"type": "string"},
        "tissue": {"type": "array", "items": _enum(S.TISSUE)}},
        "required": ["evidence_quote", "fungus", "host_plant", "tissue"]}
    return {"type": "object", "properties": {"entities": {"type": "array", "items": item}},
            "required": ["entities"]}


def stage3_schema() -> dict:
    p, r = {"pair_id": {"type": "integer"}}, ["pair_id"]
    judged(p, r, "lifestyle", S.FUNGAL_LIFESTYLE)
    judged(p, r, "effect", S.EFFECT_ON_HOST)
    p["evidence_basis_effect"] = _enum(S.EVIDENCE_BASIS)
    p["evidence_basis_lifestyle"] = _enum(S.EVIDENCE_BASIS)
    r += ["evidence_basis_effect", "evidence_basis_lifestyle"]
    return {"type": "object", "properties": {"items": {"type": "array", "items": {
        "type": "object", "properties": p, "required": r}}}, "required": ["items"]}


# ============================================================================ prompts

COMMON_RULES = """Record what THIS text says, not what you know about the organism. If the text does
not say something, use the not-stated / unclear / not-reported option. Every field named
*_quote must be copied EXACTLY, character for character, from the text below (<= 250 characters),
or be an empty string when the answer is an absence ("not stated", "no", "not reported", ...).
Never paraphrase a quote. Never invent a quote."""

STAGE1_PROMPT = COMMON_RULES + """

You are reading the title, abstract and (when present) the introduction start, methods, table/figure
captions and keyword-matched passages of ONE paper. Fill the paper card.

- text_status: complete = authors report fungi found in, grown from, or put onto plants (plant disease
  papers, chemistry/genome papers about a fungus the authors call an endophyte, fungi in algae/lichens/
  mosses/ferns all count). review_or_compilation = review/opinion/secondary analysis, no primary data.
  not_fungus_in_plant_study = bacteria only, fungicide residues, fungi on dead plant material in the lab
  with no living plant, plant extracts only, fungi from soil/buildings/animals with no plant.
- primary_aim: the purpose the paper leads with.
- fungus_source: from_study_plants = isolated/detected from plants sampled in this study (still true if
  later put back onto plants); external = culture collection / company / earlier study, then put onto
  plants here; external_not_inoculated = collection or earlier study, only grown in the lab; both; not_stated.
- sampling_approach: few_isolates / culture_survey / metabarcoding / direct_observation / mixed / review.
- uncultured_taxa: yes only if fungi detected ONLY by DNA and never cultured (OTU, ASV, clone, phylotype).
- strain_variation: yes if different strains/isolates of the SAME species differed (even if citing others);
  single_strain if the paper works with one isolate; else no.
- country_named: the country where the PLANT was collected, only if the text names it (a country adjective
  such as "Taiwanese plants" counts). A state/province/region WITHOUT its country does not count -> "not
  stated". Never use the authors' institution. Several: separate with "; ". Old names (USSR, Zaire) as written.
- coordinates_text: latitude/longitude of the sampling site exactly as written ("" if none; tables count).
- location_status: explicit (country or coordinates named) / inferable (a named site or region but no
  country or coordinates) / supplement / cited_work (text points elsewhere and gives nothing itself) /
  affiliation_only / none.
- habitat_text + biome_text: ONLY from habitat words in the text (rainforest -> tropical_moist_forest, dry
  forest -> tropical_dry_forest, temperate/boreal/conifer/plantation forest -> temperate_boreal_forest, just
  "forest" -> forest_unspecified, fynbos/chaparral/maquis -> mediterranean_scrub, savanna/cerrado ->
  tropical_grassland_savanna, prairie/steppe -> temperate_grassland_steppe, paramo/puna/alpine ->
  montane_grassland_alpine, desert -> desert_xeric, marsh/bog/wetland -> wetland_flooded_grassland, mangrove,
  tundra/polar, sea/coast/seaweed -> marine_coastal, crop/field/orchard -> agriculture_cultivated,
  garden/park/botanical garden -> urban_garden, only greenhouse/pots/lab -> greenhouse_growthchamber).
  NEVER guess a biome from the plant or the country; if no habitat is described use not_stated.
- sterilisation_checked: if tissue was surface-sterilised, was it VERIFIED with a control (final rinse water
  plated/sequenced, tissue imprint)? yes_control / no_check (sterilised, no check described) /
  not_sterilised / not_culture_based / not_applicable_external (no plant tissue processed here) / cannot_tell.
- methods (yes / no / not_stated; not_stated when the text does not describe its methods): cultured from
  surface-sterilised tissue; microscopy showing the fungus INSIDE tissue; DNA sequenced straight from tissue;
  isolate identified by sequencing a culture. inoculation: yes_confirmed_inside (inoculated and re-isolated /
  seen in tissue), yes_not_confirmed, no, not_stated.
- ubiquity_claim: yes ONLY if the text SAYS endophytes occur in all / nearly all / virtually all / every plant
  or are "ubiquitous". "Most", "many", "common", "widespread", "diverse" are NOT enough -> no.
- study_hosts: the plant(s) studied, verbatim as the authors write them ([] if none named).
- community_summary: for metabarcoding, one line (host, tissue, richness, dominant taxa); else "".
"""

STAGE2_PROMPT = COMMON_RULES + """

List every fungus x host-plant pair this TEXT SEGMENT names. One object per distinct pair.
- fungus: exactly as the authors write it (do not update old names). Keep qualifiers ("cf.", "sp. 1"). LEAVE
  OUT strain / collection codes ("Penicillium sclerotiorum PSU-A13" -> "Penicillium sclerotiorum"). A family
  or order counts if it is the only name. NOT names: group words ("endophytic fungi", "AM fungi", "dark
  septate endophytes") and DNA codes ("OTU 12", "uncultured fungus"). Fungi only: yeasts yes, bacteria
  (Bacillus, Pseudomonas, Streptomyces, ...) NO. Plants/animals are not fungi.
- host_plant: exactly as written (family names count; seaweed/alga/lichen counts). Use the study hosts below
  if the segment names the fungus but not the plant and the study has one host; otherwise "not stated".
- tissue: every plant part this pair was found in; "shoots"/"aerial parts" not separated -> aerial_parts.
- evidence_quote: the sentence or table row, copied exactly, that names the fungus (with its host if there).
For a metabarcoding table name only fungi the text names individually (cap 40 per segment); the rest is
summarised elsewhere. If the segment names no fungus, return {"entities": []}.
"""

STAGE3_PROMPT = COMMON_RULES + """

Classify each numbered fungus-plant pair below using ONLY the evidence given for that pair and the paper
card. Two SEPARATE questions:
- lifestyle: how the fungus lives in this interaction: endophyte (inside living tissue; also when the text
  just calls it "endophytic"), latent_pathogen (harmless now, shown/said to turn pathogenic later),
  plant_pathogen, saprotroph, mycorrhizal, mycoparasite (attacks other microbes), epiphyte (surface only),
  lichenised, context_dependent, unclear.
- effect: net outcome for THIS plant as the paper reports it: not_reported (fungus just isolated/detected),
  no_symptoms_not_tested (healthy/symptomless stated, benefit or harm not tested), commensal (plant response
  MEASURED, no net effect), beneficial, harmful (disease / reduced fitness), context_dependent, unclear.
  A plant pathogen can be present with no_symptoms_not_tested.
- evidence_basis_effect: how the EFFECT was shown: experimental (an experiment in this study),
  observational (seen/measured here, no manipulation), inferred_from_taxon (other studies or the fungus's
  reputation), asserted (stated, no support), not_stated. Use not_stated when effect is not_reported.
- evidence_basis_lifestyle: the same, for the LIFESTYLE. Common cases: isolated/detected from a plant in this
  study -> observational; only CALLED "an endophytic fungus" with no support -> asserted; called an
  endophyte AND cites an earlier study -> inferred_from_taxon.
lifestyle_quote / effect_quote: copy the supporting sentence exactly, or "" when the label is an absence.
"""

PROMPT_HASHES = {n: hashlib.sha256(t.encode()).hexdigest()[:12] for n, t in
                 (("stage1", STAGE1_PROMPT), ("stage2", STAGE2_PROMPT), ("stage3", STAGE3_PROMPT))}

# ============================================================================ deterministic helpers

_LIG = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"}
_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                         "–": "-", "—": "-", "−": "-", " ": " ", "­": ""})


def norm_text(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    for k, v in _LIG.items():
        s = s.replace(k, v)
    s = s.translate(_QUOTES).lower()
    s = re.sub(r"-\s*\n\s*", "", s)               # hyphenation at line breaks
    s = re.sub(r"[*_`#>|]", " ", s)               # markdown emphasis / table pipes from pymupdf4llm
    return re.sub(r"\s+", " ", s).strip()


def quote_supported(quote: str, source_norm: str) -> str:
    """-> 'exact' | 'fuzzy' | 'none' | 'empty'."""
    q = norm_text(quote)
    if not q:
        return "empty"
    if q in source_norm:
        return "exact"
    try:
        from rapidfuzz import fuzz
        if len(q) >= 25 and fuzz.partial_ratio(q, source_norm) >= 92:
            return "fuzzy"
    except Exception:                               # noqa: BLE001
        pass
    return "none"


STRAIN_CODE = re.compile(r"\b(?:[A-Z]{2,6}[- ]?\d[\w.\-]*|\d+[A-Z]+[\w\-]*|CBS\s*\d+[\d.]*|ATCC\s*\d+)\b")


def name_key(name: str) -> str:
    s = re.sub(r"\(.*?\)", " ", str(name or ""))
    s = re.sub(r"\b(?:cf|aff|sensu lato|s\.l|nom\.?|nov|comb)\b\.?", " ", s, flags=re.I)
    s = STRAIN_CODE.sub(" ", s)
    toks = re.findall(r"[A-Za-zÀ-ɏ\-]+", s)
    toks = [t.lower() for t in toks][:2]
    if len(toks) == 2 and toks[1] in ("sp", "spp"):
        toks = toks[:1] + ["sp"]
    return " ".join(toks)


def host_key(name: str) -> str:
    return re.sub(r"[^a-z ]", "", str(name or "").lower()).strip()


COORD_RE = re.compile(
    r"(?P<lat>\d{1,2}(?:[.,]\d+)?\s*[°º]\s*(?:\d{1,2}(?:[.,]\d+)?\s*['′]\s*)?"
    r"(?:\d{1,2}(?:[.,]\d+)?\s*(?:\"|″|'')\s*)?[NS])[\s,;/]+"
    r"(?P<lon>\d{1,3}(?:[.,]\d+)?\s*[°º]\s*(?:\d{1,2}(?:[.,]\d+)?\s*['′]\s*)?"
    r"(?:\d{1,2}(?:[.,]\d+)?\s*(?:\"|″|'')\s*)?[EW])")
DEC_RE = re.compile(r"(?<![\d.])(-?\d{1,2}\.\d{3,})\s*[,;/ ]\s*(-?\d{1,3}\.\d{3,})(?![\d.])")


def _dms(tok: str) -> float | None:
    nums = [float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", tok)]
    if not nums:
        return None
    v = sum(n / (60 ** i) for i, n in enumerate(nums[:3]))
    return -v if tok.strip().upper().endswith(("S", "W")) else v


def find_coordinates(text: str) -> list[dict]:
    """Regex proposals only; the LLM decides which one (if any) is the SAMPLING site."""
    out = []
    for m in COORD_RE.finditer(text):
        la, lo = _dms(m.group("lat")), _dms(m.group("lon"))
        if la is not None and lo is not None and abs(la) <= 90 and abs(lo) <= 180:
            out.append({"text": m.group(0), "lat": round(la, 5), "lon": round(lo, 5)})
    for m in DEC_RE.finditer(text):
        la, lo = float(m.group(1)), float(m.group(2))
        if abs(la) <= 90 and abs(lo) <= 180:
            out.append({"text": m.group(0), "lat": la, "lon": lo})
    return out


EN_STOP = {"the", "of", "and", "in", "to", "was", "were", "with", "from", "that", "for", "by", "is"}


def guess_language(text: str) -> str:
    toks = re.findall(r"[A-Za-zÀ-ɏ]+", text[:6000].lower())
    if len(toks) < 30:
        return "unclear"
    r = sum(t in EN_STOP for t in toks) / len(toks)
    return "english" if r > 0.12 else "non_english"


BINOM = re.compile(r"\b([A-Z][a-z]{3,})\s+([a-z]{4,})\b")


def candidate_names(text: str, genera: set | None = None) -> Counter:
    """Capitalised-binomial candidates; with a genus whitelist (COL fungi) this is the recall audit."""
    c = Counter()
    for g, e in BINOM.findall(text):
        if genera is None or g in genera:
            c[f"{g} {e}"] += 1
    return c


KW_WINDOWS = {
    "geo": re.compile(r"(?i)\b(?:latitude|longitude|coordinates|collected (?:from|in|at)|sampled (?:from|in|at)|"
                      r"study (?:site|area)|field site|located (?:in|at)|national park|reserve)\b|\d\s*[°º]"),
    "steril": re.compile(r"(?i)steril[iz]|final rinse|imprint|sterility (?:check|control)|bleach|hypochlorite|ethanol"),
    "ubiq": re.compile(r"(?i)ubiquit|all plants|every plant|virtually all|nearly all|all (?:land )?plant species|"
                       r"(?:found|occur|present) in (?:all|every)"),
    "inoc": re.compile(r"(?i)inoculat|re-?isolat|koch.?s postulates|seedlings were (?:treated|exposed)"),
}


def kw_windows(text: str, cap: int = 5000, width: int = 350) -> str:
    spans = []
    for rx in KW_WINDOWS.values():
        for m in rx.finditer(text):
            spans.append((max(0, m.start() - width), min(len(text), m.end() + width)))
    spans.sort()
    merged = []
    for a, b in spans:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    out, n = [], 0
    for a, b in merged:
        seg = text[a:b].strip()
        out.append(seg)
        n += len(seg)
        if n >= cap:
            break
    return "\n...\n".join(out)[:cap]


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\[(])|\n{2,}", text) if s.strip()]


EFFECT_TRIG = re.compile(r"(?i)pathogen|symptom|disease|lesion|inoculat|growth|beneficial|promot|biocontrol|"
                         r"antagonis|latent|asymptomatic|healthy|virulen|colon[iz]|protect|tolerance|stress")


def evidence_windows(ent: dict, text: str, host_hint: str, cap: int = 3500) -> str:
    sents = sentences(text)
    g = ent["fungus"].split()[0] if ent["fungus"] else ""
    pat = [re.escape(ent["fungus"])] if ent["fungus"] else []
    if g and len(g) > 3:
        pat.append(re.escape(g[0]) + r"\.\s+" + re.escape(" ".join(ent["fungus"].split()[1:2]) or "zzzz"))
        pat.append(re.escape(g))
    rx = re.compile("|".join(pat), re.I) if pat else None
    hits = [i for i, s in enumerate(sents) if rx and rx.search(s)]
    picked, seen = [], set()
    for i in hits[:8]:
        for j in (i - 1, i, i + 1):
            if 0 <= j < len(sents) and j not in seen:
                seen.add(j)
                picked.append(j)
    if host_hint and ent.get("host_plant", "").lower() not in ("", "not stated"):
        hr = re.compile(re.escape(ent["host_plant"].split()[0]), re.I)
        for i, s in enumerate(sents):
            if i not in seen and hr.search(s) and EFFECT_TRIG.search(s) and len(picked) < 24:
                seen.add(i)
                picked.append(i)
    out = "\n".join(sents[j] for j in sorted(set(picked)))
    return out[:cap]


# ============================================================================ LLM client


class LLM:
    def __init__(self, backend, base_url, model, seed, num_ctx, timeout, max_tokens):
        self.backend, self.base, self.model = backend, base_url.rstrip("/"), model
        self.seed, self.num_ctx, self.timeout, self.max_tokens = seed, num_ctx, timeout, max_tokens
        self.lock = threading.Lock()
        self.log: list[dict] = []

    # ---- one schema-constrained call; returns (obj | None, meta)
    def call(self, stage: str, paper: str, prompt: str, schema: dict, mock_fn=None):
        t0, meta = time.time(), {"stage": stage, "paper": paper,
                                 "prompt_sha": hashlib.sha256(prompt.encode()).hexdigest()[:12],
                                 "prompt_chars": len(prompt)}
        obj, raw, status = None, "", "ok"
        for attempt in (1, 2):
            try:
                if self.backend == "mock":
                    obj = mock_fn(prompt) if mock_fn else {}
                    raw, status = json.dumps(obj), "ok"
                    meta.update(prompt_tokens=len(prompt) // 4, completion_tokens=len(raw) // 4)
                elif self.backend == "openai":
                    r = requests.post(self.base + "/chat/completions", timeout=self.timeout, json={
                        "model": self.model, "temperature": 0, "seed": self.seed,
                        "max_tokens": self.max_tokens,
                        "messages": [{"role": "user", "content": prompt}],
                        "response_format": {"type": "json_schema", "json_schema": {
                            "name": stage, "schema": schema, "strict": True}}})
                    r.raise_for_status()
                    j = r.json()
                    raw = j["choices"][0]["message"]["content"] or ""
                    u = j.get("usage", {})
                    meta.update(prompt_tokens=u.get("prompt_tokens"),
                                completion_tokens=u.get("completion_tokens"),
                                finish=j["choices"][0].get("finish_reason"))
                    obj = json.loads(raw)
                else:                                                   # ollama
                    r = requests.post(self.base + "/api/chat", timeout=self.timeout, json={
                        "model": self.model, "stream": False, "format": schema,
                        "messages": [{"role": "user", "content": prompt}],
                        "options": {"temperature": 0, "seed": self.seed, "num_ctx": self.num_ctx,
                                    "num_predict": self.max_tokens}})
                    r.raise_for_status()
                    j = r.json()
                    raw = j.get("message", {}).get("content", "")
                    meta.update(prompt_tokens=j.get("prompt_eval_count"),
                                completion_tokens=j.get("eval_count"),
                                finish=j.get("done_reason"))
                    obj = json.loads(raw)
                status = "ok" if attempt == 1 else "ok_retry"
                break
            except json.JSONDecodeError:
                status, obj = "malformed", None
            except TIMEOUT_EXC:
                status, obj = "timeout", None
            except Exception as e:                                      # noqa: BLE001
                status, obj = f"error:{type(e).__name__}", None
        meta.update(status=status, seconds=round(time.time() - t0, 2))
        with self.lock:
            self.log.append({**meta, "response": raw[:20000]})
        return obj, meta


def _mock_stage1(_p):
    d = {"text_status": "complete", "primary_aim": "endophyte_ecology", "fungus_source": "from_study_plants",
         "sampling_approach": "culture_survey", "uncultured_taxa": "no", "strain_variation": "no",
         "location_status": "none", "sterilisation_checked": "cannot_tell", "ubiquity_claim": "no",
         "inoculation": "not_stated", "country_named": "not stated", "coordinates_text": "",
         "habitat_text": "not stated", "biome_text": ["not_stated"], "study_hosts": [], "community_summary": ""}
    for m in ("culture_sterilised", "microscopy_in_tissue", "direct_sequencing", "isolate_id_sequencing"):
        d[f"method_{m}"] = "not_stated"
    for k in list(stage1_schema()["properties"]):
        if k.endswith("_quote"):
            d[k] = ""
    return d


def _mock_stage2(prompt):
    m = re.search(r'"""\n(.*?)\n"""', prompt, re.S)
    first = (sentences(m.group(1)) or [""])[0][:200] if m else ""
    return {"entities": [{"evidence_quote": first, "fungus": "Xylaria sp.", "host_plant": "not stated",
                          "tissue": ["leaf"]}]}


def _mock_stage3(prompt):
    ids = [int(x) for x in re.findall(r"^PAIR (\d+):", prompt, re.M)]
    return {"items": [{"pair_id": i, "lifestyle_quote": "", "lifestyle": "endophyte", "effect_quote": "",
                       "effect": "not_reported", "evidence_basis_effect": "not_stated",
                       "evidence_basis_lifestyle": "observational"} for i in ids]}


# ============================================================================ text preparation

HEAD_METH = ("material", "method", "experimental", "study site", "study area", "sampling", "site description")
HEAD_INTRO = ("introduction", "background")


def prepare_text(row: dict, mode: str, pdf_dir: Path | None, max_chars: int) -> dict:
    title, abstract = str(row.get("title") or ""), str(row.get("abstract") or "")
    if mode == "abstract":
        body = f"TITLE: {title}\nABSTRACT: {abstract}"
        return {"ok": True, "stage1_text": body, "chunks": [body], "full_text": body, "n_pages": None,
                "note": "abstract"}
    import pdf_segment                                                    # lazy: needs PyMuPDF
    fn = row.get("pdf_filename")
    path = (pdf_dir / f"{row['row_id']}.pdf") if (pdf_dir and (pdf_dir / f"{row['row_id']}.pdf").exists()) \
        else (pdf_dir / str(fn) if pdf_dir and fn else None)
    if not path or not Path(path).exists():
        return {"ok": False, "note": f"pdf not found ({row['row_id']}.pdf / {fn})"}
    parsed = pdf_segment.parse_pdf(path, ocr=False)
    if not parsed["ok"]:
        return {"ok": False, "note": f"unusable pdf: {parsed['parser']} {parsed.get('error', '')}",
                "n_pages": parsed["n_pages"]}
    secs = pdf_segment._split_sections(parsed["text"])
    def pick(prefixes):
        return "\n\n".join(b for h, b in secs
                           if pdf_segment._norm_heading(h).startswith(prefixes) and b.strip())
    methods, intro = pick(HEAD_METH), pick(HEAD_INTRO)
    caps = "\n".join(p.strip() for p in re.split(r"\n\s*\n", parsed["text"])
                     if pdf_segment.TABLE_CAP_RE.match(p.strip()))[:4000]
    if not methods:                                       # heading detection failed -> whole-text prefix
        methods = parsed["text"][: max_chars]
    stage1 = (f"TITLE: {title}\nABSTRACT: {abstract}\n\nINTRODUCTION (start):\n{intro[:2500]}\n\n"
              f"METHODS:\n{methods[:max_chars]}\n\nTABLE/FIGURE CAPTIONS:\n{caps}\n\n"
              f"KEYWORD-MATCHED PASSAGES:\n{kw_windows(parsed['text'])}")
    chunks = pdf_segment.chunk_segments(pdf_segment.segment(parsed), doi=str(row["paper_id"]),
                                        max_chars=max_chars)
    return {"ok": True, "stage1_text": stage1, "chunks": chunks, "full_text": parsed["text"],
            "n_pages": parsed["n_pages"], "note": parsed["parser"]}


# ============================================================================ per-paper pipeline


def card_text(c: dict) -> str:
    keys = ("primary_aim", "fungus_source", "sampling_approach", "inoculation", "uncultured_taxa",
            "method_culture_sterilised", "method_direct_sequencing", "text_status")
    hosts = "; ".join(c.get("study_hosts") or []) or "not stated"
    return "; ".join(f"{k}={c.get(k)}" for k in keys) + f"; study_hosts={hosts}"


def run_paper(row: dict, llm: LLM, a, genera) -> dict:
    pid = str(row["paper_id"])
    rec = {"paper_id": pid, "row_id": row.get("row_id"), "mode": a.mode, "ok": False, "note": ""}
    t0 = time.time()
    prep = prepare_text(row, a.mode, a.pdf_dir, a.max_chars)
    rec["note"], rec["n_pages"] = prep.get("note", ""), prep.get("n_pages")
    if not prep["ok"]:
        return rec
    full_norm = norm_text(prep["full_text"])
    rec["language_guess"] = guess_language(prep["full_text"])
    coords = find_coordinates(prep["full_text"])
    rec["coord_candidates"] = coords[:10]

    # ---- stage 1
    p1 = (STAGE1_PROMPT + (f"\nREGEX-FOUND COORDINATE CANDIDATES (may not be the sampling site): "
                           f"{[c['text'] for c in coords[:6]]}\n" if coords else "")
          + f'\nTEXT TO ANALYSE:\n"""\n{prep["stage1_text"]}\n"""\n')
    s1, m1 = llm.call("stage1", pid, p1, stage1_schema(), _mock_stage1)
    s1_norm = norm_text(prep["stage1_text"])
    card = s1 or {}
    rec["card"], rec["stage1_status"] = card, m1["status"]
    qs = {}
    free = {"country": card.get("country_named"), "coordinates": card.get("coordinates_text"),
            "habitat": card.get("habitat_text")}
    for k in [k for k in card if k.endswith("_quote")]:
        lab = k[:-6]
        v = free[lab] if lab in free else card.get(lab)
        needs = bool(v) and str(v).strip().lower() not in ABSENCE_LABELS | {"not stated", "[]"}
        qs[lab] = {"needs_quote": needs, "support": quote_supported(card.get(k, ""), s1_norm)}
    rec["card_quote_checks"] = qs

    # ---- stage 2 (per chunk), union + dedup
    ents, n_chunk_bad = {}, 0
    host_ctx = "; ".join(card.get("study_hosts") or []) or "not stated"
    for ci, ch in enumerate(prep["chunks"]):
        p2 = (STAGE2_PROMPT + f"\nSTUDY HOSTS (from the methods): {host_ctx}\n"
              f'\nTEXT SEGMENT:\n"""\n{ch}\n"""\n')
        o2, m2 = llm.call("stage2", f"{pid}#{ci}", p2, stage2_schema(), _mock_stage2)
        if o2 is None:
            n_chunk_bad += 1
            continue
        ch_norm = norm_text(ch)
        for e in (o2.get("entities") or [])[:60]:
            fk, hk = name_key(e.get("fungus")), host_key(e.get("host_plant"))
            if not fk:
                continue
            sup = quote_supported(e.get("evidence_quote", ""), ch_norm)
            key = (fk, hk)
            cur = ents.setdefault(key, {**e, "tissue": set(), "n_chunks": 0, "quote_support": sup,
                                        "key": key})
            cur["tissue"] |= set(e.get("tissue") or [])
            cur["n_chunks"] += 1
            if cur["quote_support"] == "none" and sup != "none":
                cur.update(evidence_quote=e.get("evidence_quote", ""), quote_support=sup)
    # a fungus listed with a host AND with "not stated" -> drop the host-less duplicate
    byf = {}
    for (fk, hk) in ents:
        byf.setdefault(fk, set()).add(hk)
    for fk, hs in byf.items():
        if len(hs) > 1 and "notstated" in {h.replace(" ", "") for h in hs}:
            for h in list(hs):
                if h.replace(" ", "") == "notstated":
                    ents.pop((fk, h), None)
    title_n, abs_n = norm_text(str(row.get("title") or "")), norm_text(str(row.get("abstract") or ""))
    for e in ents.values():
        g = e["key"][0].split()[0]
        cnt = len(re.findall(re.escape(g), full_norm))
        e["listed_score"] = 3 * (g in title_n) + 2 * (g in abs_n) + min(cnt, 20) / 20
    ranked = sorted(ents.values(), key=lambda e: -e["listed_score"])
    for i, e in enumerate(ranked):
        e["listed_rank"] = i + 1
        e["tissue"] = sorted(e["tissue"])
    rec["n_entities"], rec["n_chunk_calls_bad"], rec["n_chunks"] = len(ranked), n_chunk_bad, len(prep["chunks"])

    # recall audit: capitalised binomials in the text that no entity covers (never auto-added)
    covered = {e["key"][0].split()[0] for e in ranked}
    cands = candidate_names(prep["full_text"], genera)
    rec["uncovered_name_candidates"] = [n for n, c in cands.most_common(60)
                                        if n.split()[0].lower() not in covered][:25]

    # ---- stage 3 (groups of <= 5 pairs; top 12 pairs per paper in the PoC)
    full_text = prep["full_text"]
    cls = {}
    todo = ranked[: a.max_pairs]
    for gi in range(0, len(todo), 5):
        grp = todo[gi:gi + 5]
        blocks = []
        for j, e in enumerate(grp):
            ev = evidence_windows(e, full_text, host_ctx)
            if not ev or len(ev) < 80:
                ev = f"{row.get('title') or ''}\n{row.get('abstract') or ''}"[:2500]
            e["_evidence"] = ev
            blocks.append(f"PAIR {gi + j}: fungus = {e['fungus']} | host = {e['host_plant']} | "
                          f"tissue = {','.join(e['tissue']) or 'not stated'}\nEVIDENCE:\n{ev}\n")
        p3 = (STAGE3_PROMPT + f"\nPAPER CARD: {card_text(card)}\n\n" + "\n".join(blocks))
        o3, m3 = llm.call("stage3", f"{pid}#g{gi}", p3, stage3_schema(), _mock_stage3)
        for it in ((o3 or {}).get("items") or []):
            cls[it.get("pair_id")] = it
    # ---- stage 4: mechanical verification + consistency flags (+ optional quote-only re-derivation)
    rows = []
    for i, e in enumerate(todo):
        it = cls.get(i, {})
        ev_norm = norm_text(e.get("_evidence", "")) + " " + full_norm if a.verify_against_full else \
            norm_text(e.get("_evidence", ""))
        chk = {}
        for lab in ("lifestyle", "effect"):
            v, q = it.get(lab), it.get(f"{lab}_quote", "")
            need = v is not None and str(v) not in ("unclear", "not_reported", "no_symptoms_not_tested") \
                and not (lab == "lifestyle" and v == "endophyte" and not q)
            chk[lab] = {"label": v, "needs_quote": need, "support": quote_supported(q, ev_norm)}
        flags = []
        for lab, c in chk.items():
            if c["needs_quote"] and c["support"] == "none":
                flags.append(f"{lab}_quote_unsupported")
        if it.get("effect") in ("beneficial", "harmful", "commensal") and it.get("evidence_basis_effect") == "not_stated":
            flags.append("effect_without_basis")
        if it.get("evidence_basis_effect") == "experimental" and card.get("inoculation") in ("no",):
            flags.append("experimental_but_no_inoculation")
        if a.reverify and it:
            for lab in ("lifestyle", "effect"):
                if chk[lab]["needs_quote"] and chk[lab]["support"] in ("exact", "fuzzy"):
                    vals = S.FUNGAL_LIFESTYLE if lab == "lifestyle" else S.EFFECT_ON_HOST
                    sch = {"type": "object", "properties": {"label": _enum(vals)}, "required": ["label"]}
                    o4, _ = llm.call("stage4_rederive", f"{pid}#{i}{lab}",
                                     f"Using ONLY this quote, choose the {lab}.\nQuote: {it.get(lab + '_quote')}\n"
                                     f"Options: {vals}", sch, lambda _p: {"label": vals[-1]})
                    if o4 and o4.get("label") != it.get(lab):
                        flags.append(f"{lab}_quote_label_mismatch")
        rows.append({"entity": {k: v for k, v in e.items() if k != "_evidence"}, "cls": it,
                     "checks": chk, "flags": flags})
    rec.update(ok=True, interactions=rows, seconds=round(time.time() - t0, 1))
    return rec


# ============================================================================ output

EXTRA_COLS = ["pipeline_version", "run_id", "arm", "listed_rank", "n_chunks_supporting", "entity_quote",
              "entity_quote_support", "evidence_basis_effect", "evidence_basis_lifestyle",
              "lifestyle_quote", "lifestyle_quote_support", "effect_quote", "effect_quote_support",
              "verification_flags", "text_status", "country_named", "country_resolved", "coordinates_text",
              "habitat_text", "biome_text", "wwf_biome_coords", "contains_ubiquity_claim", "inoculation",
              "study_hosts", "language_guess", "uncovered_name_candidates"]


def to_rows(rec: dict, run_id: str, arm: str, model: str = "") -> list[dict]:
    card = rec.get("card") or {}
    ds = "fulltext-reextract-v6" if rec["mode"] == "fulltext" else "abstract-reextract-v6"
    meths = [m for m in ("culture_sterilised", "microscopy_in_tissue", "direct_sequencing",
                         "isolate_id_sequencing") if card.get(f"method_{m}") == "yes"]
    if card.get("inoculation", "").startswith("yes"):
        meths.append("resynthesis_inoculation")
    coords = rec.get("coord_candidates") or []
    base = {
        "paper_id": rec["paper_id"], "doi": rec["paper_id"], "data_source": ds,
        "doc_type_ai": rec["mode"], "n_pages": rec.get("n_pages"), "schema_version": S.SCHEMA_VERSION + "+v6poc",
        "pipeline_version": PIPELINE_VERSION, "run_id": run_id, "arm": arm, "model": model,
        "n_chunks": rec.get("n_chunks"), "malformed_chunks": rec.get("n_chunk_calls_bad"),
        "is_fungus_in_plant_study": {"complete": "yes", "review_or_compilation": "no",
                                     "not_fungus_in_plant_study": "no"}.get(card.get("text_status"), "unclear"),
        "text_status": card.get("text_status"),
        "primary_aim": card.get("primary_aim"), "sampling_approach": card.get("sampling_approach"),
        "language": rec.get("language_guess"), "uncultured_taxa": card.get("uncultured_taxa"),
        "strain_variation": card.get("strain_variation"),
        "sampling_country": card.get("country_named"), "country_named": card.get("country_named"),
        "sampling_location": card.get("habitat_text"), "habitat_text": card.get("habitat_text"),
        "coordinates_given": "yes" if (card.get("coordinates_text") or "").strip() else "no",
        "coordinates_text": card.get("coordinates_text"),
        "sampling_location_status": card.get("location_status"),
        "biome": "|".join(card.get("biome_text") or []), "biome_text": "|".join(card.get("biome_text") or []),
        "sterilisation_checked": card.get("sterilisation_checked"), "fungus_source": card.get("fungus_source"),
        "detection_methods": "|".join(meths), "community_summary": card.get("community_summary"),
        "contains_ubiquity_claim": card.get("ubiquity_claim"), "inoculation": card.get("inoculation"),
        "study_hosts": "|".join(card.get("study_hosts") or []),
        "n_distinct_pairs": rec.get("n_entities"),
        "country_resolved": "", "wwf_biome_coords": "",     # TODO production: shapefile lookup from lat/lon
        "language_guess": rec.get("language_guess"),
        "uncovered_name_candidates": "|".join(rec.get("uncovered_name_candidates") or []),
    }
    out = []
    for it in rec.get("interactions") or []:
        e, c = it["entity"], it["cls"]
        eb_eff, eb_life = c.get("evidence_basis_effect"), c.get("evidence_basis_lifestyle")
        legacy_eb = eb_life if c.get("effect") in (None, "not_reported") else eb_eff   # reviewer-guide rule
        out.append({**base, "fungus": e["fungus"], "host_plant": e["host_plant"], "tissue": "|".join(e["tissue"]),
                    "fungal_lifestyle": c.get("lifestyle"), "effect_on_host": c.get("effect"),
                    "evidence_basis": legacy_eb, "evidence_basis_effect": eb_eff,
                    "evidence_basis_lifestyle": eb_life, "listed_rank": e["listed_rank"],
                    "n_chunks_supporting": e["n_chunks"], "entity_quote": e.get("evidence_quote"),
                    "entity_quote_support": e.get("quote_support"),
                    "lifestyle_quote": c.get("lifestyle_quote"), "effect_quote": c.get("effect_quote"),
                    "lifestyle_quote_support": it["checks"]["lifestyle"]["support"],
                    "effect_quote_support": it["checks"]["effect"]["support"],
                    "verification_flags": "|".join(it["flags"]),
                    "fungal_taxon": e["fungus"], "plant_host": e["host_plant"],
                    "primary_guild": S.LIFESTYLE_TO_LEGACY_GUILD.get(c.get("lifestyle"), "Unknown"),
                    "country": card.get("country_named"), "presence_absence": "Present"})
    if not out:
        out.append({**base, "presence_absence": "None Found"})
    return out


def sh(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, text=True,
                                       cwd=Path(__file__).resolve().parent).strip()
    except Exception:                                                     # noqa: BLE001
        return ""


def file_sha(p):
    try:
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]
    except Exception:                                                     # noqa: BLE001
        return ""


def server_info(llm: LLM) -> dict:
    info = {}
    if requests is None or llm.backend == "mock":
        return info
    try:
        if llm.backend == "openai":
            info["models"] = requests.get(llm.base + "/models", timeout=10).json()
            root = llm.base[: -3] if llm.base.endswith("/v1") else llm.base
            info["version"] = requests.get(root + "/version", timeout=10).json()
        else:
            info["version"] = requests.get(llm.base + "/api/version", timeout=10).json()
            tags = requests.get(llm.base + "/api/tags", timeout=10).json().get("models", [])
            info["model_digest"] = [{k: t.get(k) for k in ("name", "digest", "size")} for t in tags
                                    if t.get("name", "").startswith(llm.model.split(":")[0])]
            info["show"] = requests.post(llm.base + "/api/show", json={"model": llm.model}, timeout=10).json().get("details")
    except Exception as e:                                                # noqa: BLE001
        info["error"] = repr(e)
    return info


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["abstract", "fulltext"], required=True)
    ap.add_argument("--input", type=Path, required=True, help="dev_set_selected.csv (paper_id,row_id,title,abstract,pdf_filename,...)")
    ap.add_argument("--pdf-dir", type=Path, default=None)
    ap.add_argument("--prefix", type=int, default=25, help="use the first N rows (balanced PoC prefix)")
    ap.add_argument("--only-doc-type", choices=["full-text", "abstract-only"], default=None)
    ap.add_argument("--backend", choices=["openai", "ollama", "mock"], required=True)
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--model", default="mock")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--num-ctx", type=int, default=16384, help="ollama only; vLLM uses --max-model-len")
    ap.add_argument("--max-chars", type=int, default=24000, help="chars per chunk / stage-1 methods cap")
    ap.add_argument("--max-tokens", type=int, default=2048)
    ap.add_argument("--max-pairs", type=int, default=12)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--seed", type=int, default=20261105)
    ap.add_argument("--reverify", action="store_true", help="stage-4 quote-only label re-derivation")
    ap.add_argument("--verify-against-full", action="store_true",
                    help="accept a stage-3 quote found anywhere in the paper, not only in the shown evidence")
    ap.add_argument("--genus-list", type=Path, default=None, help="text file, one fungal genus per line (recall audit)")
    ap.add_argument("--arm", default="staged")
    ap.add_argument("--out-dir", type=Path, required=True)
    a = ap.parse_args()
    if a.backend != "mock" and requests is None:
        sys.exit("ERROR: `requests` not installed")
    a.base_url = a.base_url or ("http://127.0.0.1:11434" if a.backend == "ollama" else "http://127.0.0.1:8000/v1")
    a.out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(a.input, low_memory=False).sort_values("order")
    if a.only_doc_type:
        df = df[df["doc_type"] == a.only_doc_type]
    if a.mode == "fulltext":
        df = df[df["doc_type"] == "full-text"]
    df = df.head(a.prefix)
    genera = set(Path(a.genus_list).read_text().split()) if a.genus_list else None

    llm = LLM(a.backend, a.base_url, a.model, a.seed, a.num_ctx, a.timeout, a.max_tokens)
    run_id = time.strftime("%Y%m%dT%H%M%S") + "-" + hashlib.sha1(f"{a.model}{a.arm}{time.time()}".encode()).hexdigest()[:6]
    papers_path = a.out_dir / "papers.jsonl"
    done = set()
    if papers_path.exists():
        done = {json.loads(l)["paper_id"] for l in papers_path.read_text(encoding="utf8").splitlines() if l.strip()}
    todo = [r for r in df.to_dict("records") if str(r["paper_id"]) not in done]
    print(f"run {run_id}: {len(todo)} papers to do ({len(done)} already done) mode={a.mode} backend={a.backend} model={a.model}")

    manifest = {
        "run_id": run_id, "pipeline_version": PIPELINE_VERSION, "schema_version": S.SCHEMA_VERSION,
        "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "args": {k: str(v) for k, v in vars(a).items()},
        "git_commit": sh("git rev-parse HEAD"), "git_dirty": bool(sh("git status --porcelain")),
        "script_sha256": file_sha(__file__), "extract_schema_sha256": file_sha(Path(__file__).parent / "extract_schema.py"),
        "input_sha256": file_sha(a.input), "prompt_hashes": PROMPT_HASHES, "seed": a.seed,
        "host": platform.node(), "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "gpu": sh("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader"),
        "python": sys.version.split()[0], "server": server_info(llm),
        "sampling": {"temperature": 0, "seed": a.seed, "max_tokens": a.max_tokens, "num_ctx_ollama": a.num_ctx},
    }
    (a.out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf8")

    t0 = time.time()
    all_rows = []
    lock = threading.Lock()
    with cf.ThreadPoolExecutor(max_workers=a.concurrency) as ex, open(papers_path, "a", encoding="utf8") as pf:
        futs = {ex.submit(run_paper, r, llm, a, genera): r for r in todo}
        for fu in cf.as_completed(futs):
            r = futs[fu]
            try:
                rec = fu.result()
            except Exception as e:                                        # noqa: BLE001
                rec = {"paper_id": str(r["paper_id"]), "row_id": r.get("row_id"), "mode": a.mode, "ok": False,
                       "note": f"exception:{type(e).__name__}:{e}"}
            with lock:
                pf.write(json.dumps(rec, default=str) + "\n")
                pf.flush()
                all_rows.extend(to_rows(rec, run_id, a.arm, a.model) if rec.get("ok") else
                                [{"paper_id": rec["paper_id"], "doi": rec["paper_id"], "run_id": run_id,
                                  "arm": a.arm, "presence_absence": f"FAILED: {rec.get('note')}"}])
            print(f"  done {rec['paper_id']} ok={rec.get('ok')} {rec.get('seconds', '')}s {rec.get('note', '')[:60]}")
    wall = time.time() - t0

    cols = list(dict.fromkeys(S.CSV_COLUMNS + EXTRA_COLS))
    out_csv = a.out_dir / "v6_rows.csv"
    new = pd.DataFrame(all_rows).reindex(columns=cols)
    if out_csv.exists() and done:
        new = pd.concat([pd.read_csv(out_csv, low_memory=False), new])
    new.to_csv(out_csv, index=False)
    with gzip.open(a.out_dir / "raw_calls.jsonl.gz", "at", encoding="utf8") as g:
        for l in llm.log:
            g.write(json.dumps(l) + "\n")

    # ---- run statistics (this is the throughput / malformed-rate / quote-support table)
    L = pd.DataFrame(llm.log)
    stats = {"run_id": run_id, "wall_seconds": round(wall, 1), "papers": len(todo), "n_calls": len(L)}
    if len(L):
        per = {}
        for st, g in L.groupby("stage"):
            per[st] = {"calls": len(g), "non_ok": int((~g["status"].str.startswith("ok")).sum()),
                       "malformed": int((g["status"] == "malformed").sum()),
                       "timeouts": int((g["status"] == "timeout").sum()),
                       "prompt_tokens": int(g.get("prompt_tokens", pd.Series(dtype=float)).fillna(0).sum()),
                       "completion_tokens": int(g.get("completion_tokens", pd.Series(dtype=float)).fillna(0).sum()),
                       "mean_seconds": round(float(g["seconds"].mean()), 2),
                       "truncated_finish": int((g.get("finish", pd.Series(dtype=str)) == "length").sum())}
        stats["per_stage"] = per
        pt = sum(v["prompt_tokens"] for v in per.values())
        ct = sum(v["completion_tokens"] for v in per.values())
        stats.update(prompt_tokens=pt, completion_tokens=ct,
                     completion_tokens_per_s=round(ct / wall, 1) if wall else None,
                     papers_per_hour=round(len(todo) / wall * 3600, 1) if wall else None,
                     gpu_seconds_per_paper=round(wall / max(1, len(todo)), 1))
    rows = pd.DataFrame(all_rows)
    if len(rows) and "lifestyle_quote_support" in rows:
        for lab in ("lifestyle", "effect"):
            s = rows[f"{lab}_quote_support"].dropna()
            pos = s[s != "empty"]
            stats[f"{lab}_quote_support_rate_among_nonempty"] = (
                round(float(pos.isin(["exact", "fuzzy"]).mean()), 3) if len(pos) else None)
        stats["pairs_flagged"] = int((rows["verification_flags"].fillna("") != "").sum())
        stats["pairs_total"] = int(rows["fungus"].notna().sum())
    (a.out_dir / "run_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf8")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
