# BMB 2026-09-02
# Structure-aware PDF parsing + targeted segmentation for the full-text re-extraction
# (Task 1 Phase 0b, per NPH_task1_paired_validation_plan.md section 2b).
#
# Pipeline: parse to structured text (pymupdf4llm markdown if available, else a plain
# PyMuPDF page dump) -> keep the sections/paragraphs likely to carry the target facts
# (title, abstract, Methods, Results, table captions, any paragraph naming a
# genus-looking binomial or a country) -> drop References / Acknowledgements / Funding
# boilerplate -> chunk what's left into context-sized windows with a [DOI | section]
# header on each. Image-only / scanned PDFs are OCR'd with ocrmypdf (Tesseract) and
# cached, not skipped - older scanned papers are still part of the corpus and the study
# is about. No LLM here; monsoon_extract.py calls this.

from __future__ import annotations

import re
from pathlib import Path

try:                        # richer structure, pip-only; preferred on Monsoon
    import pymupdf4llm      # noqa: F401
    _HAVE_P4LLM = True
except Exception:
    _HAVE_P4LLM = False

try:
    import fitz  # PyMuPDF
    _HAVE_FITZ = True
except Exception:
    _HAVE_FITZ = False

# ---------------------------------------------------------------- section handling

# headings we keep (prefix match, case-insensitive, after stripping numbering/markdown)
KEEP_HEADINGS = (
    "abstract", "summary", "introduction", "material", "methods", "method",
    "experimental", "study site", "study area", "sampling", "result", "results",
    "discussion", "taxonomy", "systematic", "new taxa", "new species",
    "species description", "notes",
)
# headings we drop wholesale
DROP_HEADINGS = (
    "reference", "literature cited", "bibliography", "acknowledA", "acknowledg",
    "author contribution", "conflict of interest", "competing interest",
    "funding", "data availability", "supplementary", "supporting information",
    "appendix", "orcid", "how to cite",
)

HEADING_RE = re.compile(r"^\s{0,3}(#{1,4}\s*)?([0-9.]*\s*)?([A-Z][A-Za-z0-9 ,\-/&()]{2,60})\s*$")
TABLE_CAP_RE = re.compile(r"^\s*(table|tab\.?|fig(?:ure)?\.?)\s*\d", re.I)

# genus-looking binomial: "Xxxxx yyyyy" or "Xxxxx sp." (rough, for paragraph triage)
BINOMIAL_RE = re.compile(r"\b[A-Z][a-z]{3,}\s+(?:sp{1,2}\.?|[a-z]{3,})\b")

COUNTRIES = {
    # compact set - enough to catch a Methods sentence; not exhaustive
    "argentina", "australia", "austria", "bangladesh", "belgium", "bolivia", "brazil",
    "cameroon", "canada", "chile", "china", "colombia", "costa rica", "croatia", "cuba",
    "czech", "denmark", "ecuador", "egypt", "estonia", "ethiopia", "finland", "france",
    "germany", "ghana", "greece", "india", "indonesia", "iran", "ireland", "israel",
    "italy", "japan", "kenya", "korea", "malaysia", "mexico", "morocco", "nepal",
    "netherlands", "new zealand", "nigeria", "norway", "pakistan", "panama", "peru",
    "philippines", "poland", "portugal", "romania", "russia", "saudi arabia", "singapore",
    "slovakia", "slovenia", "south africa", "spain", "sri lanka", "sweden", "switzerland",
    "taiwan", "tanzania", "thailand", "tunisia", "turkey", "uganda", "ukraine",
    "united kingdom", "united states", "uruguay", "venezuela", "vietnam", "zimbabwe",
    "u.s.a", "u.k", "usa", "uk",
}


def _norm_heading(line: str) -> str:
    return re.sub(r"[^a-z ]", "", line.lower()).strip()


def ocr_pdf(src: str | Path, dst: str | Path, lang: str = "eng") -> bool:
    """
    Add a text layer to an image-only PDF with ocrmypdf (Tesseract). Returns True on
    success. Scanned papers (mostly pre-digitisation) are still the papers the study
    is about, so we OCR rather than skip them (Bea, 2026-09-02). The corpus is
    English-language by search design, so `eng` is the default; pass e.g.
    "eng+fra+spa" if you install those tesseract data packs. Needs `ocrmypdf` +
    tesseract on the box; if absent (or a language pack is missing) returns False and
    the caller logs the PDF as skipped.
    """
    try:
        import ocrmypdf  # noqa: PLC0415
    except Exception:
        return False
    try:
        ocrmypdf.ocr(str(src), str(dst), language=lang, skip_text=True,
                     progress_bar=False, optimize=0, jobs=1)
        return Path(dst).exists()
    except Exception:
        # retry with plain English if a multi-language request failed on a missing pack
        if lang != "eng":
            try:
                ocrmypdf.ocr(str(src), str(dst), language="eng", skip_text=True,
                             progress_bar=False, optimize=0, jobs=1)
                return Path(dst).exists()
            except Exception:
                return False
        return False


