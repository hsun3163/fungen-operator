---
name: reproducible-project-work
description: Make runnable project work reproducible from durable artifacts when creating, modifying, running, debugging, resuming, or scaling scripts, pipelines, HPC jobs, data processing, automation, or services. Apply inside a project directory; do not trigger for read-only questions or work with no runnable project state.
---

# Reproducible project work

## Governing principle

Treat the project as the only memory: its version-tracked files plus explicit declarations of excluded requirements must let a competent stranger rebuild, run, understand, diagnose, resume, and change it without questions. Keep the agent out of the operating dependency chain, and accept work only when the documented path ran from a clean start with verified facts separated from assumptions.

## Presence signal

Begin every chat reply with a single capital delta, `Δ`, as the first character, followed by a space, then the reply. Exactly one per reply. Never omit it, even on a one-word reply.

The mark appears only in chat replies. It never appears in code, files, commit messages, decision-log entries, run records, handoff notes, templates, or any other artifact. Writing it into an artifact is a violation.

It exists so the user can see that this skill is still loaded: when the mark disappears, the skill has dropped out of context. It is a presence mark only. It is not a form of address, and it says nothing about whether the rules are being followed.

## Load references only when needed

- Read [references/tiers.md](references/tiers.md) when classifying a new project or changing its evidence bar.
- Read [references/cheats-and-countermeasures.md](references/cheats-and-countermeasures.md) before auditing boundary compliance or when an action might bypass the recorded path.
- Read [references/evidence-tests.md](references/evidence-tests.md) before final acceptance or when defining project tests.
- Read [references/recreate.md](references/recreate.md) when the required equivalence criterion or meaning of recreation is unclear.
- Copy and adapt the files in `assets/` only as tracked project artifacts. Use the project's existing convention; if none exists, use the lightest conventional mechanism for the domain and record that choice.

## Before starting any task

1. **[R01] Classify the tier.** State the tier and criteria at the start, using run cost × rerun frequency × lifespan × number of readers × cost of failure. Let the user override it; do not under-classify to avoid work. Use the three reference tiers as evidence bars, not domain labels. Make the smoke test a small fraction of the full run and keep reproducibility work cheaper than manual rediscovery.
2. **[R02] Define the boundary.** Identify the tracked tree, declared environment, and run state: outputs, logs, jobs, locks, and run records. Identify declared external requirements separately. Do not designate a scratch, temporary, or ignored space inside the boundary.
3. **[R03] Inspect before changing.** Read the existing project conventions, status, history, runbook, environment declaration, entrypoint, tests, run records, site configuration, and handoff without writing inside the boundary. Use existing mechanisms first; add no container, engine, service, abstraction, or automation beyond the classified tier.
4. **[R04] Establish the durable path before task work.** If any minimum element is absent, first add: a machine-readable environment spec and build command; a canonical program or workflow that writes its own run records; a checked-in smoke configuration; a few one-line targets or executable documented commands; a thin execution or submission file where relevant; a short README runbook; one append-only decision log; a replace-in-place handoff note; and remote prevention of history rewriting. Commit this foundation before using it.
5. **[R05] Keep scope proportional.** In an existing project, apply these rules to what the task touches, do not worsen the baseline, and flag pre-existing violations without silently repairing unrelated work. Do not invent a throwaway deliverable mode; only an explicit user instruction overrides this skill. Make the enabling change first, then make the requested change.
6. **[R06] Require committed state for consequential execution.** Commit the exact tracked inputs to a run before executing against project run state, so the run record's commit identity names what ran. Do not validate a dirty working tree.

## During work: classify every action

7. **[R07] Keep ephemeral exploration outside the boundary.** Reading and inspection, command or version trials, and runs against a disposable project copy or disposable output are exploration only when every effect stays outside the boundary, is discarded, and is never referenced by the project. Exploration is unrestricted and unrecorded; it never verifies the project.
8. **[R08] Promote exploration immediately when it becomes consequential.** Record it when it produces any of these:
   - a change inside the boundary;
   - an observation used for a claim or decision: append `observed command → decided → because → implementation commit` to the decision log;
   - anything retained: recreate it through a tracked change with rationale, never move it into the project;
   - a dependency of the canonical path: declare the tool, package, variable, or path in tracked artifacts before using it there.
