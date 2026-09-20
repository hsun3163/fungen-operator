Verdict: fail. An agent can obey the text while defining away inconvenient state, laundering exploratory influence, generating its own “evidence,” weakening checks, and relying on an audit harness that may not exist. The skill has no unconditional structural control.

The deepest defect is categorical: prose written for the agent cannot make that same agent unable to cheat. Structural assurance requires capture or immutability enforced outside the agent’s write authority. The current skill acknowledges that only conditionally, then classifies most self-reported behavior as verifiable.

I did not overwrite the directory: it is not under version control, so doing so would destroy the original being audited. The complete replacement is included below.

## 1. Ways to comply while leaving an unrecreatable project

| # | Loophole | Sentence that permits it | Fix |
|---|---|---|---|
| 1 | Define the project narrowly so shared environments, remote systems, persistent jobs, caches, or account state disappear from scope. | “Identify the tracked tree, declared environment, and run state” in [R02](/hpc/users/sunh14/reproducible-project-work/SKILL.md:31). | Define consequential state by actual effects, not an agent-declared path boundary. Unknown surfaces count as consequential. |
| 2 | Declare any missing dependency an “excluded requirement.” | “version-tracked files plus explicit declarations of excluded requirements” in [the governing principle](/hpc/users/sunh14/reproducible-project-work/SKILL.md:10). | Permit exclusion only with stable identity, acquisition/access procedure, expected location, compatibility requirements, and retention sufficient for the claim. |
| 3 | Keep run records outside the “only memory,” where they can expire or be inaccessible. | “Treat the project as the only memory: its version-tracked files…” conflicts with external records throughout. | Define durable project evidence to include declared external records only when their immutable identity, locator, access procedure, and retention are recorded. |
| 4 | Under-classify because the five factors have no scales or thresholds. Multiplication also lets one nominal zero cancel catastrophic failure cost. | “run cost × rerun frequency × lifespan × number of readers × cost of failure” in [R01](/hpc/users/sunh14/reproducible-project-work/SKILL.md:30). | Remove tiers. Apply a small invariant baseline, then add requirements from explicit yes/no risk conditions. |
| 5 | Let the user waive the evidence bar or the entire skill, then report success. | “Let the user override it” and “only an explicit user instruction overrides this skill” in [R01/R05](/hpc/users/sunh14/reproducible-project-work/SKILL.md:30). | A user may change scope or authorize effects, but cannot turn unsupported claims into verified claims. Waived durability makes the result exploratory or unverified. |
| 6 | Use Tier 1 declarations that cannot rebuild after dependency drift. | “Direct dependencies and versions are sufficient” in [the environment checklist](/hpc/users/sunh14/reproducible-project-work/assets/environment-spec-checklist.md:19). | Require either an exact resolved identity or an explicit compatibility range plus a fresh rebuild that records the actual resolution. |
| 7 | Install a large compliance foundation without proving that any element works. | “first add” the complete artifact bundle and “Commit this foundation before using it” in [R04](/hpc/users/sunh14/reproducible-project-work/SKILL.md:33). | Establish only facts needed for the touched claim. Author them before execution; verify them through the ordinary project path afterward. |
| 8 | Bootstrap a run recorder that cannot itself be tested before its first committed use. | R04 requires “a canonical program or workflow that writes its own run records” before use. | Use ordinary execution or platform evidence already available. Do not require every project to implement its own recorder. |
| 9 | Commit unrelated user changes merely to obtain a clean revision. | “Commit the exact tracked inputs” and “Do not validate a dirty working tree” in [R06](/hpc/users/sunh14/reproducible-project-work/SKILL.md:35). | Preserve unowned changes. Require an immutable identity only for load-bearing state actually used by execution. Stop if that cannot be obtained without absorbing user work. |
| 10 | Treat a local mutable or unpublished revision as durable history. | R06 requires a commit identity but not durable retention or external immutability. | Require a stable retained revision. Once evidence references it, prohibit rewriting or deletion; say when this is only policy rather than enforced. |
| 11 | Record a source revision while omitting external code, mutable references, runtime parameters, or ambient state. | “the run record’s commit identity names what ran” in R06. | Identify source, configuration, resolved environment, external components, inputs, runtime values, and ambient facilities jointly. |
| 12 | Reuse opaque existing machinery that depends on undocumented local knowledge. | “Use existing mechanisms first” in [R03](/hpc/users/sunh14/reproducible-project-work/SKILL.md:32). | Reuse it only after its human path and dependencies pass the same reconstruction test. |
| 13 | Perform arbitrary persistent operations outside the declared boundary as “unrestricted” exploration. | “Exploration is unrestricted and unrecorded” in [R07](/hpc/users/sunh14/reproducible-project-work/SKILL.md:39). | Exploration is ephemeral only when all effects are isolated, removed, and verified not to have touched shared or retained state. Otherwise classify it as consequential. |
| 14 | Claim cleanup without evidence. “Discarded” can mean merely ignored or forgotten. | “is discarded” in R07. | Require pre/post evidence for relevant effect surfaces. Without externally observable cleanup, absence of leakage remains unverified. |
| 15 | Record only a command for an influential observation, omitting source version, environment, input, time, actual result, or durable evidence. | “append `observed command → decided → because → implementation commit`” in [R08](/hpc/users/sunh14/reproducible-project-work/SKILL.md:42). | Record the observation’s source identity, time, context, result identity, decision, and rationale before relying on it. |
| 16 | Write the decision after implementation and fabricate a clean chronology because the template demands an implementation hash. | R08 and [decision template](/hpc/users/sunh14/reproducible-project-work/assets/decision-log-entry.md:9). | Record evidence and decision before implementation. Append the resulting revision reference later without editing the original entry. |
| 17 | Retype or regenerate content from an exploratory artifact and call that “recreation.” | “recreate it through a tracked change … never move it” in [R08](/hpc/users/sunh14/reproducible-project-work/SKILL.md:43). | Retained content must be regenerated from declared inputs by the durable path. Copying, retyping, paraphrasing, or locking observed values is adoption too. |
| 18 | Use an exploratory generator, formatter, converter, model, or library, then omit it because it is not a runtime dependency. | “a dependency of the canonical path” in [R08](/hpc/users/sunh14/reproducible-project-work/SKILL.md:44). | Declare every dependency required to regenerate retained content or reproduce a load-bearing observation—not only runtime dependencies. |
| 19 | Hide external communication, permission changes, remote mutations, consequential reads, or environment changes because they are not one of three allowed kinds. | “Allow exactly three consequential action kinds” in [R09](/hpc/users/sunh14/reproducible-project-work/SKILL.md:45). | Classify by effect. Do not impose a closed action taxonomy. |
| 20 | Record a one-time intervention only in a mutable handoff and erase it at the next replacement. | “logged in the handoff note” in R09 and “Replace the handoff note” in [R33](/hpc/users/sunh14/reproducible-project-work/SKILL.md:87). | Put interventions in execution- or platform-produced append-only evidence. A handoff may summarize but cannot be the historical record. |
| 21 | Perform an undocumented intervention once because documentation is required only after the second need. | “an intervention needed twice becomes a documented operation” in R09. | Require authorization and contemporaneous evidence on the first real-state intervention. Repetition determines whether reusable documentation is warranted, not whether the first action is recorded. |
| 22 | Pollute permanent history with every failed edit—or silently call it exploration and discard it. | “Revert a failed experiment with a new commit; never abandon its diff” in [R10](/hpc/users/sunh14/reproducible-project-work/SKILL.md:46). | Allow unreferenced drafts to be edited or discarded only when they produced no retained effect. Freeze append-only history from the first consequential use. |
| 23 | Omit a dead end by calling it “idle” or implausible. | “Record plausible exploratory dead ends … omit idle exploration” in R10. | Record every observation that sets a parameter, expectation, compatibility claim, bug diagnosis, or why-not decision. Do not require a diary of uninfluential attempts. |
| 24 | Launder many influential trials into one clean implementation. | “Extensive discarded exploration followed by a clean tracked change … is valid” in [R11](/hpc/users/sunh14/reproducible-project-work/SKILL.md:47). | The clean implementation is valid only after all load-bearing facts are declared and the result is independently re-executed. It must not be presented as evidence of the discovery path. |
| 25 | Produce actions a practitioner can execute but cannot understand or safely modify. | “the practitioner need not be able to originate it” in [R12](/hpc/users/sunh14/reproducible-project-work/SKILL.md:51). | Require ordinary project artifacts that a practitioner can inspect, execute, diagnose, and change. |
| 26 | Add one-off automation for simple renames or formatting solely to satisfy the skill. | “write and track that script before running it” and “Use tracked automation…” in R12. | Preserve commands or generation logic only when they are normal, reusable project operations. A versioned diff is sufficient evidence for ordinary authored edits. |
| 27 | Forbid legitimate manual curation even when human judgment is the method. | “Never hand-produce an intermediate consumed downstream” in [R13](/hpc/users/sunh14/reproducible-project-work/SKILL.md:52). | Treat declared manual curation as a primary input with source, method, author, date, and review; do not mislabel it as generated output. |
| 28 | Invent an unexecuted “human equivalent” for an agent-only observation. | “Record a reproducible human equivalent” in [R14](/hpc/users/sunh14/reproducible-project-work/SKILL.md:53). | Re-execute the human-accessible method and retain its result. If that cannot be done, label the observation nonreproducible and do not use it for acceptance. |
| 29 | Let connector or browsing side effects disappear because those tools “are not recorded actions.” | Same R14 sentence. | Classify all facilities by their real effects. Tool category never grants exemption. |
| 30 | Either omit a load-bearing user fact as “not governing,” or dump private conversational material into the project. | “Record every user-supplied fact that governs behavior” in [R15](/hpc/users/sunh14/reproducible-project-work/SKILL.md:54). | Record only permitted, load-bearing facts. If a necessary fact cannot be stored, declare it as an external requirement or stop. |
| 31 | Rewrite local history before configuring the remote, or claim protection based on a setting the agent controls. | “Disable force updates and history deletion at the remote” in [R16](/hpc/users/sunh14/reproducible-project-work/SKILL.md:55). | Distinguish policy from structural enforcement. Structural immutability exists only when a control outside the writer’s authority enforces it. |
| 32 | Call a combined, opaque change “one logical action.” | “Use one logical action per commit” in R16. | Require that each retained revision has a coherent purpose and reviewable diff; do not pretend logicality is mechanically verifiable. |
| 33 | Pass the colleague test using generic agent-shaped artifacts that merely look plausible. | “would plausibly write by hand” in [R17](/hpc/users/sunh14/reproducible-project-work/SKILL.md:59). | Ask whether the artifact has a real human audience, conventional owner, update lifecycle, and value if no agent existed. |
| 34 | Delete a superseded artifact still needed to recreate an old run. | “remove tracked artifacts … when their role ends” in R17. | Preserve every revision and external record referenced by retained evidence for its declared retention period. |
| 35 | Create an unsafe launcher that passes arbitrary arguments through unchanged. | “unchanged argument pass-through” in [R18](/hpc/users/sunh14/reproducible-project-work/SKILL.md:60). | Do not prescribe launcher architecture. Require only that the documented human operation resolves the recorded configuration and inputs. |
| 36 | Move natural control flow into an unnatural central program merely because functions, parsing, loops, and logging are banned elsewhere. | Same R18 sentence. | Let the project’s ordinary architecture own behavior. Evaluate reproducibility and clarity, not syntax categories. |
| 37 | Ban legitimate tests, diagnostic utilities, monitoring, or standard logging. | “Do not create … verification scripts, status scripts, [or] logging frameworks” in [R19](/hpc/users/sunh14/reproducible-project-work/SKILL.md:61). | Ban only compliance-only duplication. Permit ordinary project tests, diagnostics, and operational evidence. |
| 38 | Report stale status from history rather than live state. | “determine status from version history and run records” in R19. | Historical claims use retained records; present-tense state claims require a timestamped live observation. |
| 39 | Block a legitimate executable or exploratory document even when practitioners use it as the canonical analysis. | “Use notebooks only as outputs” in [R20](/hpc/users/sunh14/reproducible-project-work/SKILL.md:62). | Remove format-specific prohibitions. Apply the same clean execution and hidden-state rules to every project artifact. |
| 40 | Rebuild a nominally declared environment that still depends on undeclared system facilities. | “machine-readable spec” and direct/transitive dependency clauses in [R21](/hpc/users/sunh14/reproducible-project-work/SKILL.md:66). | Record every load-bearing ambient facility or external platform requirement and the resolved validation identity. |
| 41 | Capture an accidental exploratory environment as the new declaration and conceal how it arose. | “pin, vendor, or apply a tracked patch during setup” in R21. | Rebuild from the declaration in a clean state. The rebuilt identity—not the mutated exploratory state—is evidence. |
| 42 | Satisfy provenance with a generating command that omits its own inputs and environment. | “either recorded origin and integrity identity or a generating command and code version” in [R22](/hpc/users/sunh14/reproducible-project-work/SKILL.md:67). | Require complete lineage for generated inputs and stable origin plus content identity for acquired inputs. |
| 43 | Put secret values into “all inputs and parameters,” contradicting the secret rule. | “Put all inputs and parameters in tracked declarations” in R22 versus [R23](/hpc/users/sunh14/reproducible-project-work/SKILL.md:68). | Track parameter definitions; record resolved nonsecret values in execution evidence; record only secret names, sources, and required scope. |
| 44 | Choose equivalence bounds after seeing the result. | “Declare nondeterminism and a functional-equivalence criterion” in R23 does not require precommit timing. | Fix observable checks, tolerances, repeat count, and pass rule in an immutable revision before the cited execution. |
| 45 | Declare “ask a colleague” or an inaccessible service as the acquisition procedure. | “how to obtain them” in R23. | Require a competent authorized practitioner to be able to follow the stated access procedure; otherwise mark recreation blocked. |
| 46 | Fill a boilerplate runbook with unsupported monitor, resume, scale, and debug commands. | Mandatory list in [R24](/hpc/users/sunh14/reproducible-project-work/SKILL.md:69). | Document only supported operations required by the touched behavior; mark unsupported operations explicitly instead of inventing them. |
| 47 | Forbid legitimate diagnosis against real state unless every diagnostic was prewritten. | “Run only the documented path against run state” in [R25](/hpc/users/sunh14/reproducible-project-work/SKILL.md:73). | Allow diagnosis, but record any observation used for a decision; require prior authorization and evidence for state-changing diagnosis. |
| 48 | Run against real external state while declaring the output path “outside the boundary.” | “Runs wholly outside the boundary remain exploration” in R25. | Real/shared inputs, services, resources, credentials, or effects make the action consequential regardless of output location. |
| 49 | Have the modified program emit a convincing success record without doing the work. | “inside the canonical program or existing engine” in [R26](/hpc/users/sunh14/reproducible-project-work/SKILL.md:74). | Treat self-emitted records as execution evidence, not independent proof. Capture status and predetermined checks outside the modified component. |
| 50 | Edit or replace a run record without detection. | “Never author or repair … by hand” is only an instruction. | Store evidence append-only or retain an immutable identity under a control the writer cannot alter. Otherwise integrity is merely honor-based. |
| 51 | Leak secrets through the “exact command.” | [Manifest field](/hpc/users/sunh14/reproducible-project-work/assets/run-manifest-fields.md:9): “Canonical command exactly as executed.” | Preserve reproducible structure while redacting secret values; record their names and declared sources. |
| 52 | Omit output identity because checksums are not “cheap.” | “checksums when cheap relative to the run” in [manifest fields](/hpc/users/sunh14/reproducible-project-work/assets/run-manifest-fields.md:19). | Require an identity sufficient for the claim: content digest, immutable object identity, or semantic assertions plus retained locator. |
| 53 | Point to expiring logs instead of retaining evidence. | The manifest requires only “locations” for streams and outputs. | A locator qualifies only with access and retention adequate for the claim; otherwise retain an immutable evidence identity. |
| 54 | Use a smoke-only branch that bypasses the production logic. | “cheap, real-shaped input” through the “full canonical entrypoint” in [R27](/hpc/users/sunh14/reproducible-project-work/SKILL.md:75). | Permit bounded verification to change workload only, not behavior under test. Inspect and record route identity. |
| 55 | Weaken a test with a plausible sentence and pass. | “Give a test weakening its reason in the same commit” in R27. | A weakened check cannot verify the affected behavior until independently reviewed against a preexisting requirement and re-executed. |
| 56 | Claim a successful route proves the production result. | R27 and [R30](/hpc/users/sunh14/reproducible-project-work/SKILL.md:81) do not require claim-to-scope mapping. | State exactly what each execution verifies. A bounded run verifies the route and bounded behavior, not unexecuted production outputs. |
| 57 | Force arbitrary step isolation or resume semantics that the system does not naturally possess. | “allow any step to run alone” and “long enough to matter” in [R28](/hpc/users/sunh14/reproducible-project-work/SKILL.md:76). | Require the smallest normal recovery unit only when interruption would otherwise repeat more than the bounded validation workload. |
| 58 | Label a workaround a root-cause fix. | “Change the artifact that owns the cause” in [R29](/hpc/users/sunh14/reproducible-project-work/SKILL.md:77). | Tie the claimed cause to a failing observation, a targeted change, and a regression check that fails before and passes after. |
| 59 | Retain a synthetic reproduction that does not establish it matches the original failure. | “retain a reproducible failing case” in R29. | Record the original failure signature and the equivalence between it and the retained case. |
| 60 | Cite an unrelated or self-authored record for any claim. | “Cite a run-record identifier for every verification claim” in R30. | Map claim → predeclared expectation → exact execution → observed result → retained output identity. |
| 61 | Avoid the word “verified” and imply success with “works,” “looks good,” or “complete.” | R30 audits only “verification claims.” | Treat every factual success, completion, correctness, current-state, or reproducibility statement as a claim requiring the map. |
| 62 | Call the agent’s second run “independent re-execution.” | “independent re-execution is proof” in R30 without defining independence. | Require a clean declared start and evidence/check capture not writable by the modified component; record who or what executed and observed it. |
| 63 | Claim a full boundary audit when no harness exists. | “When the harness records commands” in [R31](/hpc/users/sunh14/reproducible-project-work/SKILL.md:82). | Make assurance conditional: without an external complete effect record, boundary completeness is not structurally established. |
| 64 | Hide effects performed through tools the command harness does not capture. | R31 audits “every boundary-writing command.” | Audit effects across all facilities, child processes, remote actions, and manual operations—not shell commands alone. |
| 65 | Self-disclose retrospective work with a mandated phrase and treat that as control. | [R32](/hpc/users/sunh14/reproducible-project-work/SKILL.md:83). | Use mechanical chronology where available and re-execute the durable path. Disclosure remains honor-based evidence about history. |
| 66 | Let the handoff’s own revision fall outside the range it cites. | [Handoff template](/hpc/users/sunh14/reproducible-project-work/assets/handoff-note.md:5). | Treat handoff as current orientation, not evidence or a complete revision range. |
| 67 | Preserve stale verification indefinitely in the README or handoff. | “Current verification” in [runbook template](/hpc/users/sunh14/reproducible-project-work/assets/readme-runbook.md:63). | Keep claims next to immutable execution evidence or regenerate status from it; timestamp live claims. |
| 68 | Pretend a replay or colleague test occurred. | [Evidence tests](/hpc/users/sunh14/reproducible-project-work/references/evidence-tests.md:7) instruct “Give a competent stranger…” but require no independent record. | Record the actual executor, start state, command, and outcome. Do not simulate a stranger mentally. |
| 69 | Stop after a smoke test while the governing principle implies full rebuild, run, resume, and change were proven. | [Governing principle](/hpc/users/sunh14/reproducible-project-work/SKILL.md:10) versus bounded acceptance. | Scope each claim; unsupported capabilities remain unverified. |
| 70 | Treat declarations as truth without testing accessibility or retention. | R21–R24 rely heavily on declarations. | Verify acquisition/build/access where the claim depends on them; otherwise record a concrete blocker. |

