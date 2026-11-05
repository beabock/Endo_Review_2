#!/usr/bin/env python3
# BMB 2026-09-21
# Renders results/manual_validation/groundtruth/guild_rubric.md as a "Rubric" tab inside
# the annotation workbooks, so the rubric can't get separated from the sheet.
#
#   as a module:  add_rubric_sheet(wb)            (used by build_groundtruth_sample.py)
#   as a CLI:     python rubric_sheet.py [files]  patches existing workbooks in place
#                 (adds/replaces the Rubric tab; does not touch any other sheet)

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.workbook.properties import CalcProperties


def force_recalc(wb) -> None:
    """Force Excel to fully recalculate every formula the next time it opens this file.
    Without this, a formula cell openpyxl adds or edits (e.g. the 'method not stated'
    roll-up) can show as blank/stale until the user manually presses F9 - Ian Mounts,
    2026-09-22, reported exactly this symptom."""
    wb.calculation = CalcProperties(fullCalcOnLoad=True)

ROOT = Path(__file__).resolve().parents[2]
GT_DIR = ROOT / "results" / "manual_validation" / "groundtruth"
RUBRIC_MD = GT_DIR / "guild_rubric.md"
SHEET = "Rubric"
WIDTHS = [40, 56, 56, 22]           # A-D; paragraphs merge across all four
TOTAL = sum(WIDTHS)

HEAD = PatternFill("solid", fgColor="D9E2F3")
TBL_HEAD = PatternFill("solid", fgColor="EDEDED")


def _clean(t: str) -> str:
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"\1", t)
    return t.replace("`", "").replace("\\|", "|").strip()


def _lines_needed(text: str, width: float) -> int:
    per = max(int(width * 1.05), 10)
    return sum(max(1, math.ceil(len(seg) / per)) for seg in text.split("\n"))


def _cells(row: str) -> list[str]:
    return [_clean(c) for c in row.strip().strip("|").split("|")]