def parse_pdf(path: str | Path, *, ocr: bool = True, ocr_cache_dir: str | Path | None = None) -> dict:
    """Return {text, n_pages, ok, parser}. text is markdown-ish when pymupdf4llm is present."""
    path = Path(path)
    out = {"text": "", "n_pages": 0, "ok": False, "parser": "none"}
    if not _HAVE_FITZ:
        out["error"] = "PyMuPDF (fitz) not installed"
        return out
    try:
        with fitz.open(path) as doc:
            out["n_pages"] = doc.page_count
            if doc.page_count == 0 or doc.is_encrypted:
                return out
            # scanned-PDF guard: almost no extractable text on the first pages
            probe = "".join(doc[i].get_text() for i in range(min(3, doc.page_count)))
        if len(probe.strip()) < 200:
            if ocr:
                cache = Path(ocr_cache_dir or path.parent / "_ocr")
                cache.mkdir(parents=True, exist_ok=True)
                ocred = cache / (path.stem + ".ocr.pdf")
                if ocred.exists() or ocr_pdf(path, ocred):
                    out["parser"] = "ocr+"
                    path = ocred                 # fall through to normal parse
                else:
                    out["parser"] = "scanned-no-ocr"   # caller logs + skips
                    return out
            else:
                out["parser"] = "scanned?"
                return out
        ocr_prefix = "ocr+" if out["parser"] == "ocr+" else ""
        if _HAVE_P4LLM:
            out["text"] = pymupdf4llm.to_markdown(str(path), show_progress=False)
            out["parser"] = ocr_prefix + "pymupdf4llm"
        else:
            with fitz.open(path) as doc:
                out["text"] = "\n".join(p.get_text("text") for p in doc)
            out["parser"] = ocr_prefix + "pymupdf-plain"
        out["ok"] = bool(out["text"].strip())
    except Exception as e:                       # noqa: BLE001
        out["error"] = str(e)
    return out


def _split_sections(text: str) -> list[tuple[str, str]]:
    """Very rough section splitter: lines that look like headings start a new section."""
    sections: list[tuple[str, str]] = []
    cur_head, cur_body = "PREAMBLE", []
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped and HEADING_RE.match(line) and len(stripped.split()) <= 8:
            sections.append((cur_head, "\n".join(cur_body)))
            cur_head, cur_body = stripped, []
        else:
            cur_body.append(line)
    sections.append((cur_head, "\n".join(cur_body)))
    return sections


def _keep_section(head: str) -> bool | None:
    h = _norm_heading(head)
    if not h:
        return None
    if any(h.startswith(d[:8]) for d in DROP_HEADINGS):
        return False
    if any(h.startswith(k) for k in KEEP_HEADINGS):
        return True
    return None                                  # unknown -> paragraph-level triage


def _triage_paragraph(par: str) -> bool:
    if TABLE_CAP_RE.match(par.strip()):
        return True
    if BINOMIAL_RE.search(par):
        return True
    low = par.lower()
    return any(c in low for c in COUNTRIES)


def segment(parsed: dict, *, max_keep_chars: int = 60_000) -> list[tuple[str, str]]:
    """
    Return a list of (section_label, kept_text) after targeted filtering.
    Falls back to 'the whole document, truncated' if the structure is unreadable.
    """
    text = parsed.get("text", "")
    if not text.strip():
        return []
    sections = _split_sections(text)
    kept: list[tuple[str, str]] = []
    total = 0
    for head, body in sections:
        if not body.strip():
            continue
        decision = _keep_section(head)
        if decision is False:
            continue
        if decision is True:
            chunk_body = body
        else:                                    # unknown section: keep triaged paragraphs
            paras = [p for p in re.split(r"\n\s*\n", body) if _triage_paragraph(p)]
            if not paras:
                continue
            chunk_body = "\n\n".join(paras)
        chunk_body = chunk_body.strip()
        if not chunk_body:
            continue
        kept.append((head[:60] or "section", chunk_body))
        total += len(chunk_body)
        if total >= max_keep_chars:
            break
    if not kept:                                 # nothing matched - degrade gracefully
        kept = [("FULLDOC", text[:max_keep_chars])]
    return kept


def chunk_segments(
    segments: list[tuple[str, str]],
    *,
    doi: str = "",
    max_chars: int = 16_000,          # ~4k tokens; monsoon_extract sizes this per model
    overlap: int = 1_500,
) -> list[str]:
    """Pack (label, text) segments into <=max_chars windows, each prefixed [DOI | section]."""
    chunks: list[str] = []
    for label, body in segments:
        header = f"[{doi or 'paper'} | {label}]\n"
        room = max_chars - len(header)
        if len(body) <= room:
            chunks.append(header + body)
            continue
        start = 0
        while start < len(body):
            piece = body[start:start + room]
            chunks.append(header + piece)
            if start + room >= len(body):
                break
            start += room - overlap
    return chunks


def prepare(path: str | Path, *, doi: str = "", max_chars: int = 16_000,
            ocr: bool = True, ocr_cache_dir: str | Path | None = None) -> dict:
    """One call: parse -> segment -> chunk. Returns {ok, parser, n_pages, chunks, note}."""
    parsed = parse_pdf(path, ocr=ocr, ocr_cache_dir=ocr_cache_dir)
    res = {"ok": parsed["ok"], "parser": parsed["parser"], "n_pages": parsed["n_pages"],
           "chunks": [], "note": parsed.get("error", "")}
    if parsed["parser"] in ("scanned?", "scanned-no-ocr"):
        res["note"] = ("scanned/no-text-layer - "
                       + ("ocrmypdf not installed / OCR failed" if parsed["parser"]
                          == "scanned-no-ocr" else "OCR disabled"))
        return res
    if not parsed["ok"]:
        return res
    segs = segment(parsed)
    res["chunks"] = chunk_segments(segs, doi=doi, max_chars=max_chars)
    res["n_segments"] = len(segs)
    return res


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: python pdf_segment.py <file.pdf> [doi]")
        raise SystemExit(1)
    r = prepare(sys.argv[1], doi=sys.argv[2] if len(sys.argv) > 2 else "")
    print(f"parser={r['parser']} pages={r['n_pages']} ok={r['ok']} "
          f"segments={r.get('n_segments')} chunks={len(r['chunks'])} {r['note']}")
    for i, c in enumerate(r["chunks"]):
        print(f"\n--- chunk {i} ({len(c)} chars) ---\n{c[:600]}")
