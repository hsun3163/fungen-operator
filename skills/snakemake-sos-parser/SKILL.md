---
name: snakemake-sos-parser
description: Given a Snakemake file that wraps SoS rules, generate a standalone parse_failures.py script that parses pipeline execution output (nohup.out, snakemake log, .stderr files) and produces a structured, AI-readable failure report. Trigger when user asks to generate an error parser/monitor script for a Snakemake pipeline, or needs to debug failed Snakemake/SoS runs.
---

# Snakemake-SoS Error Parser Generator

## Purpose

Given a Snakemake file that wraps SoS rules, generate a standalone `parse_failures.py` that parses pipeline execution output and produces a structured, AI-readable failure report.

## Prompt

```xml
<system>
You are a pipeline engineer. Your job is to read a Snakemake file that wraps SoS rules and produce a single self-contained error-parsing script.

<input>
The user will provide a Snakemake file (or relevant portion). Each rule typically:
- Runs a SoS command via `shell:` directive containing `sos run ... --cwd {params.X}`
- Defines `params:` including a cwd-related param (e.g. `odir`, `cwd`) as a lambda or string
- Writes SoS run output to an internal log variable under a `runlog` param dir
- Has `output:` files (often `.done` sentinels) whose absence signals failure
- Uses wildcards (e.g. `{gwas}`, `{eqtl}`, `{chr}`) that identify the unit of work
- Is submitted to LSF via a cluster profile
</input>

<task>
Produce a Python script called `parse_failures.py` that does the following:

1. **Parse the Snakemake log** (accepts path as CLI arg, defaults to `nohup.out`):
   - Identify every failed rule instance by matching Snakemake's standard failure patterns:
     - `Error in rule {rule_name}:`
     - `RuleException:`
     - `Exiting because a job execution failed.`
     - `log: {path}` lines following error blocks
   - Extract rule name and resolved wildcards for each failure.
   - For cluster rules, extract LSF job ID from `Job <{lsf_jobid}>` or `submitted with LSF jobid {lsf_jobid}` patterns.

2. **For each failed rule with an LSF job ID, query job status**:
   - Run `bjobs -l {job_id}` and capture exit reason, memory usage, run time, exit code.
   - If bjobs unavailable (job expired), parse the LSF cluster log for `Resource usage summary` block.
   - Add LSF status to the failure record.

3. **For each failed rule, check the SoS runlog first**:
   - Locate the runlog directory from the rule's `params` block (parse param named `rlog`, `runlog`, `log_dir`, or similar).
   - Read the most recent `.log` file in that directory matching the wildcards.
   - **Critical check**: if the log contains `"is executed successfully"`, classify as `PULSE_FILE_STALE` immediately — do NOT proceed to error extraction. This is a SoS infrastructure false-positive (stale `~/.sos/tasks/` pulse files from a prior killed run). Set `suggested_fix_hint` to `"Clear stale ~/.sos/tasks/ entries; touch <output.done> manually"`.

4. **Locate SoS task stderr files generically via --cwd extraction**:
   When `--snakefile` is provided, for each rule that calls `sos run`:
   a. Parse the shell block for `--cwd {params.X}` (regex: `--cwd\s+\{params\.(\w+)\}`) to get the cwd param name.
   b. Parse the params block for that param's value:
      - Lambda form: `odir=lambda wc: f"<template>"` — extract the f-string template
      - Plain string: `odir="<value>"` — use as-is
   c. For each failure, resolve the template by substituting `{wc.KEY}` and `{wildcards.KEY}` patterns with actual wildcard values. Also substitute config-derived variables (`{OUT}`, `{RES}`, `{LD_INFO}`, etc.) by scanning the top of the snakefile for assignments like `OUT = ...`, `RES = ...`.
   d. Glob `{resolved_cwd}/**/*.stderr` recursively for SoS task stderr files.
   e. If `--snakefile` not provided or parsing fails, fall back to searching `*.stderr` under sibling directories of the runlog path.

5. **Extract a concise error snippet** from each source in priority order:
   a. Rule's declared `log:` file (wildcards resolved)
   b. SoS runlog (most recent file in runlog dir matching wildcards)
   c. SoS task stderr files found via cwd extraction (Step 4)
   d. LSF cluster log
   e. Inline Snakemake error block

   For each file: read last 50 lines, apply heuristic extraction:
   - Look for `Error:`, `Exception:`, `Traceback`, `FATAL`, `killed`, `oom-kill`, `DUE TO TIME LIMIT`, `segfault`
   - From first match, include that line plus up to 20 lines of context after
   - If no pattern matched, return last 30 lines

6. **Classify each failure** (after ruling out PULSE_FILE_STALE in Step 3):
   - `PULSE_FILE_STALE` — SoS returns non-zero but runlog ends with "is executed successfully"; stale `~/.sos/tasks/` pulse files. Fix: clear stale tasks, touch `.done`.
   - `OOM` — `oom-kill`, `Cannot allocate memory`, `MemoryError`, `std::bad_alloc`, `TERM_MEMLIMIT`
   - `TIMEOUT` — `DUE TO TIME LIMIT`, `TERM_RUNLIMIT`
   - `FILE_NOT_FOUND` — `FileNotFoundError`, `No such file or directory`
   - `DATA_FORMAT` — `ValueError`, `KeyError`, `ParserError`, `could not convert`
   - `SOS_ERROR` — `sos.error`, `Workflow exited with code`
   - `DEPENDENCY` — `ModuleNotFoundError`, `ImportError`, `command not found`
   - `UNKNOWN` — fallback

7. **Output a JSON report** to stdout (or `--out` path):

```json
{
  "pipeline": "<name inferred from Snakemake file or directory>",
  "log_source": "<path that was parsed>",
  "parse_time": "<ISO 8601>",
  "total_failed": <int>,
  "by_category": {"PULSE_FILE_STALE": 0, "OOM": 0, "TIMEOUT": 0, "...": 0},
  "failures": [
    {
      "rule": "<rule_name>",
      "wildcards": {"key": "value"},
      "bjob_id": "<LSF job ID or null>",
      "lsf_status": {"exit_code": 1, "max_mem_gb": 15.2, "run_time": "3:42:10", "exit_reason": "TERM_MEMLIMIT"} ,
      "category": "OOM",
      "sos_cwd": "<resolved --cwd path used to find .stderr files, or null>",
      "log_source": "<path to log/stderr file that was read>",
      "error_snippet": "<concise extracted error text, max 40 lines>",
      "suggested_fix_hint": "<one-line hint based on category>"
    }
  ],
  "example_stderr": "<full stderr content from first non-PULSE_FILE_STALE failure, up to 200 lines>"
}
```

</task>

<constraints>
- Single Python file, no dependencies beyond stdlib (`subprocess`, `glob`, `re`, `json`, `pathlib`, `datetime`).
- CLI args: positional log path (default `nohup.out`), optional `--out`, `--snakefile`, `--cluster-log-dir`.
- Parse snakefile with regex (not AST). Be robust to parse failures — fall back silently rather than crashing.
- Wildcard resolution: substitute `{wc.KEY}`, `{wildcards.KEY}`, and `{wc.KEY!r}` with actual values from the failure record.
- Handle partial/truncated logs.
- `example_stderr`: full content of first **non-PULSE_FILE_STALE** failure's stderr (up to 200 lines) for AI deep diagnosis.
- Do NOT hardcode rule names, paths, or wildcard names.
</constraints>

<output_format>
Return ONLY the Python script content. No explanation before or after.
</output_format>
</system>

<user>
Here is my Snakemake file:

{paste_snakemake_file_here}

Generate parse_failures.py for this pipeline.
</user>
```

## Usage

```bash
# After a failed run:
python parse_failures.py nohup.out --snakefile workflow/Snakefile --out failure_report.json

# Feed report to AI:
# "Read failure_report.json. Diagnose each failure and apply the fix directly."
# No resubmit scripts needed — just rerun the same snakemake command.
```

## Key Design Decisions

- **`PULSE_FILE_STALE` checked first** — before any error extraction. If runlog ends with "is executed successfully", it's infrastructure not code.
- **SoS stderr path derived generically** — by extracting `--cwd {params.X}` from the shell block and resolving the param lambda with actual wildcards. No hardcoded paths.
- **`example_stderr` skips PULSE_FILE_STALE** — targets first real error for AI deep diagnosis.
- The AI's output after reading the report is the fix itself. The user reruns the same snakemake command.
