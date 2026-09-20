---
name: cosi-run
description: Prepare and complete a COSI Snakemake analysis from an existing or newly derived YAML config, with a records-backed run packet, the exact direct bsub-Snakemake command in a Jupyter notebook, LSF submission, monitoring, recovery, active-set integration, and final output verification. Use when the user asks to run, launch, submit, resume, or finish a COSI workflow. Do not use for status-only inspection or workflow-code editing without a requested run.
---

# COSI Run

Own the run from configuration through verified scientific outputs. Submission is an intermediate state, not completion.

Every COSI Snakemake command that uses the LSF workflow profile—including dry-run, production, recovery, and final no-work audit—must include `lsf_project=acc_LOAD` in `--default-resources`. Never rely on the LSF executor plugin to infer the project from `bhist`.

## Start from proven provenance

Read the current checkout's `records/index.tsv`, the best matching completed packet, and the active workflow before designing a run. For shared-root COSI pecotmr expansions, also read:

- `../COSI/handoff/2026-07-23_13-05-03_COSI_pecotmr_run_and_expansion.md`
- `records/timsina2026_csf_gwas_expansion/20260725_ad3_eqtl16_oldld/`
- `../COSI/records/pecotmr_onek1k_monocyte_ad7/20260703_ad7_onek1k_monocyte_oldld/`

Treat these as templates, not present-tense status. Recheck the canonical Snakefile, active pair manifest, config, output root, logs, and scheduler state each time. In the established shared-root family, provenance may live in the `COSI` checkout while execution occurs in `COSI_pecotmr`; keep that boundary explicit.

The completed Timsina controller historically injected a `coloc_pair_slot` resource. Preserve that fact as provenance, but do not copy its controller-wrapper pattern or resource caps into a new run.

## Establish the run contract

Identify and record:

- the provenance checkout, execution checkout, canonical Snakefile, Snakemake environment, and LSF profile;
- the requested eQTL and GWAS sets, workflow scope, exact terminal pair grid, and output root;
- the supplied config, or the closest maintained config to derive from;
- expected final targets, valid result-free terminal states, downstream aggregate to refresh, and scientific acceptance criteria;
- the direct `bsub` Snakemake driver command, scheduler project/queue/resources, runtime label, and log locations.

Use the active compact manifest and packet target lists to define the universe. Do not infer it from directory listings containing stale or out-of-scope metadata. If scientific scope, LD reference, region policy, backend, or destination cannot be inferred safely, ask before submission.

## Create a durable run packet

Use the existing packet family when one exists. Otherwise create a non-overwriting packet under the appropriate checkout:

```text
records/<branch>/<analysis>/<run_id>/
  README.md
  outputs.md
  configs/
  targets/
  manifests/
  notebooks/
  logs/
  checks/
```

Add it to the authoritative `records/index.tsv`. Keep scientific outputs in their configured output root, not inside `records/`; copy small provenance and symlink bulky immutable logs when appropriate.

The packet must retain the exact config, target list, pair manifest, input manifest, validator, notebook containing the submitted command, pre-submit dry-run, scheduler receipt/job IDs, final no-work dry-run, content audit, and status/outputs summary. The notebook does not replace manifests, logs, or validators.

## Prepare or accept the config

If the user supplies a config, preserve it as the source. Do not silently rewrite it. When changes are required, create a run-specific config and record the source path and diff in the packet.

If no config is supplied, derive one from the closest completed packet rather than a blank file. Validate it against the selected Snakefile. Preserve project API details such as the intentionally spelled `anscentry` key. Check at least:

When constructing a new run-specific YAML, do not set `sos.defaults.J` or any `sos.rules.<rule>.J`. Omit inherited `J` keys as well, so every SoS stage uses the shared Snakefile default of `10000`. Do not rewrite a user-supplied source config merely to remove an existing `J`; preserve it and document that it overrides the shared default unless the user authorizes a run-specific change.

- eQTL/GWAS files, `.tbi` indexes, readable association records, sample-size provenance, IDs, and column maps;
- generic region list, LD metadata, SoS notebooks, `minerva`, executable paths, backend selectors, and QC mode;
- output root, workflow scope/subsets, reuse policy, thresholds, queues, walltimes, memory, and child job sizes;
- no stale dataset aliases, accidental GWAS-specific eQTL names, force flags, or unintended output roots.

For the established old-LD shared-root workflow, coloc may scan the strict generic list, but OTTERS weights must use the coloc-derived eQTL union `results/<eqtl>.<LD>/fine_mapped/region_list.eqtl.tsv`. Never send the generic list directly to weight training unless genome-wide training is explicitly requested.

