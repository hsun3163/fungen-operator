# Ordered evidence tests

Apply these acceptance tests in order of strength. A failed or blocked test makes the affected claim unverified; report the produced record or the blocker rather than replacing the test with prose.

## 1. Replay test

**Procedure:** Give a competent stranger the initial state, immutable commits, execution-produced run records, and decision log, but no transcript or agent context. Have the stranger follow only those records to reconstruct the final state.

**Pass:** The same process and a functionally equivalent result at the declared criterion are reached without questions.

## 2. Boundary test

**Procedure:** Compare every command in the independent command log that wrote inside the tracked tree, declared environment, or run state with the commit, run record, or handoff intervention that records it. Trace each claim to a documented-path record and inspect external references.

**Pass:** Every write has exactly the required recorded action, every verification claim cites execution evidence rather than exploration, and every outside reference is a declared external requirement.

## 3. Clean-start test

**Procedure:** Start from a fresh project copy and fresh environment, execute the documented environment build, then run the documented smoke command through the canonical route.

**Pass:** Setup completes and the smoke assertions pass with execution-produced records.

## 4. Diff test

**Procedure:** Compare a fresh copy plus declared exclusions with the validated system and inspect version status.

**Pass:** Every load-bearing artifact is visible in version control; only declared data, credentials, services, and hardware remain external.

## 5. Command-identity test

**Procedure:** Compare the exact command and configuration recorded by the validated execution with the runbook commands.

**Pass:** The documented command is the command that produced the cited validation record.

## 6. Resume test

**Procedure:** When interruption cost matters, interrupt a smoke or bounded representative run after at least one unit completes, then rerun the documented resume command.

**Pass:** It finishes without recomputing completed units, corrupting state, or duplicating output or effects.

## 7. Failure-legibility test

**Procedure:** Send a checked-in malformed or invalid real-shaped input through the canonical route.

**Pass:** The error or declared log names the failing step and input and leaves the run state diagnosable.

## 8. Orphan and path test

**Procedure:** Inspect tracked and untracked project files and search all project references for disposable, home, or user-specific paths outside the separated site-configuration layer.

**Pass:** Every file has a clear tracked or declared generated role, and no forbidden path reference remains.

## 9. Handoff test

**Procedure:** Give only the project artifacts to a competent colleague and ask how to run it, what it requires, where outputs and records go, and what remains fragile.

**Pass:** The colleague answers within minutes from the runbook, declarations, history, run records, decision log, and current handoff.
