"""(scripts/04_analyses/restructure_groundtruth_workbooks.py, 2026-10-08)
Rebuild the Task 2 ground-truth workbooks to the 2026-10-08 column layout.

usage: python restructure.py TEMPLATE_IN OUT_DIR WORKBOOK [WORKBOOK ...]
TEMPLATE_IN = current MASTER (styles + country list). Each WORKBOOK keeps only its paper
rows (row_id, text_type, paper info, language prefill); every answer cell starts blank.
"""
import sys
from copy import copy
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill, Protection
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation

LISTS = {
    "yes_no": ["yes", "no"],
    "yn_unclear": ["yes", "no", "unclear"],
    "text_reviewed": ["in progress", "complete", "could not access the text (missing or unreadable)",
                      "review or secondary compilation - no primary data of its own",
                      "not a fungus-in-plant study"],
    "primary_aim": ["endophyte ecology / diversity / community",
                    "endophyte function: growth, nutrition, or stress tolerance",
                    "endophyte function: disease protection / biocontrol",
                    "natural products / secondary metabolites / bioprospecting",
                    "plant pathology (the fungus studied as a pathogen)",
                    "fungal taxonomy / systematics / new species",
                    "genomics / transcriptomics / methods development",
                    "other (type over this cell with your own answer)"],
    "fungus_source": ["isolated or detected from plants sampled in this study",
                      "from a culture collection or another study, then put onto plants here",
                      "from a culture collection or another study (not put onto plants here)",
                      "a mix of these", "not stated"],
    "language": ["English", "non-English (type over this cell, e.g. non-English: French)",
                 "English + non-English (type over this cell, e.g. English + French)", "unclear"],
    "strain_variation": ["yes - noted", "no - not noted", "only one strain / isolate studied"],
    "location_status": ["explicitly stated (country or coordinates)",
                        "inferable from a named site / region",
                        "the text says it is in a supplement",
                        "the text says it is in another cited study",
                        "only the authors' institution country is given",
                        "no geographic information at all"],
    "biome": ["tropical / subtropical moist forest", "tropical / subtropical dry forest",
              "temperate or boreal forest", "forest - type not stated",
              "Mediterranean forest / woodland / scrub",
              "tropical grassland / savanna / shrubland", "temperate grassland / steppe / prairie",
              "montane grassland / alpine", "desert / xeric shrubland",
              "wetland / flooded grassland / bog", "mangrove", "tundra / polar", "marine / coastal",
              "agriculture / cultivated (crop, orchard, plantation, sown pasture)",
              "urban / garden / botanical collection", "greenhouse / growth chamber / lab",
              "other (type over this cell with your own answer)", "not stated"],
    "sterilisation": ["yes - a check was done (e.g. final rinse water plated or sequenced)",
                      "no - sterilised, but no check described",
                      "no - tissue was not surface-sterilised",
                      "not applicable - no plant tissue processed in this study",
                      "unclear"],
    "method_status": ["yes", "no", "not stated"],
    "inoculation": ["yes - inoculated, and confirmed inside the plant (re-isolated or seen in tissue)",
                    "yes - inoculated, but not confirmed inside the plant", "no", "not stated"],
    "tissue": ["leaf", "root", "stem / wood / bark", "seed", "fruit", "flower / reproductive",
               "aerial parts / shoots (not separated)", "whole plant",
               "other (type over this cell, e.g. other: rhizosphere soil)", "not stated"],
    "fungal_lifestyle": ["endophyte (lives inside plant tissue)",
                         "latent pathogen (no symptoms now, causes disease later)",
                         "plant pathogen (causing disease)",
                         "saprotroph (on dead or dying plant material)",
                         "mycorrhizal (any type)",
                         "mycoparasite / antagonist of other microbes",
                         "epiphyte (surface only)", "lichenised",
                         "context-dependent (varies by host / environment / strain)",
                         "not clear from the text",
                         "other (type over this cell with your own answer)"],
    "effect_on_host": ["not reported (fungus just isolated / detected)",
                       "no visible symptoms; benefit or harm not tested",
                       "neutral / commensal (plant response tested; no net effect)",
                       "beneficial to the plant", "harmful to the plant (disease / reduced fitness)",
                       "context-dependent (varies by host / environment / strain)", "unclear",
                       "other (type over this cell with your own answer)"],
    "evidence_basis": ["experimentally tested in this study",
                       "observed / measured in this study (no manipulation)",
                       "from other studies or the fungus's reputation (not shown in this paper)",
                       "asserted with no support", "not stated",
                       "other (type over this cell with your own answer)"],
    # "country" is copied from the template's Lists sheet
}

FUNGUS_HDR = "fungus_{n} (name exactly as the authors write it)"
HOST_HDR = "host_plant_{n} (name exactly as the authors write it)"
EVID_HDR = ("evidence_basis_{n} (how the EFFECT was shown; if effect = not reported, how the "
            "LIFESTYLE was shown)")

