# Taxa name resolution (Python CLI)

Resolves names in `fungal_taxon` and `plant_host` (from `data/Ollama_cleaned.csv`) to
accepted taxa against a Darwin Core taxonomy.

## Taxonomy source

Two upstreams are supported (`--taxonomy-source`, default `auto` = detect from the
Taxon.tsv header):

| value | what |
|---|---|
| `col_dwca` | **Catalogue of Life Extended Release** (COL26.x XR) DwC-A, from ChecklistBank. GBIF's current default taxonomy; ~62k integrated sources. Canonical names are rebuilt from `genericName`/`specificEpithet`; richer `taxonomicStatus` vocab handled (homotypic/heterotypic/ambiguous synonym, misapplied, provisionally accepted). |
| `gbif_backbone` | legacy **GBIF Backbone Taxonomy** (final build, 2023; DOI 10.15468/39omei). Has a `canonicalName` column. |

**Getting COL XR** (do this once, on the machine that runs resolution):
1. Sign in to <https://www.checklistbank.org> with your GBIF account.
2. Datasets → **COL Releases** → pick the latest **Extended Release** (e.g. COL26.7 XR).
   Note the exact version — cite it in the Methods.
3. Download a **partial DwC-A** for `Fungi` and (separately) `Plantae`, or the whole XR
   DwC-A. Unzip so `Taxon.tsv` exists, e.g. `data/Reference_datasets/col_xr/Taxon.tsv`.
   (If you download Fungi and Plantae separately, concatenate the two `Taxon.tsv` files,
   keeping one header.)

## Inputs / outputs

- in: `data/Ollama_cleaned.csv`, the Taxon.tsv above
- out: `data/Ollama_cleaned_synresolved.csv`,
  `results/manual_validation/taxa_unresolved_review.csv`,
  `results/logs/taxa_synonym_resolution_checkpoint.json`

## What the script does

- One output row per input row; adds `paper_id`, `interaction_id`.
- Splits multi-name cells; resolves each token in order:
  1. exact accepted match
  2. synonym → accepted
  3. abbreviation expansion (`A. niger`), paper-context genera first
  4. genus-level fallback (retain at genus rank if the binomial can't be placed)
- Missing phylum/class/order/family are backfilled from the accepted parent chain.
- Unresolved / ambiguous tokens → the review CSV. Checkpointed and resumable.

## Local run

```bash
python scripts/02_taxa_resolution/taxa_synonym_resolution.py \
  --input-csv data/Ollama_cleaned.csv \
  --taxon-tsv data/Reference_datasets/col_xr/Taxon.tsv \
  --output-csv data/Ollama_cleaned_synresolved.csv \
  --unresolved-csv results/manual_validation/taxa_unresolved_review.csv \
  --checkpoint-json results/logs/taxa_synonym_resolution_checkpoint.json \
  --checkpoint-interval 1000 --log-interval 1000 --resume
```

Smoke test: add `--max-rows 200`.

## Monsoon (SLURM)

```bash
sbatch scripts/02_taxa_resolution/slurm/run_taxa_synonym_resolution.sbatch
# override the taxonomy:
sbatch --export=TAXON_TSV=/path/gbif_backbone/Taxon.tsv,TAXONOMY_SOURCE=gbif_backbone \
       scripts/02_taxa_resolution/slurm/run_taxa_synonym_resolution.sbatch
```
