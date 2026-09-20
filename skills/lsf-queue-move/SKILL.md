---
name: lsf-queue-move
description: Inspect and safely move pending IBM LSF jobs between queues with bmod, including the LOAD bexpress helper. Use when the user mentions bexpress, bmod queue changes, moving jobs between express and premium, queue balancing, or changing a pending job's queue without resubmission.
---

# LSF Queue Move

Use LSF's in-place queue modification for pending jobs. Preserve job IDs and never assume that a queue change requires killing and resubmitting.

## Established Helper

Resolve `bexpress` with `type bexpress` before relying on it. On Minerva, the current helper is:

`/sc/arion/projects/load/scripts/bexpress`

Read the helper before each operational use because it is centrally managed and may change. The version observed on 2026-07-14:

- Lists the current user's jobs with `bjobs`.
- Selects jobs whose state is `PEND`.
- Excludes jobs already in `express` or `interactive`.
- Selects jobs with a runtime limit at or below 720 minutes.
- Runs `bmod -q express <jobid>` for every selected job.

Treat `bexpress` as a broad bulk action. It does not move express jobs to premium, and it does not target one workflow unless the current pending-job set happens to contain only that workflow.

## Workflow

1. Inspect live jobs outside the sandbox with `bjobs`.
2. Identify the exact pending job IDs, current queues, names, runtime limits, and requested resources.
3. State the proposed source queue, destination queue, and affected job count.
4. Preview every affected job ID before changing anything.
5. Change queues only after the user explicitly authorizes the move.
6. Verify the same job IDs and their new queues with `bjobs`.

Use `bmod -q <destination> <jobid>` for a targeted pending job. For example, an authorized pending express-to-premium move uses:

```bash
bmod -q premium <jobid>
```

Use `bexpress` only when the user explicitly wants all jobs selected by its current implementation moved to express.

## Preview

For a targeted request, inspect the proposed IDs directly:

```bash
bjobs -w <jobid> [<jobid> ...]
bjobs -l <jobid>
```

For a proposed `bexpress` run, reproduce its selection without the `bmod` loop and report the resulting IDs. Do not invoke `bexpress` merely to discover what it would affect.

## Safety Rules

- Never move jobs when the user asks only for inspection, explanation, planning, or skill creation.
- Never run `bexpress` as a substitute for a targeted move without explaining its account-wide selection.
- Never modify `RUN` jobs under this workflow. Queue changes are for `PEND` jobs; report running jobs separately.
- Never kill, resubmit, or duplicate jobs unless the user explicitly requests that separate operation.
- Never infer that premium is faster from the user's queue counts alone. Compare queue-wide backlog, priority, pending reasons, runtime limits, and resource eligibility.
- Keep controller jobs, workflow wrappers, and regional worker jobs distinct in the report.
- If any requested job changes state between preview and execution, stop and re-evaluate the affected set.

## Report

Report the snapshot time, selected job IDs or exact count, source and destination queues, whether a change was performed, `bmod` results, and post-change verification. If no change was authorized, say explicitly that no jobs were moved.