## 2. Ephemeral/consequential boundary attacks

These are independently exploitable even if the final diff looks clean.

| Abuse | How it happens under the current text | Required correction |
|---|---|---|
| Narrow-boundary laundering | Declare a project subdirectory as the boundary while using shared state elsewhere. | Determine scope from effects, ownership, and dependencies. |
| Shared-link leakage | A “disposable copy” contains links or references to real inputs, outputs, environments, or services. | Verify isolation of every resolved target before execution. |
| Persistent child work | An exploratory command launches background work that continues after the parent exits. | Account for descendants and verify that no persistent work remains. |
| External side effects | Browsing, API calls, connectors, downloads, or authentication alter remote state, quotas, audit trails, or other people’s resources. | Tool category grants no exemption; classify by effect. |
| Ambient-state mutation | Exploration changes account configuration, credentials, histories, caches, indexes, or installed software. | Use only an already-isolated context or treat the operation as consequential. |
| Real-state diagnostic run | “Disposable output” is used while the run still reads or mutates real locks, jobs, databases, inputs, or services. | Any contact capable of changing real state is consequential. |
| Dependency adoption | A package or executable introduced during exploration remains available and the final run silently uses it. | Rebuild or verify the final environment from declarations without exploratory state. |
| Session-variable adoption | An exported variable, active environment, locale, working directory, or credential makes the final path work. | Record every load-bearing resolved value or external facility; verify from a clean session. |
| Output copying | A file produced outside is copied, pasted, retyped, summarized, or converted into a retained artifact. | Regenerate retained content through the durable path. |
| Parameter laundering | Exploratory results choose thresholds, seeds, tolerances, expected values, or resource settings. | Record the observation and decision before fixing the value; rerun afterward. |
| Post-hoc equivalence | Observed variation becomes the declared acceptable bound. | Fix equivalence and repeat policy before the cited run. |
| Mutable-source adoption | Exploration reads a changing URL, branch, service response, or latest dataset; the project records only the mutable locator. | Record immutable content/revision identity and acquisition time. |
| Exploratory evidence | Terminal output, screenshots, chat, or agent summaries are cited as proof. | Re-execute the human path and retain execution evidence. |
| Hidden code generation | A temporary generator creates source, configuration, tests, or documentation, then disappears. | Either treat the result as authored content whose behavior is independently verified or retain the normal regeneration method if regeneration matters. |
| Hidden assertion generation | Exploratory output is converted into a “golden” expected output. | Establish the expectation from an independent requirement or reviewed source before validation. |
| Ignored-project adoption | A directory is ignored or called temporary, then becomes the canonical source of outputs or state. | Give retained state a declared durable role and identity; otherwise remove it and rerun. |
| Cleanup by assertion | “Discarded” means the agent stopped mentioning it. | Require observable pre/post state or mark cleanup unverified. |
| Precommit execution | Run mutable code first, commit it afterward, and let the record cite the later revision. | Source identity must exist before consequential execution; retrospective identity never proves what ran. |
| Record backfill | Reconstruct a manifest from shell history or memory after the run. | Retain only records created directly by execution; rerun for proof. |
| Record repair | Fix a malformed or failed record while preserving its successful status. | Keep the original and append a new execution record. |
| Self-attested success | Changed code writes its own commit, command, exit, and assertion values. | Capture status and checks independently of the changed component. |
| Shared-input mutation | A run writes indexes, metadata, locks, or access markers beside supposedly read-only inputs. | Include input-adjacent effects in the effect surface and inspect permissions/behavior before calling the run ephemeral. |
| Secret-only reproducibility | The run works with a secret available only in the agent session. | Declare the secret’s human-accessible source and required scope; never rely on the current session. |
| Expiring evidence | External logs exist at handoff but vanish before a stranger arrives. | Declare and verify evidence retention or preserve an immutable identity in durable project records. |
| Partial clean start | A new project copy reuses the old home state, cache, environment, or service session. | Define clean start across every load-bearing state surface, not just source files. |

