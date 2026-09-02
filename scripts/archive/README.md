# scripts/archive

Superseded scripts, kept for provenance. Not part of the active pipeline.

| file | replaced by | when / why |
|---|---|---|
| `monsoon_extract_v4.py` | `scripts/01_data_preproccessing/monsoon_extract.py` | 2026-09-02, Task 1 Phase 0b. v4 read only the first 12 PDF pages and truncated the prompt to 8,000 chars, so the "full-text" dataset was effectively an extended-abstract dataset. The rewrite does a structure-aware parse → targeted segmentation → context-sized chunks → schema-constrained JSON, with fields locked to the Task 2 ground-truth workbook. |
| `download_pdfs_v4.py` | `scripts/01_data_preproccessing/fetch_fulltext_pdfs.py` | 2026-09-02, Task 1 Phase 0a. v4 was Unpaywall-only, unvalidated, non-resumable. The replacement chains six OA resolvers, validates each download, is resumable + shardable, and has a `--dry-run` coverage report. |

See `NPH_task1_paired_validation_plan.md` (local planning doc) for the full rationale.
