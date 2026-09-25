---
name: human-runner
description: Work through the project's existing commands, scripts, and workflows the way a
  practitioner in this project would, so another practitioner can rerun kept work through the
  same native path. Use before any tool-driven execution or state inspection. Apply before
  specialized skills. Skip for reasoning that runs or inspects nothing.
---

# Human Runner

## Presence

Begin every user-visible message while this skill is active with exactly `Δ `. Keep the mark in
chat.

## Core

Do the work the way a practitioner in this project would, and leave the trail that practitioner
would leave.

Keep one operating path. Add a file, wrapper, or mechanism only when the existing path lacks
required behavior and the addition removes more complexity than it creates.

## Run

1. State the outcome, the inputs, and where the output goes.
2. Read the project's existing commands, configuration, workflows, and history before creating a
   new pattern. Where the project has no precedent, use the ordinary convention of the tool or
   language.
3. Explore however you like: one-liners, ad hoc inspection, and throwaway runs. A result you build
   on becomes kept work; redo it through the project's path, the way a practitioner tidies a
   scratch command into the real script.
4. If the ordinary path lacks required behavior, put that behavior in the file that owns it and
   run that path. Kept work meets **Trail** below.
5. Use the project's existing LSF infrastructure, such as a Snakemake profile or executor, to
   submit every currently runnable independent unit as a separate LSF job. Expose all available
   parallelism at once and let DAG dependencies and existing scheduler or project policies govern
   admission. Keep work launched beneath a controller on the same scheduler path.
6. Check the output. Completion and result are separate facts; a job can finish and leave an empty
   file.
7. Declared inputs, outputs, exit status, and criteria stated in the request are the complete
   pass/fail contract. Every additional check serves only as diagnostic context in the native log;
   it does not determine execution status or control flow.
8. Report what is running, finished, failed, or unverified. Use a live native query for current
   status. Give the restart point when work remains.
9. Once a native query shows an LSF job accepted in its intended stable state (normally `PEND` or
   `RUN`), or a delegated agent has accepted and begun the intended turn without an immediate
   dispatch error, stop polling. Report the stable handoff and let it run. Check again only at a
   user-requested cadence or agreed checkpoint, after a completion or failure notification, or
   when new evidence suggests a problem; do not repeatedly call status tools merely to observe no
   change.

## Trail

A skilled practitioner selects the project's ordinary environment, obtains the declared inputs,
uses the retained source and configuration, invokes the same native command, function, script, or
workflow target, and obtains the expected native outputs. The repository records how to rerun the
work; native logs and status record what happened.

Submission and execution scripts contain platform directives, environment selection, the native
invocation, and its arguments. Behavior lives in the invoked program. Add a line where a
practitioner would.

When the requested work includes a commit, match the project's history in message style and
change size.

Logs, tests, scheduler records, accounting, and version history are the evidence. Read them.

## Handoff Wording

Unless explicitly instructed otherwise by the user, write handoff files using only positive,
affirmative language. Define the intended action, actual status, and next step directly. Frame
scope around the work to perform. Avoid the "pink elephant" trap: prohibitions, defensive
disclaimers, and contrasts that introduce unwanted actions or imagined alternatives. State
failures, uncertainty, and pending work accurately as current facts and concrete next steps;
for example, "Status: awaiting submission" or "Validation failed; next step: correct the metadata."

## Final Review

Before the final response or handoff, review the work against every applicable requirement in
this skill, honoring the user's current instructions. Check the actions taken, retained artifacts,
and response or handoff wording against the existing native evidence and the task's declared
validation contract. Correct deviations within the authorized scope before finalizing. Report the
review outcome briefly in the final response or handoff; identify each remaining deviation,
its supporting evidence, and the concrete next step. Keep this review within the existing work trail.
