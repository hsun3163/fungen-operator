# Surgical edit of Prompt 1: simplicity first

Apply only the replacements below to Prompt 1. Leave all omitted text unchanged.

The edit preserves the production/adoption boundary, chat-only presence mark, thin execution wrappers, free experiments, conditional state-carrying-artifact rule, illustrative archetypes, and human-native templates. It changes clauses that still make reproducibility machinery outrank minimal complexity.

## 1. Add the controlling conflict rule in §1

Insert immediately after:

> The agent minimizes it.

Add:

> This is the controlling priority for every later clause. If compliance with another rule would add more files, steps, dependencies, mechanisms, ceremony, or concepts for a practitioner to understand than the complexity it removes, this principle wins. Use an existing practitioner-native facility when it supplies the needed fact. If no such facility exists without adding net complexity, do not build one: use less mechanism and report the resulting evidence limit honestly. Reproducibility never justifies net complexity.

Replace the final paragraph of §1 with:

> The acceptance criterion is not merely "it ran." It is: the retained result came from the simplest conventional production path that performs the work; that path ran from a clean declared start through the documented human operation; what was verified is distinguished from what was assumed; and no artifact, step, dependency, mechanism, or departure from convention remains without a reason a practitioner would accept.

## 2. Tighten the production/adoption boundary in §2

Replace the first paragraph of §2 with:

> The **production path** is the complete sequence of operations on which a retained output depends: obtaining or validating the environment, acquiring inputs, every transformation, the retained run, and every state intervention whose effect the output relies on. An operation is on the production path because of its effect, regardless of tool, working directory, stated intent, or output location; unknown load-bearing dependencies count. Every production-path step is repeatable by a practitioner from ordinary durable project artifacts: retained source and configuration, declared inputs and external requirements, the documented human operation, a declared environment, and execution- or platform-produced evidence. These facts may be distributed across the project's existing conventional artifacts. This rule never requires a new recorder, wrapper, manifest format, or documentation layer.

Replace the paragraph beginning “Everything else is free” with:

> Everything else is free. Experiments, tests, trial runs, drafts, failed attempts, and exploration need no record: any environment, any command, any location, a dirty working tree, and discarded outputs. They may happen anywhere, including inside the project directory, and need no isolation or cleanup record. Effects on shared systems are also experimental unless a retained output relies on them. Testing an uncommitted change is normal work, not a violation.

Replace the paragraph beginning “The line between the two is adoption” with:

> The line between the two is **adoption**. An experimental result, artifact, value, dependency, observation, or environment effect is adopted when a retained output depends on it, when it fixes an expectation or parameter used by the production path, or when it is presented as the delivered output or as evidence. Adoption requires promotion through ordinary retained project artifacts and regeneration by a production run. Copying, retyping, paraphrasing, converting, moving, summarizing, or fixing a value from an experimental artifact is adoption, not authored reconstruction.

Replace the decision paragraph in §2 with:

> When an experiment determines a production-path decision — a parameter, version, threshold, expected value, tolerance, dependency, or design choice — record one decision entry before implementing the choice: observation source and immutable identity, time, relevant context, result, decision, and reason. Append the implementation revision afterward without editing the original entry. Choosing among experimental results is itself a decision. Experiments that shaped nothing are not recorded.

Replace the final sentence of §2 with:

> Draft history may be tidied freely until a revision is cited by a production-run record, decision, or handoff; from that moment the cited revision is frozen.

## 3. Narrow the human-action obligations in §3

Replace the first bullet under “Human-reproducible actions” with:

> - Human-scale production operations: preserve a reusable operation when repeating the hand work would take longer than the bounded verification run or when the operation is needed again. A versioned diff is sufficient for a handful of ordinary edits. Mechanical transformations that generate retained outputs are performed through the project's normal retained mechanism; judgment edits remain authored edits, with rationale only when the diff does not explain the choice. Experimental and discarded work is unconstrained.

Replace the agent-tooling bullet with:

