---
name: xqtl-snakemake-analysis
description: Run, inspect, debug, resume, and modify xQTL Snakemake workflows in the canonical ./xqtl-protocol checkout. Use for Snakefile, rule, config, DAG, dry-run, execution, status, failure, restart, SoS, and LSF tasks related to xQTL Snakemake analysis.
---

# xQTL Snakemake Analysis

Work directly with the canonical xQTL Snakemake implementation in `./xqtl-protocol`. Keep the workflow simple, native to Snakemake, and scoped to the requested target.

## Establish The Scope

1. Read the applicable `AGENTS.md` and follow its execution boundary.
2. Treat the repository-local `./xqtl-protocol/` checkout as the source of truth.
3. Identify the exact Snakefile, included rule file, config, target, working directory, and environment involved.
4. Inspect the script, notebook, or command called by the selected rule when its behavior matters.
5. Follow the existing Snakemake rule graph and output contracts unless the user asks to change them.

## Choose The Direct Operation

- **Inspect**: read the relevant rule, config, command, log, and target output.
- **Dry-run**: run the exact Snakemake target with the repository's established environment and flags.
- **Run or resume**: use the existing launcher or a direct approved `snakemake` invocation, targeting the real scientific endpoint by default.
- **Debug**: start from the failing rule and its decisive stderr or log line.
- **Edit**: make the smallest source change needed, then rerun the affected target.
- **Status**: check the Snakemake process, relevant scheduler task when present, and requested output.

Do not blur a dry-run, submission, running job, failed job, and completed target.

## Launch The Real Endpoint

1. For a production analysis launch, target the furthest authorized scientific endpoint, such as `xqtl_core`, rather than a convenience stage target.
2. Treat an explicit user stop point as the real endpoint. Do not run beyond a sensitivity report, pre-fSuSiE boundary, consent boundary, or other requested stop.
3. Use a narrow intermediate target only when the user explicitly requests it or when diagnosing and repairing a verified failure.
4. After a narrow repair target succeeds, launch or resume the real endpoint so Snakemake carries the remaining dependency graph automatically. Do not leave a healthy analysis stopped at the repair checkpoint.
5. If the real endpoint is not runnable, identify and repair the shared contract blocker before production launch. Do not silently substitute a shorter target.

## Preserve Scientific Semantics

1. Treat the canonical notebooks, implementation scripts, and established scientific defaults as authoritative for analysis behavior.
2. Distinguish a dataset configuration change, a shared implementation repair, and a scientific-method change. Before making a scientific-method change, explain it and obtain explicit user approval.
3. Do not silently change the number of model fits, filtering population, variant filters, residualization or scaling, model defaults, or output interpretation merely to make a failing task run. Repair the execution contract or stop and report the incompatibility.
4. Classify a per-feature exclusion as an expected skip rather than a failure only when its decisive log matches a condition intentionally defined by the workflow.

## Freeze The Production Contract

1. Finalize the shared source, dataset config, runtime, queue, and resource settings before large production fan-out.
2. Do not edit scientific workflow behavior underneath active, materialized SoS tasks and assume they will inherit the edit. Treat generated SoS task commands as snapshots of the source and parameters used when they were materialized.
3. If an active run must adopt a semantic source or parameter change, stop and resubmit the affected execution graph instead of mixing old and new task definitions in one run.

## Keep It Simple

1. Prefer native Snakemake inputs, outputs, logs, resources, and exit status over custom controller layers.
2. Do not add broad audit frameworks, evidence ledgers, global preflight gates, custom completion verifiers, redundant marker validators, or generalized safeguard wrappers unless the user explicitly requests them.
3. Check only the inputs and outputs needed to answer the request or satisfy the selected rule's existing contract.
4. Reuse the repository's environment, launcher, scheduler profile, and queue settings.
5. Prefer the narrowest concrete target during debugging or repair, then return to the real endpoint after the repair succeeds.
6. Do not run concurrent Snakemake processes against the same output graph.
7. Write temporary workflow files under workspace-local `./tmp`.

## Submit Tasks

