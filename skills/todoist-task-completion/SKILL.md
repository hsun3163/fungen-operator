---
name: todoist-task-completion
description: "Complete, finish, close, verify, audit, review, reconcile, or hand off Todoist tasks and cards using native project evidence and a mandatory final review. Use for Todoist projects, task lists, delegated jobs, deliverables, comparisons, completion notes, blockers, and review-ready outputs. Triggers include 'complete this Todoist task', 'mark it done', 'finish the assigned tasks', 'which tasks are complete', 'close completed cards', 'review before completion', and 'compare these tasks or results'."
---

# Todoist Task Completion

IRON LAW: NEVER CLOSE OR REPORT A TODOIST TASK AS COMPLETE UNTIL ITS REQUESTED OUTPUT EXISTS, ITS FINAL REVIEW PASSES, AND EVERY REQUESTED COMPARISON IS SHOWN SIDE BY SIDE. NEVER ADD TRANSITION, SENSITIVITY, GAIN/LOSS, OR COUNTERFACTUAL ANALYSES WITHOUT EXPLICIT USER AUTHORIZATION.

## Completion states

Use exactly one evidence-based state:

- `complete`: every acceptance criterion passed and no required work remains.
- `review-ready`: execution passed, but the task contract requires user or named-reviewer acceptance.
- `partial`: useful requested work exists, but at least one acceptance criterion remains.
- `blocked`: a required dependency, permission, credential, or external service prevents progress.
- `not-started`: no qualifying execution artifact exists.

Submission, delegation, a dry-run, exit code 0, or a nonempty file alone is not completion.

If the user says a majority is sufficient, treat that as permission to select and finish qualifying tasks one at a time. Do not weaken the acceptance criteria of any task marked complete.

## Workflow

Track this checklist:

```text
Todoist Task Completion Progress

- [ ] Step 1: Recover the task contract ⚠️ REQUIRED
- [ ] Step 2: Resolve scope and dependencies ⛔ BLOCKING
- [ ] Step 3: Execute through the native project path
- [ ] Step 4: Build direct comparisons (conditional) ⚠️ REQUIRED
- [ ] Step 5: Perform final review ⛔ BLOCKING
- [ ] Step 6: Sync or draft the Todoist completion record
- [ ] Step 7: Report exact status and evidence
```

## Step 1: Recover the task contract ⚠️ REQUIRED

Read the Todoist title, description, comments, subtasks, labels, attachments, due information, and linked project artifacts when accessible.

Ask:

- What exact output did the user request?
- What explicit thresholds, universes, names, paths, formats, and exclusions define success?
- Which comments are later corrections that supersede earlier wording?
- Does current repository evidence disagree with the Todoist wording?

Write a compact contract containing inputs, requested outputs, acceptance criteria, exclusions, and canonical terminology. Later user corrections override older task comments. If a conflict would materially change the output, resolve it with the user before execution.

If no Todoist connector is available, use task content already pasted or frozen in the project. Do not fabricate live task state. Continue local work when the task contract is otherwise available, and label Todoist synchronization as unverified.

## Step 2: Resolve scope and dependencies ⛔ BLOCKING

Classify each requested item as independent, dependent, deferred, or outside scope.

Ask:

- Can this task execute independently now?
- Does it require licensed access, credentials, manual review, or another unfinished task?
- Is the requested action read-only, local execution, or an external status mutation?

Execute independent work without inventing dependencies. Do not start deferred analyses or broaden the scientific scope merely because adjacent data exist. Use the specialized project skill and native workflow that own the requested artifact.

## Step 3: Execute through the native project path

Use existing scripts, notebooks, workflows, environments, and output locations. Preserve provenance and rerun instructions.

For every retained result, capture:

- exact canonical input and output paths;
- command, script, notebook, or workflow that produced it;
- exit status plus native validation, test, log, or scheduler evidence;
- limitations, unresolved dependencies, and whether the result is current or historical.

Check the output itself. A successful process that produced missing, empty, stale, or semantically wrong output is not complete.

## Step 4: Direct comparison gate (conditional) ⚠️ REQUIRED

When the task says `compare`, place the compared items side by side by default.

Use matched:

- definitions and selection criteria;
- axes, units, denominators, field order, and visual scale where applicable;
- labels and corresponding evidence paths.

Prefer a two-column table, paired panels/facets, or aligned lists. State unavoidable mismatches next to both items rather than hiding them in a footnote.

Do not substitute or add:

- sensitivity analyses;
- transition, gained/lost, or before/after analyses;
- threshold counterfactuals;
- derived universes or alternative definitions.

Perform those only when the user explicitly requests or authorizes them. Existing historical analyses of those types do not become the primary comparison deliverable automatically.

## Step 5: Final review ⛔ BLOCKING

Review the final artifact, not only its generator.

### Technical review

- Open the canonical output and confirm it is nonempty and current.
- Run the native validation, tests, checksums, or status query appropriate to the task.
- Reconcile reported counts and claims against source rows.
- Confirm no stale path, label, threshold, universe, or completion claim remains.

### Reviewer-facing review

- For visual work, inspect the rendered final figure, notebook, HTML, deck, or report at its intended size.
- For multiple visual outputs, provide one compact gallery or index when requested or when no existing review surface covers them.
- For nonvisual work, provide a concise evidence summary with clickable canonical paths.
- Keep comparisons side by side and repeat material interpretation limits beside the output.

Final review fails if any requested item is absent, a validation fails, the displayed output is stale, comparison geometry is unmatched without explanation, or a required limitation is missing.

Do not automatically spawn a separate reviewer. The executing agent performs this gate unless the user explicitly requests independent review.

## Step 6: Sync or draft the Todoist completion record

Only mutate Todoist when the user explicitly requested completion/closure or separately approves the status change.

Before closing, add or prepare a completion note containing:

```text
Outcome: complete | review-ready | partial | blocked | not-started
Delivered: exact canonical outputs
Validation: tests, checks, logs, or scheduler evidence
Final review: artifact inspected and result
Limitations: remaining scientific or service boundaries
Remaining work: dependent or deliberately deferred tasks
```

If a connector is unavailable, return the exact note for manual posting and say `Todoist not synchronized`. Never imply a comment, move, or closure occurred without connector evidence.

## Step 7: Report

Lead with the outcome. Separate completed tasks from partial, blocked, deferred, and unverified tasks. Include exact paths and the restart point for anything unfinished.

For a comparison, use this structure:

| Evidence | Item A | Item B |
|---|---|---|
| Definition | matched definition | matched definition |
| Result | direct result | direct result |
| Validation | native evidence | native evidence |
| Limitation | item-specific boundary | item-specific boundary |

## Examples

- `Complete Todoist task 123`: recover the contract, execute natively, validate outputs, review the final artifact, then close only if the request authorized closure.
- `Compare 8080 and 5095 and finish the card`: display the two profiles side by side with matched definitions; do not add transition or sensitivity analyses; review the rendered comparison before closure.
- `Which delegated Todoist jobs are finished? Close the completed ones`: inspect current native artifacts, close only tasks whose own contracts pass, and leave blocked or partial jobs explicit.

## Anti-patterns

- Do not call a delegated or submitted task complete merely because work started.
- Do not treat agent prose as evidence when canonical files, logs, or service responses can be inspected.
- Do not silently analyze different universes under the same comparison label.
- Do not turn a direct comparison into a sensitivity or transition study.
- Do not create a gallery full of task-management cards when the user requested figure review only.
- Do not close umbrella tasks while required child deliverables remain unless the user explicitly accepts that boundary.
- Do not report Todoist synchronization without connector evidence.

## Pre-delivery checklist

- [ ] Task contract reflects the latest user corrections.
- [ ] Every requested output exists at the reported canonical path.
- [ ] Native validation, tests, logs, checksums, or scheduler evidence were checked.
- [ ] Every comparison is visibly side by side with matched definitions.
- [ ] No unauthorized sensitivity, transition, gain/loss, or counterfactual analysis was added.
- [ ] The final rendered or canonical artifact was inspected.
- [ ] Counts and claims reconcile to source evidence.
- [ ] Limitations and remaining dependencies are explicit.
- [ ] Todoist mutation is either verified or labeled unsynchronized.
- [ ] No task is called complete while required work remains.
