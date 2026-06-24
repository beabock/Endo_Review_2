#!/usr/bin/env python3
# BMB 2026-06-24
# Runs the full analysis pipeline sequentially. Pass --dry-run to preview the
# execution order, or --continue-on-error to keep going past failures.

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List


def find_r_executable() -> str:
	"""Find Rscript on PATH first, then use common Windows install paths."""
	in_path = shutil.which("Rscript")
	if in_path:
		return in_path

	candidates = [
		Path("C:/Program Files/R"),
		Path("C:/Program Files (x86)/R"),
	]
	for root in candidates:
		if not root.exists():
			continue
		discovered = sorted(root.glob("R-*/bin/Rscript.exe"), reverse=True)
		if discovered:
			return str(discovered[0])

	raise FileNotFoundError(
		"Could not find Rscript. Please install R and add Rscript to PATH."
	)


def is_runnable_script(path: Path) -> bool:
	return path.is_file() and path.suffix.lower() in {".py", ".r"}


def collect_stage_scripts(stage_dir: Path, exclude: Iterable[Path] | None = None) -> List[Path]:
	exclude_set = {p.resolve() for p in (exclude or [])}
	scripts = [
		p
		for p in sorted(stage_dir.iterdir())
		if is_runnable_script(p) and p.resolve() not in exclude_set
	]
	return scripts


def build_command(script_path: Path, r_exec: str) -> List[str]:
	if script_path.suffix.lower() == ".py":
		return [sys.executable, str(script_path)]
	if script_path.suffix.lower() == ".r":
		return [r_exec, str(script_path)]
	raise ValueError(f"Unsupported script type: {script_path}")


def run_script(script_path: Path, r_exec: str, dry_run: bool = False) -> int:
	cmd = build_command(script_path, r_exec)
	print(f"\n[RUN] {script_path}")
	print("      " + " ".join(cmd))

	if dry_run:
		return 0

	completed = subprocess.run(cmd, check=False)
	return int(completed.returncode)


def main() -> int:
	parser = argparse.ArgumentParser(description="Run all pipeline scripts in sequence.")
	parser.add_argument(
		"--continue-on-error",
		action="store_true",
		help="Continue running later scripts even if one fails.",
	)
	parser.add_argument(
		"--dry-run",
		action="store_true",
		help="Print execution order without running scripts.",
	)
	args = parser.parse_args()

	repo_root = Path(__file__).resolve().parents[1]
	scripts_root = repo_root / "scripts"

	stage01_script = scripts_root / "01_data_preproccessing" / "02_ollama_cleanup.R"
	stage02_script = scripts_root / "02_taxa_resolution" / "taxa_synonym_resolution.py"

	stage03_dir = scripts_root / "03_standardize_metadata"
	stage04_dir = scripts_root / "04_analyses"
	stage05_dir = scripts_root / "05_plotting"
	stage05_fallback_dir = scripts_root / "plotting"

	if not stage01_script.exists():
		raise FileNotFoundError(f"Missing required script: {stage01_script}")
	if not stage02_script.exists():
		raise FileNotFoundError(f"Missing required script: {stage02_script}")
	if not stage03_dir.exists():
		raise FileNotFoundError(f"Missing stage directory: {stage03_dir}")
	if not stage04_dir.exists():
		raise FileNotFoundError(f"Missing stage directory: {stage04_dir}")

	r_exec = find_r_executable()
	failures: List[Path] = []

	execution_plan: List[Path] = [stage01_script, stage02_script]

	execution_plan.extend(collect_stage_scripts(stage03_dir))
	execution_plan.extend(collect_stage_scripts(stage04_dir))

	stage05_scripts: List[Path] = []
	if stage05_dir.exists():
		stage05_scripts = collect_stage_scripts(stage05_dir)

	if not stage05_scripts and stage05_fallback_dir.exists():
		print("[INFO] No runnable files in scripts/05_plotting; falling back to scripts/plotting")
		stage05_scripts = collect_stage_scripts(stage05_fallback_dir)

	execution_plan.extend(stage05_scripts)

	print("[INFO] Sequential pipeline run starting")
	print(f"[INFO] Repository root: {repo_root}")
	print(f"[INFO] Scripts to run: {len(execution_plan)}")

	for idx, script in enumerate(execution_plan, start=1):
		print(f"[INFO] ({idx}/{len(execution_plan)})")
		code = run_script(script, r_exec=r_exec, dry_run=args.dry_run)
		if code != 0:
			print(f"[ERROR] Script failed with exit code {code}: {script}")
			failures.append(script)
			if not args.continue_on_error:
				break

	if failures:
		print("\n[SUMMARY] Pipeline completed with failures:")
		for failed in failures:
			print(f"  - {failed}")
		return 1

	print("\n[SUMMARY] Pipeline completed successfully.")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())