1. Run every Snakemake, SoS, or LSF submission outside the sandbox through the approved host execution path.
2. Request strictly more than 30 GB of memory for every submitted task. Use at least 31 GB when the configuration accepts integer gigabytes, and preserve the repository's native memory-unit syntax.
3. Submit any notebook, script, or probe expected to need more than 10 GB rather than running it in the foreground session.
4. Record the submitted command and job identifier when execution will outlive the interaction.
5. Activate the complete pinned runtime in the thin dataset launcher and nested task template, not in the Snakefile. Keep the launcher invocation simple and ensure outer and child tasks enter the same intended runtime.
6. On Minerva, target eligible nested analysis tasks to the `express` queue with a 12-hour run limit by default. Use another queue or run limit only for a concrete runtime requirement or explicit user direction. Change the source config for future tasks; use `bmod` only for already-pending jobs.
7. After submission, perform one immediate scheduler check to distinguish `submitted` from `running` or `pending`; do not start a polling loop unless the user requests monitoring.

## Validate Through LSF

1. Run every test and validation command through an LSF job, never in the local or foreground session. This includes syntax checks, unit tests, config-generation checks, deterministic-regeneration checks, fixture workflows, and Snakemake dry-runs.
2. Keep read-only source and artifact inspection local when useful; inspection alone is not a test.
3. Request strictly more than 30 GB for each validation job, capture its exact command and LSF job identifier, and judge success from the LSF exit status plus its normal test output.
4. Fan out independent validation jobs when their inputs and outputs do not overlap; single-threaded tests must run concurrently whenever the dependency graph permits.

## Fan Out LSF Work

1. Fan out independent contexts, chromosomes, regions, and other DAG branches as much as reasonably possible within one Snakemake controller.
2. Treat a rule's `threads` value or LSF `bsub -n` request as a per-job resource, not as the workflow-wide concurrency limit.
3. Do not set the controller to `--cores 1` merely because individual numerical jobs use one thread. Set `--cores` high enough to expose the intended outer fan-out.
4. Preserve one-thread execution where scientific determinism or the implementation requires it. Independent one-thread jobs must run concurrently whenever the DAG permits.
5. Limit fan-out only for a concrete dependency, scheduler or project cap, memory or storage pressure, controlled-data boundary, or explicit user instruction. State the limiting reason instead of silently serializing the run.
6. Keep one controller per output graph; achieve concurrency through the shared Snakemake DAG and its SoS/LSF tasks, not through competing controllers.

## Debug And Restart

1. Capture the failing Snakemake invocation, target, rule, and first decisive error.
2. Inspect the selected rule's declared inputs, outputs, resources, log, and called implementation.
3. If the rule launches SoS or LSF, inspect that child layer only as far as needed to explain the failure.
4. Patch the smallest relevant source layer.
5. Rerun the narrowest affected target after an accepted patch.
6. Continue downstream only after that target succeeds.
7. Preserve valid completed outputs and default nested execution to non-forceful reuse. Force only the rule outputs whose scientific or execution contract was invalidated.
8. Do not delete outputs merely to trigger a rerun when native Snakemake or SoS force controls can express the restart.
9. Remember that stopping a Snakemake controller may leave outer SoS jobs and nested LSF children active. With explicit termination authorization, resolve and stop the exact controller, outer jobs, and descendants; never use a broad job-name kill. Confirm clearance once, then resubmit the real endpoint.

## Recognize Completion

Use the workflow's normal evidence: Snakemake exits successfully, the requested target satisfies its existing output contract, and any submitted child task has finished successfully. Do not invent an independent verification system or require unrelated project-wide checks.

## Report

Return the exact target and command, the decisive error or result, files changed, the restart point, and the current status: `not run`, `running`, `failed`, or `completed`.

For production status, report aggregate counts by context and state: total input features, completed outputs, expected skips, genuine failures, running, and pending. Inspect one representative decisive stderr for each distinct failure signature rather than every feature. Use a point-in-time scheduler snapshot and do not keep polling unless the user explicitly asks to monitor.
