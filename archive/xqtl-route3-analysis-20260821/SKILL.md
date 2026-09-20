---
name: xqtl-route3-analysis
description: Run, resume, audit, and repair MESA/xQTL Protocol Route3 workflows that combine Snakemake, SoS notebooks, and Minerva LSF. Use when asked to launch Route3, report current progress, diagnose Snakemake/SoS/LSF failures, compare Route3 behavior with the canonical ./xqtl-protocol checkout, choose a safe restart target, validate TensorQTL or SuSiE/TWAS completion, or establish provenance for MESA xQTL outputs.
---

# xQTL Route3 Analysis

Operate Route3 as an evidence-backed translation of the canonical xQTL mini-protocol in `./xqtl-protocol`. Preserve its scientific stage graph while making execution restartable and observable.

## Establish The Contract

1. Read the applicable `AGENTS.md` before inspecting or changing Route3. Treat it as the controlling harness and execution contract.
2. Treat the repository-local `./xqtl-protocol/` checkout as the scientific semantic source of truth. Use its mini-protocol wrappers under `./xqtl-protocol/pipeline/`.
3. Do not substitute `./xqtl-renovated/xqtl-protocol/` as semantic authority unless the user explicitly scopes the task to that checkout. Report any drift between the two checkouts.
4. Map the failing or requested Route3 rule to one of these canonical wrappers:
   - `bulk_expression.ipynb`
   - `genotype_preprocessing.ipynb`
   - `phenotype_preprocessing.ipynb`
   - `covariate_preprocessing.ipynb`
   - `qtl_association_testing.ipynb`
   - `2_finemapping.ipynb`
5. Inspect the lower-level notebook invoked by that wrapper within `./xqtl-protocol`, then inspect the corresponding Route3 rule and notebook.
6. Preserve stage boundaries, ordering, `for_each`, `group_by`, fan-out, and fan-in. Do not replace `A -> B -> C` with one opaque step.
7. State a fidelity verdict for every proposed workflow change: `faithful`, `faithful-to-source-Snakemake-only`, or `not faithful`.

Read [references/workflow-contract.md](references/workflow-contract.md) before changing a stage or declaring it complete.

## Choose The Operation

Classify the request before acting:

- **Plan**: resolve inputs, context universe, stage graph, resources, and exact targets; do not claim execution.
- **Dry-run**: build the DAG and capture the rule counts; do not claim outputs exist.
- **Launch or resume**: run the exact approved Snakemake invocation and record its log path and process or LSF job ID.
- **Status**: inspect live processes, LSF state, Snakemake logs, SoS child tasks, and concrete outputs.
- **Repair**: establish one failure signature, patch the smallest faithful layer, and rerun the narrowest checkpoint.
- **Audit**: validate concrete artifacts independently of signatures and marker files.

Never blur these states in the report.

## Build An Evidence Ledger

Resolve this skill's directory (the directory containing this `SKILL.md`) and run
the bundled read-only scanner first when a Route3 work root exists:

```bash
python <skill-dir>/scripts/audit_route3.py --root MESA/work/route3_rna
```

Use `--json` for machine-readable evidence and `--strict` only when incompleteness should fail the command. The scanner does not query LSF and does not infer scientific success from marker files.

Record, at minimum:

- exact Snakefile, config, working directory, target, and runtime roots;
- shared genotype artifacts and chromosome manifest;
- context names and sample-matching artifacts;
- phenotype chromosome manifests and whether every listed file exists;
- Marchenko covariate files;
- TensorQTL marker plus regional-significance output;
- SuSiE/TWAS marker plus exact region-list-to-RDS missing and extra counts;
- newest relevant Snakemake log, SoS stderr, and LSF job evidence.

## Execute Safely

1. Dry-run the exact target before launching unless the user explicitly asks to skip it.
2. Prefer the narrowest concrete output target over `all` during repair.
3. Use the repository's existing launcher, config, SoS scheduler settings, and queue policy before inventing wrappers.
4. Keep shared genotype preprocessing shared. Ancestry and assay contexts diverge through phenotype/sample selection, not separate raw genotype QC copies.
5. Keep independent runs isolated by work root, runtime home/root, logs, and Snakemake metadata. Do not run concurrent Snakemake processes against the same output graph.
6. Write Route3 temporary files under workspace-local `./tmp`, never `/tmp`.
7. Send any notebook, script, or probe expected to exceed 10 GB through SoS/LSF. Do not risk the interactive session.
8. Invoke Snakemake, SoS, and all LSF clients outside the sandbox through the approved execution path.
9. Capture stdout/stderr in a durable log whenever a run will outlive the interaction.

For a normal resume, use the repository's established flags. `--rerun-incomplete`, `--rerun-triggers mtime`, or `--keep-going` are operational choices, not substitutes for selecting the right checkpoint.

## Monitor Three Layers

Treat these as separate state machines:

1. **Snakemake parent**: rule selected, target reason, shell return code, and final workflow status.
2. **SoS workflow**: section status, signatures, declared outputs, task IDs, and pending steps.
3. **LSF child**: submitted job ID, queue, exit status, TERM reason, memory maximum, and child stdout/stderr.

A successful LSF child does not prove the SoS parent received a result. A successful SoS signature check does not prove an output was materialized. A touched Snakemake marker does not prove all expected scientific artifacts exist.

Use the exact error text to select the next inspection. Read [references/failure-playbook.md](references/failure-playbook.md) for recurring signatures.

## Repair And Restart

1. Quote the first decisive error from the deepest failing layer.
2. Identify the declared input/output contract at that layer.
3. Compare behavior with the canonical notebook and source Snakemake path in `./xqtl-protocol`.
4. Patch only the layer that violates the contract.
5. Do not purge signatures reflexively. First prove a signature or stale output is the cause.
6. Do not pre-create a declared output to appease build mode.
7. Rerun the narrowest safe checkpoint immediately after an accepted patch.
8. Monitor until that checkpoint has explicit external success evidence or reaches a new failure signature.
9. Advance downstream only after the current stage is verified.

## Verify Completion

Require all applicable evidence:

- Snakemake reports the target rule finished without a later workflow error.
- SoS reports the expected workflow/steps completed, not merely constructed or skipped.
- Required concrete outputs exist, are nonempty where appropriate, and pass format checks.
- Manifest row counts agree with materialized outputs.
- Marker files were created only after output validation.
- LSF children are no longer pending/running and have no unresolved failure status.

For TensorQTL, validate every expected chromosome's nominal, regional, index, and regional-significance outputs before accepting `.done_cis`.

For SuSiE/TWAS, compare expected analysis regions with both fine-mapping and TWAS-weight outputs. Preserve explicit no-result records only when that is the source workflow's declared contract; do not count a tiny placeholder as a successful model.

## Report Precisely

Return:

1. operation performed;
2. exact target and invocation or audit root;
3. decisive log/scheduler/output evidence;
4. root cause or current stage;
5. changed files, if any;
6. fidelity verdict, if code changed;
7. restart point and current external status.

Say `running`, `failed`, `incomplete`, or `verified complete`; never use “done” for a patch, submission, dry-run, signature construction, or marker alone.
