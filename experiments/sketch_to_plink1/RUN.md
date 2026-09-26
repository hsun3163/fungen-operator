# Reproduction path

Status: scientific optimization completed and closed on 2026-09-23. See the [archived negative result and benchmark decision](../../archive/sketch_to_plink1_20260923/README.md). The historical tuning commands below document the completed pilot.

## Fixed-bin behavioral fixture

Use theta = 1 as a fixed choice in the existing frequency-aware rank bins. The output has 10,000 synthetic rows and 20,000 variants from the original 20 prepared regions. BIM A1 counts ALT. Its role is an opaque genotype object for behavioral tests; scientific integration fixtures use separately generated synthetic or public genotypes.

From the repository root, the exact export/format-verification command is:

```bash
bsub -K -P acc_LOAD -J sketch-fixed-bin-export -n 1 -W 30 -M 4096 -R 'rusage[mem=4096]' -oo output/sketch_to_plink1/logs/fixed_bin_export.%J.out -eo output/sketch_to_plink1/logs/fixed_bin_export.%J.err /usr/bin/env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /sc/arion/work/sunh14/conda/envs/py3.11/bin/python experiments/sketch_to_plink1/sketch_mwe.py export --theta 1 --export-prefix output/sketch_to_plink1/behavioral_fixture/genotype --verify-export
```

Completed and verified job: `270113524` (90 seconds, peak memory 178 MB). The exporter wrote `.bed/.bim/.fam`, an allele map, and `export.json` with file hashes. PLINK 1.9 rewrote the complete BED byte-identically with preserved allele order; 32 recoded variants matched the generated calls across all 10,000 rows. `roundtrip_verified.json` records the passing checks. The 50,000,003-byte BED has SHA256 `cd48b88a48021b52e3ff4353557a3bcb1eb448c5eb1e3263bb230696b47cd235`. The fitted pilot remains at its original prefix and its BED hash was rechecked unchanged. Final review confirmed the fixed parameter, synthetic identifiers, genotype type metadata, retained negative-result evidence, and completed format verification.

## Synthetic covariates and phenotypes

The fixed-bin fixture is extended with 12 correlated covariates and 40 quantitative phenotypes (20 genetic signals and 20 null controls). See [TRAITS.md](TRAITS.md) for the equations, formats, and verification contract. The deterministic seed is `20260924`.

```bash
bsub -K -P acc_LOAD -J sketch-fixture-traits -n 1 -W 30 -M 4096 -R 'rusage[mem=4096]' -oo output/sketch_to_plink1/logs/fixture_traits.%J.out -eo output/sketch_to_plink1/logs/fixture_traits.%J.err /usr/bin/env LD_LIBRARY_PATH=/sc/arion/work/sunh14/conda/envs/py3.11/lib OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /sc/arion/work/sunh14/conda/envs/py3.11/bin/python experiments/sketch_to_plink1/simulate_traits.py
```

Completed and verified job: `270117742` (LSF elapsed 49 seconds; sampled peak memory 560 MB; Python peak RSS 646 MB). Products are in `output/sketch_to_plink1/behavioral_fixture/traits/`; `qc_summary.json` confirms 12 covariates, 40 phenotypes, exact alignment of 10,000 samples, zero missing values, full design rank 13, recovery of all 30 causal effects with correct direction and P < 5E-8, and 1,200 successful native PLINK association checks. Of the 20 null traits, one crosses its regional Bonferroni threshold; the realized result is retained. Final review checked all output hashes, the generator hash, unchanged genotype input hashes, sample-order identity in every exported table, and BED coordinates/indexing.

Initial job `270116349` stopped at SciPy import because the system C++ library lacked `GLIBCXX_3.4.30`. The command above selects the pinned conda libraries explicitly; its import/help preflight passed. Job `270117019` then exposed a chr21 region with maximum SNP MAF 0.0908, so causal eligibility was set uniformly to MAF >= 0.05 before outcome evaluation. The genotype-PC panel retains MAF >= 0.10.

