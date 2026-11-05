# BMB 2026-06-05, rewritten 2026-09-02 (Task 1 Phase 0b)
# Runs Ollama on Monsoon to extract structured plant-fungus data. Cluster-only.
#
# Rewrite goals (NPH_task1_paired_validation_plan.md section 2b):
#   - no more "first 12 pages / first 8000 chars" truncation (the v4 bug)
#   - structure-aware parse -> targeted segmentation -> context-sized chunks
#     (pdf_segment.py), one schema-constrained call per chunk, union+dedup
#   - schema-constrained JSON decoding against extract_schema.EXTRACTION_SCHEMA
#     (fields + value sets LOCKED to the Task 2 workbook, so output is directly
#     scoreable against the human ground truth)
#   - explicit num_ctx + temperature=0 per model; --model for the bake-off
#   - runs on abstracts OR full text (--mode); output labelled so the paired
#     comparison (Phase 3) can join on paper_id
#
# The old v4 script is scripts/archive/monsoon_extract_v4.py. Output here is
# global_endo_extraction_v5.csv; the v4 CSV is left untouched.
#
# Examples:
#   python monsoon_extract.py --mode fulltext  --manifest full_corpus/pdf_manifest.csv \
#       --pdf-dir full_corpus --model mistral --out global_endo_extraction_v5.csv
#   python monsoon_extract.py --mode abstract --input Abstracts_for_Monsoon.csv \
#       --model qwen2.5:32b --out abstract_reextraction_v5.csv --shard 0 --nshards 4

from __future__ import annotations

import argparse
import json
import re
import signal
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_schema as S          # noqa: E402
import pdf_segment                  # noqa: E402

try:
    import ollama                   # noqa: E402
except Exception:
    ollama = None

# model -> (num_ctx, max_chars_per_chunk). max_chars ~= num_ctx * 3.5 chars/token,
# minus prompt overhead. Override with --num-ctx / --max-chars.
MODEL_CFG = {
    "mistral":       (8192, 20_000),
    "mistral:latest": (8192, 20_000),
    "qwen2.5:7b":    (16384, 42_000),
    "qwen2.5:14b":   (16384, 42_000),
    "qwen2.5:32b":   (16384, 42_000),
    "llama3.1:8b":   (16384, 42_000),
    "gemma2:9b":     (8192, 20_000),
}
DEFAULT_CFG = (8192, 20_000)


class Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise Timeout()


def _norm(s) -> str:
    return re.sub(r"[^a-z0-9 ]", "", str(s or "").lower()).strip()


def call_model(model: str, prompt: str, num_ctx: int, timeout: int = 180) -> tuple[dict | None, str]:
    """One schema-constrained generate call. Returns (parsed_obj|None, status)."""
    if ollama is None:
        return None, "no-ollama"
    have_alarm = hasattr(signal, "SIGALRM")
    if have_alarm:
        signal.signal(signal.SIGALRM, _alarm)
        signal.alarm(timeout)
    try:
        resp = ollama.generate(
            model=model, prompt=prompt,
            format=S.EXTRACTION_SCHEMA,               # <-- schema-constrained decoding
            options={"temperature": 0, "num_ctx": num_ctx},
        )
        raw = resp.get("response", "{}")
        return json.loads(raw), "ok"
    except Timeout:
        return None, "timeout"
    except json.JSONDecodeError:
        return None, "malformed"
    except Exception as e:                            # noqa: BLE001
        return None, f"error:{type(e).__name__}"
    finally:
        if have_alarm:
            signal.alarm(0)


def _first(*vals):
    for v in vals:
        if v not in (None, "", [], "not_stated", "unclear"):
            return v
    return vals[0] if vals else None


