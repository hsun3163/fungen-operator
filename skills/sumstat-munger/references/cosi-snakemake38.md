# COSI Snakemake_38 Sumstat Munger Reference

## Canonical Paths

- Munger root:
  `/sc/arion/projects/load/users/sunh14/myloid_paper/Myloid-paper/1_DataPrep/Snakemake_38`
- Snakefile:
  `/sc/arion/projects/load/users/sunh14/myloid_paper/Myloid-paper/1_DataPrep/Snakemake_38/Snakefile`
- Common configs:
  `config_main_working_hg38.yaml`, `config_main_working_eQTL_gen.yaml`, `config_AD_GWAS_hg38.yaml`, `config_ADAD_working_hg38.yaml`
- Main output directory:
  `output/`
- Production-style final directory:
  `output/final_output/`
- Snakemake logs:
  `.snakemake/log/*.snakemake.log`
- Required conda env:
  `/sc/arion/work/sunh14/conda/envs/sumstat_munger`
- Known required executable:
  `/sc/arion/work/sunh14/conda/envs/sumstat_munger/bin/vt`

## Config Entry Shape

Use an existing config as the base. A minimal raw-table entry looks like:

```yaml
SUMSTATS:
  my_sumstat_name:
    FILE: /absolute/path/to/input.tsv.gz
    URL: NA
    N: 12345
    TRAIT: AD
    COLUMNS:
      CHROM: chromosome
      POS: base_pair_location
      ID: variant_id
      EA: effect_allele
      OA: other_allele
      EAF: effect_allele_frequency
      BETA: beta
      SE: se
      P: p_value
```

For gene/eQTL-style inputs, map `TRAIT` to the gene/feature column instead of using a fixed trait:

```yaml
SUMSTATS:
  my_eqtl_name:
    FILE: /absolute/path/to/nominal_eqtl.tsv.gz
    URL: NA
    N: 193
    GAF: AF_nfe
    COLUMNS:
      CHROM: chr
      POS: pos
      ID: variant_id
      EA: effect_allele
      OA: other_allele
      BETA: beta
      SE: se
      P: pval_nominal
      TRAIT: phenotype_id
```

Optional keys seen in working configs include `SEP`, `NA_VALUES`, `NOTE`, `IS_LOGISTIC`, `N_CASES`, `N_CTRLS`, `GAF`, `STAR_ALLELE`, and `NALT_ALLELE`.

## Output Contract

For `SUMSTATS` key `<name>`, successful munger outputs include:

```text
output/<name>.chr1.CPRA_b38.vcf.gz
...
output/<name>.chr22.CPRA_b38.vcf.gz
output/<name>.chrall.CPRA_b38.vcf.gz
output/<name>.chrall.CPRA_b38.vcf.gz.tbi
output/<name>.chrall.CPRA_b38.tsv.gz
output/<name>.chrall.CPRA_b38.tsv.gz.tbi
```

The VCF `ASS` INFO field stores association data in this order:

`ALT|TRAIT|BETA|SE|Z|P|N|N_CASES|N_CTRLS|OR|OR_L95|OR_U95|DIR|P_HET`

## Evidence Patterns

Useful Snakemake log lines:

```text
Provided cluster nodes: 300
rule split_sumstats_tsv_by_chr:
Submitted job ... queue <premium>.
rule concat_sumstats_chr_vcfs:
bcftools concat --threads 4 -Oz -o output/<name>.chrall.CPRA_b38.vcf.gz ...
Finished job ...
555 of 555 steps (100%) done
Complete log: .snakemake/log/<timestamp>.snakemake.log
```

Useful validation commands:

```bash
find output -maxdepth 1 -name '<name>.chr*.CPRA_b38.vcf.gz' -printf '%f\n' | sort -V
find output -maxdepth 1 -name '<name>.chr*.CPRA_b38.vcf.gz.tbi' -printf '%f\n' | sort -V
tabix output/<name>.chrall.CPRA_b38.vcf.gz 1 | sed -n '1,3p'
zcat output/<name>.chrall.CPRA_b38.tsv.gz | sed -n '1,12p'
```

Use `tabix <vcf.gz> 1`, not bare `tabix <vcf.gz>`, when streaming indexed records; bare `tabix` can interpret the call as an indexing operation.

## Known Trap

The current Snakefile computes `Z = BETA / SE` when `Z` is absent, then drops rows with missing `Z`. Rows such as `BETA=0` and `SE=0` become `0/0 -> NA` and are removed. This is expected behavior for the current munger; report it explicitly when row counts differ.

The `--profile lsf` jobs inherit the environment from the parent Snakemake process. The profile jobscript is just `{exec_job}`; it does not activate conda. Launching from `py3.11` can produce `vt: command not found` even though `vt` exists in `sumstat_munger`.
