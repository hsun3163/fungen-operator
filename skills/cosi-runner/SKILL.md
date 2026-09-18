---
name: cosi-runner
description: "Prepare, launch, resume, inspect, debug, and finish COSI or COSI_pecotmr Snakemake, SoS, and LSF reruns from one visible operator notebook and one YAML per output graph. Use for COSI runs, reruns, production submissions, munger dependencies, pair-completion grids, INTACT endpoints, OTTERS weights, old-LD analyses, status checks, and requests such as run COSI, launch this YAML, resume the rerun, check all pairs, or make the operator notebook."
---

# COSI Runner

Run COSI through the existing workflow while preserving one human-readable execution path:

`operator notebook -> YAML -> bsub -> Snakemake -> local Snakefile -> SoS -> implementation modules -> outputs`

IRON LAW: EVERY KEPT COSI SUBMISSION MUST COME FROM A COMPLETE, VISIBLE `bsub <<'LSF'` NOTEBOOK CELL. NEVER ADD A DRY-RUN STAGE, OUT-OF-BAND AUDIT, WRAPPER, CONTROLLER, OR ALTERNATIVE EXECUTION PATH.

## Workflow

Copy this checklist into the working notes and keep it current:

```text
COSI Runner Progress:

- [ ] Step 1: Establish the run contract and native execution path
- [ ] Step 2: Create or update one operator notebook and the run YAML
- [ ] Step 3: Confirm the scientific graph and submission scope
- [ ] Step 4: Submit the prerequisite munger when needed
- [ ] Step 5: Submit COSI production from the visible notebook cell
- [ ] Step 6: Monitor, debug, and non-forcefully resume the same endpoint
- [ ] Step 7: Verify declared completion and the requested scientific summary
```

## 1. The Run Contract

1. Read every applicable `AGENTS.md` and the selected YAML, Snakefile, profile, and called SoS files.
2. Identify the exact COSI checkout, run root, output graph, gene universe, eQTL inputs, GWAS inputs,
   LD source, model set, thresholds, and requested endpoint.
3. Distinguish planned, submitted, pending, running, failed, completed, and verified. Never describe
   a submission receipt or abundant intermediate files as completion.
4. Reuse the established COSI implementation modules. Keep run-specific decisions in YAML or declared
   mapping inputs. Modify shared workflow code only when decisive evidence identifies a real workflow
   defect and the user has authorized that change.
5. Preserve a fresh output graph when requested. Do not symlink or call executables from an older COSI
   workflow to avoid copying the required local implementation.

## 2. Maintain One Operator Notebook

Copy [assets/operator_notebook.ipynb](assets/operator_notebook.ipynb) into the run workspace. It is the
current full legacy core3 old-LD AD7 by eQTL18 rerun notebook retained as the structural template.

Before execution, replace every template-specific path, config, target, job name, expected output,
dependency token, historical job statement, queue choice, and narrative claim. Do not execute the
asset directly. Reuse the copied notebook for production, status, repairs, and resume; do not
make separate notebooks for phases or retries.

The notebook must retain visible sections for:

1. run identity, input contract, hashes, and expected products;
2. prerequisite munger production and non-forceful resume when the run creates a new input;
3. dependency-gated COSI production and resume using the same cell;
4. native scheduler and declared-output status;
5. final product checks and requested aggregation.

Save executed notebooks so each submission cell retains the LSF receipt and job ID. A source edit does
not make an unexecuted notebook a current command record.

## 3. Keep Commands Literal And Minimal

Every retained submission cell must show the complete `bsub <<'LSF'` body, LSF resources, environment
activation, working directory, Snakefile, YAML, profile, options, target, and log paths. Do not replace
the command with `bsub <wrapper>`, a launcher controller, a target generator, or a monitoring program.

Activate `cosi` inside every COSI LSF body. Activate `sumstat_munger` inside every prerequisite munger
LSF body. Run Snakemake as `python -m snakemake` after activation so rule jobs inherit the intended
runtime.

Avoid shell alias chains where multiple notebook variables merely repeat one value. The current local
Snakefile's per-unit runtime exports own isolated SoS HOME, temporary, cache, and task-log directories.
The notebook driver should supply only the Snakemake storage prefixes and variables it directly needs;
do not duplicate `HOME`, `COSI_SOS_HOME`, `COSI_SOS_EXEC_HOME`, `TMPDIR`, `TEMP`, `TMP`, or XDG aliases
at driver scope unless the inspected workflow proves that scope is required.

## 4. Create One YAML Per Output Graph

Start from the closest working COSI YAML and preserve its keys, hierarchy, types, and semantics. Put
the pair universe, region list, input VCFs, gene-ID maps, LD metadata, model selection, thresholds, and
reuse behavior in YAML rather than hidden notebook variables.

For the retained current-rerun template, preserve these choices unless the user explicitly changes the
scientific contract:

```yaml
otters_weights_parallel_methods: true
otters_weights_step: OTTERS_weights_by_method
otters_weights_methods: prs_cs
otters_test_step: OTTERS_test
otters_test_models: P0.001,P0.05,PRScs
otters_required_models_for_test: P0.001,P0.05,PRScs
reuse_coloc_outputs: false
restrict_coloc_aggregation_to_generic: true
region_list_pp4: 0.5
```

