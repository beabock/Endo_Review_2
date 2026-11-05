#!/usr/bin/env python3
# BMB 2026-11-05 (Thread B). Serving-throughput benchmark for the v6 bake-off: how many
# schema-constrained extraction calls per second does a given ENGINE + MODEL sustain, at several
# client concurrency levels and prompt lengths? Produces the measured numbers that replace the
# assumptions in the compute estimate (NPH_extraction_v6_design.md, section 9).
#
# It needs no PDFs: prompts are built from DEV-set abstracts (short = 1 abstract ~ 0.4k tokens,
# medium = 8 abstracts ~ 3k tokens, long = 30 abstracts ~ 11k tokens) wrapped in the real
# stage-2 prompt + schema. Every prompt is DISTINCT (different abstracts), so vLLM prefix caching
# cannot flatter the result; a second 'shared-prefix' series shows what caching adds.
#
# GPU job: run it through run_v6_poc.sbatch (STEP=bench), not on a login node, and only after
# Bea OKs the GPU request.
#
# Output: <out-dir>/bench.json and bench.md (one row per prompt-length x concurrency).

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import statistics
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_v6_poc as X          # noqa: E402


def build_prompts(abstracts: list[str], n_abs: int, n_prompts: int, shared_prefix: bool) -> list[str]:
    out = []
    pre = X.STAGE2_PROMPT + "\nSTUDY HOSTS (from the methods): not stated\n"
    for i in range(n_prompts):
        idx = [(i * n_abs + j) % len(abstracts) for j in range(n_abs)]
        body = "\n\n".join(abstracts[k] for k in idx)
        out.append(f'{pre}\nTEXT SEGMENT:\n"""\n{body}\n"""\n')
    if shared_prefix:                       # same long document, different trailing question
        doc = "\n\n".join(abstracts[: max(n_abs, 8)])
        out = [f'{pre}\nTEXT SEGMENT:\n"""\n{doc}\n"""\nNote {i}: list the pairs.\n' for i in range(n_prompts)]
    return out


def run_level(llm: X.LLM, prompts: list[str], conc: int) -> dict:
    schema = X.stage2_schema()
    t0 = time.time()
    metas = []
    with cf.ThreadPoolExecutor(max_workers=conc) as ex:
        for obj, meta in ex.map(lambda p: llm.call("bench", "bench", p, schema), prompts):
            metas.append(meta)
    wall = time.time() - t0
    ok = [m for m in metas if m["status"].startswith("ok")]
    lat = sorted(m["seconds"] for m in metas)
    pt = sum((m.get("prompt_tokens") or 0) for m in metas)
    ct = sum((m.get("completion_tokens") or 0) for m in metas)
    return {"concurrency": conc, "n": len(prompts), "wall_s": round(wall, 1),
            "req_per_s": round(len(prompts) / wall, 3),
            "prompt_tok_per_s": round(pt / wall, 1), "completion_tok_per_s": round(ct / wall, 1),
            "mean_prompt_tokens": round(pt / len(prompts)), "mean_completion_tokens": round(ct / len(prompts)),
            "p50_s": round(statistics.median(lat), 2), "p95_s": round(lat[int(0.95 * (len(lat) - 1))], 2),
            "malformed": sum(m["status"] == "malformed" for m in metas),
            "timeouts": sum(m["status"] == "timeout" for m in metas),
            "errors": sum(m["status"].startswith("error") for m in metas),
            "truncated": sum(m.get("finish") == "length" for m in metas), "ok": len(ok)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, required=True, help="dev_set_selected.csv (needs an abstract column)")
    ap.add_argument("--backend", choices=["openai", "ollama", "mock"], required=True)
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--model", required=True)
    ap.add_argument("--concurrency", default="1,4,8,16,32", help="comma list")
    ap.add_argument("--lengths", default="short:1,medium:8,long:30", help="name:n_abstracts, comma list")
    ap.add_argument("--n-prompts", type=int, default=24, help="prompts per (length, concurrency) cell")
    ap.add_argument("--num-ctx", type=int, default=16384)
    ap.add_argument("--max-tokens", type=int, default=512)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--warmup", type=int, default=2)
    ap.add_argument("--out-dir", type=Path, required=True)
    a = ap.parse_args()
    base = a.base_url or ("http://127.0.0.1:11434" if a.backend == "ollama" else "http://127.0.0.1:8000/v1")
    a.out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(a.input, low_memory=False)
    abstracts = [str(x) for x in df["abstract"].dropna() if len(str(x)) > 300]
    llm = X.LLM(a.backend, base, a.model, 20261105, a.num_ctx, a.timeout, a.max_tokens)
    llm.call("warmup", "w", build_prompts(abstracts, 1, 1, False)[0], X.stage2_schema(), X._mock_stage2)
    results = []
    for spec in a.lengths.split(","):
        name, n_abs = spec.split(":")
        for shared in (False, True) if name == "long" else (False,):
            prompts = build_prompts(abstracts, int(n_abs), a.n_prompts, shared)
            for _ in range(a.warmup):                          # JIT / cache warm
                llm.call("warmup", "w", prompts[0], X.stage2_schema(), X._mock_stage2)
            for c in [int(x) for x in a.concurrency.split(",")]:
                r = run_level(llm, prompts, c)
                r.update(length=name + ("+shared_prefix" if shared else ""), model=a.model, backend=a.backend)
                results.append(r)
                print(json.dumps(r))
    (a.out_dir / "bench.json").write_text(json.dumps(
        {"args": {k: str(v) for k, v in vars(a).items()}, "server": X.server_info(llm), "results": results}, indent=2))
    cols = ["length", "concurrency", "n", "mean_prompt_tokens", "mean_completion_tokens", "req_per_s",
            "prompt_tok_per_s", "completion_tok_per_s", "p50_s", "p95_s", "malformed", "timeouts", "errors", "truncated"]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    lines += ["| " + " | ".join(str(r[c]) for c in cols) + " |" for r in results]
    (a.out_dir / "bench.md").write_text(f"# bench: {a.backend} / {a.model}\n\n" + "\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
