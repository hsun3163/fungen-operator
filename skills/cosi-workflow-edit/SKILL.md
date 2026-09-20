---
name: cosi-workflow-edit
description: Edit or review COSI Snakemake, SoS, config, rerun, OTTERS backend, old-OTTERS, pecotmr, LD, SST, and submission workflow code safely. Use when Codex is asked to change, generate, compare, dry-run, submit, or debug workflow files, rerun scripts, generated configs, backend switches, or Snakemake/SoS submission behavior in the COSI project.
---

# COSI Workflow Edits

Prefer parameterizing the canonical workflow over creating one-off Snakefiles.

## Before Editing

- Identify the canonical workflow currently used by the run, not just a similarly named file.
- Compare the candidate edit against the canonical workflow for: coloc reuse, OTTERS weight region source, backend step names, output root, old/new LD choice, corrected SST convention, and force flags.
- Treat `hg38/*/meta/pair/*.input_meta.txt` as the ground truth for what Snakemake actually propagated into SoS.
- Preserve config API names used by the pipeline, including intentionally misspelled keys such as `anscentry`.

## OTTERS Backend Invariants

- `coloc_abf` may scan `region_list_generic`.
- OTTERS weight training must use `results/{eqtl}.{LD_INFO}/fine_mapped/region_list.eqtl.tsv`.
- Do not pass `region_list_generic` directly to an OTTERS weight rule unless the user explicitly asks for genome-wide weight training.
- Add new OTTERS backends through config/backend switches or configurable SoS step names. Do not copy the whole workflow unless there is a documented reason.
- Verify rendered weight commands show the intended backend step and `--region_list {input.region}`.

## Validation

- Dry-run after workflow edits before submission.
- Prefer a single target or pair for validation before a broad run.
- Keep writable runtime paths inside the checkout/output root: `TMPDIR`, `XDG_CACHE_HOME`, Snakemake source cache, local storage, temp dirs, and task logs.
- Write mappings, generated manifests, dry-run summaries, and audit artifacts under `temp_reference/`.
