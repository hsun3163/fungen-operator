# Reproduction path

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