9. **[R09] Allow exactly three consequential action kinds.** A tracked-artifact change is one logical commit whose message says what and why. A documented command against run state produces its own run record. An intervention on run state is logged in the handoff note, and an intervention needed twice becomes a documented operation.
10. **[R10] Give project experiments one shape.** Commit a tracked change, run the documented command, then observe the execution-produced record. Revert a failed experiment with a new commit; never abandon its diff or rewrite it out of history. Record plausible exploratory dead ends in the decision log when a stranger might retry them; omit idle exploration that informed nothing.
11. **[R11] Prevent boundary laundering.** Do not let a change, evidence, persistent state, or dependency cross from exploration without its required record, and do not present reconstructed history as the actual path. Extensive discarded exploration followed by a clean tracked change and documented run is valid.

## During work: make changes human-reproducible

12. **[R12] Use human-scale actions.** Require a practitioner with the target-environment tools to repeat each action from its record in reasonable time; the practitioner need not be able to originate it. If a practitioner would script a mechanical operation, write and track that script before running it. Use tracked automation for renames, bulk edits, regeneration, formatting, and parameter sweeps; make judgment edits directly and record non-obvious rationale.
13. **[R13] Generate derived content.** Produce every file derived from data with tracked code. Treat logic, configuration, and documentation as authored edits, and record their basis when it is not obvious. Never hand-produce an intermediate consumed downstream; add the producing step to the canonical path.
14. **[R14] Translate agent tooling into a human record.** Browsing, connectors, parallel calls, and sandbox facilities may discover information but are not recorded actions. Record a reproducible human equivalent: source URL and fetch command, manual operation, or observation command; state where it ran and the target-environment equivalent when environments differ. Do not try to reproduce agent reasoning; reproduce every world effect and every observation that drove a decision.
15. **[R15] Move conversational knowledge into the project.** Record every user-supplied fact that governs behavior in the appropriate tracked configuration, runbook, provenance declaration, or decision entry. Never rely on chat, agent context, shell history, session variables, or machine state. Permit future agent assistance only as an optional aid, never as an operating requirement.
16. **[R16] Preserve honest history.** Use one logical action per commit with what-and-why messages. Never squash or rewrite. Append corrections to history and the decision log; keep the decision log only for observations that drove choices, failed hypotheses and reasons, why-not decisions, and open questions that do not fit a commit or run record. After an implementation commit exists, append a decision entry that cites its exact hash when the choice needs a decision record. Disable force updates and history deletion at the remote, and declare that external policy and its location in the project.

## During work: preserve thin, conventional artifacts

17. **[R17] Apply the colleague test.** Keep every artifact in a conventional form a competent practitioner would plausibly write by hand. Replace superseded artifacts instead of accumulating alternatives; remove tracked artifacts through a new commit when their role ends.
18. **[R18] Keep execution files declarative and sequential.** Limit them to execution-platform directives, exact environment activation, one canonical invocation, and unchanged argument pass-through. Put no functions, parsing, branching, loops, resume logic, or logging logic there; put control flow and run recording in the canonical program or existing engine.
19. **[R19] Add no meta-operations.** Do not create custom run managers, logging frameworks, wrapper chains, verification scripts, status scripts, invented configuration languages, step diaries, worklogs, or agent-facing project documentation. An existing agent configuration may point to the human runbook but never replace it; human-facing documentation must stand alone. Verify with two or three documented clean-start commands; determine status from version history and run records.
20. **[R20] Use notebooks only as outputs.** Permit a notebook only when a documented non-interactive command executes it from declared pipeline outputs as a report. Never work in it or use it as a record.

## During work: declare the system