Do not introduce pair-slot resources, YAML-level `J` overrides, force options, separate controllers,
or an alternative config format. For the retained full rerun, use `jobs=10000`, SoS `J=10000`,
Minerva `max_running_jobs=10000`, and `acc_LOAD` unless the user changes the run contract.

## 5. Confirm Before Submitting

Show the user the exact run root, notebook, YAML, prerequisite inputs, pair count, gene count, target,
environment, queue, and any scientific or workflow edits before the first submission when those were
not already explicit in the request.

If the user asked only to prepare files, stop before `bsub`. A request to run, launch, resume, finish,
or complete authorizes ordinary non-destructive work through the stated endpoint, but not a method
change, another output graph, destructive cleanup, or bypassing an approval gate.

Submit production only for the exact graph and endpoint the user authorized. When a prerequisite
munger is still running, use the notebook's native LSF dependency instead of adding another stage.

## 6. Submit The Native Run

Run every `bsub`, Snakemake, SoS, and LSF operation outside the sandbox through the approved host path.
Submit the exact intended production graph from the visible notebook cell with its YAML, Snakefile,
run directory, profile, environment, target, and execution-affecting options.

When a prerequisite munger is part of the run:

1. submit its production cell when its declared products are absent;
2. retain the returned job ID in notebook output;
3. submit COSI production with `#BSUB -w "done(MUNGER_JOB_ID)"` when the prerequisite is in flight;
4. resume from the same production cells without force.

Do not add a dry-run controller or a separate review stage to the operator notebook.

## 7. Submit, Debug, And Resume

Rerun the same visible production cell without force to resume. Preserve valid completed outputs and
use native Snakemake and SoS reuse; do not delete or overwrite scientific outputs to manufacture a
clean run.

On failure, follow the literal chain to the first decisive error:

`notebook receipt -> controller accounting/log -> Snakemake rule -> SoS task if present -> declared output`

Fix the smallest confirmed defect within the authorized graph, then resume the original endpoint from
the same production cell. Do not stop at an intermediate repair target when the requested endpoint
remains unfinished.

Use the configured per-pair and per-dataset SoS isolation. For the retained rerun, coloc and TWAS are
isolated per GWAS-eQTL pair, weights and eQTL RSS per eQTL, and GWAS RSS per GWAS. OTTERS weights use
the coloc-derived eQTL union, not the full generic region list.

Record timeouts, memory-limit failures, deterministic errors, and empty weights in each eQTL's native
`failed_genes.tsv` when the workflow contract requires it. Do not invent a parallel failure ledger.

## 8. Verify Completion

Use one live scheduler snapshot plus native logs and declared outputs. Do not build or run an extra
auditor, scanner, ledger, verifier job, or completion controller unless the user explicitly asks for
one. Once jobs are stably pending or running, stop polling unless monitoring was requested.

For a pair-completion COSI graph, require exactly one endpoint per configured pair:

- nonempty, schema-valid INTACT results when genes passed regional coloc; or
- `.no_coloc_hits` when complete coloc results legitimately contain no passing genes.

Require all configured pairs, no unresolved coloc/weight/TWAS/RSS/SuSiE-coloc units, the requested
prerequisite products, and the declared terminal products. Report weight failures recorded in
`failed_genes.tsv` as missing scientific coverage rather than silently calling them complete.

Run only the aggregation requested by the user and derive it from canonical results. For the retained
rerun, the requested examples are 5095 (regional PP at least 0.5 and INTACT PP at least 0.95) and 8080
(regional PP at least 0.8 and INTACT PP at least 0.8), compared against the stated legacy sets. Do not
turn this into an unrelated audit suite.

Report the exact notebook, YAML, target, LSF job IDs, decisive result or error, changed files, current
state, missing scientific coverage, and restart point.

## Anti-Patterns

- Do not submit from a shell or hidden script and later paste the command into the notebook.
- Do not create dataset-specific Snakefiles, copied rule families, wrapper launchers, or controllers.
- Do not add dry-run or dry-run-review sections to the operator notebook.
- Do not add checks simply because more checks are possible.
- Do not claim completion from RDS counts, partial output trees, or a successful submission receipt.
- Do not mix scientific outputs from an older graph into a requested fresh rerun.
- Do not force reruns, broadly terminate jobs, or delete outputs without explicit authorization.
- Do not silently change genes, datasets, models, LD, thresholds, or missing-data semantics.

## Pre-Delivery Checklist

- [ ] Applicable `AGENTS.md` instructions were followed.
- [ ] The copied notebook and YAML identify one exact output graph.
- [ ] Every kept submission is a complete visible `bsub <<'LSF'` cell.
- [ ] COSI cells activate `cosi`; munger cells activate `sumstat_munger`.
- [ ] No redundant driver-level SoS alias chain remains without evidence it is required.
- [ ] No wrapper, extra audit, controller, hidden generator, force option, or unauthorized output reuse was added.
- [ ] No dry-run or dry-run-review section was added.
- [ ] Job receipts, current state, terminal outputs, failures, and restart point are reported precisely.
- [ ] The copied notebook is valid `nbformat` JSON and each `%%bash` cell passes `bash -n` after removing the magic line.