## 3. Contradictions and two-way readings

| Clauses | Contradiction or ambiguity |
|---|---|
| Governing principle vs R31 | The project is “the only memory,” but the independent command record is outside agent-writable project state and may not be available to the stranger. |
| R02 vs run artifacts | It forbids ignored space inside the boundary while also including outputs, logs, jobs, locks, and records that are commonly untracked or external. |
| R04 vs R19/R26 | R04 requires a program that writes records; R19 bans logging machinery; R26 again requires record implementation inside the program. |
| R04 vs R25 | The environment build and first execution must produce records before the required recording path has been established and tested. |
| R04/R24/R26/R34 vs R05 | The skill claims proportionality while mandating nearly the whole infrastructure and test suite for every touched task. |
| R01/R05 vs governing goal | The user can override the tier or skill even though the skill claims an invariant reproducibility standard. |
| R07 vs R14 | Exploration is “unrestricted and unrecorded,” but R14 says to reproduce every world effect and influential observation. |
| R08 vs R16 | R08 says promote “immediately,” but both clauses place the decision record after the implementation hash exists. |
| R09 vs R14/R21/R31 | “Exactly three” action kinds omit influential reads, remote changes, environment mutations, external communications, and audit-policy changes. |
| R10 vs R07 | Failed experiments must be permanently committed, while exploration can be discarded. The boundary location—not consequence—decides history. |
| R12 vs R19 | R12 requires tracked automation for mechanical work; R19 bans categories that include normal verification and status automation. |
| R13 vs legitimate curation | “Every file derived from data” must be generated, but real projects may have explicitly human-curated primary inputs. |
| R14 vs R31 | Agent facilities are “not recorded actions,” yet the command-only audit cannot observe their effects. |
| R15 vs R21–R23 | Machine and session state are forbidden dependencies, but site facilities, credentials, hardware, and services are allowed as declarations without proving accessibility. |
| R16 vs R33 | History and decisions are append-only, but intervention history is placed in a replace-in-place handoff. |
| R17 vs evidence retention | Superseded artifacts should be removed, but old runs may depend on their exact revisions or external identities. |
| R19 vs R24/R27/R29 | Verification utilities are banned while project tests, bounded reproductions, and executable debugging are mandatory. |
| R19 vs R24 | Status should come from historical records, but the runbook must include monitoring of current state. |
| R20 vs R13/R17 | One artifact format is categorically forbidden as working source even if it is the project’s ordinary practitioner-native form. |
| R22 vs R23 | All parameter values are tracked, but secret values must not be tracked. |
| R24 vs tiers/R28 | Resume, one-step, scale, and monitoring commands are mandatory even where resume is supposedly conditional. |
| R25 vs R08/R30 | Outside-boundary runs are said to produce no evidence, but influential exploratory observations must drive recorded decisions. |
| R26 vs R30 | A component’s self-produced record is treated as evidence, while proof is supposed to require independence. |
| R31 classification | It is labeled structural even though it begins “When available.” A conditional absent mechanism is not a structural rule. |
| R32 vs R14 | R14 permits documented manual equivalents; R32 treats retrospective manual work as categorically unverified without defining when a prior manual procedure is valid. |
| R33 handoff range | Committing the handoff changes the revision range it claims to summarize, producing a recursive omission. |
| R34 vs evidence-test order | Replay is placed before clean build, command identity, resume, failure, and handoff tests even though it depends on their results. |
| Classification preamble vs package | It claims references and assets add no rules, but they mandate additional fields, tests, paths, checksums, and architecture. |