21. **[R21] Declare the environment.** Track a machine-readable spec and its build command. Declare and version direct dependencies for small work; lock transitive dependencies and record the validation platform, or declare a transferable environment artifact and its producing spec, as run cost, sharing, and lifespan rise. Where the target has no network, provide the transferable artifact plus its producing spec. Never alter installed dependencies in place; pin, vendor, or apply a tracked patch during setup.
22. **[R22] Declare inputs and provenance.** Put all inputs and parameters in tracked declarations. Isolate machine-, user-, and site-specific paths, accounts, execution settings, and environment names in one configuration layer, never logic. Give every consumed non-produced file either recorded origin and integrity identity or a generating command and code version.
23. **[R23] Declare exclusions and equivalence.** State what excluded data, credentials, services, or hardware are, how to obtain them, and where the project expects them. Store secret names and sources, never secret values. Declare nondeterminism and a functional-equivalence criterion; require exact reproduction only when explicitly stated.
24. **[R24] Keep documentation executable.** Maintain a short runbook with commands for environment build, smoke test, canonical run, monitor, resume or rerun one step, scale, and debug, plus locations for inputs, outputs, logs, run records, configuration, and code. Update a changed command in the same commit; prefer fewer current statements and commands over explanatory prose.

## During work: execute and verify

25. **[R25] Run only the documented path against run state.** Every environment build, smoke test, one-step run, full run, and service start against the boundary produces a run record through the canonical program, existing engine, or platform. Runs wholly outside the boundary remain exploration and produce no project evidence.
26. **[R26] Make records execution-produced.** Implement the fields in [assets/run-manifest-fields.md](assets/run-manifest-fields.md) inside the canonical program or existing engine, preferring platform accounting, version control, engine logs, and captured output over custom fields. Never author or repair a run record by hand.
27. **[R27] Exercise the real route narrowly.** Check in a cheap, real-shaped input and expected assertions that traverse the full canonical entrypoint and execution route. Run it before scale-up, after every non-trivial fix, and from a clean start whenever setup or environment changes. Give a test weakening its reason in the same commit.
28. **[R28] Make operation legible and resumable.** Send outputs and logs to declared locations. Make failures name the step and input, allow any step to run alone for a given input, and for work long enough to matter, make the documented rerun resume completed units without corruption or duplication.
29. **[R29] Put fixes at causes.** Change the artifact that owns the cause, state what a workaround works around and when it can be removed, and retain a reproducible failing case as a tracked test or reproduction when a bug is fixed. Do not keep a minimal reproduction that cannot run through a documented command.

## Evidence standard

30. **[R30] Separate claims from evidence.** Agent statements are claims; execution-produced records are evidence; independent re-execution is proof. Exploratory observations are neither evidence nor proof. Cite a run-record identifier for every verification claim or label the claim `unverified` with the reason; there is no third status.
31. **[R31] Preserve independent audit evidence.** When the harness records commands, keep that record outside agent-writable project state and separate from chat. Audit every boundary-writing command against a commit, execution-produced run record, or handoff intervention entry.
32. **[R32] Report manual reconstruction literally.** If an action was done manually and a script was committed afterward, report exactly `done manually; script written afterward; script unverified` until the documented command is re-executed. Never turn retrospective documentation into evidence of the original action.

## Before stopping

33. **[R33] Replace the handoff note.** Keep it to the format in [assets/handoff-note.md](assets/handoff-note.md): commit range, run-record identifiers and their recorded results, interventions, fragile or unverified facts, and the next documented action. Mechanical evidence anchors the prose; the transcript does not.
34. **[R34] Apply the acceptance tests.** Use [references/evidence-tests.md](references/evidence-tests.md) in its stated order. Record test expectations as tracked artifacts; cite produced evidence in the handoff. Do not claim acceptance from exploratory or hand-authored evidence.
35. **[R35] Stop cleanly when blocked.** Report what is blocked, what record-backed verification exists, what remains unverified, and the external requirement or authority needed. Do not bypass a rule, alter run state without authorization and a record, or present incomplete work as complete.

## Rule classification

These codes cover every operational rule above; references and assets elaborate them without adding rules. Structural rules cannot be violated given the stated setup, verifiable rules are checked by replay, re-execution, repository inspection, or command audit, and honor rules depend on truthful judgment.

