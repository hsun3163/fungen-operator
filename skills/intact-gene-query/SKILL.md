---
name: intact-gene-query
description: Build and query a cached INTACT noQC gene dataframe for the COSI project. Use when asked for gene-level results from `hg38/*/results/*/*.ADSP.*/intact/*.ADSP.*.ADSP.*.intact.results.tsv` and when freshness must be verified before returning results.
---

# Intact Gene Query

Run the workflow script to keep INTACT query results current and return gene hits from one saved query dataframe.

## Workflow

1. Accept a user gene name and choose match mode.
2. Run `bash skills/intact-gene-query/scripts/run_intact_gene_query.sh <GENE> [exact|contains]`.
3. Let the script check whether `query_df` needs refresh.
4. Let the script rebuild `query_df` when stale.
5. Let the script query the saved dataframe and write a gene result TSV to `analysis/gene_query/<GENE>/`.
6. Let the script auto-generate a notebook in the same gene folder that:
   1. Loads `tidyverse` and `data.table`.
   2. Reads the local TSV filename (same folder).
   3. Filters rows with `intact_pp > 0.8`.
   4. Draws a plot with `x = z_score`, `y = AD + eQTL`, dot size `= intact_pp`, and red points for `intact_pp >= 0.8`.
7. Report row counts, distinct files, and key top hits back to the user.

## Freshness Checks

The workflow script rebuilds `query_df` if any check fails.

1. `analysis/intact_query_df.rds` or `analysis/intact_query_df_file_summary.tsv` is missing.
2. Source file count changed from summary.
3. Source file set changed from summary.
4. Any source file is newer than `analysis/intact_query_df.rds`.

## Commands

```bash
bash skills/intact-gene-query/scripts/run_intact_gene_query.sh EED exact
```

```bash
bash skills/intact-gene-query/scripts/run_intact_gene_query.sh BIN1 contains
```

## Outputs

The workflow writes or updates:

1. `analysis/intact_query_df.rds`
2. `analysis/intact_query_df.tsv.gz`
3. `analysis/intact_query_df_file_summary.tsv`
4. `analysis/gene_query/<GENE>/intact_query_gene_<GENE>_<exact|contains>.tsv`
5. `analysis/gene_query/<GENE>/intact_query_gene_<GENE>_<exact|contains>.ipynb`
## Scripts

1. `skills/intact-gene-query/scripts/run_intact_gene_query.sh`
2. `analysis/build_intact_query_df.R`
3. `analysis/query_intact_gene.R`
4. `skills/intact-gene-query/scripts/generate_gene_query_notebook.py`

## Reporting Format

For each user query, report:

1. Whether refresh was needed and why.
2. Total matched rows.
3. Distinct contributing source files.
4. Top rows with `gwas_name`, `eqtl_name`, `gene_name`, and `intact_pp`.