# (key, header, width, list, group)   group: info / q / method / block1..5 / end
SPEC = [
    ("row_id", "row_id", 9, None, "info"),
    ("text_reviewed", "text_reviewed", 22, "text_reviewed", "info"),
    ("date_reviewed", "date_reviewed", 12, None, "info"),
    ("text_type", "text_type", 11, None, "info"),
    ("paper_id", "paper_id", 22, None, "hidden"),
    ("doi_link", "doi_link", 20, None, "hidden"),
    ("year", "year", 6, None, "hidden"),
    ("journal", "journal", 18, None, "hidden"),
    ("title", "title", 40, None, "info"),
    ("abstract", "abstract", 66, None, "info"),
    ("primary_aim", "Q1  paper's main purpose", 24, "primary_aim", "q"),
    ("fungus_source", "Q2  where did the fungi come from?", 26, "fungus_source", "q"),
    ("language", "Q3  language of the text you are reading", 16, "language", "q"),
    ("uncultured", "Q4  any sequence-only (uncultured) taxa? (detected only by DNA, never grown in "
                   "culture)", 18, "yn_unclear", "q"),
    ("strain", "Q5  strain-level variation noted?", 18, "strain_variation", "q"),
    ("country", "Q6a  COUNTRY where the plant was sampled (not the authors' institution)", 20,
     "country", "q"),
    ("coords", "Q6b  does the text give GPS coordinates for where the plant was sampled?", 18,
     "yes_no", "q"),
    ("loc_status", "Q7  what geographic information does the text contain?", 26,
     "location_status", "q"),
    ("biome", "Q8  biome where the plant was sampled (only if the text describes the habitat; "
              "otherwise not stated)", 24, "biome", "q"),
    ("n_pairs", "Q9  how many distinct fungus-host pairs does the text name? (each named fungus, "
                "once for each plant the text links it to; never count isolates or individual "
                "plants; one whole number)", 24, None, "q"),
    ("steril", "Q10  was the surface-sterilisation checked?", 24, "sterilisation", "q"),
    ("ubiquity", "Q11  does the text state that endophytes are found in all or nearly all "
                 "plants?", 20, "yes_no", "q"),
    ("m_culture", "Methods: cultured fungi from surface-sterilised tissue", 18, "method_status",
     "method"),
    ("m_micro", "Methods: performed microscopy on tissue", 18, "method_status", "method"),
    ("m_seq", "Methods: molecular (DNA) sequencing from tissue", 18, "method_status", "method"),
    ("m_isolate", "Methods: isolate ID by sequencing", 18, "method_status", "method"),
    ("m_inoc", "Methods: fungus inoculated onto a plant", 26, "inoculation", "method"),
]
for n in range(1, 6):
    g = f"block{n}"
    SPEC += [
        (f"fungus_{n}", FUNGUS_HDR.format(n=n), 22, None, g),
        (f"host_plant_{n}", HOST_HDR.format(n=n), 20, None, g),
        (f"tissue_{n}", f"tissue_{n}", 16, "tissue", g),
        (f"fungal_lifestyle_{n}", f"fungal_lifestyle_{n}", 22, "fungal_lifestyle", g),
        (f"effect_on_host_{n}", f"effect_on_host_{n}", 26, "effect_on_host", g),
        (f"evidence_basis_{n}", EVID_HDR.format(n=n), 26, "evidence_basis", g),
    ]
SPEC += [
    ("extra", "extra_pairs_or_NGS_community_summary (a count and a few words, no names needed, "
              "e.g. 9 more named pairs, all oak leaves; or 142 OTUs from oak leaves)", 40, None, "end"),
    ("unsure", "anything_you_were_unsure_about", 40, None, "end"),
]

FILLS = {"method": "E7E0EF", "block1": "EAF1F8", "block2": "EEF5E6", "block3": "EAF1F8",
         "block4": "EEF5E6", "block5": "EAF1F8"}
COPY_KEYS = {"row_id", "text_type", "paper_id", "doi_link", "year", "journal", "title",
             "abstract", "language"}


def old_key(header: str):
    h = str(header or "").strip().lower()
    if h in ("row_id", "text_reviewed", "date_reviewed", "paper_id", "doi_link", "year",
             "journal", "title", "abstract"):
        return h
    if h in ("text_type", "reading_stage"):
        return "text_type"
    if "language of the text" in h:
        return "language"
    return None


INSTRUCTIONS = [
    ("How to use this file", 20, True),
    ("", 14, False),
    ("1.  Keep the printed guide (the Word document sent with this file) beside you.", 14, False),
    ("     It explains every column, with examples.", 14, False),
    ("2.  Work in the Review tab, one row at a time, left to right.", 14, False),
    ("3.  Column D (text_type) tells you what to read:", 14, False),
    ("        abstract  = read only the abstract in that row. Do not open the PDF.", 14, False),
    ("        full text = open the PDF with the same name as the row (row K001b = K001b.pdf).", 14, False),
    ("4.  Pick answers from the drop-down lists. If the right answer is not listed,", 14, False),
    ("     type your own; Excel will warn you, click Yes to keep it.", 14, False),
    ("5.  When a row is finished, set column B (text_reviewed) to 'complete'.", 14, False),
    ("6.  The paper details (columns A and D to J) are locked so they can't be changed by", 14, False),
    ("     accident. If Excel says a cell is protected, you are in one of those columns.", 14, False),
    ("", 14, False),
    ("Work on your own. Please don't discuss the papers until everyone is done.", 14, False),
    ("Questions? Ask Bea before guessing.", 14, True),
]


