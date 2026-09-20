# Cheats and countermeasures

Load this list before a boundary audit or whenever an action might bypass the recorded path. Each item elaborates the cited rules in `SKILL.md`.

| Cheat | Countermeasure | Audit evidence | Rules |
|---|---|---|---|
| Launder a consequential effect from exploration into the project, or reconstruct a cleaner history and present it as actual | Recreate retained content through a reasoned tracked change; declare dependencies before use; preserve actual commits and execution records | Compare every boundary write in the independent command log with commits, run records, and intervention entries | R08–R11, R31 |
| Modify or patch the project's installed environment outside its spec | Explore in a separate disposable environment; pin, vendor, or apply the patch through tracked setup | Clean-start environment build, spec diff, and environment identity in the run record | R08, R15, R21 |
| Export a load-bearing variable or activate an undeclared site facility | Put it in the declared environment or separated site configuration before use | Clean-start and path tests; run-record configuration and environment identities | R08, R15, R21–R23 |
| Run an undocumented command against project run state and call it validation | Add the command to the runbook or canonical operation first; execute it only after commit | Command-identity and boundary tests | R09, R24–R26, R30 |
| Create an ignored, temporary, scratch, or unclear file inside the boundary | Give it a tracked role or create it outside the boundary and discard it | Version status plus orphan and path test | R02, R07–R09, R17 |
| Hand-produce an intermediate later consumed by the system | Add a tracked generating step and regenerate through the documented path | Diff, replay, and input-provenance audit | R12–R13, R22 |
| Adopt a throwaway environment, file, parameter, or path directly | Discard it; express the discovered requirement in a tracked declaration and verify it through a documented run | Clean-start replay and decision entry for the choice | R08, R10, R21–R23 |
| Intervene on a job, output, or lock without a record | Put the exact intervention and target in the current handoff; document it as an operation after the second need | Independent command log versus handoff and run-state history | R09, R31, R33 |
| Author, edit, backfill, or repair a run record | Make the canonical program, existing engine, or platform produce it; rerun to obtain evidence | Re-execution, platform accounting, immutable captured output | R25–R26, R30 |
| Treat exploratory success as proof that a fix works | Commit the discovered fix, run the documented route, cite the produced record | Commit-to-record identity and command-identity test | R07–R10, R30 |
| Do work manually, then commit a script as though it produced the result | Report exactly `done manually; script written afterward; script unverified` until re-executed | Command log, timestamps, commit order, and R32 disclosure | R32 |
| Weaken a test silently to make a run pass | Put the reason in the same commit and preserve the intended behavior as a tracked expectation | Test-history diff and replay | R27 |
| Squash, amend, force-update, delete, or otherwise rewrite action history | Append corrective and revert commits; disable rewrite at the remote | Remote policy and commit graph | R10, R16 |
| Replace mechanical evidence with a prose status, diary, notebook, or reconstructed report | Keep status in version history and run records; use the handoff only to point to them | Handoff and command-identity tests | R19–R20, R30, R33 |
| Hide agent-only knowledge in chat, context, shell history, or configured machine state | Declare every governing fact in tracked project artifacts | Clean-start, diff, and handoff tests | R15, R21–R24 |
| Build custom wrappers, status tools, verifiers, logging systems, or configuration layers to simulate rigor | Use the canonical program, platform evidence, and a few documented commands | Human-native review and repository diff | R17–R20, R24–R26 |
| Keep superseded alternatives or failed working-tree experiments | Remove superseded files in a tracked commit; preserve failed experiments through revert commits or decision entries | History, version status, and orphan test | R10, R16–R17 |
| Under-classify the tier to avoid environment, evidence, resume, or service obligations | State the five classification factors and accept user override | Compare stated factors with actual operating context | R01 |
| Bypass a blocked scheduler, service, data source, credential, hardware requirement, or authority | Stop with record-backed facts, unverified facts, and the exact external need | Handoff, command log, and claim audit | R23, R30, R35 |

The disqualifying offense is laundering because it hides the dependency the reconstruction omitted. Discarded exploration followed by one clean tracked change and one documented execution is the intended path, not laundering.