## Make SoS isolation and timeout accounting explicit

Use a new run-level Snakemake-driver runtime label and confirm the canonical Snakefile gives every concurrently running parent its own task store:

- coloc: one SoS runtime per GWAS x eQTL pair;
- weights: one per eQTL weight root;
- OTTERS test/TWAS: one per GWAS x eQTL pair;
- GWAS RSS: one per GWAS;
- eQTL RSS: one per eQTL.

For each unit, the parent and its LSF-executed SoS children must use the same isolated `HOME`, `.sos`, `TMPDIR`, `XDG_CACHE_HOME`, and task-log root. Never share a single run-level `.sos` store across concurrent parents, and never clean a task store while its parent or children are live.

Keep weight jobs inside the actual queue limit and leave a grace interval before LSF termination so status is written. In the proven express configuration this is 719 minutes / `11:59:00` with a five-minute internal grace; revalidate current queue limits before copying it. After `TERM_RUNLIMIT`, memory kills, or internal timeouts, reconcile scientific weight files, `cache_status.tsv`, and `failed_genes.tsv`. A valid cache may override lost pulse state; `missing` remains unresolved and must not be marked done.

## Define exact targets and valid terminal states

Materialize the Cartesian pair grid in `manifests/` and one absolute terminal target per intended pair in `targets/`. Validate the exact count and membership before submitting.

The usual scientific terminal is the pairwise `*.intact.results.tsv`. A fully evaluated pair with no coloc-derived genes may instead end in an explicit `.no_coloc_hits` marker. Do not fabricate an empty INTACT table and do not accept a no-hit marker unless all expected coloc shards completed and the derived region list is structurally valid and header-only.

If the run extends the active core-method universe, define the aggregate/finalizer target now. Pairwise completion alone is not full completion: the active manifest/status and combined table must also be refreshed and validated.

## Record commands in a notebook and executable scripts

Before submission, create `notebooks/run.ipynb` with the R kernel. Prefer `scripts/run_notebook.py init` from this skill. Record exact, shell-quoted values rather than placeholders:

- objective, run ID, checkout boundary, git commit, and dirty-state note;
- source/run configs and hashes, Snakefile/profile, pair count, targets, output root, and acceptance criteria;
- exact input-validation, packet-validation, smoke, dry-run, production, recovery, finalizer, and final-audit commands;
- Snakemake-driver/child job IDs and log paths as they appear;
- material failures, recovery decisions, final counts, and evidence.

The notebook must contain the literal direct command that is executed: `bsub` followed by the Snakemake executable and its complete arguments. Do not create or invoke `run_controller_*.sh`, `submit_*.sh`, `bash -lc`, or another intermediate controller/wrapper. Prepare runtime directories before submission and pass any required environment explicitly through the submitting environment or LSF's environment option. Never put secrets or tokens in the notebook.

For every recorded Snakemake command, keep required defaults in one option, for example `--default-resources mem_mb=32768 runtime=720 lsf_project=acc_LOAD`. Include the explicit project even when the selected profile already defaults it.

## Gate production

Complete these gates in order:

1. Validate every new VCF/index and its sample-size/identifier assumptions.
2. Validate the packet, exact pair grid, config paths, targets, backend, queues, isolation roots, force policy, direct-command shape, explicit `lsf_project=acc_LOAD`, and absence of controller-injected rule caps.
3. Run the final production command as a real no-force Snakemake dry-run and save the entire output.
4. Count non-header unique regions in every relevant production region list and record the counts.
5. If every relevant region list contains fewer than 500 regions, record `smoke_skipped_region_count_lt_500` and proceed without a separate smoke run. If any relevant list contains 500 or more regions, run an isolated real smoke using representative regions for every new input family, verify the Snakemake driver/parents/children and scientific content, then require a no-work smoke dry-run before production.

Do not use `--ignore-incomplete` as a production default. Use `--unlock` only after proving no live Snakemake driver owns the worktree. Use `--nolock` only when inherited from a validated design and after confirming concurrent drivers cannot target the same outputs. Do not add `--force`, `--forceall`, `--forcerun`, or `sos.force: true` to get past stale bookkeeping.

## Submit with intended fanout

Submit one direct command of this shape through the established scheduler project and long-running queue:

```text
bsub <LSF options and explicit environment> /absolute/path/to/snakemake \
  -s <canonical Snakefile> <explicit targets> --workflow-profile <LSF profile> \
  --jobs unlimited <storage/config arguments> \
  --default-resources mem_mb=32768 runtime=720 lsf_project=acc_LOAD
```

