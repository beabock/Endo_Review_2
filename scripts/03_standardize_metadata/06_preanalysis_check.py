#!/usr/bin/env python3
# BMB 2026-06-05
# Validation checks on the cleaned dataset — completeness report written to results/logs/.

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


DEFAULT_STANDARDIZED_FILE = "data/Ollama_cleaned_synresolved_standardized_final.csv"
DEFAULT_FILTERED_FILE = "data/Ollama_cleaned_synresolved_filtered.csv"
DEFAULT_FILTERED_AUDIT_FILE = "results/logs/filtered_rows.csv"
DEFAULT_REPORT_FILE = "results/logs/preanalysis_check_report.txt"
DEFAULT_JSON_FILE = "results/logs/preanalysis_check_report.json"

REQUIRED_COLUMNS = [
    "paper_id",
    "interaction_id",
    "fungal_taxon_resolved",
    "fungal_taxon_status",
    "fungal_taxon_accepted_ids",
    "plant_host_resolved",
    "plant_host_status",
    "plant_host_accepted_ids",
    "country",
    "biome",
    "tissue",
    "primary_guild",
]

STATUS_COLUMNS = ["fungal_taxon_status", "plant_host_status"]
SUMMARY_COLUMNS = ["country", "biome", "tissue", "primary_guild", "relevance", "doc_type_ai"]

MISSING_TOKENS = {"", "na", "n/a", "none", "null", "unknown", "unresolved"}


def normalize_text(value):
    if value is None:
        return ""
    return str(value).strip()


def is_missing(value):
    return normalize_text(value).lower() in MISSING_TOKENS


def count_rows(file_path):
    if not file_path.exists():
        return None

    with file_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        return max(sum(1 for _ in reader) - 1, 0)


def analyze_csv(file_path):
    with file_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []

        row_count = 0
        paper_ids = set()
        interaction_ids = Counter()
        missing_counts = Counter()
        status_counts = {col: Counter() for col in STATUS_COLUMNS}
        summary_counts = {col: Counter() for col in SUMMARY_COLUMNS}

        for row in reader:
            row_count += 1

            paper_id = normalize_text(row.get("paper_id"))
            interaction_id = normalize_text(row.get("interaction_id"))
            if paper_id:
                paper_ids.add(paper_id)
            if interaction_id:
                interaction_ids[interaction_id] += 1

            for col in REQUIRED_COLUMNS:
                if is_missing(row.get(col)):
                    missing_counts[col] += 1

            for col in STATUS_COLUMNS:
                value = normalize_text(row.get(col)) or "EMPTY"
                status_counts[col][value] += 1

            for col in SUMMARY_COLUMNS:
                value = normalize_text(row.get(col)) or "EMPTY"
                summary_counts[col][value] += 1

        duplicate_interaction_rows = sum(count - 1 for count in interaction_ids.values() if count > 1)
        duplicate_interaction_ids = sum(1 for count in interaction_ids.values() if count > 1)

    return {
        "file_path": str(file_path),
        "fieldnames": fieldnames,
        "row_count": row_count,
        "unique_papers": len(paper_ids),
        "unique_interactions": len(interaction_ids),
        "duplicate_interaction_rows": duplicate_interaction_rows,
        "duplicate_interaction_ids": duplicate_interaction_ids,
        "missing_counts": dict(missing_counts),
        "status_counts": {col: dict(counter) for col, counter in status_counts.items()},
        "summary_counts": {col: dict(counter) for col, counter in summary_counts.items()},
    }


