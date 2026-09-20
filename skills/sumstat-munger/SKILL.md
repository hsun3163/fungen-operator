---
name: sumstat-munger
description: Prepare, run, debug, or validate COSI/LOAD sumstat munger jobs that convert raw GWAS/eQTL/TensorQTL summary statistics into CPRA_b38 TSV/VCF outputs under Myloid-paper/1_DataPrep/Snakemake_38. Use when Codex needs to add a SUMSTATS config entry, run the Snakemake_38 munger through Snakemake/LSF, produce or link `.chrall.CPRA_b38.vcf.gz` files, audit `.tbi` indexes, or explain munger row-drop/allele behavior.
---

# Sumstat Munger

## Core Rule

Use the live Snakemake munger, not ad hoc scatter scripts. The source of truth is:

`/sc/arion/projects/load/users/sunh14/myloid_paper/Myloid-paper/1_DataPrep/Snakemake_38/Snakefile`

Read the current `Snakefile` and config before changing or running anything. If this is part of Route3/MESA work, keep `xqtl-protocol` read-only unless the user explicitly says otherwise.

For detailed local paths and config examples, read `references/cosi-snakemake38.md`.

## Workflow

1. Identify the input form.
   - Raw table input should be TSV-like, optionally gzipped.
   - Confirm genome build, chromosome field, position field, effect allele, other allele, effect size field, P value, sample size, and trait/gene field.
   - Use bounded probes such as `zcat --force <file> | sed -n '1,5p'`; avoid full scans unless needed.

2. Add or isolate a config entry.
   - Prefer a run-specific config copied from an existing working config.
   - Add one `SUMSTATS:<name>` entry with `FILE`, `URL: NA`, `N` or `N_CASES`/`N_CTRLS`, optional `TRAIT`, optional `GAF`, and a `COLUMNS` map.
   - Required semantic columns are `CHROM`, `POS`, `EA`, `OA`, `P`, and either `TRAIT` or config-level `TRAIT`.
   - The munger can derive missing effect fields in several cases, but do not rely on inference silently. State which fields are input versus derived.

3. Dry-run the narrow target first.
   - Target the exact desired outputs for the sumstat name:

```bash
cd /sc/arion/projects/load/users/sunh14/myloid_paper/Myloid-paper/1_DataPrep/Snakemake_38
snakemake -s Snakefile --configfile <config.yaml> -n \
  output/<name>.chrall.CPRA_b38.vcf.gz \
  output/<name>.chrall.CPRA_b38.vcf.gz.tbi \
  output/<name>.chrall.CPRA_b38.tsv.gz
```

4. Submit through Snakemake/LSF for real runs.
   - Activate the `sumstat_munger` conda environment before launching Snakemake. The LSF profile submits the environment Snakemake was launched from; it does not activate `sumstat_munger` inside each job.
   - If you write an LSF controller/wrapper script that runs `conda activate`, do not use `set -u`/`nounset` around the activation. Use `set -eo pipefail` or disable nounset before activation. Existing conda deactivate hooks such as `deactivate-ipdb.sh` can reference unset variables like `CONDA_PYTHONBREAKPOINT_BACKUP` and make the controller exit before Snakemake starts.
   - Use the local LSF Snakemake profile when available. Do not launch high-memory full munger work in the foreground session.
   - A typical shape is:

```bash
source /sc/arion/work/sunh14/conda/mambaforge/etc/profile.d/conda.sh
conda activate /sc/arion/work/sunh14/conda/envs/sumstat_munger
cd /sc/arion/projects/load/users/sunh14/myloid_paper/Myloid-paper/1_DataPrep/Snakemake_38
snakemake -s Snakefile --configfile <config.yaml> --profile lsf --jobs 300 --latency-wait 120 \
  output/<name>.chrall.CPRA_b38.vcf.gz \
  output/<name>.chrall.CPRA_b38.vcf.gz.tbi \
  output/<name>.chrall.CPRA_b38.tsv.gz
```

5. Validate completion from Snakemake evidence.
   - Check `.snakemake/log/<timestamp>.snakemake.log` for `Complete log:` and `100% done`.
   - Verify all 22 per-chromosome VCFs plus `chrall` and their `.tbi` indexes exist.
   - Probe the VCF through its index:

```bash
tabix output/<name>.chrall.CPRA_b38.vcf.gz 1 | sed -n '1,3p'
```

   - If `bcftools` is available, inspect the header:

```bash
bcftools view -h output/<name>.chrall.CPRA_b38.vcf.gz | sed -n '1,40p'
```

6. Place final products only when asked.
   - Production consumers often look under `output/final_output/`.
   - Prefer symlinks to completed munger outputs unless the user asks for physical copies.
   - Link both `.vcf.gz` and `.vcf.gz.tbi`, preserving basenames.

## Munger Behavior To Remember

- Outputs are named `output/<name>.chr{1..22}.CPRA_b38.vcf.gz`, `output/<name>.chrall.CPRA_b38.vcf.gz`, and matching `.tbi` files. TSV outputs use the same stem with `.tsv.gz`.
- The main DAG splits input by chromosome, processes per-chromosome TSVs, converts to VCF, matches ALT to effect allele, annotates 1000G/dbSNP/gnomAD when configured, and concatenates `chrall`.
- If `Z` is missing and `BETA` plus `SE` are present, the munger computes `Z = BETA / SE`.
- Rows with missing `CHROM`, `POS`, `EA`, `OA`, `TRAIT`, or `Z` are dropped. A `BETA=0` and `SE=0` row becomes `0/0 -> NA` and is removed.
- `P=0` is replaced with the smallest positive usable floating-point value.
- If input lacks `EAF`, provide `GAF` so the workflow can annotate allele frequency from gnomAD. Without either, the munger fails.
- Chromosomes are constrained to integer autosomes `1..22`; `chr` prefixes are stripped, but non-autosomal contigs are not part of the standard target set.
- `vt` is required by the Snakefile. If jobs fail with `vt: command not found`, verify Snakemake was launched from `/sc/arion/work/sunh14/conda/envs/sumstat_munger`, not `py3.11`.

## Reporting

Be explicit about what is verified versus inferred. For large genomic artifacts, prefer bounded smoke checks: existence, index readability, header shape, first indexed records, and Snakemake completion markers. Do not claim record-identical equivalence unless you actually ran a full comparison.