def merge_chunk_objs(objs: list[dict]) -> dict:
    """Union interactions (dedup on fungus|host|tissue-set) + reconcile paper fields."""
    if not objs:
        return {}
    merged: dict = {}
    # paper-level: prefer the first informative value; union the list fields
    scalar = ["is_fungus_in_plant_study", "primary_aim", "sampling_approach", "language",
              "uncultured_taxa", "strain_variation", "sampling_location",
              "sampling_location_status", "sterilisation_checked"]
    for f in scalar:
        merged[f] = _first(*[o.get(f) for o in objs])
    merged["biome"] = sorted({b for o in objs for b in (o.get("biome") or []) if b})
    merged["detection_methods"] = sorted(
        {m for o in objs for m in (o.get("detection_methods") or []) if m})
    merged["community_summary"] = _first(*[o.get("community_summary") for o in objs]) or ""

    seen, inter = {}, []
    for o in objs:
        for it in (o.get("interactions") or []):
            if not isinstance(it, dict):
                continue
            fg, hs = _norm(it.get("fungus")), _norm(it.get("host_plant"))
            if not fg and not hs:
                continue
            key = (fg, hs, tuple(sorted(it.get("tissue") or [])))
            if key in seen:
                continue
            seen[key] = True
            inter.append(it)
    merged["interactions"] = inter
    reported_n = _first(*[o.get("n_distinct_pairs") for o in objs])
    merged["n_distinct_pairs"] = max(int(reported_n or 0), len(inter))
    return merged


def to_rows(paper_id: str, doi: str, m: dict, ctx: dict) -> list[dict]:
    base = {
        "paper_id": paper_id, "doi": doi,
        "source_file": ctx.get("source_file"), "data_source": ctx["data_source"],
        "doc_type_ai": ctx["doc_type"], "n_pages": ctx.get("n_pages"),
        "model": ctx["model"], "schema_version": S.SCHEMA_VERSION,
        "n_chunks": ctx["n_chunks"], "malformed_chunks": ctx["malformed_chunks"],
        "is_fungus_in_plant_study": m.get("is_fungus_in_plant_study"),
        "primary_aim": m.get("primary_aim"), "sampling_approach": m.get("sampling_approach"),
        "language": m.get("language"), "uncultured_taxa": m.get("uncultured_taxa"),
        "strain_variation": m.get("strain_variation"),
        "sampling_location": m.get("sampling_location"),
        "sampling_location_status": m.get("sampling_location_status"),
        "biome": "|".join(m.get("biome") or []),
        "n_distinct_pairs": m.get("n_distinct_pairs"),
        "sterilisation_checked": m.get("sterilisation_checked"),
        "detection_methods": "|".join(m.get("detection_methods") or []),
        "community_summary": m.get("community_summary") or "",
    }
    inters = m.get("interactions") or []
    if not inters:
        return [{**base, **dict.fromkeys(
            ["fungus", "host_plant", "tissue", "fungal_lifestyle", "effect_on_host",
             "evidence_basis", "interaction_notes", "fungal_taxon", "plant_host",
             "primary_guild", "country"]),
            "presence_absence": "None Found"}]
    rows = []
    for it in inters:
        life = it.get("fungal_lifestyle")
        rows.append({
            **base,
            "fungus": it.get("fungus"), "host_plant": it.get("host_plant"),
            "tissue": "|".join(it.get("tissue") or []),
            "fungal_lifestyle": life, "effect_on_host": it.get("effect_on_host"),
            "evidence_basis": it.get("evidence_basis"),
            "interaction_notes": it.get("interaction_notes"),
            # legacy aliases for 02_ollama_cleanup.R / merge_final_data.py
            "fungal_taxon": it.get("fungus"), "plant_host": it.get("host_plant"),
            "primary_guild": S.LIFESTYLE_TO_LEGACY_GUILD.get(life, "Unknown"),
            "country": m.get("sampling_location"),
            "presence_absence": "Present",
        })
    return rows


# ---------------------------------------------------------------- inputs

def iter_abstracts(path: Path):
    df = pd.read_csv(path, low_memory=False)
    doi_c = next(c for c in ("DOI", "doi", "paper_id") if c in df.columns)
    abs_c = next(c for c in ("abstract", "Abstract", "AB", "text") if c in df.columns)
    for _, r in df.iterrows():
        doi = str(r[doi_c]).strip()
        txt = str(r.get(abs_c) or "").strip()
        if doi and txt:
            yield doi, doi, txt, {"source_file": None, "n_pages": None}