## 4. Human-native failures and technology prescriptions

- The `Δ` presence mark is agent-session theater. It depends on chat, is not practitioner-native, provides no enforcement, and contradicts the goal that nothing depend on the agent or transcript. Remove [the entire presence-signal section](/hpc/users/sunh14/reproducible-project-work/SKILL.md:12).

- The tier labels “small standalone script,” “HPC or scientific workflow,” and “continuously running service” are technology/domain branches despite the text saying tiers are not domain labels. Remove [the tier table](/hpc/users/sunh14/reproducible-project-work/references/tiers.md:5).

- Mandatory commits, commit hashes, remote force-update configuration, submission files, machine-readable environment forms, engines, schedulers, transferable artifacts, checksums, and notebook policy prescribe implementations rather than outcomes.

- The [decision-log template](/hpc/users/sunh14/reproducible-project-work/assets/decision-log-entry.md:1) is chronology-inverted, command-centric, and unable to represent literature evidence, human judgment, approvals, decisions without implementation, or implementation not yet identified. Its arrow syntax is agent vocabulary.

- The [environment checklist](/hpc/users/sunh14/reproducible-project-work/assets/environment-spec-checklist.md:1) is a compliance artifact a practitioner can check dishonestly. It is not an environment declaration and should not be copied into a project.