The Snakemake process launched by `bsub` is the only driver. Do not insert a shell or controller script between `bsub` and Snakemake. Pass `--jobs unlimited` explicitly so no profile job ceiling caps ready Snakemake jobs. Pass `lsf_project=acc_LOAD` explicitly on fresh launches and every no-force resume; the outer `bsub -P acc_LOAD` does not propagate a Snakemake child resource and is not a substitute.

Do not inject custom Snakemake resource slots for coloc, weights, OTTERS test, or RSS. The direct command must omit `COSI_COLOC_PAIR_SLOTS`, all `*_PARENT_SLOTS` variables, `--resources ..._slot=...`, and matching `--set-resources` assignments. Let the shared Snakefile expose every dependency-ready parent. LSF policy still governs actual admission. Do not add SoS `J` overrides to newly constructed YAML files; inherit the shared `J=10000` default. The selected Minerva scheduler config must likewise retain `max_running_jobs: 10000`.

Capture the Snakemake driver job ID, submission receipt, child naming pattern, Snakemake/SoS log roots, and the first live scheduler state in both packet and notebook. A `bsub` response, `PEND`, or `RUN` proves acceptance only.

## Monitor and recover without discarding good work

A `cosi-run` request is terminal by default: do not declare success at submission. For long jobs, use meaningful checkpoints or later turns rather than busy polling, keep the packet/notebook current, and resume from the recorded entry point.

At each checkpoint reconcile:

- Snakemake driver state and latest Snakemake log;
- relevant LSF parents and SoS children;
- expected versus observed pair, region, and stage artifacts;
- nonempty content and schema for sampled and terminal files;
- per-stage SoS task stores and weight failure accounting.

An empty queue is neither success nor proof that every child failed. If SoS reports missing pulse files but all scientific shards exist, treat this first as task-state loss: preserve outputs, wait for unrelated active work to settle, stop only proven-stale parents or the direct Snakemake driver, and resume with another direct no-force `bsub` Snakemake command carrying `--default-resources ... lsf_project=acc_LOAD` so shared workflow rules validate outputs and recreate terminal markers. Never delete all `.sos` state or rerun broad completed stages as the first recovery.

On a real failure, identify the first failing rule, pair/region, and upstream cause. Empty/header-only weight regions usually point to coloc-derived region generation; partial SuSiE objects and absent scientific cache files are real incomplete outputs. Fix and no-force resume within scope. Retry a transient root cause at most twice; stop for direction if it recurs, changes scientific inputs, or requires destructive cleanup.

## Verify and close out

Completion requires all applicable gates:

1. The direct Snakemake driver exits successfully and the final Snakemake log has no unresolved failed jobs.
2. No relevant LSF work remains unexpectedly active.
3. Packet validator confirms the exact terminal pair grid.
4. Each pair has the expected unique coloc shard count derived from its region list and its pair-local task store.
5. Each INTACT target is nonempty/schema-correct with expected TWAS and SuSiE-coloc inputs, or is a validated `no_coloc_hits` terminal.
6. SuSiE-RSS objects contain the downstream-required fitted result, not only a partial likelihood object.
7. Weight `cache_status.tsv` has no unresolved `missing` regions; time/memory/error entries are represented in `failed_genes.tsv` as required by the workflow.
8. A final no-mutation dry-run schedules no requested work.
9. When this expands the active universe, the finalizer refreshes the canonical manifest/status and combined core-method table, preserves prior rows, and reports result-bearing versus no-hit counts.

Append the terminal outcome and exact evidence to the notebook. Update `README.md`, `outputs.md`, manifests/checks, and `records/index.tsv` with complete, usable, partial, stale, or failed status. Report exact completed, no-hit, explicitly failed/skipped, unresolved, and missing counts plus the reproducible resume command.

## Notebook helper

Use `scripts/run_notebook.py` to maintain the ledger:

```bash
python <skill-dir>/scripts/run_notebook.py init --output <packet>/notebooks/run.ipynb \
  --title <title> --cwd <execution-checkout> --config <config> --snakefile <snakefile> \
  --dry-run-command <exact-command> --submit-command <exact-command> \
  --driver-log <path> --target <target> --expected-output <path>

python <skill-dir>/scripts/run_notebook.py append --notebook <packet>/notebooks/run.ipynb \
  --heading Submission --body <timestamped-facts> --status submitted

python <skill-dir>/scripts/run_notebook.py finalize --notebook <packet>/notebooks/run.ipynb \
  --outcome completed --summary <result> --evidence <path-or-check>
```