def build_report(standardized_stats, filtered_rows, filtered_audit_rows):
    lines = []
    warnings = []
    failures = []

    fieldnames = standardized_stats["fieldnames"]
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in fieldnames]

    lines.append("=" * 72)
    lines.append("PRE-ANALYSIS QA CHECK")
    lines.append("=" * 72)
    lines.append(f"Standardized file: {standardized_stats['file_path']}")
    lines.append(f"Rows: {standardized_stats['row_count']:,}")
    lines.append(f"Unique papers: {standardized_stats['unique_papers']:,}")
    lines.append(f"Unique interaction IDs: {standardized_stats['unique_interactions']:,}")
    lines.append("")

    if missing_columns:
        failures.append("Missing required columns: " + ", ".join(missing_columns))
    if standardized_stats["row_count"] == 0:
        failures.append("Standardized file contains no data rows.")
    if standardized_stats["duplicate_interaction_rows"] > 0:
        warnings.append(
            f"Duplicate interaction_id values found across {standardized_stats['duplicate_interaction_rows']:,} extra row(s)."
        )

    lines.append("STRUCTURAL CHECKS")
    lines.append("-" * 72)
    lines.append(f"Required columns present: {'yes' if not missing_columns else 'no'}")
    lines.append(f"Duplicate interaction rows: {standardized_stats['duplicate_interaction_rows']:,}")
    lines.append(f"Duplicate interaction IDs: {standardized_stats['duplicate_interaction_ids']:,}")

    lines.append("")
    lines.append("KEY STATUS COUNTS")
    lines.append("-" * 72)
    for col in STATUS_COLUMNS:
        counts = Counter(standardized_stats["status_counts"].get(col, {}))
        resolved_total = sum(count for value, count in counts.items() if value.lower() not in {"unresolved", "empty", "na", "n/a", "none", "null", "unknown"})
        unresolved_total = sum(count for value, count in counts.items() if value.lower() in {"unresolved", "empty", "na", "n/a", "none", "null", "unknown"})
        lines.append(f"{col}: resolved/other={resolved_total:,} | unresolved/empty={unresolved_total:,}")
        if resolved_total == 0:
            warnings.append(f"No resolved values detected in {col}.")

    lines.append("")
    lines.append("MISSINGNESS")
    lines.append("-" * 72)
    for col in REQUIRED_COLUMNS:
        missing = standardized_stats["missing_counts"].get(col, 0)
        pct = (missing / standardized_stats["row_count"] * 100) if standardized_stats["row_count"] else 0.0
        lines.append(f"{col}: {missing:,} missing ({pct:.1f}%)")
        if col in {"country", "biome", "tissue", "primary_guild"} and standardized_stats["row_count"] and pct >= 50.0:
            warnings.append(f"High missingness in {col}: {pct:.1f}%.")

    lines.append("")
    lines.append("FILTERING RECONCILIATION")
    lines.append("-" * 72)
    if filtered_rows is None:
        warnings.append("Filtered dataset not found; row reconciliation was skipped.")
        lines.append("Filtered dataset: not found")
    else:
        lines.append(f"Filtered file rows: {filtered_rows:,}")
        if filtered_audit_rows is None:
            warnings.append("Filtered audit file not found; reconciliation against filtered_rows.csv was skipped.")
            lines.append("Filtered audit rows: not found")
        else:
            lines.append(f"Filtered audit rows: {filtered_audit_rows:,}")
            expected_total = filtered_rows + filtered_audit_rows
            lines.append(f"Filtered + audit rows: {expected_total:,}")
            if expected_total != standardized_stats["row_count"]:
                warnings.append(
                    "Row reconciliation mismatch: standardized rows do not equal filtered rows plus filtered audit rows."
                )

        if filtered_rows > standardized_stats["row_count"]:
            warnings.append("Filtered dataset has more rows than the standardized dataset.")
        elif filtered_rows == standardized_stats["row_count"]:
            warnings.append("Filtered dataset has the same row count as the standardized dataset.")

    lines.append("")
    lines.append("SUMMARY COUNTS")
    lines.append("-" * 72)
    for col in SUMMARY_COLUMNS:
        counts = Counter(standardized_stats["summary_counts"].get(col, {}))
        top_value, top_count = counts.most_common(1)[0] if counts else ("EMPTY", 0)
        lines.append(f"{col}: top={top_value!r} ({top_count:,})")

    if warnings:
        lines.append("")
        lines.append("WARNINGS")
        lines.append("-" * 72)
        for warning in warnings:
            lines.append(f"- {warning}")

    if failures:
        lines.append("")
        lines.append("FAILURES")
        lines.append("-" * 72)
        for failure in failures:
            lines.append(f"- {failure}")

    lines.append("")
    if failures:
        status = "FAIL"
    elif warnings:
        status = "PASS_WITH_WARNINGS"
    else:
        status = "PASS"

    lines.append("STATUS: " + status)

    return lines, warnings, failures


def build_parser():
    parser = argparse.ArgumentParser(description="Run pre-analysis QA checks on the standardized dataset.")
    parser.add_argument("--standardized-file", default=DEFAULT_STANDARDIZED_FILE, help="Stage-03 standardized CSV")
    parser.add_argument("--filtered-file", default=DEFAULT_FILTERED_FILE, help="Filtered CSV from stage 03")
    parser.add_argument("--filtered-audit-file", default=DEFAULT_FILTERED_AUDIT_FILE, help="Filtered rows audit CSV")
    parser.add_argument("--report-file", default=DEFAULT_REPORT_FILE, help="Human-readable report path")
    parser.add_argument("--json-file", default=DEFAULT_JSON_FILE, help="JSON report path")
    return parser


def main():
    args = build_parser().parse_args()

    standardized_path = Path(args.standardized_file)
    filtered_path = Path(args.filtered_file)
    filtered_audit_path = Path(args.filtered_audit_file)
    report_path = Path(args.report_file)
    json_path = Path(args.json_file)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    if not standardized_path.exists():
        report_path.write_text(f"Missing standardized file: {standardized_path}\n", encoding="utf-8")
        json_path.write_text(json.dumps({"status": "FAIL", "failure": "Missing standardized file"}, indent=2), encoding="utf-8")
        print(f"Error: missing standardized file: {standardized_path}")
        return 1

    standardized_stats = analyze_csv(standardized_path)
    filtered_rows = count_rows(filtered_path)
    filtered_audit_rows = count_rows(filtered_audit_path)

    lines, warnings, failures = build_report(standardized_stats, filtered_rows, filtered_audit_rows)

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    json_path.write_text(
        json.dumps(
            {
                "standardized_stats": standardized_stats,
                "filtered_rows": filtered_rows,
                "filtered_audit_rows": filtered_audit_rows,
                "warnings": warnings,
                "failures": failures,
                "status": "FAIL" if failures else ("PASS_WITH_WARNINGS" if warnings else "PASS"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print("\n".join(lines))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())