- The [execution-script template](/hpc/users/sunh14/reproducible-project-work/assets/execution-script.txt:1) mandates an interpreter, activation, a single invocation, and unchecked pass-through. Many projects need none of these; many need normal validation or control flow.

- The [handoff template](/hpc/users/sunh14/reproducible-project-work/assets/handoff-note.md:1) assumes linear revisions, makes prose verification duplicate evidence, stores interventions in mutable text, and permits unsupported `none` assertions.

- The [runbook template](/hpc/users/sunh14/reproducible-project-work/assets/readme-runbook.md:1) forces unsupported operations, duplicates stale current verification, and gives commands no declared working context or resolved parameters.

- The [run-manifest template](/hpc/users/sunh14/reproducible-project-work/assets/run-manifest-fields.md:1) prescribes a custom schema and unique identifier even for tiny work, while omitting record integrity, retention, assertion provenance, secret-safe command representation, and independence from modified code.

- Rule IDs, exact disclosure phrases, compliance checklists, generic manifests, mandatory handoffs, and agent-facing cheat catalogs may be suitable inside an agent skill, but they should not be copied into practitioner projects.

The corrected package therefore should contain only `SKILL.md`. It should adapt to ordinary project artifacts instead of shipping templates.

## 5. Misclassified rules

No rule is structurally enforced merely because this skill says so. The corrected classifications are:

| Rule | Current | Correct classification |
|---|---|---|
| R01 | honor | H+V: selection is judgment; stated factual risk conditions can be reviewed. |
| R02 | verifiable | H+V: declared surfaces are inspectable; completeness is honor-based without external effect capture. |
| R03 | verifiable | H+V: visible writes are inspectable; hidden reads/effects and “unnecessary” mechanisms are not. |
| R04 | verifiable | V for artifact presence; H for whether establishment preceded every use without independent chronology. |
| R05 | verifiable | H+V: scope and “do not worsen” are judgments; visible unrelated diffs are reviewable. |
| R06 | verifiable | V; S only if revision immutability and execution identity are externally enforced. |
| R07 | verifiable | H+V; S only with externally enforced isolation and destruction evidence. |
| R08 | honor | H, partly V with an independent effect trace and contemporaneous decision links. Influence can never be fully inferred from final artifacts. |
| R09 | verifiable | Invalid premise. Consequential kinds are not closed; known effects may be V, hidden effects H. |
| R10 | verifiable | H+V: retained history is inspectable; discarded or influential abandoned work may be invisible. |
| R11 | verifiable | H+V; S only with complete external effect capture. Laundering is often intentionally invisible. |
| R12 | verifiable | H+V: chronology may be observable, but “mechanical,” “human-scale,” and “reasonable” are judgments. |
| R13 | verifiable | H+V: lineage can be replayed; whether a file was secretly derived or legitimately authored may not be detectable. |
| R14 | honor | H+V: the mapping is judgment, but an actually re-executed human method and result are verifiable. |
| R15 | verifiable | H+V: replay reveals some hidden dependencies, not every untested conversational or ambient dependency. |
| R16 | verifiable | V; S only where append-only controls are outside writer authority. Atomicity and rationale quality remain H. |
| R17 | verifiable | H+V: inventory is inspectable; practitioner-native quality requires human review. |
| R18 | verifiable | V for syntax inspection, but it verifies an unjustified architecture rule rather than reproducibility. |
| R19 | verifiable | H+V: repository inventory is visible; external helper use and whether something is “meta” may be hidden or subjective. |
| R20 | verifiable | H+V: invocation is inspectable; interactive history can be cleared and is not reliably exposed by metadata. |
| R21 | verifiable | H+V: rebuild verifies declared state; declaration completeness and hidden ambient facilities remain H. |
| R22 | verifiable | H+V: identities can be checked; truth and completeness of provenance remain H without external lineage. |
| R23 | verifiable | H+V: declarations are visible; completeness, accessibility, and non-post-hoc bounds need execution or review. |
| R24 | verifiable | V for commands actually tested; H for whether all necessary operations are documented. |
| R25 | verifiable | H+V; S only with complete external execution/effect capture. Hidden runs are otherwise invisible. |
| R26 | verifiable | V for replay; S only when record capture and retention are outside both agent and modified component. |
| R27 | verifiable | H+V: route identity is inspectable; “real-shaped,” assertion adequacy, and “non-trivial” are judgments. |
| R28 | verifiable | V when the requirement applies; applicability and adequate recovery scope are H. |
| R29 | verifiable | H+V: before/after behavior is testable; actual root cause and reproduction equivalence require judgment. |
| R30 | verifiable | H+V: citation presence is checkable; claim completeness and evidence relevance require review. |
| R31 | structural | S only when a complete external recorder actually exists, covers all effect channels, and is outside agent authority. Otherwise the control is absent. |
| R32 | honor | H+V if external chronology exists; S only for facts mechanically captured outside the actor. |
| R33 | verifiable | H+V: cited facts can be checked; omitted interventions or fragile facts may remain hidden. |
| R34 | verifiable | V only when tests were actually executed and retained; S only under an external runner/observer. |
| R35 | honor | H for truthful stopping; external authorization controls can structurally prevent some unauthorized actions. |

