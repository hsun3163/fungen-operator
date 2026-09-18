---
name: xqtl-runner
description: Run, resume, inspect, debug, and finish MESA, AIDA, and CARDIA through the canonical xQTL Protocol Snakemake, SoS, and LSF workflow. Maintain one generated operator notebook per dataset and one canonical-style YAML per output graph, preserve the literal command chain, and require a successful dry-run before production submission.
---

# xQTL Runner

Run each dataset through the existing shared xQTL workflow without creating dataset-specific workflow
infrastructure.

The execution chain is:

`skill notebook template` -> `dataset operator notebook` -> `dataset YAML` -> `bsub` -> `Snakemake`
-> `canonical rules and analysis notebooks/scripts` -> `SoS/LSF` -> `outputs`

## Use The Canonical Workflow

1. Read the applicable `AGENTS.md` first.
2. Treat the repository-local `./xqtl-protocol/` checkout as the source of truth.
3. Use its canonical Snakefile and included rules, analysis notebooks and scripts, SoS workflows, LSF
   profile, and YAML configuration structure.
4. Keep MESA, AIDA, and CARDIA notebooks, YAML files, run directories, logs, and output graphs separate.
5. Do not create dataset-specific Snakefiles, copied rules, custom controllers, stage-script chains, or
   alternative workflow implementations.
6. Put dataset-specific choices in the dataset YAML. Modify shared workflow code only when decisive
   evidence shows a genuine shared-workflow defect.

## Maintain One Operator Notebook Per Dataset

Use [templates/operator_notebook.ipynb](templates/operator_notebook.ipynb), which is the current CARDIA
operator notebook retained as the structural template.

For each dataset:

1. Copy the template once into the dataset workspace and name it `MESA_operator.ipynb`,
   `AIDA_operator.ipynb`, or `CARDIA_operator.ipynb`.
2. Replace every CARDIA-specific path, job name, target, config, expected output, queue override, and
   narrative statement in the copied notebook before executing it.
3. Reuse that same notebook throughout the dataset lifecycle. Do not create separate operator
   notebooks for stages, targets, failures, or retries.
4. Never run a production analysis directly from the skill template.

The dataset operator notebook is the authoritative executable command log for that dataset.

## Use The Notebook As The Command Log

Keep the literal commands actually used in notebook cells to:

1. identify the repository, dataset workspace, runtime, and inputs;
2. generate or update each dataset YAML and display it for inspection;
3. define the intended Snakemake target;
4. submit the exact Snakemake dry-run through `bsub`;
5. submit the production controller through `bsub`;
6. retain submitted commands and job identifiers in cell output;
7. inspect scheduler state, native logs, and declared outputs;
8. debug failures, rerun the dry-run after changes, and resume the authorized endpoint.

Execute every dry-run and production submission from its visible cell in the dataset operator
notebook. Save the executed notebook so that cell output contains the scheduler acknowledgment and
job ID. Kept workflow submissions originate from that notebook cell; use an external shell only for
temporary diagnosis, not to submit the retained run.

A thin launcher may activate the pinned runtime, but it must not hide the Snakemake command or add
another workflow layer. The notebook records how the analysis was operated; scientific analysis logic
remains in the canonical repository.

Activate `/sc/arion/work/sunh14/conda/envs/xqtl-r-base-fsusie` directly in every retained Minerva
submission. It supplies Snakemake, SoS, TensorQTL, R, SuSiE/fSuSiE, and the required R packages as one
runtime. Do not source `activate_local_pixi.sh`, add a Pixi directory to `PATH`, retain a relocated
Pixi `sos_bin`, or combine `xqtl-reno` with a fallback runtime. Dataset YAMLs inherit `sos`, `python3`,
and `Rscript` from the activated environment unless a verified shared contract requires otherwise.

Use this visible cell shape for both dry-run and production submission:

```bash
%%bash
bsub <<'LSF'
#BSUB -J <dataset>_<target>
#BSUB -P acc_LOAD
#BSUB -q premium
#BSUB -W <controller-walltime>
#BSUB -n 1
#BSUB -R "span[hosts=1] rusage[mem=40GB]"
#BSUB -oo <dataset-workspace>/logs/<dataset>.<target>.%J.out
#BSUB -eo <dataset-workspace>/logs/<dataset>.<target>.%J.err
source <runtime-activation>
python -m snakemake \
  --snakefile <repo>/xqtl-protocol/code/snakemake/Snakefile \
  --configfile <dataset-yaml> \
  --directory <dataset-run-directory> \
  --profile <repo>/xqtl-protocol/code/snakemake/profiles/lsf \
  --cores <cores> --jobs <jobs> <target>
LSF
```

The production cell contains that complete command. Do not replace it with `bsub <wrapper-script>`.

## Generate Canonical Dataset YAMLs

Generate one canonical-style YAML for each distinct dataset output graph from the single dataset
operator notebook. Separate modality or consent graphs may therefore have separate YAMLs without
creating another operator notebook.

Start from the closest canonical repository YAML and preserve its field names, hierarchy, types,
defaults, and semantics. Keep dataset paths, populations, visits, covariates, targets, and other
dataset choices in the YAML rather than scattering them across shell commands or hidden notebook
variables. Keep every generated YAML visible and inspectable from the operator notebook. Do not invent
a parallel configuration format.

## Reuse Genotype Within A Dataset

Each operator notebook defines one neutral genotype location per dataset and consent group. Every
analysis graph in that notebook uses the same location for cohort-level VCF QC, PLINK QC, and the
chromosome split; do not assign ownership to a modality, copy the outputs, or recompute them.

