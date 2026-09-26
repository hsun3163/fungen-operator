# MWS-01 revision 2 — operator result (oss_500_20260925_01)

**Status: complete.** Canonical `phenotype_by_chrom` target produced both declared manifests
plus the indexed chr22 BED; conclusion readiness reports `nothing_to_do`; notebook verification passed.

## Trail (one notebook, in order)

| # | Action | Cell | Status | Native job |
|---|---|---|---|---|
| 1 | `prepare_config` | `dfaf605e6fe94bf9a2000d9042aed0b7` | `materialized` | — (config write) |
| 2 | `check_readiness` `phase=before_run` | `ddcf6b42b09b48bd9b0b20ea9a89459a` | `ready` | `270472274` RUN→DONE |
| 3 | `initiate_run` | `68a97b9e4dc5400f8d91cfd993cdb897` | `submitted` | `270472474` PEND→DONE |
| 4 | `check_readiness` `phase=conclusion` | `680b432a0c1143c982932cb0a8332059` | `nothing_to_do` | `270472540` RUN→DONE |

Superseded history cell `056f50ffc401471c9be90357925931bd` (`prepare_config`) was staged but never
executed: the first `prepare_config` call returned an unsupported-call error yet still staged a cell,
and the retried call superseded it. No duplicate workflow work ran.

## Submission contract actually used

Rendered `#BSUB` lines in every executed cell: `-J fungen_mws01 -P acc_LOAD -q express`,
readiness `-W 00:10`, production `-W 01:00`, `-n 1`, `-M 32GB`, `-R "span[hosts=1] rusage[mem=32GB]"`,
`-oo/-eo` under `logs/<cell_id>.%J.{out,err}`. Workflow ran `--cores 72 --jobs 100 --latency-wait 120`.
Inner SoS rule job: `270472483` (queue `premium`, DONE).

- Readiness evidence: `Nothing to be done` absent at before_run, DAG showed `phenotype_by_chrom count 1`;
  conclusion log shows `Nothing to be done (all requested files are present and up to date).`
- Native completion event, not invented polling: `bwait -w 'done(270472474)'` →
  `done(270472474): Wait condition satisfied` (`logs/bwait_270472474.log`).

## Products (declared outcome met)

`work/data_preprocessing/SYN/phenotype_data/`:

- `phenotypes.phenotype_by_chrom_files.txt` — 1 data row (`22` → chr22 BED)
- `phenotypes.phenotype_by_chrom_files.region_list.txt` — 16 data rows
- `phenotypes.chr22.bed.gz` — header declares **500** sample columns; **16** phenotype rows; all variants `chr22`
- `phenotypes.chr22.bed.gz.tbi` — tabix index reads; `tabix -l` → `chr22`; indexed query
  `chr22:29673217-29673218` returns the 2 expected trait rows
- Preservation: the produced BED is byte-for-byte identical to
  `zcat traits/phenotypes.bed.gz | (header + rows where chrom == chr22)` — `PASS_ROWS_VALUES_AND_ORDER_IDENTICAL`,
  `PASS_SAMPLE_COLUMN_ORDER_IDENTICAL`; 16 input chr22 rows → 16 produced rows, 500 samples

Verification jobs (native LSF, `-P acc_LOAD -q express -n 1 -W 00:10 -M 32GB -R 'span[hosts=1] rusage[mem=32GB]'`):

- `270472546` → `All active cells re-render identically.` (exit 0)
- `270472626` → index/column checks; short-exited 141 from `zcat | head` under `pipefail` (SIGPIPE), rerun below
- `270472703` → 16 phenotype rows, 500 sample columns, 16 region rows, 1 manifest row, chr22 only (exit 0)
- `270472995` → `PASS_ROWS_VALUES_AND_ORDER_IDENTICAL` / `PASS_SAMPLE_COLUMN_ORDER_IDENTICAL`: the produced BED is
  byte-for-byte identical to the chr22 rows of the supplied input. An earlier attempt `270472990` `EXIT`ed with
  exit 2 from my own quoting error in the inline `bsub -lc` form; resubmitted as a heredoc job, no scientific change
- `270472995` → byte-for-byte chr22-subset equality, exit 0. An earlier attempt `270472990` `EXIT`ed with
  exit 2 from my own quoting error in the `bsub -lc` form; resubmitted as a heredoc job, no scientific change

Compute-node verification used `/sc/arion/work/sunh14/conda/envs/xqtl-r-base-fsusie/bin/python` with
`PYTHONPATH=/sc/arion/projects/load/users/sunh14/fungen-operator/src`, CLI `python -m fungen_operator verify <notebook>`.

## Protected contracts

- Inputs unchanged; `sha256sum` matches `task.yaml input_sha256` for `genotype.bed/.bim/.fam`,
  `traits/phenotypes.bed.gz(.tbi)`, `traits/covariates.cov.gz`.
- Recorded source identity (all four cells, identical): commit `f0912cfab346694fbaf21f81c293711d3de948cc`,
  `dirty: true`, hashes match the four `source_constructs` in `task.yaml`
  (`Snakefile 657aea8a…`, `04_phenotype_covariate_prep.smk f54dea12…`,
  `pipeline/phenotype_formatting.ipynb 2b92dc44…`, `phenotype_formatting.R b7d8055c…`).
- Canonical default config `2fefb9cf…` equals `task.yaml source_config_sha256`; the supplied trial
  `config.yaml` was **adopted as baseline unchanged**. Non-default scientific fields in that supplied file
  (`chromosomes=[chr22]`, `start_from=phenotype_bed`, `themes[name=SYN,…]`, empty `reference.*`,
  empty `genotype.vcf_files`) came from the author-supplied config, not from this operator.

## Model and interventions

- Driver recorded selection: `codex exec --oss --ephemeral`, "existing codex wrapper default, no explicit
  model override"; `runtime_before` model `qwen3.8-flash-next:125b-a6b-q4_K_M`
  (family `qwen4exp`, 176.9B, Q4_K_M, 262144 context). No runtime change was attempted here.
- Pre-existing parent interventions in `driver.json`: authentication-symlink proposal rejected by
  automatic review (nothing copied or linked), and a duplicate project config key corrected before any
  model turn (`worker.startup01.stderr.log`).
- No approval-path failure in this trial: every LSF/SoS/Snakemake invocation, including all host
  `fungen_operator execute` calls and read-only `bjobs`, requested `require_escalated` on its first
  attempt and was accepted. No persistent shell/interpreter/script rule was added.
