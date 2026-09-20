#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SUMMARY_MD="$BASE_DIR/SUMMARY.md"

cat > "$SUMMARY_MD" <<'EOF'
# INTACT Gene Query Handoff (Auto-Generated)

This summary is generated from the current repo state and skill scripts.

## Context Summary (Current Understanding)

- Built a reproducible INTACT gene-query workflow with caching, per-gene outputs, and auto-generated R notebooks.
- Added an exact/contains query pipeline and defaulted to exact unless explicitly requested.
- Implemented Ensembl-to-gene symbol backfill using `hg38/cardiogenics_region_list_by_trait.with_gtf.tsv` to fix missing `gene_name` (especially CARDIOGENICS_MC).
- Updated source INTACT TSVs in place to fill `gene_name` for CARDIOGENICS_MC pairs.
- Added a notebook plot: `z_score` on x, `AD + eQTL` on y, dot size = `intact_pp`, red highlight for `intact_pp >= 0.8`.

## Primary Workflow

Run this for any gene (defaults to exact match):

```bash
bash skills/intact-gene-query/scripts/run_intact_gene_query.sh <GENE> [exact|contains]
```

Outputs land in `analysis/gene_query/<GENE>/`:
- `analysis/gene_query/<GENE>/intact_query_gene_<GENE>_<exact|contains>.tsv`
- `analysis/gene_query/<GENE>/intact_query_gene_<GENE>_<exact|contains>.ipynb`

The notebook:
1. Loads `tidyverse` and `data.table`.
2. Reads the local TSV filename (same folder).
3. Filters rows with `intact_pp > 0.8`.
4. Plots `z_score` vs `AD + eQTL` with dot size = `intact_pp` and red highlight for `intact_pp >= 0.8`.

## Cache and Dataframe Build

Cache rebuild happens automatically when stale.

Core files:
- `analysis/build_intact_query_df.R`
- `analysis/intact_query_df.rds`
- `analysis/intact_query_df.tsv.gz`
- `analysis/intact_query_df_file_summary.tsv`

## Gene Query Logic

Exact gene queries backfill missing `gene_name` from Ensembl IDs using:
- `hg38/cardiogenics_region_list_by_trait.with_gtf.tsv`

Implementation:
- `analysis/query_intact_gene.R`

Source INTACT TSVs are updated in place to fill `gene_name` for CARDIOGENICS_MC rows.

## Notebook Generator

Notebook creation is handled by:
- `skills/intact-gene-query/scripts/generate_gene_query_notebook.py`

It uses the Jupyter helper:
- `~/.codex/skills/jupyter-notebook/scripts/new_notebook.py`

## Skill Files

Skill doc:
- `skills/intact-gene-query/SKILL.md`

Runner:
- `skills/intact-gene-query/scripts/run_intact_gene_query.sh`

Handoff:
- `skills/intact-gene-query/scripts/handoff.sh`

## Example

```bash
bash skills/intact-gene-query/scripts/run_intact_gene_query.sh MEF2C exact
```
EOF

echo "Wrote SUMMARY.md"
