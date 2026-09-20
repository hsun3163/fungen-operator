---
name: snakemake-lsf-triage
description: Fast log-first triage for this user's Snakemake + LSF workflows. Use when they ask "why stuck", "what is the error", "what now", or need the decisive failure signal from `nohup.out`, `.snakemake/log`, or LSF logs.
argument-hint: [repo-path]
disable-model-invocation: false
user-invocable: false
allowed-tools:
  - Bash
  - Read
  - Grep
---

# Snakemake LSF Triage

Use this for the user's recurring HPC workflow debugging in COSI and route3/xQTL when the immediate goal is to identify the real blocker with minimal churn.

Do not use this to redesign the pipeline, swap tools away from the truth notebook, or make broad semantic changes before the decisive log signal is known.

## When to use

Triggers:
1. The user asks "why stuck", "what is the error", "what is going on now", "what now", or asks to inspect `nohup.out`.
2. Snakemake reports `MissingOutputException`, `LockException`, dry-run parse issues, or an LSF job failure.
3. A workflow appears hung, laggy, or inconsistent after route3/COSI shell setup.

Non-goals:
1. Do not jump to pipeline redesign or substitute route3/new backends when the user is preserving old notebook truth.
2. Do not bundle extra helper files into a requested fix commit unless the user asked for them.

## Inputs / context to gather

1. Confirm the active cwd and submit entrypoint.
   - In COSI, check whether `workflow/run_snakemake_lsf.sh` points at `workflow/snakefile.py`.
   - In route3/xQTL, identify the relevant Snakefile rule, shell wrapper, and truth notebook.
2. Read the newest top-level run logs first.
   - `nohup.out`
   - latest `.snakemake/log/*.snakemake.log`
   - rule-specific LSF logs under `.snakemake/lsf_logs/` when a job ran remotely
3. If the user named a specific output or path, inspect that exact path before making claims.
4. If the shell behavior looks inconsistent, print `HOME` and inspect wrappers that delegate through `$HOME`.

## Procedure

1. Identify the failure class from logs before editing anything.
   - `LockException` or missing `--cores`
   - `MissingOutputException`
   - `TERM_MEMLIMIT` / `SIGKILL` / `TERM_RUNLIMIT`
   - read-only cache path under `.cache/snakemake`
   - route3 shell env override such as `.route3-home`
2. For Snakefile syntax or parsing claims, validate with Snakemake itself.
   - Prefer `snakemake --dry-run` with the smallest viable config.
   - Do not treat `python -m py_compile` as decisive for Snakefiles using Snakemake directives.
3. If the failure is `MissingOutputException`, trace the exact naming chain.
   - Expected path from Snakemake rule
   - Actual on-disk file names
   - Shell wrapper naming flags
   - Truth notebook naming convention
4. If the failure is an LSF kill, find the decisive scheduler line.
   - Look for `TERM_MEMLIMIT`, `TERM_RUNLIMIT`, memory summary, runtime summary, and `Signals.SIGKILL`.
   - Treat that as more important than generic Snakemake cleanup text.
   - For Snakemake resource overrides, inspect the rendered dry-run resource line. Bare numeric time values can be parsed in unexpected units; for `susie_twas`, use an explicit value such as `runtime=144h` and confirm it renders as `runtime=8640` minutes before production.
5. If `snakemake --unlock` is slow, inspect `.snakemake` contents and size.
   - If the goal is only unlocking, remove only the lock if possible.
   - If the state tree is huge and the user wants lag gone, explain the safety boundary before clearing `.snakemake`.
6. If the shell looks broken after route3 setup, inspect env overrides.
   - `echo $HOME`
   - wrapper body such as `/hpc/users/sunh14/.local/bin/codex`
   - repo scripts exporting `HOME="${ROOT}/.route3-home"`
7. Report back with:
   - decisive failure signal
   - exact file/log path
   - next action
   - what is still hypothesis

## Efficiency plan

1. Start with `rg` over the repo and the named log/error strings instead of opening large files blindly.
2. Read `nohup.out` and the newest `.snakemake/log` before per-rule logs; this often reveals whether the issue is startup, scheduler, or naming.
3. Cache the truth boundary early:
   - active Snakefile
   - shell wrapper
   - truth notebook
4. Stop once you have one decisive blocker and one concrete next action. Do not keep exploring side hypotheses unless the user asks.

## Pitfalls and fixes

- Symptom: `py_compile` says the Snakefile is invalid.
  - Likely cause: Snakemake directive syntax, not an actual current-file error.
  - Fix: run Snakemake dry-run with a minimal config.

- Symptom: `MissingOutputException` after a job "completed".
  - Likely cause: naming/path mismatch, not compute failure.
  - Fix: compare expected output names to actual produced files and the notebook/wrapper naming convention.

- Symptom: workflow looks hung and logs mention `LockException` or missing `--cores`.
  - Likely cause: startup failure happened before meaningful execution.
  - Fix: inspect both `nohup.out` and the newest `.snakemake/log` entries before calling it a hang.

- Symptom: Snakemake says cleanup/user termination, but LSF logs show `TERM_MEMLIMIT`.
  - Likely cause: scheduler memory kill is the real blocker.
  - Fix: raise memory or rerun the specific region/rule with a larger request.

- Symptom: `TERM_RUNLIMIT` follows a nominal long-runtime resubmission.
  - Likely cause: a bare numeric Snakemake resource override was interpreted in the wrong time unit.
  - Fix: use explicit units (for example `susie_twas:runtime=144h`) and require the intended minutes in the dry-run render before submitting.

- Symptom: `snakemake --unlock` is very slow.
  - Likely cause: huge `.snakemake` state tree.
  - Fix: inspect `.snakemake` contents; if the user wants lag removed and accepts the safety boundary, clear stale state and then watch for cache-path issues.

- Symptom: command wrappers fail only in a route3/MESA shell.
  - Likely cause: `HOME` override to `.route3-home`.
  - Fix: restore the real interactive `HOME` and keep the fake home confined to pipeline shells.

## Verification checklist

1. Name the decisive failure signal verbatim.
2. Cite the exact file/log path that proved it.
3. State the next action in one sentence.
4. Mark any remaining explanation as hypothesis if it was not confirmed in code/logs.
5. If you propose a naming fix, list both expected and actual names.
6. If you propose a memory increase, cite the observed requested/max memory numbers.
7. If a runtime override is involved, cite the CLI value and rendered dry-run resource value.
