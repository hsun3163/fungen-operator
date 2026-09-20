---
name: debug-pipeline
description: Systematic COSI Snakemake, SoS, LSF, OTTERS, coloc_abf, and rerun debugging/status triage. Use when a pipeline run fails, user says "debug", "what failed", "why did it fail", "check the pipeline", asks for current job/output status, asks whether jobs actually ran, asks to inspect SoS/LSF tasks, or requests broad result/weight-tree audits.
---

# Debug Pipeline

Systematic debugging of COSI Snakemake+SoS pipeline failures and queue/output status. Follow concrete evidence first; do not jump to code inspection unless logs point there.

## Operating Rules

- For LSF interactions (`bjobs`, `qstat`, `bqueues`, `bsub`, `bkill`, `list_sos`), run outside the sandbox on the first attempt.
- For broad result/weight-tree scans, save raw scan output under `temp_reference/` and inspect the saved file with `head`, `tail`, `rg`, and `wc`.
- Deploy a worker whenever practical for routine monitoring, queue/status scans, and large read-only filesystem walks.
- To verify whether jobs actually ran instead of signature-skipping, grep runlogs for `submitted`; no `submitted` lines means no new cluster jobs were launched.
- Do not call setup or submission complete. A run is complete only when expected final outputs exist, or a concrete blocker is documented.

## Debug Chain (follow in order)

### Step 1: nohup.out
Read the tail of `nohup.out` (or `archive/nohup.out` if moved).
- Identify: which rule failed, exit code, timestamp
- Look for: `Error`, `non-zero exit`, `MissingOutputException`, `Signals.SIGTERM`
- Record: the failed rule name and wildcards (e.g., `coloc_abf` for `{gwas}.{eqtl}`)

### Step 2: Snakemake log
Read the latest `.snakemake/log/*.snakemake.log`.
- Confirm which rules failed and their job IDs
- Check if Snakemake itself had errors (lock issues, DAG problems, resource errors)
- Look for: `Error in rule`, `Shutting down`, `CalledProcessError`

### Step 3: Snakemake cluster log (if jobs were submitted to LSF)
Check LSF stderr/stdout if the failed rule was a cluster job (not a `localrule`).
- For LSF: check `bjobs -l <JOBID>` or the job's stderr file under `.snakemake/`
- Look for: `TERM_MEMLIMIT`, `TERM_RUNLIMIT`, `Exited with exit code`
- If the rule is a `localrule` (like `coloc_abf`), skip this step

### Step 4: Step-specific runlog
Navigate to the rule's runlog directory. Common patterns:
- `hg38/{ancestry}/results/{gwas}/{eqtl}/{step}/runlog/*.log`
- `hg38/{ancestry}/results/{gwas}/{eqtl}/coloc/runlog/*.log`
Read the most recent log for the failing pair.
- Look for: SoS completion message ("is executed successfully"), error messages, job counts
- If log ends with "is executed successfully" but wrapper failed → **pulse file issue** (see Step 6)

### Step 5: SoS task stderr
If Step 4 shows SoS submitted cluster tasks, inspect individual task stderr:
- `hg38/{ancestry}/results/{gwas}/{eqtl}/{step}/{substep}/*.stderr`
- For coloc_abf: `hg38/{ancestry}/results/{gwas}/{eqtl}/coloc/coloc_abf/coloc_abf/*.stderr`
- Look for: R errors, missing files, invalid data (AF values, MAF, `s` parameter)

### Step 6: Generated scripts and SoS task status
If a generated SoS/R script exists under a run directory, inspect it to confirm what actually executed.

If Steps 4-5 show no real error, check for stale SoS infrastructure:
- `~/.sos/tasks/*.soserr` — look for "considered as aborted due to missing pulse file"
- `~/.sos/status_cache.pickle` — may have stale "running" entries from killed prior runs
- If found: this is a pulse file issue. Clear stale entries in `~/.sos/tasks/`, touch `.done` manually.

## Decision Rules
- If Step 4 log ends with "is executed successfully" → pulse file issue (Step 6), NOT a code/data bug
- If Step 5 shows R errors with AF/MAF/`s` → data trap (invalid AF values or per-variant N for case-control `s`)
- If Step 3 shows TERM_MEMLIMIT → increase memory request
- If Step 1 shows SIGTERM → check if external kill (walltime, user) vs Snakemake shutdown cascade
- For `coloc_abf`, if the runlog says `is executed successfully`, suspect SoS pulse/status infrastructure before blaming data or logic
- For OTTERS reruns, inspect `results/weights/*/failed_genes.tsv`, `cache_status.tsv`, `.done`, and `.done.failed` before deciding whether a weight root is usable
- **If the failure is a missing input file** → trace upstream (Step 7)
- NEVER suggest `-s force` (reruns all regions — unacceptable)
- NEVER suggest destructive fixes without asking

### Step 7: Upstream trace (missing input files)
If any step reveals a `MissingInputException` or the failing command references a file that doesn't exist:
1. Identify which Snakemake rule produces the missing file (check `snakefile_combined.py` rule outputs)
2. Check if that producer rule ran: look for its entry in `nohup.out` and `.snakemake/log/`
3. If the producer rule ran but failed → restart this debug chain from Step 1 for that rule
4. If the producer rule never ran → check why: was its own input missing (recurse), was it skipped by Snakemake (check DAG), or did a prior run create a stale `.done` sentinel that made Snakemake think it was complete?
5. Check the producer rule's `.done` file: does it exist? Is its timestamp older than expected? Was it created by a failed run that touched `.done` prematurely?
6. Report the full upstream chain: `failing_rule → missing_file → producer_rule → producer_failure_reason`

## Reporting
After completing the trace, report:
1. Which step in the chain revealed the root cause
2. The root cause (one sentence)
3. The specific error message or evidence
4. Proposed fix (minimal, non-destructive)
