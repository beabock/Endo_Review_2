#!/usr/bin/env python3
# BMB 2026-06-05
# Uses Ollama to scan full-text PDFs for explicit ubiquity claims about endophytes.
# Designed for Monsoon HPC; outputs per-shard CSVs merged by merge_ubiquity_shards.py.

from __future__ import annotations

import argparse
import csv
import importlib
import json
import os
import re
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}
DEFAULT_INPUT_DIR = "/scratch/bmb646/Bea_Nick_papers_endoreview"
DEFAULT_OUTPUT_DIR = "results/ubiquity_claims"
DEFAULT_ABSTRACT_CSV = "/scratch/bmb646/Abstracts_for_Monsoon.csv"
DEFAULT_ABSTRACT_TEXT_COLS = ["Abstract", "abstract", "ABSTRACT", "summary", "text"]
DEFAULT_ABSTRACT_ID_COLS = ["DOI", "doi", "paper_id", "id", "Title", "title"]

KEYWORD_RE = re.compile(
    r"\b(ubiquit(?:ous|y)|all\s+plants|every\s+plant|nearly\s+all\s+plants|"
    r"found\s+in\s+(?:all|most)\s+plants|widespread|cosmopolitan|broadly\s+distributed)\b",
    re.IGNORECASE,
)