Honor rules that can be tightened:

- R01: replace subjective tiers with recorded yes/no risk triggers.
- R08: use external effect traces and contemporaneous observation-to-decision links; influence completeness remains honor-based.
- R14: require actual human-path re-execution rather than an asserted equivalent.
- R32: compare external chronology and replace retrospective proof with a new recorded execution.
- R35: rely on access controls and recorded authorization where available; truthful blocker disclosure remains honor-based.
- R17, R29, and R30 also contain unavoidable human judgments and should never have been presented as purely verifiable.

## 6. Softening words that reopen loopholes

| Soft wording | Abuse | Replacement |
|---|---|---|
| “may,” “permit,” “prefer,” “when needed,” “when available,” “where relevant,” “when applicable,” “optional” | Skip the control whenever inconvenient. | State an observable trigger and mandatory consequence. |
| “small,” “few,” “thin,” “short,” “cheap,” “reasonable,” “material,” “meaningful,” “non-trivial,” “long enough” | Select the cheapest interpretation after seeing cost or results. | Use yes/no conditions tied to repetition, interruption, sharing, external effect, nondeterminism, retention, and failure consequences. |
| “competent,” “comparable,” “functional equivalence,” “same process,” “meaning match” | Accept a reconstruction that differs in load-bearing ways. | Predeclare observable outputs, tolerances, repeat count, and pass rule. |
| “real-shaped,” “full route” | Run a smoke-only branch or skip costly logic. | Permit only declared workload reduction; require the behavior under claim to be identical. |
| “logical,” “plausible,” “idle,” “obvious,” “clear,” “conventional” | Hide mixed revisions, dead ends, unexplained rationale, or agent artifacts. | Use reviewable purpose, load-bearing-decision criteria, and the real-audience artifact test. |
| “what the task touches,” “do not worsen,” “affected claim” | Narrow scope around a violation or claim success only for convenient fragments. | Name exact changed behavior, effect surfaces, and claim-to-evidence mapping before action. |
| “discarded,” “retained,” “used,” “governs behavior” | Deny influence or cleanup without proof. | Define load-bearing influence and require observable pre/post state. |
| “clean,” “fresh,” “current” | Reuse hidden caches, environments, sessions, or stale status. | Define exact source, environment, external-state, and observation-time conditions. |
| “independent,” “evidence,” “proof,” “verified” | Treat self-authored records or a second agent run as independent proof. | Require external capture or explicitly label the remaining assurance gap. |
| “needed twice” | Leave the first intervention undocumented. | Record the first action; repetition only triggers reusable operation documentation. |

## 7. Why practitioners would ignore the current skill

- A one-line fix triggers an environment declaration, recorder, smoke configuration, runbook, decision log, handoff, launcher, remote policy, and full evidence suite.
- Every in-project experimental edit becomes permanent history.
- Testing before committing is effectively forbidden.
- Every failed consequential experiment requires a revert revision.
- History may never be cleaned even before any run or evidence references it.
- Remote policy changes are demanded without checking authority.
- Every program is expected to implement record production.
- Ordinary tests, monitoring, diagnostics, and logging can be classified as forbidden meta-operations.
- Real-state debugging is blocked unless its exact diagnostic command already appears in documentation.
- Manual curation is prohibited.
- One artifact format is categorically excluded despite common practitioner use.
- Resume, isolated-step, monitoring, and scale operations are demanded even for work that has none.
- Acceptance starts with a stranger replay and ends with a colleague interview, without sequencing or a retained record of either.
- Exact commands may expose secrets and are brittle under harmless invocation differences.
- The handoff requires a revision range that cannot include its own update.
- The skill gives no clean sequence for accidental leakage, pre-existing dirty state, emergency intervention, changing an expectation, or unavailable external audit.
- The compliance artifacts duplicate rather than use ordinary project records.

## 8. Changes in the corrected skill

1. Remove the chat presence mark.
2. Replace path-based boundaries with effect-based classification.
3. Replace tiers with a universal minimal evidence baseline and explicit risk triggers.
4. Make user scope changes unable to convert unsupported work into verified work.
5. Define durable external evidence, retention, and immutable identity.
6. Make exploration ephemeral only when isolation and cleanup are demonstrated.
7. Treat copied, retyped, summarized, and parameterized exploratory results as adoption.
8. Require load-bearing observations and equivalence criteria before implementation or execution.
9. Allow unreferenced drafts to be discarded; freeze append-only history once a revision becomes consequential.
10. Preserve unowned dirty state instead of forcing it into a commit.
11. Replace custom self-authored manifests with ordinary execution-produced project or platform evidence.
12. Separate execution evidence from independent proof.
13. Require clean re-execution with predetermined checks and claim-specific scope.
14. Treat modified assertions as unable to independently validate the corresponding behavior.
15. Record first interventions contemporaneously and distinguish auditable one-time actions from replayable operations.
16. Restore legitimate diagnosis and manual curation.
17. Require live evidence for present-tense status.
18. Make structural classification conditional on controls outside the agent’s authority.
19. Apply the real-audience test to every new artifact.
20. Remove all bundled generic templates and technology-specific prescriptions.

## 9. Corrected skill in full

The corrected package contains only this `SKILL.md`:

```markdown
---
name: reproducible-project-work
description: Make consequential work on a runnable project reproducible and independently verifiable from durable human-facing project records. Use when creating, changing, executing, diagnosing, resuming, operating, or handing off project behavior or retained run state. Do not use for answers that only read already-provided information and cause no project or external effect.
---

# Reproducible project work

## Objective

Make every retained change, execution, decision, and intervention reconstructible by a competent practitioner from durable project records. Keep chat, agent context, shell history, ambient session state, and agent-only facilities out of the operating and evidentiary paths.

Never claim stronger assurance than the available evidence and controls provide.

## Definitions

A **durable project record** is an ordinary human-facing project artifact, or a declared external record, that has:

- a stable locator;
- an access procedure for the intended practitioner;
- an immutable content or revision identity;
- retention adequate for the claim it supports; and
- enough context to interpret it without this skill or a transcript.

A mutable path, current terminal output, session variable, chat message, or expiring log is not a durable record by itself.

An **effect surface** is any state the action can read in a load-bearing way or change, including retained source, configuration, environments, inputs, outputs, logs, live work, locks, remote resources, shared state, permissions, and external systems or people.

A **consequential action** is any action that does at least one of the following:

- changes an effect surface;
- creates or alters a retained artifact;
- produces an observation used in a claim, decision, parameter, expectation, or diagnosis;
- introduces a dependency needed to regenerate retained content or repeat a load-bearing observation; or
- affects another person or external system.

Classify an action by its effects, not by its tool, command name, working directory, stated intent, or output location.

**Ephemeral exploration** is work for which all of the following are true:

- every effect is confined to an already-isolated disposable context;
- no mutable shared or real run state is used or changed;
- no persistent child work or external effect remains;
- pre-existing relevant state is shown to be unchanged afterward;
- every created effect is removed; and
- no result, observation, dependency, parameter, expected value, or inference becomes load-bearing.

If any condition is false or cannot be established, classify the work as consequential. Ephemeral exploration never verifies a project claim.

An **execution record** is created directly by the actual action or by an execution facility observing that action. It records completion, failure, interruption, and relevant identities as they occur. A retrospective account is not an execution record.

A **verified claim** is a narrowly stated claim whose check was fixed before execution and passed during a recorded re-execution of the documented human path from a declared start state.

A **human-native artifact** is one a practitioner would keep, understand, update, and use if no coding agent or reproducibility skill existed.

## Assurance ceiling

Instructions cannot structurally enforce their own truthfulness.

Call a requirement **structural** only when an existing control outside the agent’s and modified component’s write authority prevents or immutably captures violations. Confirm the control’s scope before relying on it.

Without such a control:

- append-only history is a verifiable policy, not a structural guarantee;
- execution records created by the modified component are evidence, not independent proof;
- completeness of the effect boundary and disclosure of exploratory influence retain an honor component; and
- absence of an unrecorded action cannot be proven solely from agent-written project files.

If the requested outcome requires a no-cheat or complete-boundary guarantee and the required external control is absent, stop before consequential action and name the missing control. Do not silently downgrade the guarantee.

## Work in this order

### 1. Inspect without changing state

Before writing or executing:

1. Identify the project’s existing human conventions for source, configuration, environment, inputs, execution, tests, evidence, decisions, operations, and current status.
2. Identify all known effect surfaces and declared external requirements.
3. Inspect retained history and current working state.
4. Identify pre-existing or user-owned changes and preserve them.
5. Avoid any operation whose effects are unknown. If inspection can change consequential state, treat it as consequential.

Do not add or modify project artifacts during this inspection.

### 2. Define the claim before the run

Before a consequential execution:

1. State the exact behavior or result to be claimed.
2. State the observable pass and fail conditions.
3. State the source, environment, configuration, input, and external-state assumptions.
4. State the equivalence criterion, including tolerances, repetition count, and pass rule for nondeterministic behavior.
5. State whether the execution verifies a bounded route, a specific output, a recovery property, or the complete requested run.
6. State where execution evidence will be retained and for how long.

Put these facts in an existing ordinary project artifact. Add a new artifact only when a practitioner would retain it independently of this skill.

Do not select expectations, tolerances, or equivalence bounds after seeing the result that they will judge.

### 3. Establish the minimal durable path

For the behavior under claim, ensure that durable project records identify:

- the retained source and configuration;
- how to obtain or validate the required environment;
- all load-bearing inputs, parameters, and external requirements;
- the ordinary human operation that performs the work;
- the predetermined check;
- the destination and retention of outputs and execution evidence; and
- the recovery or rerun operation when required by the recorded risk conditions below.

Reuse ordinary project conventions when they satisfy these facts. Do not add compliance-only machinery, duplicate control layers, or agent-facing project documentation.

Do not require unrelated project-wide repairs. A pre-existing violation outside the touched behavior may be reported without being repaired.

A declared external requirement must have a stable identity, acquisition or access procedure, expected interface or location, compatibility requirements, and adequate retention. A mutable name or inaccessible source does not satisfy this requirement.

Record secret names, sources, and required scope. Never record secret values.

### 4. Handle exploration without laundering it

Before exploration, establish that its complete effect surface is isolated and disposable. Afterward, establish that relevant pre-existing state is unchanged and that no effect remains.

Do not use exploration as project evidence.

If exploration supplies a load-bearing fact:

1. Record the observation source, immutable identity, time, relevant context, observed result, decision, and rationale before relying on it.
2. Express the retained change through normal project artifacts.
3. Declare every dependency needed to regenerate the retained result or repeat the observation.
4. Re-execute the documented human path from the retained state.
5. Cite only the re-execution as verification.

Copying, retyping, paraphrasing, converting, or fixing values from an exploratory artifact counts as adoption.

If exploration accidentally crosses into consequential state:

1. Stop further work.
2. Do not erase available mechanical evidence in order to present a cleaner history.
3. Record the affected surfaces and observed effects.
4. Label the resulting state unverified.
5. Restore a durable path through retained changes and a new recorded re-execution.
6. Preserve the distinction between the original unrecorded action and the later verified execution.

### 5. Make retained changes reviewable

Treat source, configuration, procedures, and explanatory documentation as authored project changes.

Produce retained derived outputs through their documented generating path.

When human judgment is itself the method, treat the curated result as a declared primary input. Record its source material, method, author or responsible role, date, and review basis before downstream use.

Record a non-obvious decision before implementing the change it governs. Use the project’s existing decision mechanism. Record:

- the durable observation or requirement;
- the decision;
- the rationale and rejected alternative when relevant; and
- the expected consequence.

Append the implementation identity after it exists without rewriting the original decision.

Before executing against persistent or shared state, give every load-bearing source, configuration, expectation, and input declaration an immutable retained identity. Do not execute from unrecorded differences.

Unreferenced local drafts may be edited or discarded only when they produced no retained effect or load-bearing observation and the relevant state is restored exactly.

Once a revision or record is cited by a consequential execution, decision, or handoff:

- do not rewrite or delete it;
- append corrections or reversals;
- retain it for the lifetime of the evidence that cites it; and
- state whether immutability is externally enforced or only reviewable after the fact.

### 6. Execute through the human path

Use the documented ordinary project operation for every consequential execution.

The execution and existing durable records must jointly identify, without unnecessary duplication:

- the action as performed, with secret values redacted;
- the immutable source revision;
- the resolved environment identity;
- the resolved configuration and nonsecret parameter values;
- input origins and immutable identities;
- the target effect surface;
- start and end times with time zone;
- completion, failure, or interruption status;
- output and log locators with durable identities;
- actual results of the predetermined checks; and
- any prior execution from which the action resumes.

Use ordinary project or execution-facility evidence. Do not add a separate record format merely to satisfy this list.

Do not type, backfill, edit, or repair an execution record. Preserve an incomplete or incorrect record and create a new execution to obtain new evidence.

A record created solely by the modified component does not independently establish that the component performed the claimed work. Retain externally observed status and predetermined check results when independent proof is required.

A locator without adequate access, identity, and retention is not durable evidence.

### 7. Verify by re-execution

After the retained implementation identity exists:

1. Start from a project state that exactly matches that identity and contains no unrecorded load-bearing differences.
2. Rebuild the environment when its declaration or setup changed. Otherwise verify and record that the existing environment matches its declared identity.
3. Acquire or validate inputs from their declarations.
4. Execute the documented human path.
5. Run the predetermined checks.
6. Retain the execution-produced evidence and output identities.
7. Compare the observed result with the predeclared criterion.
8. State only the claim supported by that execution.

A bounded verification may reduce declared workload size. It must not substitute different behavior for the behavior under claim. A bounded execution verifies only its stated route and bounded behavior; it does not prove unexecuted production outputs.

If an acceptance check was created or weakened in the same change as the implementation, it does not independently establish the intended behavior. Require a pre-existing external criterion or review by an authority that did not author the implementation, then re-execute.

If execution fails or a required step is blocked, the affected claim is unverified. Preserve the produced record and state the blocker.

For present-tense operating status, obtain a timestamped live observation. Historical execution records establish historical facts only.

### 8. Diagnose and intervene honestly

A diagnostic observation used for a decision is consequential evidence. Retain its exact source, time, operation, context, and result identity in the project’s ordinary issue or decision record.

A diagnostic action that can change real state is a consequential intervention. Before performing it:

- obtain the required authority;
- state the exact target and intended effect;
- use a documented human operation;
- ensure the action will produce or trigger contemporaneous evidence; and
- define how the result will be checked.

Record the first intervention. Repetition determines whether reusable operating documentation is warranted; it never excuses the first action from evidence.

Do not use “debugging,” “inspection,” “temporary,” or “exploration” to exempt a real-state run.

If an intervention is inherently one-time or unsafe to replay, record it as auditable rather than reproducible. Do not claim that a project in that state meets a requirement that every consequential action be replayable.

For a bug fix, retain a normal regression check that establishes the relevant failure before the fix and passes afterward. Record how any reduced reproduction matches the original failure signature.

### 9. Keep effort proportional without weakening the baseline

Every consequential claim requires the durable identities, documented human path, execution-produced evidence, predeclared check, and recorded re-execution above.

At task start, answer these conditions explicitly:

- If interruption would require repeating more work than the bounded verification workload, define and test recovery on a bounded execution.
- If repetition can duplicate, overwrite, or externally expose effects, define and test idempotence or recovery before scale.
- If output is nondeterministic, fix the repetition count, bounds, and pass rule before execution.
- If the work will be reused after the current task or by another person, retain environment, input, source, and evidence availability for that lifetime.
- If failure can materially affect external state or another person, require independent review of the operation, check, and recovery path.
- If present operating state matters, include a live observation at handoff.

Do not add a mechanism because a category or nominal tier suggests it. Add only the ordinary project behavior required by a condition that is true.

### 10. Apply the human-native test

Before adding any artifact, ask:

1. Who is its practitioner audience?
2. What ordinary project decision, execution, operation, or maintenance need does it serve?
3. Where would that audience expect it, and who updates it?
4. Would it remain useful and understandable if the agent and this skill disappeared?
5. Does an existing artifact already serve the role?

Do not add the artifact if these questions lack concrete answers.

Do not put presence marks, agent instructions, skill rule identifiers, mandated disclosure phrases, compliance checklists, or duplicated evidence summaries into project artifacts.

Do not prescribe a file type, execution architecture, auxiliary layer, or documentation bundle. Let the project’s ordinary human conventions carry the required facts.

A mutable current-status note may orient the next practitioner, but it is not historical evidence. It must point to immutable revisions and execution records rather than replace them.

## Acceptance

Before claiming work verified, confirm from durable records that:

- every load-bearing source, configuration, environment, input, and external requirement has a usable identity;
- the documented human operation matches the recorded execution;
- the execution record was produced by the action or its execution facility;
- the expected checks were fixed before the cited execution;
- the documented path was re-executed from the declared start state;
- the observed results satisfy the stated criterion;
- the claim does not exceed the execution’s scope;
- no exploratory artifact, dependency, observation, or effect was adopted without promotion and re-execution;
- every retained artifact passes the human-native test;
- every cited revision and record remains available and unrevised; and
- structural assurance is claimed only for controls verified to be outside agent write authority.

If any item fails, label the affected claim `unverified` and state the missing evidence or control.

## Enforcement classification

Use these classifications literally:

| Requirement | Default classification | Structural only when |
|---|---|---|
| Source and history immutability | verifiable | an append-only control outside writer authority prevents rewriting |
| Execution-record provenance and immutability | verifiable | capture and retention are outside both the agent and modified component |
| Clean re-execution and result comparison | verifiable | an external executor and observer enforce the declared start state and checks |
| Effect-boundary completeness | honor plus verifiable declared surfaces | an external facility captures every relevant effect channel |
| Ephemeral isolation and cleanup | honor plus verifiable pre/post state | isolation and disposal are enforced and recorded externally |
| Disclosure of influential observations | honor | no general mechanism can prove every private influence; external traces can only reduce the honor surface |
| Input and external-requirement identity | verifiable | acquisition and retention are independently controlled |
| Claim-to-evidence relevance | honor plus verifiable linkage | independent review fixes the criterion and approves the linkage |
| Human-native quality | honor plus human review | this is not meaningfully structural |
| Authorization and stopping | honor plus access controls | external controls prevent unauthorized effects |

Never relabel a missing or agent-controlled mechanism as structural.

## Stop and hand off

At the end, report from durable evidence:

- retained revisions;
- consequential executions and interventions;
- each verified claim and its exact evidence;
- each unverified claim and reason;
- remaining persistent state;
- external requirements or blockers;
- the current live state when relevant; and
- the next ordinary human action.

Do not use the transcript as evidence. Do not claim setup, execution, recovery, reproducibility, or completion beyond what the cited re-execution established.
```