> - Agent tooling is for discovery, not production. Browsing, connectors, parallel calls, and sandbox facilities do not become the recorded production operation. If their result becomes load-bearing, record the ordinary practitioner-accessible source or operation and actually repeat that human path before citing it. If no human path exists, declare the dependency or observation nonreproducible and do not cite it as verification.

Replace the production-run-record bullet with:

> - Every execution cited as verification leaves execution- or platform-produced evidence. Existing conventional evidence is used first. The evidence and retained project artifacts jointly identify the operation, immutable source revision, resolved environment, configuration, inputs, nonsecret runtime values, time, result status, and retained output location and identity. Secret values are redacted; secret names and declared sources are retained. If these facts are not available without adding a custom mechanism, report the affected claim as unverified rather than building one. Routine reruns of an already documented production path inherit its declared claim and do not require new authored ceremony.

Replace the commit bullet with:

> - A revision cited by a production-run record, decision, or handoff is immutable. Before it is cited, drafts and failed experiments may be edited, discarded, squashed, or reordered freely. Never absorb unrelated user changes merely to obtain an immutable production identity; stop if the load-bearing state cannot be identified without doing so.

Replace the user-knowledge bullet with:

> - Record permitted user-supplied knowledge only when a retained output or production operation depends on it. Put it in the ordinary artifact that owns the behavior. If necessary knowledge cannot be stored, declare it as an external requirement or leave the affected claim unverified.

## 4. Replace the evidence-mechanism bullets in §4

Replace the first two bullets of §4 with:

> - Evidence standard: agent statements are claims; execution- or platform-produced records are evidence; regeneration from a clean declared start with status and checks captured outside the modified component is independent proof. A record emitted only by the modified component is evidence, not independent proof. Experimental runs and observations are never verification evidence.
> - Run evidence is produced by execution, never authored or repaired. Use the project's existing program, engine, platform, version history, captured output, and accounting records. Do not add recording code or a custom manifest solely for this skill. The ordinary records must jointly identify the operation, immutable revision, resolved configuration and environment, input identities, retained output locations and identities, timestamps, and result status. Preserve incomplete or incorrect records and obtain new evidence from a new run.

Replace the claim bullet with:

> - Every factual success statement — including "works," "looks good," "complete," "fixed," and present-tense status — cites evidence that supports exactly that scope or is reported as `unverified` with the reason. A bounded run verifies its route and bounded behavior, not unexecuted production outputs. Present-tense status requires a timestamped live observation.

Replace the test-expectations bullet with:

> - Test expectations, tolerances, and equivalence criteria are retained before the cited run. Creating or weakening a check in the same change as the implementation does not independently validate the affected behavior until a practitioner who did not author the implementation reviews the criterion and the production path is rerun.

Replace the decision/history bullet with:

> - Decision entries are append-only; corrections are new entries. Revisions and execution records become immutable when cited. State whether immutability is enforced by a control outside the writer's authority or is a reviewable policy.

Replace the harness bullet with:

> - An external harness is structural evidence only when it exists, its coverage has been confirmed, and the agent cannot alter its records. Audit effects across every facility the harness covers, not shell commands alone. When no such control exists, proceed under the available verifiable and honor controls and state the assurance actually provided; never relabel an absent control as structural.

Replace the tier-override bullet with:

> - Proportional requirements are selected from the observable risk conditions in §9. A user may change scope or authorize effects; a user cannot convert an unsupported claim into a verified claim. Deliberately understating a true risk condition is a violation.

## 5. Preserve §5 but edit the conflicting operational bullets

Replace the submission/execution bullet with:

> - Submission and execution wrappers, when the project convention needs one, remain thin: execution directives, environment selection, one fixed invocation, and optional pass-through. No functions, parsing, orchestration, resume logic, or branching. This constrains the wrapper layer only; it does not prescribe the program's architecture.

Replace the run-recording bullet with:

> - Run recording uses the existing canonical program, engine, or platform when it already provides ordinary execution evidence. Never add a wrapper or recording subsystem for this purpose. If native evidence is insufficient and a new mechanism would add net complexity, retain less evidence and report the limit honestly.

Replace the `verify`/`status` bullet with:

> - No compliance-only verification, status, logging, or monitoring mechanism. Ordinary project tests, diagnostics, monitoring, and logging remain valid. Verification uses the smallest documented human operation that exercises the claim. Historical records establish historical facts; current status comes from a timestamped live observation.

Replace the “Subtraction is part of every task” bullet with:

> - Subtraction is part of every task: remove what the task makes unnecessary. Report the net change in files, production-path steps, dependencies, and runbook length in the final response or an existing handoff. Growth requires a reason a practitioner would accept; the report itself never requires a new project artifact.

Add after the minimality bullet:

> - Templates supplied by this skill are optional starting points, never a required project artifact set. Instantiate one only when the project lacks that role, the current task needs the role, and a practitioner would normally create it.

## 6. Replace §6 with a record hierarchy that does not mandate ceremony

Replace all of §6 with:

> ### 6. The record — no step diary
>
> Do not document the agent's sequence of attempts. Use the project's existing ordinary records. Add one of the supplied templates only when the corresponding human need actually exists.
>
> - **Version history:** the immutable revision a production run cites, with rationale in the ordinary change record when the diff is not self-explanatory. Draft history is free before citation and frozen afterward.
> - **Execution evidence:** records produced by the program, engine, or platform for executions cited as verification. Never backfill or repair them.
> - **Decision record:** use the project's existing decision mechanism. If none exists, create the supplied terse append-only decision log only when a load-bearing experimental observation, why-not decision, open question, or first-occurrence production intervention needs a durable home. Record the observation and decision before implementation; append the implementation identity afterward.
> - **Handoff:** use the project's existing current-status convention. If none exists, create the supplied short mutable handoff only when another practitioner needs continuity. It orients by pointing to immutable evidence; it is never evidence itself and contains no self-referential revision range.
>
> An artifact that carries execution state is a canonical source only when a documented human operation executes it from a clean state in its declared order. Otherwise it may be a generated report but not a hidden operating or evidentiary dependency.
>
> Agent-facing progress or worklog files are scaffolding, not project documentation. Agent configuration may point to human-facing documentation but never replace it. The project must remain operable without an agent.

## 7. Replace §7 entirely

Replace all of §7 with:

> ### 7. Sequencing
>
> Inspect the project's existing path before adding anything. Experiments and ordinary task work may begin immediately and remain free.
>
> Before an execution is used to produce a retained deliverable or cited as verification, establish only the durable path that its claim needs:
>
> 1. an immutable identity for the load-bearing source and configuration;
> 2. declared environment requirements sufficient to rebuild or validate the production environment;
> 3. declared inputs, external requirements, and nonsecret runtime values;
> 4. one ordinary documented human operation;
> 5. a predeclared observable result or equivalence criterion; and
> 6. execution- or platform-produced evidence available from existing project facilities.
>
> Add a project artifact only when one of these facts has no ordinary home and a practitioner would create that artifact for the same task. If native evidence is unavailable without adding net complexity, do not build a recorder: perform the work if authorized, label the affected claim unverified, and state the missing evidence.
>
> Establish the path before adoption, then regenerate the retained output through it. Make the change simple, then make the simple change.

## 8. Replace §8 with scoped engineering requirements

Replace all of §8 with:

> ### 8. Engineering requirements
>
> **Environment.** Declare only the load-bearing environment requirements for the production path using the project's existing convention. Record the resolved production identity. Rebuild rather than adopt experimental environment state. Require an exact resolved environment or transferable artifact only when the reuse, availability, or external-impact conditions in §9 make drift consequential. Never modify a shared production environment in place without a retained declaration of the change.
>
> **Inputs and provenance.** Declare every input, parameter, dependency, and ambient facility on which the retained output depends. Keep site-specific values in the project's existing configuration convention, outside behavior logic. An acquired input has stable origin, identity, access procedure, expected location, compatibility, and retention. A generated input has complete lineage through its generating operation, source revision, environment, and own inputs. Record secret names and sources, never values. Treat human-curated primary inputs as declared inputs with source material, method, author or responsible role, date, and review basis.
>
> **Verification.** Before an execution is cited, retain the observable claim and criterion. Use the smallest input that exercises the same behavior and ordinary execution route; a bounded run may reduce workload but not substitute different behavior. Regenerate from a clean declared start when environment or setup changes. Record who or what executed the verification and the start state. A check authored or weakened with the implementation requires independent review before it verifies that behavior.
>
> **Diagnosis.** Read-only diagnosis against real state is allowed. When an observation shapes a production decision, record its source, time, operation, context, and result before implementation. A state-changing diagnosis is a production intervention: obtain authority, identify the exact target and intended effect, and retain contemporaneous execution- or platform-produced evidence. Record the first occurrence in the append-only decision record; repetition determines whether it becomes a documented ordinary operation.
>
> **Observability and recovery.** Use existing output, log, and status facilities. Add no parallel mechanism. Require a bounded recovery test only when interruption would repeat more work than the bounded verification workload. Require idempotence or recovery evidence only when repetition can duplicate, overwrite, or externally expose effects. Failures identify the smallest ordinary recovery unit and relevant input when the existing platform supports that context.
>
> **Fixes and knowledge.** Fix the owning cause rather than adding a workaround layer. A root-cause claim ties the recorded failure to fail-before/pass-after evidence and states how any reduced reproduction matches the original signature. Keep a regression case only when it prevents recurrence and uses the project's normal test convention. A workaround states the condition for removal.
>
> **Documentation.** Document only supported operations required to use or change the touched behavior. Use executable commands where the domain has commands and ordinary procedures where it does not. Mark unsupported operations rather than inventing them. Update an existing runbook in the same change that alters an operation; create one from the supplied template only when the task needs a durable operating interface and none exists.

## 9. Replace §9 with observable proportionality conditions

Replace all of §9 with:

> ### 9. Proportionality
>
> The governing principle and adoption rule are constant. Additional engineering and evidence obligations are driven by these yes/no conditions, not by domain or arithmetic:
>
> 1. **Interruption:** would interruption repeat more work than the bounded verification workload? If yes, define and test recovery on a bounded run.
> 2. **Repetition hazard:** can rerunning duplicate, overwrite, or externally expose effects? If yes, define and test idempotence or recovery before scale.
> 3. **Nondeterminism:** can equivalent runs vary? If yes, fix the repetition count, bounds, and pass rule before the cited run.
> 4. **Reuse:** will the result be reused after the current task or by another practitioner? If yes, retain source, environment, input, and evidence availability for that lifetime.
> 5. **External impact:** can failure materially affect shared state, another person, or an external system? If yes, require independent review of the operation, criterion, and recovery path.
> 6. **Live state:** does the claim concern current operation? If yes, obtain a timestamped live observation.
>
> The reference archetypes — a small standalone program, a shared or costly workflow, and persistent operation — illustrate combinations of these conditions; they do not select requirements.
>
> Use existing project mechanisms first. Do not add a container, engine, automation layer, abstraction, or configuration option solely because an archetype commonly has one. Apply the rules only to the behavior under claim, do not worsen the baseline, and report pre-existing unrelated complexity without silently expanding scope.
>
> If a rule blocks progress, stop only when authority, access, or a required production-path fact is missing. Otherwise proceed with the simplest authorized path and state unsupported claims as unverified.

## 10. Correct the override sentence in §10

Replace:

> There is no throwaway mode: the user overrides the skill by instruction when they want to.

With:

> The user may request exploratory work, reduce scope, or authorize effects. Such an instruction does not make an experimental output a reproduced deliverable and cannot convert an unsupported claim into a verified claim.

## 11. Reorder and scope the evidence tests in §11

Replace the introductory sentence and numbered list in §11 with:

> Include these as the skill's acceptance tests. Apply the complexity gate before and after every applicable evidence test: no test or evidence mechanism may add more complexity than it removes.
>
> 1. **Complexity gate:** every new file, production step, dependency, mechanism, option, intermediate, and departure from convention has a stated reason a practitioner accepts. No duplicated mechanism remains. The runbook grows only when capability grows. Remove a part whose only reason is agent history or compliance ceremony.
> 2. **Regeneration test:** an independent executor starts from the retained revision and declared environment and follows the ordinary production path to regenerate each delivered output to the predeclared criterion. Record the executor, start state, operation, and result using existing evidence. If existing facilities cannot retain that evidence without net complexity, label independent regeneration unverified rather than adding machinery.
> 3. **Adoption test:** every retained output comes from a production execution whose immutable revision existed before the run. No production-path dependency is untracked or undeclared. Every success claim cites production evidence rather than an experimental run.
> 4. **Clean-start test:** the declared environment and inputs can be obtained or validated, and the documented bounded operation passes from a project state matching the cited revision with no unrecorded load-bearing differences.
> 5. **Diff test:** everything needed to operate the touched behavior is visible in retained project artifacts except declared external requirements. Unrelated user changes were not absorbed.
> 6. **Operation-identity test:** the ordinary documented operation is the operation that produced the cited evidence, allowing secret redaction and nonsemantic invocation differences.
> 7. **Recovery test:** apply only when the interruption condition in §9 is true. Interrupt a bounded run after a completed unit and repeat the documented operation; it finishes without corrupting state, duplicating effects, or repeating completed work beyond the declared recovery unit.
> 8. **Repetition-safety test:** apply only when the repetition-hazard condition is true. Repeat the bounded operation and verify the predeclared idempotence or recovery criterion.
> 9. **Failure-legibility test:** when the touched behavior accepts distinguishable inputs or units, send a bounded invalid input through the ordinary route and verify that existing evidence identifies the relevant failure context.
> 10. **Orphan and path test:** every retained or declared generated artifact has a practitioner-recognizable role; no retained production dependency points to an undeclared user-, session-, or temporary-state value.
> 11. **Handoff test:** apply only when continuity beyond the current task is needed. A practitioner can find the operating path, requirements, evidence, fragile facts, and next action from ordinary artifacts without the transcript.

## 12. Edit the skill-format resource lists in §12

Replace the references bullet with:

> - References, loaded on demand: the cheat-and-countermeasure list; an illustrative archetype table keyed to the yes/no risk conditions rather than tiers; the evidence tests in full; and the definition of "recreate."

Replace the assets bullet with:

> - Assets are optional human-native starting points only: a thin submission/execution wrapper skeleton; a short runbook skeleton; the corrected decision-entry format; and the mutable handoff format. Do not include an environment checklist or custom run-manifest schema. Put the short environment and jointly-identifiable evidence requirements in `SKILL.md`.

In the body-structure bullet, replace:

> tier classification

With:

> the six yes/no proportionality conditions

## 13. Strengthen the conflict rule in §13

Replace:

> Any mechanism added for reproducibility's or assurance's sake that a practitioner would not have added on their own. Where the skill's own rules would add parts to a project, the rule loses.

With:

> Any mechanism, artifact, step, dependency, or ceremony added solely for reproducibility, assurance, or compliance when a practitioner would not have added it to perform or operate the work. The governing principle overrides every conflicting clause: use an existing native facility, reduce the claim, or report `unverified`; never add net complexity to satisfy the skill.

Add:

> - Any universal project-artifact bundle. Supplied templates are optional and instantiated only when the touched behavior needs the role and the project lacks it.

## 14. Tighten the output self-audit in §14

Replace the minimality-test sentence in the final bullet with:

> Apply the minimality test to the skill itself before every other self-audit: list every rule whose compliance can add a file, production step, dependency, mechanism, option, review, or ceremony to a project. For each, name its exact observable trigger and the greater complexity it removes. Drop or narrow every rule that lacks both. Then audit every remaining template as optional: show the concrete project condition that justifies instantiating it. Fix all failures before presenting the final version and list the surgical changes.

## Resulting priority order

After these edits, Prompt 1 has this controlling order:

1. Minimize what a practitioner must understand.
2. Use the simplest direct conventional production path.
3. Keep experiments free.
4. Prevent adoption without promotion and regeneration.
5. Use reproducibility as evidence only when existing ordinary facilities provide it without net complexity.
6. Report unsupported claims honestly instead of adding assurance machinery.