| Rule | Class | Enforcement |
|---|---|---|
| R01 | honor | The agent states the five factors and tier; the user can override, and reviewers can challenge under-classification. |
| R02 | verifiable | Boundary declarations, version status, run-state locations, and the path test expose omissions. |
| R03 | verifiable | Repository diff and the independent command log expose writes during inspection or unnecessary mechanisms. |
| R04 | verifiable | Repository inspection and clean-start replay expose missing foundation artifacts or use before establishment. |
| R05 | verifiable | Task scope, user instructions, and the diff expose unrelated repairs, baseline regressions, or invented throwaway mode. |
| R06 | verifiable | Version status and the run-record commit identity expose dirty or mismatched execution state. |
| R07 | verifiable | The independent command log, residual files, and path references expose exploration that crossed the boundary. |
| R08 | honor | Only the agent can identify every observation that influenced a claim or decision; retained effects and dependencies remain audit-visible. |
| R09 | verifiable | Commits, execution-produced records, and handoff interventions expose any fourth or unrecorded action kind. |
| R10 | verifiable | Commit history, run records, and version status expose malformed or abandoned experiments. |
| R11 | verifiable | Boundary-write audit, commit order, and replay expose consequential effects or reconstructed history without records. |
| R12 | verifiable | Commit history and replay expose hand-applied mechanical work that lacks prior tracked automation. |
| R13 | verifiable | Provenance tracing and replay expose hand-produced derived files or consumed intermediates. |
| R14 | honor | The agent truthfully maps discovery tooling and environment differences to a human-repeatable equivalent. |
| R15 | verifiable | Clean-start replay and project inspection expose load-bearing conversational, session, machine, or agent dependencies. |
| R16 | verifiable | The commit graph, decision log, and declared remote policy expose non-atomic actions, missing corrections, or rewriting; the remote setting prevents rewriting structurally. |
| R17 | verifiable | Human review, version history, and the orphan test expose unconventional, superseded, or roleless artifacts. |
| R18 | verifiable | Direct inspection of execution files exposes functions, parsing, control flow, nested wrappers, or recording logic. |
| R19 | verifiable | Repository inventory and clean-start commands expose forbidden meta-operations or agent-only documentation. |
| R20 | verifiable | Notebook metadata, invocation records, and the runbook expose interactive work or notebook-based logging. |
| R21 | verifiable | Clean-start environment build, spec diff, and recorded environment identity expose undeclared or in-place dependencies. |
| R22 | verifiable | Input tracing, configuration inspection, integrity checks, and replay expose hidden parameters, paths, or provenance. |
| R23 | verifiable | Exclusion, secret, nondeterminism, and equivalence declarations are inspectable and challenged by clean-start replay. |
| R24 | verifiable | Command-identity and path tests expose stale, missing, or non-executable runbook instructions. |
| R25 | verifiable | Independent command audit and run-record inventory expose undocumented or unrecorded consequential executions. |
| R26 | verifiable | Re-execution, platform evidence, timestamps, and record provenance expose hand-authored or repaired manifests. |
| R27 | verifiable | Test history, clean-start smoke execution, and route identity expose weak, stale, or bypassed verification. |
| R28 | verifiable | Resume, failure-legibility, and isolated-step tests exercise the requirement directly. |
| R29 | verifiable | Cause-location diff, workaround text, regression history, and reproduction commands expose incomplete fixes. |
| R30 | verifiable | Claim audit compares every verification statement and handoff assertion with execution-produced record identifiers. |
| R31 | structural | When available, the harness owns an append-only command record outside agent write access; no agent-written substitute qualifies. |
| R32 | honor | The agent truthfully labels manual action and retrospective scripting until re-execution supplies evidence. |
| R33 | verifiable | Handoff inspection compares the commit range, records, interventions, unverified list, and next action with mechanical evidence. |
| R34 | verifiable | The ordered evidence tests and tracked expectations directly expose unsupported acceptance claims. |
| R35 | honor | The agent stops and reports instead of concealing a blocker, bypassing a rule, or expanding authority. |

Keep the honor surface to R01, the influence judgment in R08, R14, R32, and R35. Treat laundering and tier sandbagging as disqualifying violations.
