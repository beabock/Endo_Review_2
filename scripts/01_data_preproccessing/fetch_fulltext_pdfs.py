#!/usr/bin/env python3
# BMB 2026-09-02
# Multi-resolver full-text PDF retriever for the Task 1 re-download
# (NPH_task1_paired_validation_plan.md, Phase 0a). Replaces the single-source
# download_pdfs.py (archived).
#
# Resolvers, tried in order until a VALID PDF lands:
#   Unpaywall -> OpenAlex -> Europe PMC -> Semantic Scholar -> CORE -> publisher
#   <meta citation_pdf_url> on the DOI landing page
#
# Features: resumable (skips DOIs that already have a valid PDF), shardable
# (--shard i --nshards n), download validation (magic bytes + PyMuPDF open + page
# count), a per-DOI manifest, a structured miss log, and a --dry-run mode that only
# does resolver lookups and writes a coverage report broken down by publisher /
# journal (answers Referee 2: "are abstract-only papers concentrated in particular
# publishers/journals?").
#
# NOTHING here is run at scale without sign-off. Start with:
#   python fetch_fulltext_pdfs.py --input Abstracts_for_Monsoon.csv --dry-run
#
# Env (optional, improve coverage / rate limits):
#   UNPAYWALL_EMAIL (required; falls back to --email)
#   S2_API_KEY, CORE_API_KEY

from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path

import pandas as pd
import requests

try:
    import fitz  # PyMuPDF - for validation
    _HAVE_FITZ = True
except Exception:
    _HAVE_FITZ = False

UA = "NAU-EndoReview/1.0 (mailto:%s)"
TIMEOUT = 25
MIN_PDF_BYTES = 10_000


# ---------------------------------------------------------------- helpers

def norm_doi(x) -> str:
    if not isinstance(x, str):
        return ""
    x = x.strip().lower()
    x = re.sub(r"^https?://(dx\.)?doi\.org/", "", x)
    x = re.sub(r"^doi:\s*", "", x)
    return x.strip()


def doi_to_filename(doi: str) -> str:
    return re.sub(r"[^a-z0-9._-]", "_", doi) + ".pdf"


def looks_like_pdf(content: bytes) -> bool:
    return content[:5] == b"%PDF-" or b"%PDF-" in content[:1024]


def validate_pdf(path: Path) -> tuple[bool, int, str]:
    """(ok, n_pages, note). Rejects HTML-error-pages saved as .pdf and 0-page files."""
    try:
        if path.stat().st_size < MIN_PDF_BYTES:
            return False, 0, "too small"
        head = path.read_bytes()[:1024]
        if not looks_like_pdf(head):
            return False, 0, "not a PDF (magic bytes)"
        if not _HAVE_FITZ:
            return True, -1, "fitz unavailable - size/magic only"
        with fitz.open(path) as d:
            n = d.page_count
        return (n >= 1), n, ("ok" if n >= 1 else "0 pages")
    except Exception as e:                        # noqa: BLE001
        return False, 0, f"open failed: {e}"


class Session:
    def __init__(self, email: str):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = UA % email
        self.email = email

    def get(self, url, **kw):
        kw.setdefault("timeout", TIMEOUT)
        return self.s.get(url, **kw)

    def json(self, url, **kw):
        try:
            r = self.get(url, **kw)
            if r.status_code == 200:
                return r.json()
        except Exception:                        # noqa: BLE001
            pass
        return None


# ---------------------------------------------------------------- resolvers
# each returns (pdf_url | None, meta_dict)

def r_unpaywall(sess: Session, doi: str) -> tuple[str | None, dict]:
    d = sess.json(f"https://api.unpaywall.org/v2/{doi}", params={"email": sess.email})
    if not d:
        return None, {}
    meta = {"journal": d.get("journal_name"), "publisher": d.get("publisher"),
            "is_oa": d.get("is_oa"), "oa_status": d.get("oa_status"),
            "genre": d.get("genre")}
    loc = d.get("best_oa_location") or {}
    url = loc.get("url_for_pdf")
    if not url:
        for loc in d.get("oa_locations", []):
            if loc.get("url_for_pdf"):
                url = loc["url_for_pdf"]
                break
    return url, meta