## Historical scientific experiment

The experiment code is under this directory. Ignored run products, caches, manifests, results, logs, and pilot data are under `output/sketch_to_plink1/`. Run commands from the repository root with `/sc/arion/work/sunh14/conda/envs/py3.11/bin/python`; sketch reads use `/sc/arion/work/sunh14/conda/envs/py3.11/bin/Rscript` and the installed `pecotmr` 0.3.4 / `pgenlibr` 0.3.2 helpers. LSF submissions use project `acc_LOAD`, one core, 4 GB, and one BLAS thread.

Preparation and the main single-theta run:

```bash
python experiments/sketch_to_plink1/sketch_mwe.py prepare
python experiments/sketch_to_plink1/sketch_mwe.py jobs
mkdir -p output/sketch_to_plink1/logs
bsub -P acc_LOAD -n 1 -W 60 -M 4096 -R 'rusage[mem=4096]' -oo output/sketch_to_plink1/logs/preflight.%J.out -eo output/sketch_to_plink1/logs/preflight.%J.err /usr/bin/env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /sc/arion/work/sunh14/conda/envs/py3.11/bin/python experiments/sketch_to_plink1/sketch_mwe.py worker --index 1
bsub -P acc_LOAD -J 'sketch-dev[2-136]' -n 1 -W 60 -M 4096 -R 'rusage[mem=4096]' -oo output/sketch_to_plink1/logs/development.%J.%I.out -eo output/sketch_to_plink1/logs/development.%J.%I.err /usr/bin/env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /sc/arion/work/sunh14/conda/envs/py3.11/bin/python experiments/sketch_to_plink1/sketch_mwe.py worker
python experiments/sketch_to_plink1/sketch_mwe.py reduce
python - <<'PY'
import pandas as pd
p='output/sketch_to_plink1/prepared/jobs.tsv'
d=pd.read_csv(p,sep='\t')
d[d.phase=='development_refinement'].to_csv('output/sketch_to_plink1/prepared/refinement_jobs.tsv',sep='\t',index=False)
PY
bsub -P acc_LOAD -J 'sketch-refine[1-64]' -n 1 -W 60 -M 4096 -R 'rusage[mem=4096]' -oo output/sketch_to_plink1/logs/refinement.%J.%I.out -eo output/sketch_to_plink1/logs/refinement.%J.%I.err /usr/bin/env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /sc/arion/work/sunh14/conda/envs/py3.11/bin/python experiments/sketch_to_plink1/sketch_mwe.py worker --manifest /sc/arion/projects/load/users/sunh14/fungen-operator/output/sketch_to_plink1/prepared/refinement_jobs.tsv
python experiments/sketch_to_plink1/sketch_mwe.py reduce
bsub -P acc_LOAD -J 'sketch-valid[1-24]' -n 1 -W 60 -M 4096 -R 'rusage[mem=4096]' -oo output/sketch_to_plink1/logs/validation.%J.%I.out -eo output/sketch_to_plink1/logs/validation.%J.%I.err /usr/bin/env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /sc/arion/work/sunh14/conda/envs/py3.11/bin/python experiments/sketch_to_plink1/sketch_mwe.py worker --manifest /sc/arion/projects/load/users/sunh14/fungen-operator/output/sketch_to_plink1/prepared/validation_jobs.tsv
python experiments/sketch_to_plink1/sketch_mwe.py finalize
python experiments/sketch_to_plink1/sketch_mwe.py export
python experiments/sketch_to_plink1/supporting_audits.py method-audit
python experiments/sketch_to_plink1/supporting_audits.py postprocess
python experiments/sketch_to_plink1/tie_audit.py
```

`reduce` runs once after the coarse grid and appends the refinement manifest when warranted. Run it again after the refinement array; it freezes the selected parameters and only then creates the held-out manifest. Job ids from this run: pilot 270018535, coarse array 270019219, refinement array 270020605, validation array 270022434. Their native logs remain under `output/sketch_to_plink1/logs/`.