def iter_fulltexts(manifest: Path, pdf_dir: Path):
    man = pd.read_csv(manifest)
    ok = man[man["status"] == "downloaded"] if "status" in man.columns else man
    for _, r in ok.iterrows():
        p = pdf_dir / str(r["filename"])
        if p.exists():
            yield str(r["doi"]), str(r["doi"]), p, {"source_file": r["filename"],
                                                    "n_pages": r.get("n_pages")}


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["abstract", "fulltext"], required=True)
    ap.add_argument("--input", type=Path, help="abstract mode: CSV with doi + abstract")
    ap.add_argument("--manifest", type=Path, help="fulltext mode: pdf_manifest.csv")
    ap.add_argument("--pdf-dir", type=Path, help="fulltext mode: folder of PDFs")
    ap.add_argument("--model", default="mistral")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--num-ctx", type=int, default=0)
    ap.add_argument("--max-chars", type=int, default=0)
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--no-ocr", action="store_true",
                    help="skip scanned PDFs instead of OCR'ing them (default: OCR via ocrmypdf)")
    ap.add_argument("--ocr-cache", type=Path, default=None,
                    help="dir for OCR'd copies (default: <pdf-dir>/_ocr)")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    num_ctx, max_chars = MODEL_CFG.get(args.model, DEFAULT_CFG)
    num_ctx = args.num_ctx or num_ctx
    max_chars = args.max_chars or max_chars

    if args.mode == "abstract":
        if not args.input:
            ap.error("--input required for --mode abstract")
        items = list(iter_abstracts(args.input))
    else:
        if not (args.manifest and args.pdf_dir):
            ap.error("--manifest and --pdf-dir required for --mode fulltext")
        items = list(iter_fulltexts(args.manifest, args.pdf_dir))

    if args.nshards > 1:
        items = [x for i, x in enumerate(items) if i % args.nshards == args.shard]
    if args.limit:
        items = items[:args.limit]

    done = set()
    all_rows = []
    if args.out.exists():
        prev = pd.read_csv(args.out, low_memory=False)
        all_rows = prev.to_dict("records")
        done = set(prev["paper_id"].astype(str))
        print(f"resuming: {len(done)} papers already done")

    print(f"mode={args.mode} model={args.model} num_ctx={num_ctx} max_chars={max_chars} "
          f"papers={len(items)}")

    for i, (pid, doi, payload, extra) in enumerate(items):
        if str(pid) in done:
            continue
        if args.mode == "abstract":
            chunks = [S.build_prompt(payload, doc_type="abstract", doi=doi)]
            n_pages, doc_type, data_source = None, "abstract", "abstract-reextract"
        else:
            prep = pdf_segment.prepare(payload, doi=doi, max_chars=max_chars,
                                       ocr=not args.no_ocr,
                                       ocr_cache_dir=args.ocr_cache or (args.pdf_dir / "_ocr"))
            n_pages = prep["n_pages"]
            if not prep["chunks"]:
                all_rows.append({"paper_id": pid, "doi": doi,
                                 "source_file": extra["source_file"],
                                 "data_source": "fulltext-reextract",
                                 "doc_type_ai": "fulltext", "model": args.model,
                                 "schema_version": S.SCHEMA_VERSION,
                                 "presence_absence": f"PDF unusable: {prep['note']}"})
                continue
            chunks = [S.build_prompt(c, doc_type="fulltext", doi=doi) for c in prep["chunks"]]
            doc_type, data_source = "fulltext", "fulltext-reextract"

        objs, malformed = [], 0
        for prompt in chunks:
            obj, status = call_model(args.model, prompt, num_ctx, args.timeout)
            if obj is None:
                malformed += 1
            else:
                objs.append(obj)

        merged = merge_chunk_objs(objs)
        ctx = {"model": args.model, "doc_type": doc_type, "data_source": data_source,
               "n_pages": n_pages, "n_chunks": len(chunks), "malformed_chunks": malformed,
               "source_file": extra["source_file"]}
        all_rows.extend(to_rows(pid, doi, merged, ctx))

        if (i + 1) % 5 == 0:
            pd.DataFrame(all_rows).reindex(columns=S.CSV_COLUMNS).to_csv(args.out, index=False)
            print(f"[{i+1}/{len(items)}] {doi}  interactions={len(merged.get('interactions', []))} "
                  f"malformed_chunks={malformed}")

    pd.DataFrame(all_rows).reindex(columns=S.CSV_COLUMNS).to_csv(args.out, index=False)
    print(f"wrote {args.out} ({len(all_rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