def add_rubric_sheet(wb, md_path: Path = RUBRIC_MD, index: int = 1):
    if SHEET in wb.sheetnames:
        del wb[SHEET]
    ws = wb.create_sheet(SHEET, index)
    for i, w in enumerate(WIDTHS, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.sheet_view.showGridLines = False

    r = 1

    def para(text, bold=False, size=11, fill=None, indent=0):
        nonlocal r
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
        c = ws.cell(r, 1, text)
        c.font = Font(bold=bold, size=size)
        c.alignment = Alignment(wrap_text=True, vertical="top", indent=indent)
        if fill:
            for col in range(1, 5):
                ws.cell(r, col).fill = fill
        ws.row_dimensions[r].height = max(16, 15 * _lines_needed(text, TOTAL - 2 * indent) + 3)
        r += 1

    lines = md_path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip():
            if r > 1 and ws.row_dimensions[r - 1].height != 6:
                ws.row_dimensions[r].height = 6
                r += 1
            i += 1
            continue
        if ln.strip() == "---":
            i += 1
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", ln)
        if m:
            lvl, txt = len(m.group(1)), _clean(m.group(2))
            para(txt, bold=True, size={1: 15, 2: 13, 3: 12, 4: 11}[lvl],
                 fill=HEAD if lvl <= 2 else None)
            i += 1
            continue
        if ln.lstrip().startswith("|"):
            block = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                block.append(lines[i])
                i += 1
            rows = [_cells(b) for b in block if not re.match(r"^\s*\|[\s:\-|]+\|\s*$", b)]
            ncol = max(len(x) for x in rows)
            for k, cells in enumerate(rows):
                cells = cells + [""] * (ncol - len(cells))
                if ncol == 1:
                    span = [(1, 4)]
                elif ncol == 2:
                    span = [(1, 1), (2, 4)]
                elif ncol == 3:
                    span = [(1, 1), (2, 2), (3, 4)]
                else:
                    span = [(j + 1, j + 1) for j in range(ncol)]
                need = 1
                for (a, b), txt in zip(span, cells):
                    ws.merge_cells(start_row=r, start_column=a, end_row=r, end_column=b) if a != b else None
                    c = ws.cell(r, a, txt)
                    c.alignment = Alignment(wrap_text=True, vertical="top")
                    c.font = Font(bold=(k == 0), size=10)
                    if k == 0:
                        for col in range(a, b + 1):
                            ws.cell(r, col).fill = TBL_HEAD
                    need = max(need, _lines_needed(txt, sum(WIDTHS[a - 1:b])))
                ws.row_dimensions[r].height = max(16, 14 * need + 3)
                r += 1
            r += 1
            continue
        bm = re.match(r"^(\s*)[-*]\s+(.*)$", ln)
        if bm:
            depth = len(bm.group(1)) // 2
            buf = [bm.group(2).strip()]
            i += 1
            while (i < len(lines) and lines[i].strip() and lines[i].startswith(" ")
                   and not re.match(r"^\s*[-*]\s", lines[i])):
                buf.append(lines[i].strip())
                i += 1
            para("•  " + _clean(" ".join(buf)), size=10, indent=1 + depth)
            continue
        # plain paragraph: join soft-wrapped continuation lines
        buf = [ln.strip()]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(
                r"^(#{1,4}\s|\||---|\s*[-*]\s)", lines[i]):
            buf.append(lines[i].strip())
            i += 1
        para(_clean(" ".join(buf)), size=10)

    ws.freeze_panes = "A2"
    return ws


METHOD_HEADERS = ["culture from sterilised tissue", "microscopy in tissue",
                  "direct sequencing from tissue", "isolate ID by sequencing",
                  "resynthesis / re-inoculation"]           # 'method not stated' stays yes/no
NEW_STEP6 = [
    "6. Method columns (the purple block) - fill EVERY one on a complete row:",
    "     yes = the text says the method was used   no = the text says it was not",
    "     not stated = the text doesn't say. Set the last column, 'method not",
    "     stated', to yes if the text says nothing at all about how the fungus was",
    "     shown to be inside the plant. The Rubric tab defines each method.",
]


def patch_method_dropdowns(wb) -> str:
    """Give the five method columns a yes / no / not stated dropdown (Lists-sheet backed)."""
    from openpyxl.worksheet.datavalidation import DataValidation
    ws, lists = wb["Review"], wb["Lists"]
    hdr = {c.value: c.column for c in ws[1]}
    col = next((c for c in range(1, lists.max_column + 1) if lists.cell(1, c).value == "method_status"), None)
    if col is None:
        col = lists.max_column + 1
        lists.cell(1, col, "method_status")
        for k, v in enumerate(["yes", "no", "not stated"], start=2):
            lists.cell(k, col, v)
    rng = f"Lists!${get_column_letter(col)}$2:${get_column_letter(col)}$4"
    n = ws.max_row
    targets = {get_column_letter(hdr[h]) for h in METHOD_HEADERS if h in hdr}
    dvs = ws.data_validations.dataValidation
    for dv in list(dvs):                               # drop the old yes/no validation
        if any(str(rg).startswith(t) and str(rg)[len(t):len(t) + 1] == "2" for t in targets for rg in dv.sqref.ranges):
            dvs.remove(dv)
    for t in sorted(targets):
        v = DataValidation(type="list", formula1=rng, allow_blank=True, showDropDown=False,
                           showErrorMessage=True, errorStyle="warning",
                           error="Not in the list - OK to keep if you mean it.",
                           errorTitle="Custom value")
        ws.add_data_validation(v)
        v.add(f"{t}2:{t}{n}")
    return f"{len(targets)} method dropdowns -> yes/no/not stated"


def patch_instructions(wb) -> None:
    ws = wb["Instructions"]
    for r in range(1, ws.max_row + 1):
        v = ws.cell(r, 1).value
        if isinstance(v, str) and v.startswith("6. Method columns"):
            for k in range(3):                          # old step 6 was 3 lines - rewrite the block
                ws.cell(r + k, 1, NEW_STEP6[k])
            # lines 4-5 go on the following rows (7. starts right after) - insert space
            ws.insert_rows(r + 3, amount=2)
            for k in (3, 4):
                c = ws.cell(r + k, 1, NEW_STEP6[k])
                c.font = Font(size=10)
            return


def patch_workbook(path: Path) -> str:
    wb = load_workbook(path)
    add_rubric_sheet(wb)
    print("  ", patch_method_dropdowns(wb))
    patch_instructions(wb)
    force_recalc(wb)
    try:
        wb.save(path)
        return f"patched {path.name}"
    except PermissionError:
        alt = path.with_name(path.stem + "_RUBRIC.xlsx")
        wb.save(alt)
        return f"WARNING {path.name} is open/locked - wrote {alt.name} instead"


def refresh_rubric(path: Path) -> str:
    """Re-render ONLY the Rubric tab (idempotent; safe to re-run after editing the md)."""
    wb = load_workbook(path)
    add_rubric_sheet(wb)
    force_recalc(wb)
    try:
        wb.save(path)
        return f"rubric refreshed: {path.name}"
    except PermissionError:
        alt = path.with_name(path.stem + "_RUBRIC.xlsx")
        wb.save(alt)
        return f"WARNING {path.name} is open/locked - wrote {alt.name} instead"


# ---------------------------------------------------------------------------------
# Geography split (Q7 -> Q7a country / Q7b site / Q7c coordinates) and completeness aids
# ---------------------------------------------------------------------------------
Q7_OLD = "Q7  where was the plant SAMPLED? (not the authors' institution)"
Q7A = "Q7a  COUNTRY where the plant was sampled (not the authors' institution)"
Q7B = "Q7b  site / locality where it was sampled (free text)"
Q7C_OLD = "Q7c  does the paper itself give coordinates for the site?"
Q7C = "Q7c  COORDINATES the paper gives for the site (type as written; 'not stated' if none)"
# 2026-09-22 (Bea Bock, "simplifying could be a good idea"): the short-lived separate
# Q7a "is the location information in the main text?" question is gone - it overlapped too
# much with Q8 ("what geographic information does the text contain?") and nothing enforced
# the two staying consistent. Q8's own vocabulary now absorbs the supplement/cited-study
# deferral cases; see merge_location_source_into_q8() for the one-time migration of any
# workbook that still has the separate column.
Q7D_OLD_PREFIX = "is the location information"     # content marker for that old column
CHECK_COL = "cells_still_missing (auto - 0 = row is finished)"

COUNTRIES = [
    "not stated",
    "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Antarctica", "Argentina",
    "Armenia", "Australia", "Austria", "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh",
    "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bhutan", "Bolivia",
    "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria", "Burkina Faso",
    "Burundi", "Cambodia", "Cameroon", "Canada", "Cape Verde", "Central African Republic",
    "Chad", "Chile", "China", "Colombia", "Comoros", "Costa Rica", "Croatia", "Cuba",
    "Cyprus", "Czechia", "Democratic Republic of the Congo", "Denmark", "Djibouti",
    "Dominica", "Dominican Republic", "Ecuador", "Egypt", "El Salvador",
    "Equatorial Guinea", "Eritrea", "Estonia", "Eswatini", "Ethiopia", "Fiji", "Finland",
    "France", "French Guiana", "French Polynesia", "Gabon", "Gambia", "Georgia", "Germany",
    "Ghana", "Greece", "Greenland", "Guatemala", "Guinea", "Guinea-Bissau", "Guyana",
    "Haiti", "Honduras", "Hong Kong", "Hungary", "Iceland", "India", "Indonesia", "Iran",
    "Iraq", "Ireland", "Israel", "Italy", "Ivory Coast", "Jamaica", "Japan", "Jordan",
    "Kazakhstan", "Kenya", "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho",
    "Liberia", "Libya", "Lithuania", "Luxembourg", "Madagascar", "Malawi", "Malaysia",
    "Maldives", "Mali", "Malta", "Mauritania", "Mauritius", "Mexico", "Moldova", "Mongolia",
    "Montenegro", "Morocco", "Mozambique", "Myanmar", "Namibia", "Nepal", "Netherlands",
    "New Caledonia", "New Zealand", "Nicaragua", "Niger", "Nigeria", "North Korea",
    "North Macedonia", "Norway", "Oman", "Pakistan", "Palestine", "Panama",
    "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland", "Portugal",
    "Puerto Rico", "Qatar", "Republic of the Congo", "Reunion", "Romania", "Russia",
    "Rwanda", "Saudi Arabia", "Senegal", "Serbia", "Seychelles", "Sierra Leone",
    "Singapore", "Slovakia", "Slovenia", "Solomon Islands", "Somalia", "South Africa",
    "South Korea", "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname", "Svalbard",
    "Sweden", "Switzerland", "Syria", "Taiwan", "Tajikistan", "Tanzania", "Thailand",
    "Timor-Leste", "Togo", "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan",
    "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom", "United States",
    "Uruguay", "Uzbekistan", "Vanuatu", "Venezuela", "Vietnam", "Yemen", "Zambia",
    "Zimbabwe",
]


def _shift_sqref(sqref, at_col: int, by: int) -> str:
    from openpyxl.worksheet.cell_range import CellRange
    out = []
    for rg in str(sqref).split():
        cr = CellRange(rg)
        if cr.min_col >= at_col:
            cr.shift(col_shift=by)
        elif cr.max_col >= at_col:
            cr.expand(right=by)
        out.append(cr.coord)
    return " ".join(out)


def _lists_col(wb, name, values):
    lists = wb["Lists"]
    col = next((c for c in range(1, lists.max_column + 1) if lists.cell(1, c).value == name), None)
    if col is None:
        col = lists.max_column + 1
        lists.cell(1, col, name)
        for k, v in enumerate(values, start=2):
            lists.cell(k, col, v)
    L = get_column_letter(col)
    return f"Lists!${L}$2:${L}${len(values) + 1}"


def _dv(ws, formula, col_letter, n):
    from openpyxl.worksheet.datavalidation import DataValidation
    v = DataValidation(type="list", formula1=formula, allow_blank=True, showDropDown=False,
                       showErrorMessage=True, errorStyle="warning",
                       error="Not in the list - OK to keep if you mean it.",
                       errorTitle="Custom value")
    ws.add_data_validation(v)
    v.add(f"{col_letter}2:{col_letter}{n}")


def patch_geography(wb) -> str:
    """Q7 -> Q7a/b/c in an existing workbook. Idempotent. Old Q7 text is moved to Q7b."""
    ws = wb["Review"]
    hdr = [c.value for c in ws[1]]
    if Q7A in hdr:
        return "geography already split"
    if Q7_OLD not in hdr:
        return "Q7 column not found - skipped"
    c = hdr.index(Q7_OLD) + 1                     # 1-based col of old Q7
    n = ws.max_row
    ncol = ws.max_column
    widths = {i: ws.column_dimensions[get_column_letter(i)].width for i in range(1, ncol + 1)}
    for dv in ws.data_validations.dataValidation:
        dv.sqref = type(dv.sqref)(_shift_sqref(dv.sqref, c + 1, 2))
    ws.insert_cols(c + 1, amount=2)
    for i in range(c + 1, ncol + 1):              # old col i is now col i + 2
        ws.column_dimensions[get_column_letter(i + 2)].width = widths[i]
    ws.column_dimensions[get_column_letter(c)].width = 24
    ws.column_dimensions[get_column_letter(c + 1)].width = 30
    ws.column_dimensions[get_column_letter(c + 2)].width = 18
    ws.cell(1, c, Q7A)
    for k, t in ((1, Q7B), (2, Q7C)):
        h = ws.cell(1, c + k, t)
        h._style = ws.cell(1, c)._style
    for r in range(2, n + 1):
        old = ws.cell(r, c).value
        if old not in (None, ""):                 # preserve any earlier free-text answer
            ws.cell(r, c + 1, old)
            ws.cell(r, c, None)
        for k in (0, 1, 2):
            ws.cell(r, c + k).alignment = Alignment(wrap_text=True, vertical="top")
    _dv(ws, _lists_col(wb, "country", COUNTRIES), get_column_letter(c), n)
    lists = wb["Lists"]
    yn = next(cc for cc in range(1, lists.max_column + 1) if lists.cell(1, cc).value == "yn")
    _dv(ws, f"Lists!${get_column_letter(yn)}$2:${get_column_letter(yn)}$3",
        get_column_letter(c + 2), n)
    return f"Q7 split into Q7a/b/c (cols {get_column_letter(c)}-{get_column_letter(c + 2)})"


FUNGAL_LIFESTYLE_RENAMES = {
    "endophyte (foliar, root, or dark-septate; symptomless in living tissue)":
        "endophyte (any plant tissue; symptomless in living tissue)",   # stem != saprotroph
    "not clear from the paper": "not clear from the text",              # paper -> text pass
}


def patch_fungal_lifestyle_vocab(wb) -> str:
    """Reword fungal_lifestyle values (see FUNGAL_LIFESTYLE_RENAMES). Same list length each
    time, so no dropdown-range resize is needed - a straight find/replace of the Lists cell
    value and any already-typed matching answers."""
    lists, ws = wb["Lists"], wb["Review"]
    col = next((c for c in range(1, lists.max_column + 1)
                if lists.cell(1, c).value == "fungal_lifestyle"), None)
    if col is None:
        return "fungal_lifestyle list not found"
    n_fixed = 0
    for r in range(2, lists.max_row + 1):
        old = lists.cell(r, col).value
        if old in FUNGAL_LIFESTYLE_RENAMES:
            lists.cell(r, col, FUNGAL_LIFESTYLE_RENAMES[old])
            n_fixed += 1
    for row in ws.iter_rows():
        for c in row:
            if c.value in FUNGAL_LIFESTYLE_RENAMES:
                c.value = FUNGAL_LIFESTYLE_RENAMES[c.value]
    return (f"fungal_lifestyle: {n_fixed} value(s) reworded" if n_fixed
            else "fungal_lifestyle values already up to date")


AERIAL = "aerial parts / shoots (not separated)"


def patch_tissue_vocab(wb) -> str:
    """Add the 'aerial parts / shoots (not separated)' tissue value (idempotent)."""
    lists, ws = wb["Lists"], wb["Review"]
    col = next((c for c in range(1, lists.max_column + 1) if lists.cell(1, c).value == "tissue"), None)
    if col is None:
        return "tissue list not found"
    vals = [lists.cell(r, col).value for r in range(2, lists.max_row + 1)
            if lists.cell(r, col).value is not None]
    if AERIAL in vals:
        return "tissue vocab already updated"
    old_rng = f"Lists!${get_column_letter(col)}$2:${get_column_letter(col)}${len(vals) + 1}"
    vals.insert(vals.index("flower / reproductive") + 1, AERIAL)
    for k, v in enumerate(vals, start=2):
        lists.cell(k, col, v)
    new_rng = f"Lists!${get_column_letter(col)}$2:${get_column_letter(col)}${len(vals) + 1}"
    n = 0
    for dv in ws.data_validations.dataValidation:
        if dv.formula1 == old_rng:
            dv.formula1 = new_rng
            n += 1
    return f"tissue vocab + aerial parts ({n} dropdowns re-pointed)"


def set_rollup_formula(wb) -> str:
    """'method not stated' fills itself in: yes only if all five methods are 'not stated'."""
    ws = wb["Review"]
    hdr = [c.value for c in ws[1]]
    m1 = hdr.index(METHOD_HEADERS[0]) + 1
    ro = next(i for i, h in enumerate(hdr, 1) if str(h).startswith("method not stated"))
    a, b = get_column_letter(m1), get_column_letter(ro - 1)
    for dv in list(ws.data_validations.dataValidation):      # a formula cell needs no dropdown
        keep = [rg for rg in str(dv.sqref).split()
                if not re.match(rf"^{get_column_letter(ro)}\d", rg)]
        if len(keep) != len(str(dv.sqref).split()):
            if keep:
                dv.sqref = type(dv.sqref)(" ".join(keep))
            else:
                ws.data_validations.dataValidation.remove(dv)
    for r in range(2, ws.max_row + 1):
        c = ws.cell(r, ro, f'=IF($B{r}<>"complete","",IF(COUNTIF({a}{r}:{b}{r},"not stated")=5,"yes","no"))')
        c.alignment = Alignment(horizontal="center", vertical="top")
    ws.cell(1, ro).value = "method not stated (fills itself in)"
    return "roll-up column is now a formula"


_Q_VOCAB = {"Q1": "yn_unclear", "Q2": "primary_aim", "Q3": "sampling_approach", "Q4": "language",
            "Q5": "yn_unclear", "Q6": "strain_variation", "Q7a": "country",
            "Q8": "sampling_location_status", "Q9": "biome", "Q11": "sterilisation_checked"}
_SLOT_VOCAB = {"tissue": "tissue", "fungal_lifestyle": "fungal_lifestyle",
               "effect_on_host": "effect_on_host", "evidence_basis": "evidence_basis"}


def rebuild_dropdowns(wb) -> str:
    """Recreate EVERY dropdown from the column headers + the Lists sheet.

    Needed because a workbook re-saved in Excel stores cross-sheet dropdowns in an extension
    block that openpyxl silently drops on load. Rebuilding makes the patch safe on any copy
    (including one an annotator has already partly filled in) and idempotent."""
    ws, lists = wb["Review"], wb["Lists"]
    rng = {}
    for c in range(1, lists.max_column + 1):
        name = lists.cell(1, c).value
        n = sum(1 for r in range(2, lists.max_row + 1) if lists.cell(r, c).value not in (None, ""))
        if name and n:
            L = get_column_letter(c)
            rng[name] = f"Lists!${L}$2:${L}${n + 1}"
    ws.data_validations.dataValidation = []
    n_rows, made = ws.max_row, 0
    for ci, h in enumerate([c.value for c in ws[1]], 1):
        h = str(h or "")
        key = None
        if h == "text_reviewed":
            key = "text_reviewed"
        elif h.startswith(tuple(f"{q} " for q in _Q_VOCAB)) or h.split(" ")[0] in _Q_VOCAB:
            key = _Q_VOCAB.get(h.split(" ")[0])
        elif h in METHOD_HEADERS:
            key = "method_status"
        else:
            key = _SLOT_VOCAB.get(re.sub(r"_\d+$", "", h))
        if key and key in rng:
            _dv(ws, rng[key], get_column_letter(ci), n_rows)
            made += 1
    return f"{made} dropdowns rebuilt"


def patch_q7c(wb) -> str:
    """Q7c: yes/no dropdown -> coordinates as text (or 'no'). Idempotent; keeps typed answers."""
    ws = wb["Review"]
    for c in ws[1]:
        if c.value == Q7C_OLD:
            c.value = Q7C
            return "Q7c is now coordinates-as-text"
    return "Q7c already coordinates-as-text"


def _lists_col_force(wb, name, values):
    """Like _lists_col, but overwrites an EXISTING column's values too (for vocab whose
    wording we've since changed, e.g. after Ian's Q7 feedback) - not just create-if-missing."""
    lists = wb["Lists"]
    col = next((c for c in range(1, lists.max_column + 1) if lists.cell(1, c).value == name), None)
    if col is None:
        col = lists.max_column + 1
        lists.cell(1, col, name)
    old_max = lists.max_row
    for k, v in enumerate(values, start=2):
        lists.cell(k, col, v)
    for k in range(len(values) + 2, old_max + 1):
        lists.cell(k, col, None)
    L = get_column_letter(col)
    return f"Lists!${L}$2:${L}${len(values) + 1}"


# old location-source value -> the Q8 value it corresponds to, ONLY carried across when Q8
# is still blank (the "yes"/"partly" values are ambiguous between explicit/inferable, so
# those are left for the rater instead of guessed).
_LOCSRC_TO_Q8 = {
    "no - the main text says location details are in a supplement":
        "the main text says location details are in a supplement",
    "no - the main text says location details are in another cited study":
        "the main text says location details are in another cited study",
    "no - the main text gives no direct location information": "no geographic information at all",
}


def layout_q7(wb) -> str:
    """Make sure the three Q7 sub-columns (country / site / coordinates) carry the CURRENT
    header wording and sit in order [country, site, coordinates] as Q7a/b/c. Columns are
    found by a stable content substring, not by their current "Q7x" letter or position, so
    this is safe to re-run on a workbook from any earlier round of this patch - including one
    someone has already typed real answers into (values are carried along, never dropped).
    Also runs the one-time merge_location_source_into_q8() migration (see that docstring)."""
    ws = wb["Review"]
    msg2 = merge_location_source_into_q8(wb)

    def find(substr):
        return next((i for i, c in enumerate(ws[1], 1)
                     if isinstance(c.value, str) and substr in c.value), None)

    i_country = find("COUNTRY where the plant")
    i_site = find("site / locality where it was sampled")
    i_coord = find("COORDINATES the paper gives") or find("does the paper itself give coordinates")
    if i_country is None or i_site is None or i_coord is None:
        return f"Q7 columns not found - run patch_geography/patch_q7c first ({msg2})"

    n = ws.max_row
    src = [i_country, i_site, i_coord]
    c0 = min(src)
    target = [c0, c0 + 1, c0 + 2]
    moved = src != target
    if moved:
        for r in range(1, n + 1):
            vals = [ws.cell(r, i).value for i in src]        # read all 3 before writing any
            for col, v in zip(target, vals):
                ws.cell(r, col, v)

    for col, text in zip(target, (Q7A, Q7B, Q7C)):            # canonical text, wherever it sits
        h = ws.cell(1, col, text)
        h.font, h.fill, h.alignment = Font(bold=True, color="FFFFFF", size=10), \
            PatternFill("solid", start_color="2C5F8A"), Alignment(wrap_text=True, vertical="top")
    for col, w in zip(target, (24, 30, 20)):
        ws.column_dimensions[get_column_letter(col)].width = w

    what = "reordered" if moved else "already in place"
    return (f"Q7 layout {what}: country={get_column_letter(target[0])}, "
            f"site={get_column_letter(target[1])}, coordinates={get_column_letter(target[2])} "
            f"({msg2})")


def merge_location_source_into_q8(wb) -> str:
    """One-time migration (Bea Bock, 2026-09-22, 'simplifying could be a good idea'): the
    short-lived separate Q7a "is the location information in the main text?" column is
    dropped, and Q8 ("what geographic information does the text contain?") absorbs its
    supplement / cited-study values. Any already-typed location-source answer is carried into
    Q8 where Q8 is still blank (see _LOCSRC_TO_Q8); 'yes'/'partly' answers are dropped since
    they don't map to a single Q8 value. Idempotent: a no-op once the column is gone."""
    ws = wb["Review"]
    hdr = [c.value for c in ws[1]]
    i_q8 = next(i for i, h in enumerate(hdr, 1) if isinstance(h, str) and h.startswith("Q8"))
    q8_header = "Q8  what geographic information does the text contain?"
    renamed = ws.cell(1, i_q8).value != q8_header
    ws.cell(1, i_q8).value = q8_header                 # catches the earlier paper->text miss
    _lists_col_force(wb, "sampling_location_status", [
        "sampling location is explicitly stated",
        "sampling location is inferable from a named field site / region",
        "the main text says location details are in a supplement",
        "the main text says location details are in another cited study",
        "no sampling location - only the authors' institutional country is given",
        "no geographic information at all",
    ])

    i_locsrc = next((i for i, h in enumerate(hdr, 1)
                     if isinstance(h, str) and Q7D_OLD_PREFIX in h), None)
    if i_locsrc is None:
        return f"Q8 vocab expanded{' + header text fixed' if renamed else ''}; " \
               "no separate location-source column (already merged)"
    n_carried = 0
    for r in range(2, ws.max_row + 1):
        old = ws.cell(r, i_locsrc).value
        if old in _LOCSRC_TO_Q8 and not ws.cell(r, i_q8).value:
            ws.cell(r, i_q8, _LOCSRC_TO_Q8[old])
            n_carried += 1
    ws.delete_cols(i_locsrc, 1)
    return f"location-source column removed, merged into Q8 ({n_carried} answers carried across)"


def patch_text_reviewed_header(wb) -> str:
    """Rename 'paper_reviewed' to 'text_reviewed': the Review header cell AND the Lists
    vocab column name it's looked up by (Bea Bock, 2026-09-22). Idempotent; keeps style."""
    ws, lists = wb["Review"], wb["Lists"]
    done = 0
    for c in ws[1]:
        if c.value == "paper_reviewed":
            c.value = "text_reviewed"
            done += 1
    for c in lists[1]:
        if c.value == "paper_reviewed":
            c.value = "text_reviewed"
            done += 1
    return f"text_reviewed: renamed ({done} cells)" if done else "text_reviewed: already renamed"


def remove_completeness(wb) -> str:
    """Bea Bock, 2026-09-22: 'I'm not sure that's true and we can just remove that' - the
    amber/grey/'cells_still_missing' auto-check is removed. It had already been fixed once
    (see git history) and re-verified with a real formula engine, but the repeated back-and-
    forth wasn't worth keeping for a 20-paper pilot round; the plain blank-means-not-done /
    N/A-means-skip rule in the rubric is enough on its own. This cleans up any column and
    conditional formatting an earlier version of the patch left behind; idempotent."""
    ws = wb["Review"]
    hdr = [c.value for c in ws[1]]
    if CHECK_COL in hdr:
        ws.delete_cols(hdr.index(CHECK_COL) + 1, 1)
    if len(ws.conditional_formatting._cf_rules):
        ws.conditional_formatting = type(ws.conditional_formatting)()
        return "completeness check removed (column + colouring)"
    return "no completeness check present"


NEW_Q7_LINES = [
    "     Q7a/b/c - where the PLANT was SAMPLED (never the authors' institution):",
    "         country (only if the paper names it), site/locality (a place name), and",
    "         coordinates as written (or 'no'). Never look anything up. Q8 = what the",
    "         paper tells you about location.",
]


def patch_instructions_geo(wb) -> str:
    ws = wb["Instructions"]
    for r in range(1, ws.max_row + 1):
        v = ws.cell(r, 1).value
        if isinstance(v, str) and v.strip().startswith(("Q7/Q8 - Q7 is", "Q7a/b/c - where")):
            for k in range(3):
                ws.cell(r + k, 1, NEW_Q7_LINES[k])
            return "instructions Q7 lines updated"
    return "Q7 instruction lines not found"


def patch_geo_all(path: Path) -> str:
    wb = load_workbook(path)
    msgs = [patch_geography(wb), patch_q7c(wb), layout_q7(wb), patch_tissue_vocab(wb),
            patch_fungal_lifestyle_vocab(wb), patch_text_reviewed_header(wb), rebuild_dropdowns(wb),
            set_rollup_formula(wb), remove_completeness(wb), rewrite_instructions(wb)]
    add_rubric_sheet(wb)
    force_recalc(wb)
    try:
        wb.save(path)
        return f"{path.name}: " + "; ".join(msgs)
    except PermissionError:
        alt = path.with_name(path.stem + "_RUBRIC.xlsx")
        wb.save(alt)
        return f"WARNING {path.name} is open/locked - wrote {alt.name} instead"


# ---------------------------------------------------------------------------------
# Instructions tab: ONE source used by the builder and by the in-place patcher
# ---------------------------------------------------------------------------------
def instruction_lines(who: str, is_kappa: bool) -> list[tuple[str, bool]]:
    L = [
        ("Fungal endophyte literature - extraction check", True),
        ("", False),
        (f"File for: {who}", True),
        ("", False),
        ("BEFORE YOU START", True),
        ("- Open the 'Rubric' tab in a SECOND WINDOW so it sits beside the Review tab:", False),
        ("  Excel > View > New Window, then View > Arrange All. The Rubric tab explains", False),
        ("  every dropdown; this page is the short version.", False),
        ("- You read the texts yourself. You are NOT checking any software's output.", False),
        ("- Record what the TEXT says, not what you know about the fungus or plant.", False),
        ("  (If a text only says 'Espeletia', do not fill in a country from what you know.)", False),
        ("", False),
        ("THE REVIEW TAB - one row at a time, left to right", True),
        ("1. reading_stage says how much to read.", False),
        ("     abstract  = read ONLY the text in that row's 'abstract' column. Do not open", False),
        ("                 the PDF. Answering 'not stated' a lot is expected and correct.", False),
        ("     full text = open the matching PDF from the shared Google Drive folder (named", False),
        ("                 after the row, e.g. row K001b -> file K001b.pdf) and read it all.", False),
        ("   Each full-text paper has TWO rows: the abstract row (do it FIRST), then the", False),
        ("   full-text row. On the full-text row you may copy your abstract answers across", False),
        ("   and then correct them.", False),
        ("2. Q1 to Q11: pick from each dropdown. If the right answer is not listed, type it", False),
        ("   in (Excel shows a warning but keeps it).", False),
        ("     Q4  = the language of the text you are reading on THIS row.", False),
        ("     Q7a/b/c = where the PLANT was collected (never the authors' institution).", False),
        ("         Q7a country - only if the main text names it (NEVER look one up).", False),
        ("         Q7b place name as given.  Q7c coordinates exactly as written (several:", False),
        ("         up to 3 separated by ;  more: 'multiple sites (N) - see Table 1'), or", False),
        ("         'not stated'. Always record coordinates when given, even if a place is", False),
        ("         also named.", False),
        ("     Q8 = what the text tells you about location - pick the option that says", False),
        ("         location details are 'in a supplement' or 'in another cited study' if", False),
        ("         that's what the text itself says; do NOT open the supplement or the", False),
        ("         cited study to check.", False),
        ("     Q10 = how many distinct fungus x host-plant pairs the text NAMES (true", False),
        ("         count, even above 5). Fill Q10 before the interaction blocks.", False),
        ("3. Purple method columns: every one gets yes / no / not stated.", False),
        ("     yes = used.  no = you read the methods and it was not used.", False),
        ("     not stated = you cannot tell (the usual answer on an abstract row).", False),
        ("     The last column, 'method not stated', fills itself in - do not type in it.", False),
        ("4. Interaction blocks (shaded, 5 available): one block per distinct fungus x", False),
        ("   host-plant pair the text NAMES. Six cells each:", False),
        ("     fungus / host_plant - exactly as the authors write them (even if outdated).", False),
        ("     tissue              - several go in one cell: leaf, root. Only 'shoots' or", False),
        ("                           'aerial parts'? Pick 'aerial parts / shoots (not separated)'.", False),
        ("     fungal_lifestyle    - how the fungus lives (endophyte, pathogen, ...)", False),
        ("     effect_on_host      - what happened to THIS plant", False),
        ("     evidence_basis      - how the EFFECT was established (tested here / observed", False),
        ("                           here / inferred / asserted). If the effect is 'not reported',", False),
        ("                           how the LIFESTYLE was established.", False),
        ("   Lifestyle and effect are different questions: a pathogen can be present with", False),
        ("   no symptoms. More than 5 pairs? Fill the 5 most prominent and list the rest", False),
        ("   in 'extra_pairs_or_NGS_community_summary'. Metabarcoding text? Do not list", False),
        ("   every OTU - fill blocks for named taxa only and describe the community in the", False),
        ("   summary column.", False),
        ("   Blocks you do not need can stay empty, or type N/A in the 'fungus' cell.", False),
        ("   Inside a block you do fill, answer all six cells ('not stated' / 'not", False),
        ("   reported' where the text is silent).", False),
        ("5. text_reviewed (2nd column) - set it when the row is finished:", False),
        ("     complete                        = fill the whole row.", False),
        ("     could not access the paper      = a full-text row you could not get. Stop.", False),
        ("     review or secondary compilation = Q1 = no, Q3 = review, answer Q4 only;", False),
        ("                                       leave the rest of the row empty.", False),
        ("     not a fungus-in-plant study     = Q1 = no; leave the rest empty.", False),
        ("   An empty text_reviewed means 'not done yet'.", False),
        ("6. date_reviewed (3rd column): today's date. Your name is the file name, so no", False),
        ("   initials. Anything you were unsure about: last column.", False),
        ("", False),
        ("QUESTIONS? Ask Bea before guessing - a question now is better than a wrong answer.", False),
    ]
    if is_kappa:
        L += [("", False),
              ("This is the shared agreement block. Work independently - do not discuss the", False),
              ("papers with the other reviewers until all files are back.", False)]
    return L


def write_instructions(ws, who: str, is_kappa: bool) -> None:
    for row in ws.iter_rows():
        for c in row:
            c.value = None
    for i, (t, b) in enumerate(instruction_lines(who, is_kappa), 1):
        c = ws.cell(row=i, column=1, value=t)
        c.font = Font(bold=b, size=14 if i == 1 else 11)
    ws.column_dimensions["A"].width = 100


def rewrite_instructions(wb) -> str:
    ws = wb["Instructions"]
    who, is_kappa = "", False
    for r in range(1, 12):
        v = ws.cell(r, 1).value
        if isinstance(v, str) and v.startswith("File for:"):
            who = v[len("File for: "):]
    is_kappa = "shared agreement block" in who or "kappa" in who.lower()
    if not who:
        return "Instructions: could not find 'File for:' line - left alone"
    write_instructions(ws, who, is_kappa)
    return "Instructions tab rewritten"


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    rubric_only = "--rubric-only" in sys.argv          # (idempotent)
    geo = "--geo" in sys.argv                          # Q7 split + completeness (idempotent)
    targets = [Path(a) for a in args] or sorted(GT_DIR.glob("groundtruth_*.xlsx"))
    for t in targets:
        if t.name.startswith("~$") or t.stem.endswith(("_NEW", "_RUBRIC")):
            continue
        print(patch_geo_all(t) if geo else refresh_rubric(t) if rubric_only else patch_workbook(t))
