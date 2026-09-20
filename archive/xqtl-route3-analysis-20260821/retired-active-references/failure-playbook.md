# Route3 Failure Playbook

## Contents

1. Parent/child result failures
2. False completion
3. Genotype and sample-QC failures
4. Phenotype and TensorQTL failures
5. SuSiE/TWAS failures
6. Scheduler and concurrency failures

## Parent/Child Result Failures

### `No result is received for task <id>`

Do not classify this as a signature problem from the message alone.

1. Find the child's LSF job ID.
2. Inspect `bjobs -l`/`bhist -l`, `%J.out`, `%J.err`, and the SoS task status.
3. Check whether the declared concrete output exists and is substantive.
4. Check whether the child executed, skipped under `-s build`, was killed, or wrote to a different path.
5. Compare parent-declared output, child-declared output, and script-produced path character for character.

If a child reports success but only constructs or accepts a signature while the output is absent, the defect is a parent/child materialization contract. Purging signatures is not a durable fix.

### `Step ... is ignored with signature constructed`

Treat this as “not executed.” Verify the output. Never infer that signature construction materialized it.

## False Completion

### Touched marker after failed SoS

Ensure shell control flow checks the SoS exit code and validates all expected outputs before `touch`. A marker validator must fail closed.

### Pre-created declared output

Do not `touch` an output before the SoS section that declares it. SoS may then consider the task satisfied and the parent may wait for a result that was never produced.

### Marker exists but outputs are missing

Move or invalidate only the exact bad marker after a read-only audit identifies missing artifacts. Do not bulk-delete signatures or outputs.

## Genotype And Sample-QC Failures

### `.bed is too small to be a valid .pgen file`

Inspect the complete `.bed/.bim/.fam` trio and the branch semantics. Common causes are an empty/touched `.bed`, a missing companion file, a bad prefix, or an empty related subset routed into PLINK as a dataset.

### `No variants remaining after main filters`

Check which branch is running. On the related branch, verify Route3 did not reapply unrelated-sample MAC/MAF/HWE filters. The faithful path extracts previously selected variants and applies sample missingness filtering.

### KING output has few rows

KING `.kin0` contains pairs passing its reporting/kinship threshold, not every sample pair. A small row count is not itself an error. Validate sample input and thresholds before diagnosing missing samples.

### Empty related set

Represent it using the source branch's explicit empty-related behavior. Do not masquerade a zero-byte marker as a valid PLINK trio.

## Phenotype And TensorQTL Failures

### Tabix or unsorted BED error

Validate coordinate sort order, bgzip format, header, and `.tbi` against the full annotated phenotype BED before chromosome splitting. Do not re-annotate solely to repair sorting/indexing.

### `NAs introduced by coercion` followed by matrix/index errors

Inspect BED metadata columns. Route3 phenotype BEDs can contain `#chr start end ID strand` before samples. Treating `strand` as expression introduces `NA` and can fail imputation or matrix indexing.

### TensorQTL `FileNotFoundError`

Compare normalized genotype/phenotype manifests with the notebook's `for_each` units. Verify every referenced path from within the actual Pixi/SoS execution environment before launching Snakemake.

### Python exit code `-9`

Treat as likely external kill, then prove it with LSF `TERM_*`, `MAX MEM`, and requested memory. Absence of Python traceback is consistent with SIGKILL but not sufficient evidence by itself.

### `Unable to determine R library path ... exit status 255`

Treat as an environment error when it is the decisive child failure. Verify the exact R binary, `LD_LIBRARY_PATH`, module initialization, and Pixi activation inside the LSF job. Do not dismiss it as a warning when no downstream task starts.

## SuSiE/TWAS Failures

### Too few output RDS files

Compare expected region count, submitted tasks, successful tasks, no-result records, and both output families. Do not use aggregate file size alone as completion evidence.

### Tiny RDS exists

Deserialize it. Classify explicit no-variant records separately from swallowed exceptions, empty lists, and malformed result objects.

### `subscript out of bounds` after genotype QC

Check whether zero variants remain and whether phenotype metadata shifted sample columns. Preserve an explicit no-result record only if the source workflow contract requires one.

### TWAS weight exists but association row is absent

Inspect the saved TWAS result object. A zero-row `twas_result` means the association model produced no usable statistic; it is not equivalent to a missing weight file. Trace overlap, imputation/model QC, and method-specific output.

## Scheduler And Concurrency Failures

### Queue is empty while Snakemake appears active

Inspect the Snakemake process tree and SoS parent. It may be computing locally, blocked collecting child results, or already failed while an outer wrapper remains alive.

### Job finished but parent is stuck

Inspect SoS task status and result collection. LSF transport completion is not parent workflow completion.

### Snakemake lock

First prove no live Snakemake process owns the work graph. Concurrent runs from another directory can still target the same outputs and corrupt provenance even when lock files differ. Isolate work and runtime roots before parallel launches.

### Express walltime mismatch

Compare requested walltime with queue limits in the actual submitted `bjobs -l` command. A patched config has no effect on already submitted children.