Use dataset-local symlinks from every graph's expected data_preprocessing/genotype path to the neutral
shared directory. Record and execute those commands near the top of the operator notebook before any
graph's dry-run. Run one genotype-producing controller at a time, and finish genotype preprocessing
before launching another production controller that can write through the shared path.

Reuse stops at cohort-level genotype preparation. Sample matching, kinship subsets, PCA, and merged
covariates remain in each analysis graph because they depend on that graph's phenotype samples and
covariates.

## Preserve The Literal Command Chain

The notebook must make this chain traceable:

`operator notebook cell` -> `dataset YAML` -> `bsub command` -> `Snakemake command` -> `Snakefile and
rule` -> `canonical notebook or script` -> `SoS/LSF child task` -> `output`

When debugging, follow that chain until the first decisive error. Do not replace it with wrappers,
hidden command generators, secondary controllers, or custom orchestration frameworks.

## Require The Production Dry-Run

A successful dry-run of the exact intended production graph is required before production submission.
Use the same dataset YAML, Snakefile, working directory, target, scheduler profile, environment, and
relevant Snakemake options. Do not submit production after a failed dry-run.

Repeat the dry-run after any change to the dataset YAML, target, Snakemake command, Snakefile or
included rules, called analysis notebook or script, execution-affecting runtime settings, or any input
or parameter that changes the DAG. Record the successful command and result in the operator notebook.

## Run To The Authorized Endpoint

A request to run, resume, finish, or complete a dataset authorizes the ordinary work needed to reach
the furthest stated scientific endpoint: generate or update the notebook and YAML, dry-run, submit,
inspect failures, repair dataset-local defects, retry, and continue downstream.

After a narrow repair target succeeds, rerun the required dry-run and resume the real authorized
endpoint. Do not leave a healthy analysis stopped at an intermediate repair target.

An explicit stop point defines the endpoint. Authorization does not extend to a scientific-method
change, another dataset or output graph, destructive cleanup, or bypassing an external approval.

## Preserve Scientific Semantics

Treat canonical notebooks, implementation scripts, and established defaults as authoritative. Keep
the configured populations, visits, covariates, model fits, variant filters, residualization, scaling,
scientific defaults, and output interpretation unchanged unless the user explicitly changes the
scientific request. Record approved dataset choices in its config; do not improvise a replacement
analysis to make a task run.

Finalize the dataset config, runtime, queue, and resources before large fan-out. Materialized SoS tasks
retain their original commands and parameters. If an authorized dataset-local change invalidates
materialized tasks, stop the affected graph and resubmit it cleanly rather than mixing task generations.

## Execute And Fan Out Through LSF

1. Run every Snakemake, SoS, and LSF submission outside the sandbox through the approved host path.
2. Request at least 32 GB, or `32768 MB`, for every controller and child task. Set both the outer and
   nested requests; do not assume Snakemake resources are forwarded to SoS or LSF.
3. Keep the queue split fixed: the notebook `bsub` submits the Snakemake controller to `premium`;
   the controller submits every rule job to `premium` through the shared LSF profile defaults
   (`profiles/lsf/config.yaml`); SoS submits its tasks to `express` through the shared `sos.yml`
   host file. Never add `bsub` inside a rule, a per-rule queue override, or a `--set-resources`
   queue/runtime override to route work.
4. Submit memory-heavy notebook or script work instead of running it in the foreground session.
5. Use the established shared profile and existing DAG to expose all currently runnable independent
   contexts, chromosomes, regions, and other branches. Set `--cores` and job capacity high enough to
   expose that DAG while preserving each rule's intended threads and resources.
6. Keep one controller per output graph. Fan out through existing Snakemake rules and their existing
   SoS/LSF execution. Do not create additional controllers, copy rules, manually partition work, or
   redesign the DAG to increase concurrency.
7. Submit the required exact-graph dry-run through the same visible `bsub` form. Production remains
   blocked until it succeeds; do not create additional validation jobs or gates.

## Debug And Resume

Capture the exact Snakemake invocation, config, target, failing rule, and first decisive stderr or log
line. Inspect SoS or LSF only when that rule launches the corresponding layer. First correct the
smallest dataset-local input, config, or retained preparation defect. If decisive evidence instead
shows a genuine shared-workflow defect, follow `AGENTS.md` and repair the canonical contract without
creating a dataset-specific route. Rerun the narrowest affected target, then automatically resume the
authorized endpoint.

Preserve valid completed outputs and use native non-forceful reuse. Force only outputs invalidated by
the confirmed defect. Use Snakemake or SoS restart controls instead of deleting outputs. Do not run
competing controllers against the same output graph.

If the user authorizes termination, identify and stop the exact controller and its remaining SoS or
LSF descendants. Confirm clearance once before resubmission; never use a broad job-name kill.

## Completion And Reporting

The requested endpoint is complete when Snakemake exits successfully and its declared target outputs
exist; submitted child tasks must also finish successfully. Other than the required production
dry-run, additional checks provide diagnostic context in native logs. They do not create new control
flow, completion markers, verifier requirements, or failure stages.

Distinguish `not run`, `dry-run failed`, `dry-run passed`, `submitted`, `pending`, `running`, `failed`,
`completed`, and `unverified`. For current status, take one live scheduler snapshot and inspect only
the outputs and representative errors needed for the request. Once a submission is stably `PEND` or
`RUN`, stop polling unless the user requests monitoring or new evidence indicates a problem.

Report the exact command, config, target, decisive result or error, changed dataset files, current
state, and restart point. Give aggregate context counts when they directly answer the request; do not
build an independent scanner, ledger, or verifier to produce them.