@dataclass
class DetectionResult:
    source_type: str
    source_file: str
    doc_id: str
    contains_ubiquity_claim: bool
    claim_strength: str
    claim_scope: str
    confidence: float
    evidence_sentences: List[str]
    rationale: str
    citation: str
    text_chars: int
    snippets_used: int
    keyword_hits: int
    model_name: str
    error: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect fungal endophyte ubiquity claims from full-text files using Ollama."
    )
    parser.add_argument("--input-dir", default=DEFAULT_INPUT_DIR, help="Directory with PDF/TXT/MD files")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory for output files")
    parser.add_argument(
        "--source-mode",
        choices=["fulltext", "abstract", "both", "paired"],
        default="fulltext",
        help=(
            "Input source mode: fulltext files, abstract CSV, both independently, "
            "or paired (try DOI-matched PDF first then fallback to abstract)."
        ),
    )
    parser.add_argument(
        "--abstract-csv",
        default="",
        help="Optional path to CSV containing abstract text (used in abstract/both modes)",
    )
    parser.add_argument(
        "--abstract-text-col",
        default="",
        help="Column name for abstract text (auto-detected if omitted)",
    )
    parser.add_argument(
        "--abstract-id-col",
        default="",
        help="Column name for row id/DOI/title (auto-detected if omitted)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OLLAMA_MODEL", ""),
        help="Ollama model name (or set OLLAMA_MODEL env var)",
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=500,
        help="Write checkpointed output files every N processed items (default: 500)",
    )
    parser.add_argument(
        "--n-shards",
        type=int,
        default=1,
        help="Total number of shards to split the workload into (default: 1)",
    )
    parser.add_argument(
        "--shard-id",
        type=int,
        default=0,
        help="Zero-based shard id for this process (0 <= shard-id < n-shards)",
    )
    parser.add_argument(
        "--ollama-host",
        default=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"),
        help="Ollama API host, e.g. http://127.0.0.1:11434",
    )
    parser.add_argument("--max-files", type=int, default=0, help="Max number of files to process (0 = all)")
    parser.add_argument(
        "--max-snippets",
        type=int,
        default=5,
        help="Max keyword-centered snippets per document",
    )
    parser.add_argument(
        "--snippet-window",
        type=int,
        default=500,
        help="Character window around each keyword hit",
    )
    parser.add_argument(
        "--max-context-chars",
        type=int,
        default=8000,
        help="Maximum text length sent to model per file",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.0,
        help="Optional delay between model calls",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.model:
        raise SystemExit(
            "Missing Ollama model name. Pass --model <name> or set OLLAMA_MODEL in the environment."
        )
    if args.source_mode in {"fulltext", "both", "paired"}:
        input_dir = Path(args.input_dir)
        if not input_dir.exists() or not input_dir.is_dir():
            raise SystemExit(f"Input directory not found: {input_dir}")

    if args.source_mode in {"abstract", "both", "paired"}:
        csv_path = Path(args.abstract_csv) if args.abstract_csv else Path(DEFAULT_ABSTRACT_CSV)
        if not csv_path.exists() or not csv_path.is_file():
            raise SystemExit(
                f"Abstract CSV not found: {csv_path}. Pass --abstract-csv <path> or use --source-mode fulltext."
            )


def read_pdf(path: Path) -> str:
    try:
        pypdf = importlib.import_module("pypdf")
        PdfReader = getattr(pypdf, "PdfReader")
    except Exception as exc:
        raise RuntimeError(
            "Reading PDF requires the pypdf package. Install it with: pip install pypdf"
        ) from exc

    reader = PdfReader(str(path))
    chunks: List[str] = []
    for page in reader.pages:
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        if txt:
            chunks.append(txt)
    return "\n".join(chunks)


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return read_pdf(path)
    if suffix in {".txt", ".md"}:
        return read_text_file(path)
    return ""


def iter_documents(input_dir: Path) -> Iterable[Path]:
    for path in sorted(input_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def pick_column(preferred: str, fieldnames: List[str], defaults: List[str]) -> str:
    if preferred:
        if preferred not in fieldnames:
            raise RuntimeError(f"Column '{preferred}' not found in CSV. Columns: {fieldnames}")
        return preferred
    for name in defaults:
        if name in fieldnames:
            return name
    raise RuntimeError(f"Could not auto-detect required column. Columns: {fieldnames}")


def load_abstract_rows(
    csv_path: Path,
    text_col: str,
    id_col: str,
) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with csv_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        if not fieldnames:
            raise RuntimeError(f"CSV appears to have no header: {csv_path}")

        resolved_text_col = pick_column(text_col, fieldnames, DEFAULT_ABSTRACT_TEXT_COLS)
        resolved_id_col = pick_column(id_col, fieldnames, DEFAULT_ABSTRACT_ID_COLS)

        for i, row in enumerate(reader, start=1):
            abstract_text = str(row.get(resolved_text_col, "") or "").strip()
            if not abstract_text:
                continue
            doc_id = str(row.get(resolved_id_col, "") or "").strip() or f"row_{i}"
            source_name = f"{csv_path.name}:row_{i}"
            doi = str(row.get("DOI", "") or row.get("doi", "") or "").strip()
            rows.append(
                {
                    "source_name": source_name,
                    "doc_id": doc_id,
                    "abstract_text": abstract_text,
                    "doi": doi,
                }
            )

    return rows


def compact_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def collect_snippets(
    text: str,
    max_snippets: int,
    snippet_window: int,
    max_context_chars: int,
) -> Tuple[str, int, int]:
    """Collect text snippets. For speed, just grab first max_context_chars."""
    text = compact_whitespace(text)
    if not text:
        return "", 0, 0

    # Count keyword hits for reporting
    matches = list(KEYWORD_RE.finditer(text))
    keyword_hits = len(matches)

    # Simple: just take the first max_context_chars to avoid complex snippet logic
    context = text[:max_context_chars]
    
    return context, 1, keyword_hits


def build_prompt(context: str, source_name: str) -> str:
    return (
        "You are an information extraction model for scientific literature.\n"
        "Decide whether the text contains a claim that fungal endophytes are ubiquitous, "
        "near-universal, or found in nearly all plants.\n"
        "Return strict JSON only with keys: contains_ubiquity_claim (boolean), claim_strength "
        "(explicit|qualified|none), claim_scope (endophytes_general|specific_taxon|other|none), "
        "confidence (0-1), evidence_sentences (array), citation (string: if the claim cites a reference, extract it; "
        "otherwise empty), rationale (string).\n\n"
        f"Source: {source_name}\n"
        "Text:\n"
        f"{context}"
    )


def sanitize_for_filename(value: str) -> str:
    # Mirrors the DOI->filename style used in previous Monsoon scripts.
    return value.replace("/", "_").replace("\\", "_").strip()


def find_pdf_for_row(input_dir: Path, doi: str, doc_id: str) -> Optional[Path]:
    candidates: List[Path] = []

    if doi:
        doi_key = sanitize_for_filename(doi)
        candidates.append(input_dir / f"{doi_key}.pdf")
        candidates.append(input_dir / f"DOI_{doi_key}.pdf")

    if doc_id:
        doc_key = sanitize_for_filename(doc_id)
        candidates.append(input_dir / f"{doc_key}.pdf")
        candidates.append(input_dir / f"DOI_{doc_key}.pdf")

    for c in candidates:
        if c.exists() and c.is_file():
            return c

    return None


def get_ollama_client(ollama_host: str):
    try:
        ollama_mod = importlib.import_module("ollama")
    except Exception as exc:
        raise RuntimeError("Missing Python package 'ollama'. Install with: pip install ollama") from exc

    client_ctor = getattr(ollama_mod, "Client", None)
    if client_ctor is None:
        # Fallback for older package APIs.
        return ollama_mod
    return client_ctor(host=ollama_host)


def parse_model_json_response(content: str) -> Dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(content[start : end + 1])
        raise RuntimeError("Could not parse JSON content from Ollama response")


def timeout_handler(signum, frame):
    raise TimeoutError("Model request exceeded timeout")


def ollama_generate_json(
    ollama_host: str,
    model: str,
    prompt: str,
    timeout_seconds: int = 120,
) -> Dict:
    """Generate JSON from Ollama with simple timeout."""
    client = get_ollama_client(ollama_host)
    
    # Set timeout alarm
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    
    try:
        response_data = client.generate(
            model=model,
            prompt=prompt,
            format="json",
            stream=False,
        )
        signal.alarm(0)  # Cancel alarm
        
        content = ""
        if isinstance(response_data, dict):
            content = str(response_data.get("response", "") or "")
        else:
            content = str(getattr(response_data, "response", "") or "")

        if not content:
            raise RuntimeError("Ollama returned empty response content")

        return parse_model_json_response(content)
    
    except TimeoutError as exc:
        signal.alarm(0)
        raise RuntimeError(f"Model request timeout after {timeout_seconds}s: {exc}") from exc
    except Exception as exc:
        signal.alarm(0)
        raise RuntimeError(f"Ollama API request failed: {exc}") from exc


def fetch_ollama_tags(ollama_host: str) -> Dict:
    client = get_ollama_client(ollama_host)
    try:
        tags = client.list()
    except Exception as exc:
        raise RuntimeError(f"Cannot connect to Ollama at {ollama_host}: {exc}") from exc

    if isinstance(tags, dict):
        return tags
    if hasattr(tags, "model_dump"):
        return tags.model_dump()
    return {}


def model_available(tags_json: Dict, requested_model: str) -> bool:
    models = tags_json.get("models", [])
    if not isinstance(models, list):
        return False

    names: List[str] = []
    for m in models:
        if isinstance(m, dict):
            for key in ("name", "model"):
                value = m.get(key)
                if isinstance(value, str) and value.strip():
                    names.append(value.strip())

    req = requested_model.strip()
    if req in names:
        return True

    # Also allow matching without explicit tag, e.g., mistral == mistral:latest.
    if ":" not in req:
        prefix = req + ":"
        if any(n.startswith(prefix) for n in names):
            return True

    return False


def preflight_ollama(ollama_host: str, model: str) -> None:
    tags = fetch_ollama_tags(ollama_host)
    if not model_available(tags, model):
        available = []
        for m in tags.get("models", []):
            if isinstance(m, dict) and isinstance(m.get("name"), str):
                available.append(m["name"])
        preview = ", ".join(available[:15]) if available else "<none>"
        raise SystemExit(
            "Ollama is reachable, but requested model was not found: "
            f"'{model}'. Available models (first 15): {preview}. "
            "Run 'ollama pull <model>' or set OLLAMA_MODEL to an installed model."
        )


def to_result(
    response_json: Dict,
    source_file: str,
    doc_id: str,
    text_chars: int,
    snippets_used: int,
    keyword_hits: int,
    model_name: str,
    source_type: str = "",
) -> DetectionResult:
    contains = bool(response_json.get("contains_ubiquity_claim", False))
    strength = str(response_json.get("claim_strength", "none")).strip().lower() or "none"
    scope = str(response_json.get("claim_scope", "none")).strip().lower() or "none"

    confidence_raw = response_json.get("confidence", 0.0)
    try:
        confidence = float(confidence_raw)
    except Exception:
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    evidence = response_json.get("evidence_sentences", [])
    if not isinstance(evidence, list):
        evidence = []
    evidence = [str(x).strip() for x in evidence if str(x).strip()][:3]

    rationale = str(response_json.get("rationale", "")).strip()
    
    citation = str(response_json.get("citation", "")).strip()

    return DetectionResult(
        source_type=source_type,
        source_file=source_file,
        doc_id=doc_id,
        contains_ubiquity_claim=contains,
        claim_strength=strength,
        claim_scope=scope,
        confidence=confidence,
        evidence_sentences=evidence,
        rationale=rationale,
        citation=citation,
        text_chars=text_chars,
        snippets_used=snippets_used,
        keyword_hits=keyword_hits,
        model_name=model_name,
    )


def write_outputs(results: List[DetectionResult], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    all_csv = output_dir / "ubiquity_claims_all.csv"
    pos_csv = output_dir / "ubiquity_claims_positive.csv"
    jsonl_file = output_dir / "ubiquity_claims_all.jsonl"

    fieldnames = [
        "source_type",
        "source_file",
        "doc_id",
        "contains_ubiquity_claim",
        "claim_strength",
        "claim_scope",
        "confidence",
        "evidence_sentences",
        "rationale",
        "citation",
        "text_chars",
        "snippets_used",
        "keyword_hits",
        "model_name",
        "error",
    ]

    with all_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(
                {
                    "source_type": r.source_type,
                    "source_file": r.source_file,
                    "doc_id": r.doc_id,
                    "contains_ubiquity_claim": r.contains_ubiquity_claim,
                    "claim_strength": r.claim_strength,
                    "claim_scope": r.claim_scope,
                    "confidence": f"{r.confidence:.3f}",
                    "evidence_sentences": " || ".join(r.evidence_sentences),
                    "rationale": r.rationale,
                    "citation": r.citation,
                    "text_chars": r.text_chars,
                    "snippets_used": r.snippets_used,
                    "keyword_hits": r.keyword_hits,
                    "model_name": r.model_name,
                    "error": r.error,
                }
            )

    positives = [r for r in results if r.contains_ubiquity_claim and not r.error]
    with pos_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in positives:
            writer.writerow(
                {
                    "source_type": r.source_type,
                    "source_file": r.source_file,
                    "doc_id": r.doc_id,
                    "contains_ubiquity_claim": r.contains_ubiquity_claim,
                    "claim_strength": r.claim_strength,
                    "claim_scope": r.claim_scope,
                    "confidence": f"{r.confidence:.3f}",
                    "evidence_sentences": " || ".join(r.evidence_sentences),
                    "rationale": r.rationale,
                    "citation": r.citation,
                    "text_chars": r.text_chars,
                    "snippets_used": r.snippets_used,
                    "keyword_hits": r.keyword_hits,
                    "model_name": r.model_name,
                    "error": r.error,
                }
            )

    with jsonl_file.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(
                json.dumps(
                    {
                        "source_type": r.source_type,
                        "source_file": r.source_file,
                        "doc_id": r.doc_id,
                        "contains_ubiquity_claim": r.contains_ubiquity_claim,
                        "claim_strength": r.claim_strength,
                        "claim_scope": r.claim_scope,
                        "confidence": r.confidence,
                        "evidence_sentences": r.evidence_sentences,
                        "rationale": r.rationale,
                        "citation": r.citation,
                        "text_chars": r.text_chars,
                        "snippets_used": r.snippets_used,
                        "keyword_hits": r.keyword_hits,
                        "model_name": r.model_name,
                        "error": r.error,
                    },
                    ensure_ascii=True,
                )
                + "\n"
            )


def main() -> None:
    args = parse_args()
    validate_args(args)

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    # Ensure output dir exists early so checkpoint writes succeed during long runs
    output_dir.mkdir(parents=True, exist_ok=True)

    documents: List[Path] = []
    abstract_rows: List[Dict[str, str]] = []

    if args.source_mode in {"fulltext", "both"}:
        documents = list(iter_documents(input_dir))

    if args.source_mode in {"abstract", "both", "paired"}:
        abstract_csv_path = Path(args.abstract_csv) if args.abstract_csv else Path(DEFAULT_ABSTRACT_CSV)
        abstract_rows = load_abstract_rows(
            csv_path=abstract_csv_path,
            text_col=args.abstract_text_col,
            id_col=args.abstract_id_col,
        )

    # Apply sharding if requested: split both document list and abstract rows by index modulo n_shards
    n_shards = max(1, int(args.n_shards))
    shard_id = int(args.shard_id) % n_shards
    if n_shards > 1:
        if documents:
            docs_sharded: List[Path] = []
            for i, p in enumerate(documents):
                if (i % n_shards) == shard_id:
                    docs_sharded.append(p)
            documents = docs_sharded
        if abstract_rows:
            abs_sharded: List[Dict[str, str]] = []
            for i, row in enumerate(abstract_rows):
                if (i % n_shards) == shard_id:
                    abs_sharded.append(row)
            abstract_rows = abs_sharded

    if args.max_files > 0:
        if args.source_mode == "fulltext":
            documents = documents[: args.max_files]
        elif args.source_mode == "abstract":
            abstract_rows = abstract_rows[: args.max_files]
        elif args.source_mode == "both":
            # In combined mode, split the cap across both sources deterministically.
            half = max(1, args.max_files // 2)
            documents = documents[:half]
            abstract_rows = abstract_rows[: max(0, args.max_files - len(documents))]
        else:
            abstract_rows = abstract_rows[: args.max_files]

    if not documents and not abstract_rows:
        raise SystemExit("No inputs found for selected source mode.")

    print(f"Source mode: {args.source_mode}")
    print(f"Input dir: {input_dir}")
    print(f"Output dir: {output_dir}")
    print(f"Model: {args.model}")
    print(f"Ollama host: {args.ollama_host}")
    print(f"Full-text files to process: {len(documents)}")
    print(f"Abstract rows to process: {len(abstract_rows)}")

    # Fail fast if Ollama is down or model is unavailable.
    preflight_ollama(args.ollama_host, args.model)

    results: List[DetectionResult] = []

    for idx, path in enumerate(documents, start=1):
        rel_path = str(path.relative_to(input_dir))
        doc_id = path.stem
        print(f"[fulltext {idx}/{len(documents)}] Processing: {rel_path}")

        try:
            raw_text = load_document(path)
            raw_text = raw_text or ""
            context, snippets_used, keyword_hits = collect_snippets(
                raw_text,
                max_snippets=args.max_snippets,
                snippet_window=args.snippet_window,
                max_context_chars=args.max_context_chars,
            )

            if not context:
                results.append(
                    DetectionResult(
                        source_type="fulltext",
                        source_file=rel_path,
                        doc_id=doc_id,
                        contains_ubiquity_claim=False,
                        claim_strength="none",
                        claim_scope="none",
                        confidence=0.0,
                        evidence_sentences=[],
                        rationale="No readable text could be extracted from file.",
                        text_chars=0,
                        snippets_used=0,
                        keyword_hits=0,
                        model_name=args.model,
                        citation="",
                        error="no_text_extracted",
                    )
                )
                continue

            prompt = build_prompt(context=context, source_name=rel_path)
            response_json = ollama_generate_json(
                ollama_host=args.ollama_host,
                model=args.model,
                prompt=prompt,
            )
            result = to_result(
                response_json=response_json,
                source_file=rel_path,
                doc_id=doc_id,
                text_chars=len(raw_text),
                snippets_used=snippets_used,
                keyword_hits=keyword_hits,
                model_name=args.model,
            )
            result.source_type = "fulltext"
            results.append(result)

            # Checkpoint writes for long runs to produce partial outputs incrementally
            try:
                if args.checkpoint_interval > 0 and len(results) % args.checkpoint_interval == 0:
                    write_outputs(results, output_dir)
                    print(f"Checkpoint: wrote {len(results)} results to {output_dir}")
            except Exception as _:
                print("WARNING: checkpoint write failed; continuing")

            # Checkpoint writes for long runs to produce partial outputs incrementally
            try:
                if args.checkpoint_interval > 0 and len(results) % args.checkpoint_interval == 0:
                    write_outputs(results, output_dir)
                    print(f"Checkpoint: wrote {len(results)} results to {output_dir}")
            except Exception as _:
                print("WARNING: checkpoint write failed; continuing")

            if args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)

        except Exception as exc:
            results.append(
                DetectionResult(
                    source_type="fulltext",
                    source_file=rel_path,
                    doc_id=doc_id,
                    contains_ubiquity_claim=False,
                    claim_strength="none",
                    claim_scope="none",
                    confidence=0.0,
                    evidence_sentences=[],
                    rationale="",
                    text_chars=0,
                    snippets_used=0,
                    keyword_hits=0,
                    model_name=args.model,
                    citation="",
                    error=str(exc),
                )
            )
            print(f"  ERROR: {exc}")
            try:
                if args.checkpoint_interval > 0 and len(results) % args.checkpoint_interval == 0:
                    write_outputs(results, output_dir)
                    print(f"Checkpoint: wrote {len(results)} results to {output_dir}")
            except Exception:
                pass
            try:
                if args.checkpoint_interval > 0 and len(results) % args.checkpoint_interval == 0:
                    write_outputs(results, output_dir)
                    print(f"Checkpoint: wrote {len(results)} results to {output_dir}")
            except Exception:
                pass

    for idx, row in enumerate(abstract_rows, start=1):
        source_name = row["source_name"]
        doc_id = row["doc_id"]
        abstract_text = row["abstract_text"]
        doi = row.get("doi", "")

        process_label = "abstract"
        raw_text = abstract_text
        source_type = "abstract"

        if args.source_mode == "paired":
            matched_pdf = find_pdf_for_row(input_dir=input_dir, doi=doi, doc_id=doc_id)
            if matched_pdf is not None:
                process_label = "paired-pdf"
                source_type = "fulltext"
                source_name = str(matched_pdf.relative_to(input_dir))
                try:
                    raw_text = load_document(matched_pdf) or ""
                except Exception:
                    # Keep abstract fallback if PDF read fails.
                    raw_text = abstract_text
                    source_type = "abstract"
                    process_label = "paired-abstract-fallback"
            else:
                process_label = "paired-abstract-fallback"

        print(f"[{process_label} {idx}/{len(abstract_rows)}] Processing: {source_name}")

        try:
            context, snippets_used, keyword_hits = collect_snippets(
                raw_text,
                max_snippets=args.max_snippets,
                snippet_window=args.snippet_window,
                max_context_chars=args.max_context_chars,
            )

            if not context:
                results.append(
                    DetectionResult(
                        source_type=source_type,
                        source_file=source_name,
                        doc_id=doc_id,
                        contains_ubiquity_claim=False,
                        claim_strength="none",
                        claim_scope="none",
                        confidence=0.0,
                        evidence_sentences=[],
                        rationale="No readable text found in abstract row.",
                        text_chars=0,
                        snippets_used=0,
                        keyword_hits=0,
                        model_name=args.model,
                        citation="",
                        error="no_text_extracted",
                    )
                )
                continue

            prompt = build_prompt(context=context, source_name=source_name)
            response_json = ollama_generate_json(
                ollama_host=args.ollama_host,
                model=args.model,
                prompt=prompt,
            )
            result = to_result(
                response_json=response_json,
                source_file=source_name,
                doc_id=doc_id,
                text_chars=len(raw_text),
                snippets_used=snippets_used,
                keyword_hits=keyword_hits,
                model_name=args.model,
            )
            result.source_type = source_type
            results.append(result)

            if args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)

        except Exception as exc:
            results.append(
                DetectionResult(
                    source_type=source_type,
                    source_file=source_name,
                    doc_id=doc_id,
                    contains_ubiquity_claim=False,
                    claim_strength="none",
                    claim_scope="none",
                    confidence=0.0,
                    evidence_sentences=[],
                    rationale="",
                    text_chars=0,
                    snippets_used=0,
                    keyword_hits=0,
                    model_name=args.model,
                    citation="",
                    error=str(exc),
                )
            )
            print(f"  ERROR: {exc}")

    write_outputs(results, output_dir)

    n_total = len(results)
    n_pos = sum(1 for r in results if r.contains_ubiquity_claim and not r.error)
    n_err = sum(1 for r in results if r.error)
    print("\nRun complete.")
    print(f"  Total files processed: {n_total}")
    print(f"  Positive ubiquity-claim files: {n_pos}")
    print(f"  Files with errors: {n_err}")
    print(f"  Outputs written to: {output_dir}")


if __name__ == "__main__":
    main()