def build(template_path: Path, src_path: Path, out_path: Path):
    tpl = openpyxl.load_workbook(template_path)
    tws = tpl["Review"]
    hdr_style = copy(tws["A1"]._style)
    data_style = copy(tws["A2"]._style)
    tl = tpl["Lists"]
    country = None
    for c in tl[1]:
        if c.value == "country":
            country = [tl.cell(r, c.column).value for r in range(2, tl.max_row + 1)]
            country = [v for v in country if v]
    assert country, "country list not found in template"

    src = openpyxl.load_workbook(src_path)
    sws = src["Review"]
    colmap = {}
    for c in sws[1]:
        k = old_key(c.value)
        if k and k not in colmap:
            colmap[k] = c.column
    rows = []
    for r in range(2, sws.max_row + 1):
        rid = sws.cell(r, colmap["row_id"]).value
        if rid in (None, "") or str(rid).strip().lower() == "x":
            continue
        rec = {}
        for k in COPY_KEYS:
            if k in colmap:
                rec[k] = sws.cell(r, colmap[k]).value
        rows.append(rec)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Review"
    # header
    for j, (key, header, width, lst, group) in enumerate(SPEC, start=1):
        cell = ws.cell(1, j, header)
        cell._style = copy(hdr_style)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        ws.column_dimensions[L(j)].width = width
        if group == "hidden":
            ws.column_dimensions[L(j)].hidden = True
    ws.row_dimensions[1].height = 75
    # data
    for i, rec in enumerate(rows, start=2):
        for j, (key, header, width, lst, group) in enumerate(SPEC, start=1):
            cell = ws.cell(i, j, rec.get(key))
            cell._style = copy(data_style)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if group in FILLS:
                cell.fill = PatternFill("solid", fgColor=FILLS[group])
        ws.row_dimensions[i].height = 150
    last = len(rows) + 1
    # lock the paper-info columns (A, D-J) so a pasted row cannot overwrite them; no password
    LOCKED = {"row_id", "text_type", "paper_id", "doi_link", "year", "journal", "title", "abstract"}
    for i in range(2, last + 1):
        for j, sp in enumerate(SPEC, start=1):
            ws.cell(i, j).protection = Protection(locked=sp[0] in LOCKED)
    ws.protection.sheet = True
    ws.protection.formatColumns = False      # still allowed: resize / unhide columns
    ws.protection.formatRows = False
    ws.protection.formatCells = False
    ws.freeze_panes = "E2"

    # Lists sheet
    lists = dict(LISTS)
    lists["country"] = country
    ls = wb.create_sheet("Lists")
    ref = {}
    for j, (name, vals) in enumerate(lists.items(), start=1):
        ls.cell(1, j, name)
        for i, v in enumerate(vals, start=2):
            ls.cell(i, j, v)
        ref[name] = f"Lists!${L(j)}$2:${L(j)}${len(vals) + 1}"
    ls.sheet_state = "hidden"

    # dropdowns (warning style: a typed answer is kept after the warning)
    by_list = {}
    for j, (key, header, width, lst, group) in enumerate(SPEC, start=1):
        if lst:
            by_list.setdefault(lst, []).append(f"{L(j)}2:{L(j)}{last}")
    for lst, ranges in by_list.items():
        dv = DataValidation(type="list", formula1=ref[lst], allow_blank=True,
                            showErrorMessage=True, errorStyle="warning",
                            errorTitle="Not in the list",
                            error="This answer is not in the list. Click Yes to keep it anyway.")
        for rg in ranges:
            dv.add(rg)
        ws.add_data_validation(dv)

    # Q9 must be a single whole number (no ranges)
    j9 = next(j for j, sp in enumerate(SPEC, start=1) if sp[0] == "n_pairs")
    dvn = DataValidation(type="whole", operator="greaterThanOrEqual", formula1="0",
                         allow_blank=True, showErrorMessage=True, errorStyle="warning",
                         errorTitle="Please type one number",
                         error="Q9 should be one whole number, e.g. 3 (not a range). Click Yes to keep it anyway.")
    dvn.add(f"{L(j9)}2:{L(j9)}{last}")
    ws.add_data_validation(dvn)

    # Instructions sheet (short pointer; the full guide is the Word document)
    ins = wb.create_sheet("Instructions")
    ins.column_dimensions["A"].width = 110
    for i, (text, size, bold) in enumerate(INSTRUCTIONS, start=1):
        c = ins.cell(i, 1, text)
        c.font = Font(size=size, bold=bold)
    wb.active = 0
    wb.save(out_path)
    return len(rows)


if __name__ == "__main__":
    tpl, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in sys.argv[3:]:
        p = Path(f)
        n = build(tpl, p, out_dir / p.name)
        print(f"{p.name}: {n} rows")