def r_openalex(sess: Session, doi: str) -> tuple[str | None, dict]:
    d = sess.json(f"https://api.openalex.org/works/https://doi.org/{doi}",
                  params={"mailto": sess.email})
    if not d:
        return None, {}
    meta = {"openalex_oa": (d.get("open_access") or {}).get("is_oa")}
    loc = d.get("best_oa_location") or d.get("primary_location") or {}
    return loc.get("pdf_url"), meta


def r_europepmc(sess: Session, doi: str) -> tuple[str | None, dict]:
    d = sess.json("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                  params={"query": f"DOI:{doi}", "format": "json", "resultType": "core"})
    try:
        res = d["resultList"]["result"][0]
    except Exception:
        return None, {}
    for ft in (res.get("fullTextUrlList") or {}).get("fullTextUrl", []):
        if ft.get("documentStyle") == "pdf" and ft.get("availability") in ("Open access", "Free"):
            return ft.get("url"), {}
    pmcid = res.get("pmcid")
    if pmcid:
        return (f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextPDF"), {}
    return None, {}


def r_semanticscholar(sess: Session, doi: str) -> tuple[str | None, dict]:
    headers = {}
    if os.getenv("S2_API_KEY"):
        headers["x-api-key"] = os.environ["S2_API_KEY"]
    d = sess.json(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
                  params={"fields": "openAccessPdf,isOpenAccess"}, headers=headers)
    if not d:
        return None, {}
    return (d.get("openAccessPdf") or {}).get("url"), {}


def r_core(sess: Session, doi: str) -> tuple[str | None, dict]:
    key = os.getenv("CORE_API_KEY")
    if not key:
        return None, {}
    d = sess.json("https://api.core.ac.uk/v3/search/works",
                  params={"q": f'doi:"{doi}"', "limit": 1},
                  headers={"Authorization": f"Bearer {key}"})
    try:
        w = d["results"][0]
    except Exception:
        return None, {}
    return w.get("downloadUrl"), {}


META_PDF_RE = re.compile(
    r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)["\']', re.I)


def r_publisher_meta(sess: Session, doi: str) -> tuple[str | None, dict]:
    try:
        r = sess.get(f"https://doi.org/{doi}", headers={"Accept": "text/html"})
        if r.status_code == 200 and "html" in r.headers.get("content-type", ""):
            m = META_PDF_RE.search(r.text[:200_000])
            if m:
                return m.group(1), {}
    except Exception:                            # noqa: BLE001
        pass
    return None, {}


RESOLVERS = [
    ("unpaywall", r_unpaywall), ("openalex", r_openalex), ("europepmc", r_europepmc),
    ("semanticscholar", r_semanticscholar), ("core", r_core),
    ("publisher_meta", r_publisher_meta),
]


# ---------------------------------------------------------------- download

def try_download(sess: Session, url: str, dest: Path) -> tuple[bool, str]:
    try:
        r = sess.get(url, stream=True, allow_redirects=True)
        if r.status_code != 200:
            return False, f"http {r.status_code}"
        ct = r.headers.get("content-type", "").lower()
        content = r.content
        if "pdf" not in ct and not looks_like_pdf(content):
            return False, f"not pdf (ct={ct[:40]})"
        dest.write_bytes(content)
        ok, n, note = validate_pdf(dest)
        if not ok:
            dest.unlink(missing_ok=True)
            return False, note
        return True, f"ok ({n}p)"
    except Exception as e:                        # noqa: BLE001
        return False, f"exc {e}"


# ---------------------------------------------------------------- main

def load_dois(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    col = next((c for c in ("DOI", "doi", "paper_id") if c in df.columns), None)
    if col is None:
        raise SystemExit(f"no DOI column in {path} (looked for DOI/doi/paper_id)")
    df["_doi"] = df[col].map(norm_doi)
    df = df[df["_doi"].str.len() > 0].drop_duplicates("_doi").reset_index(drop=True)
    return df


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, required=True,
                    help="CSV with a DOI / doi / paper_id column")
    ap.add_argument("--out-dir", type=Path, default=Path("full_corpus"))
    ap.add_argument("--manifest", type=Path, default=None,
                    help="default: <out-dir>/pdf_manifest.csv")
    ap.add_argument("--email", default=os.getenv("UNPAYWALL_EMAIL", ""),
                    help="Unpaywall contact email (or set UNPAYWALL_EMAIL)")
    ap.add_argument("--dry-run", action="store_true",
                    help="resolver lookups only; write a coverage report, download nothing")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0, help="stop after N DOIs (testing)")
    ap.add_argument("--sleep", type=float, default=0.3)
    args = ap.parse_args()

    if not args.email:
        raise SystemExit("need --email or UNPAYWALL_EMAIL")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.manifest or (args.out_dir / "pdf_manifest.csv")

    df = load_dois(args.input)
    if args.nshards > 1:
        df = df[df.index % args.nshards == args.shard].reset_index(drop=True)
    if args.limit:
        df = df.head(args.limit)

    done = {}
    if manifest_path.exists():
        prev = pd.read_csv(manifest_path)
        done = {r["doi"]: r for _, r in prev.iterrows()}

    sess = Session(args.email)
    rows, t0 = [], time.time()
    for i, doi in enumerate(df["_doi"]):
        fn = doi_to_filename(doi)
        dest = args.out_dir / fn

        if not args.dry_run and doi in done and str(done[doi].get("status")) == "downloaded" \
                and dest.exists() and validate_pdf(dest)[0]:
            rows.append(done[doi].to_dict())
            continue

        tried, pdf_url, hit_resolver, meta = [], None, None, {}
        for name, fn_res in RESOLVERS:
            try:
                url, m = fn_res(sess, doi)
            except Exception as e:                # noqa: BLE001
                url, m = None, {"err": str(e)}
            meta.update({k: v for k, v in m.items() if v is not None})
            tried.append(name if url else f"{name}:none")
            if url and not pdf_url:
                pdf_url, hit_resolver = url, name
                if args.dry_run:
                    break
            time.sleep(args.sleep)

        row = {"doi": doi, "filename": fn, "resolver": hit_resolver,
               "resolver_url": pdf_url, "tried": ";".join(tried),
               "journal": meta.get("journal"), "publisher": meta.get("publisher"),
               "is_oa": meta.get("is_oa"), "oa_status": meta.get("oa_status"),
               "genre": meta.get("genre"), "status": None, "note": None, "n_pages": None}

        if args.dry_run:
            row["status"] = "resolvable" if pdf_url else "no_oa_pdf"
        elif pdf_url:
            ok, note = try_download(sess, pdf_url, dest)
            row["status"] = "downloaded" if ok else "download_failed"
            row["note"] = note
            if ok:
                row["n_pages"] = validate_pdf(dest)[1]
            else:                                 # try the other resolvers' urls
                for name, fn_res in RESOLVERS:
                    if name == hit_resolver:
                        continue
                    try:
                        url, _ = fn_res(sess, doi)
                    except Exception:             # noqa: BLE001
                        url = None
                    if not url:
                        continue
                    ok, note = try_download(sess, url, dest)
                    if ok:
                        row.update(status="downloaded", resolver=name,
                                   resolver_url=url, note=note,
                                   n_pages=validate_pdf(dest)[1])
                        break
        else:
            row["status"] = "no_oa_pdf"

        rows.append(row)
        if (i + 1) % 25 == 0:
            pd.DataFrame(rows).to_csv(manifest_path, index=False)
            rate = (i + 1) / (time.time() - t0)
            print(f"[{i+1}/{len(df)}] {rate:.1f} doi/s  last={doi} -> {row['status']}")

    man = pd.DataFrame(rows)
    man.to_csv(manifest_path, index=False)

    # ---- summary
    print(f"\n{len(man)} DOIs")
    print(man["status"].value_counts().to_string())
    if args.dry_run:
        rep = args.out_dir / "coverage_report.csv"
        miss = man[man["status"] != "resolvable"]
        by_pub = (miss.groupby(["publisher", "journal"], dropna=False)
                  .size().reset_index(name="n_missing").sort_values("n_missing",
                                                                    ascending=False))
        by_pub.to_csv(rep, index=False)
        print(f"\nabstract-only concentration (top 15) -> {rep}")
        print(by_pub.head(15).to_string(index=False))
        cov = (man["status"] == "resolvable").mean()
        print(f"\nresolvable OA coverage: {cov:.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