The separate MAF-triggered follow-up is `two_stratum_v1`:

```bash
python experiments/sketch_to_plink1/two_stratum_followup.py prepare-reserved
python experiments/sketch_to_plink1/two_stratum_followup.py dev-jobs
mkdir -p output/sketch_to_plink1/two_stratum_v1/logs
bsub -P acc_LOAD -J 'two-theta-dev[2-72]' -n 1 -W 60 -M 4096 -R 'rusage[mem=4096]' -oo output/sketch_to_plink1/two_stratum_v1/logs/development.%J.%I.out -eo output/sketch_to_plink1/two_stratum_v1/logs/development.%J.%I.err /usr/bin/env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /sc/arion/work/sunh14/conda/envs/py3.11/bin/python experiments/sketch_to_plink1/two_stratum_followup.py worker
python experiments/sketch_to_plink1/two_stratum_followup.py reduce-dev
bsub -P acc_LOAD -J 'two-theta-valid[1-12]' -n 1 -W 60 -M 4096 -R 'rusage[mem=4096]' -oo output/sketch_to_plink1/two_stratum_v1/logs/validation.%J.%I.out -eo output/sketch_to_plink1/two_stratum_v1/logs/validation.%J.%I.err /usr/bin/env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /sc/arion/work/sunh14/conda/envs/py3.11/bin/python experiments/sketch_to_plink1/two_stratum_followup.py worker --manifest /sc/arion/projects/load/users/sunh14/fungen-operator/output/sketch_to_plink1/two_stratum_v1/prepared/validation_jobs.tsv
python experiments/sketch_to_plink1/two_stratum_followup.py finalize
python experiments/sketch_to_plink1/two_stratum_report.py
```

The two-stratum freeze is written by `reduce-dev` before `validation_jobs.tsv` is created. Job ids from this run: successful worker pilot 270039216, development array 270039771, reserved validation array 270041975. Initial diagnostic pilot attempts 270037593 and 270038624 exited before producing results; the first lacked an existing log directory, and the second exposed a missing helper path variable. Both issues were fixed before the successful pilot and full arrays. Native logs for successful jobs are in `output/sketch_to_plink1/two_stratum_v1/logs/`.

The main theta=1.4305556 pilot BED/BIM/FAM is an experimental output because the frozen acceptance gates failed. PLINK 1.9 round-trip uses `--keep-allele-order`; its exact output and 32-variant, all-row call checks are recorded in `output/sketch_to_plink1/pilot/roundtrip_verified.json`.

## 500-sample behavioral MWE, 2026-09-25

The user-selected MWE takes the first 500 rows in the parent FAM order. Native PLINK retains all 20,000 variants and their allele orientation. Phenotype and covariate tables retain the exact stored values for those same samples: 40 phenotypes and 12 covariates. The parent fixture and its original diagnostics remain the 10,000-sample record.

```bash
bsub -K -P acc_LOAD -q express -J fungen_fixture_500 -n 1 -W 00:10 -M 32GB -R 'span[hosts=1] rusage[mem=32GB]' -oo output/sketch_to_plink1/logs/subset_500.%J.out -eo output/sketch_to_plink1/logs/subset_500.%J.err /sc/arion/work/sunh14/conda/envs/xqtl-r-base-fsusie/bin/python experiments/sketch_to_plink1/subset_fixture.py
```

Job **270415437** completed successfully. Output: `output/sketch_to_plink1/behavioral_fixture_500/`. The script refuses an existing output directory. `fixture_metadata.json` retains the native PLINK command, sample-selection rule, input/output hashes, and verification results. Every selected genotype call and allele, phenotype/covariate value, sample position, and indexed phenotype row matched the parent selection; all parent input hashes remained unchanged. The phenotype header is **7,518 bytes** and its longest line is **7,657 bytes**.

This subset keeps the parent's behavioral scope. Full-sample association, power, and empirical-variance diagnostics apply to the parent; they are not reinterpreted as results for 500 samples.
