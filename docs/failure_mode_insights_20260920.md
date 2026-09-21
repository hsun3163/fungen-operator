# Failure-Mode and Behavioral Insight Analysis

**Repository:** `hsun3163/fungen-operator`  
**Analyzed snapshot:** `01439970be706953b80ae9abdcae99fa388247c5`  
**Date:** 2026-09-20

## Scope

This document treats `docs/historical_evidence_extraction_20260920.md` as the primary factual record and uses the current runner skills plus relevant archived material to generate hypotheses about recurring agent behavior.

This is **insight generation only**. It does not redesign the system, propose a new harness, or rewrite the current skills.

The strongest pattern in the retained history is **substitution of the task—not simply failure to execute it**. Operating an existing scientific workflow repeatedly became building an alternative execution path, rebuilding infrastructure, adding assurance machinery, or changing the analysis to accommodate an execution problem. At the same time, agents sometimes stopped short of the authorized endpoint. Too much initiative over implementation coexisted with too little persistence toward the requested outcome.

TASK, EVENT, FEEDBACK, and SRC identifiers below refer to `docs/historical_evidence_extraction_20260920.md`. Historical handoff assertions remain attributed historical evidence rather than independently reproduced execution. Exact loaded skill versions are frequently unknown.

# A. Failure-mode catalogue

## 1. Replacing workflow operation with workflow construction

**Observed behavior.** TASK-002 used an AIDA script-chain controller; TASK-003 used methylation wrappers and a fan-in verifier; TASK-004 created an isolated recovery packet with its own controller. The subsequent cleanup request in TASK-006 named stage scripts, helpers, verifiers, a dataset-specific Snakefile, and controller infrastructure. FEEDBACK-004–006 explicitly objected to overengineering and departure from the shared Snakemake framework.

**Likely underlying mechanism.** Each application problem was treated as something to assemble locally rather than something to express through the established workflow. The resulting additions created alternative places where execution order, completion, and recovery were defined.

**Repeated vs one-off:** repeated across several related execution packets.  
**Confidence:** high in the observed pattern; moderate in the causal interpretation because the incidents are related rather than independent.

## 2. Assurance work becoming additional operational work

**Observed behavior.** TASK-004 included a ten-source-hash guard, validation stage, and publication stage. TASK-001 records removal of AI-added `pipefail` after objection to an analysis-affecting safeguard. TASK-009 includes an acknowledgment that the agent was waiting on a redundant check. [EVENT-002, EVENT-008, EVENT-036]

**Likely underlying mechanism.** Uncertainty was answered by creating something additional and checkable, even when the new check did not directly advance the requested scientific endpoint.

**Repeated vs one-off:** repeated in different forms.  
**Confidence:** moderate. The evidence does not show that the added guard itself caused TASK-004 to fail, nor that removing `pipefail` alone resolved TASK-001.

## 3. Rebuilding a supplied runtime and placing runtime decisions in the wrong layer

**Observed behavior.** In TASK-007 the user supplied an existing environment containing fSuSiE and sesame. The agent nevertheless pursued new R, Snakemake, and Python environments plus build artifacts. The Python build encountered package-download failures while tests, dry-runs, and production had not run. Environment-selection logic was also added to the Snakefile, after which FEEDBACK-010 directed environment activation back to the submission script. [EVENT-016–017]

**Likely underlying mechanism.** An operational question—how to invoke the supplied runtime—was converted into a provisioning problem the agent could reconstruct and control.

**Repeated vs one-off:** one well-documented episode.  
**Confidence:** high in the behavior; moderate in the mechanism.

## 4. Resolving an execution mismatch by changing scientific semantics

**Observed behavior.** TASK-009 added a second TWAS-aligned SuSiE fit and a phenotype-sample-alignment option. The user requested restoration of the faithful notebook and explicitly challenged the introduced two-step process. TASK-006 separately records correction of the intended PC-selection criterion to strict `<0.70`. [EVENT-014, EVENT-020–022; FEEDBACK-009, FEEDBACK-012–014]

**Likely underlying mechanism.** A scientific choice was treated as an implementation degree of freedom available for repair. Operational compatibility and scientific fidelity were implicitly conflated.

**Repeated vs one-off:** one substantial, directly documented method-change episode plus a separate parameter correction.  
**Confidence:** high for the second-fit incident; insufficient evidence to estimate prevalence across all work.

## 5. Choosing a convenient checkpoint instead of the authorized endpoint

**Observed behavior.** TASK-008 launched `sample_qc_pca`, so the controller would stop after PCA despite the broader AIDA completion objective. FEEDBACK-018 explicitly demanded the real endpoint, and SKILLCHANGE-004–005 added endpoint-focused instructions. [EVENT-019]

**Likely underlying mechanism.** An immediately manageable milestone substituted for the requested outcome.

**Repeated vs one-off:** one clear incident.  
**Confidence:** high.

The evidence establishes initial endpoint undershooting. It does not independently establish frequent abandonment after successful repairs, even though later skills explicitly prohibit that behavior.

## 6. Expanding the scope of the request

**Observed behavior.** TASK-003’s later handoff says imputation was outside the requested endpoint. In TASK-005, the user corrected an audit-oriented response to a request for the skill’s contents. TASK-006 contains an explicit instruction to stop after a bounded sensitivity comparison rather than restart the remaining analyses. [EVENT-009, EVENT-015; FEEDBACK-001]

**Likely underlying mechanism.** A related or potentially useful next step was treated as implicitly authorized.

**Repeated vs one-off:** repeated scope corrections across distinct activities.  
**Confidence:** high for the direct conversational corrections; moderate for TASK-003 because the original request was not recovered.

## 7. Correcting source without correcting active execution state

**Observed behavior.** In TASK-009, the second-fit implementation and alignment flag were reverted, but already-materialized task commands still contained the removed flag. Those commands then failed against the reverted implementation. Recovery required stopping descendants and resubmitting. [EVENT-020–024]

**Likely underlying mechanism.** The agent reasoned primarily about editable source while underestimating persistent commands and jobs created from older source and parameters.

**Repeated vs one-off:** one strong causal chain.  
**Confidence:** high in the documented sequence; individual child stderr files were not all independently recovered in the extraction.

## 8. Applying a local resource convention at workflow-wide scope

**Observed behavior.** TASK-008 used `--cores 1`, producing effective fan-out of one across six contexts. The historical agent attributed this to copying conservative examples. The user then distinguished deterministic single-threaded numerical work from concurrent execution of independent jobs. [EVENT-018; FEEDBACK-011, FEEDBACK-019]

**Likely underlying mechanism.** A locally sensible setting was transferred across levels without preserving its meaning.

**Repeated vs one-off:** one clear incident.  
**Confidence:** high in the configuration and serialization; the explanation about copying examples is self-reported.

## 9. Spending attention without answering the requested question

**Observed behavior.** TASK-009 includes redundant checking and polling, followed by requests to stop polling and report aggregate completion/failure counts rather than inspect individual genes. [EVENT-035–036; FEEDBACK-016–017]

**Likely underlying mechanism.** More observation was equated with more progress without tying the observation to a decision or to the reporting granularity the user actually requested.

**Repeated vs one-off:** multiple manifestations within one long episode.  
**Confidence:** high in the mismatch; insufficient evidence for a broad model-level tendency.

## 10. Damaging configuration while editing the operational record

**Observed behavior.** TASK-013’s notebook narrative reports accidental overwriting of the methylation configuration during notebook editing. Recovery regenerated the configuration and reapplied the intended override. The first recovery dry-run failed and a subsequent retry reportedly passed. Scientific recovery remained explicitly unverified. [EVENT-030]

**Likely underlying mechanism.** Editing the operator record crossed into consequential configuration state.

**Repeated vs one-off:** one source-reported incident.  
**Confidence:** moderate in the event; low-to-moderate in the mechanism because the exact mutation sequence was not reconstructed.

## A proposed failure mode that is not established as recurrent: confusing submission with completion

The record does not strongly support treating false completion claims as a dominant recurrent problem. TASK-002 used the narrower phrase `submission_complete`; TASK-004 reported failure/incompleteness; TASK-007 reported no production launch; TASK-009 reported the replacement controller as running. TASK-008’s “operationally normal” reassurance warrants scrutiny, but it is not itself a claim of scientific endpoint completion.

# B. Cross-cutting behavioral patterns

## 1. The consequential issue is often a boundary crossing

Many corrections concern **where a decision belongs** rather than whether the decision is locally sensible:

- environment activation versus scientific workflow logic;
- dataset configuration versus scientific-method changes;
- diagnosis versus redesign;
- per-job resources versus workflow-wide concurrency;
- operational state versus scientific completion;
- requested aggregation versus per-feature inspection.

A useful interpretation is therefore not merely “the agent writes too much code.” It is that the agent sometimes makes a decision at a different level from the one the user delegated.

## 2. Some recovery work addressed problems introduced by the agent’s own additions

TASK-003’s added wrapper had a shell syntax error. TASK-007’s environment-building effort encountered dependency-download failures. TASK-009’s added fit and flag later required revert, termination, and resubmission.

The evidence supports the existence of this feedback loop: extra machinery can create a second layer of problems that then consumes further agent effort. The record does not quantify how much total debugging time this consumed.

## 3. “More autonomy” versus “less autonomy” is the wrong axis

The user repeatedly wanted **more initiative** in reaching the real endpoint and exposing independent work, while simultaneously demanding **less initiative** in changing scientific semantics, building alternate workflows, adding checks, or widening scope.

FEEDBACK-011–019 show both directions of correction within the same broader execution episode.

The desired behavior appears closer to:

> persistence within the authorized operation, restraint outside it.

## 4. Instructions themselves may have contributed to excess machinery

Archived `reproducible-project-work` required a substantial foundation before task work: environment specifications, a run-record-producing program, smoke config, execution files, a runbook, decision log, handoff, and history protection. Archived Route3 instructions required a scanner and evidence ledger.

Therefore, at least some artifact proliferation could have been **compliance with an expansive instruction regime**, rather than simple disobedience by the model. Missing exact loaded-skill versions prevent attribution of these instructions to specific incidents.

# C. User-correction themes

## Preserve the established workflow

**Agent behavior:** alternate controllers, wrappers, dataset-specific Snakefiles, bespoke stage chains.  
**User objection:** overengineering and deviation from the shared Snakemake framework.  
**Behavioral implication:** use the established implementation as the normal locus of operation rather than creating a parallel one.  
**Evidence:** FEEDBACK-002–006.

## Preserve scientific intent

**Agent behavior:** incorrect PC-selection interpretation; additional model fit and sample-alignment semantics.  
**User objection:** these were not the selected analysis.  
**Behavioral implication:** scientific choices are constraints, not implementation freedoms available to make execution easier.  
**Evidence:** FEEDBACK-009, FEEDBACK-012–014.

## Reach—but do not exceed—the endpoint

**Agent behavior:** stopping at a convenience checkpoint in one case; proposing continuation beyond an explicit stop in another.  
**User objection:** aim at the real endpoint unless explicitly stopped, and stop when explicitly told.  
**Behavioral implication:** initiative should track the authorized scientific endpoint in both directions.  
**Evidence:** FEEDBACK-018; EVENT-015.

## Use resources at the appropriate level

**Agent behavior:** runtime logic in the Snakefile; serializing independent work through `--cores 1`.  
**User objection:** environment belongs in submission logic; independent single-threaded jobs should still fan out.  
**Behavioral implication:** preserve the distinction between per-task settings and workflow-level execution policy.  
**Evidence:** FEEDBACK-010–011, FEEDBACK-019.

## Answer the requested question rather than expand the activity

**Agent behavior:** auditing when description was requested; redundant polling; per-gene inspection when aggregate counts were requested.  
**User objection:** the extra work was unnecessary and consumed time/tokens.  
**Behavioral implication:** match both operation type and reporting granularity to the request.  
**Evidence:** FEEDBACK-001, FEEDBACK-016–017.

Note that FEEDBACK-020 explicitly required validation through LSF. Not all operational ceremony in the history was autonomously invented by the agent.

# D. Skill-evolution observations

## 1. Several incident-to-rule links are unusually explicit

The historical packet documents a sequence rather than merely a thematic resemblance:

- **2026-08-22:** source authority was corrected, Route3 was retired, and the generic xQTL Snakemake skill was introduced after objections to specialized auditors and overengineered controls.
- **2026-08-24:** endpoint and concurrency corrections became explicit skill sections; concurrency wording was strengthened after further user correction.
- **2026-08-25:** the second-fit/restart discussion was followed by instructions covering scientific semantics, materialized task snapshots, runtime ownership, non-forceful reuse, descendant termination, and aggregate reporting.

See SKILLCHANGE-001–013.

These records show that incidents changed the instructions. They do **not** demonstrate that the changed instructions later eliminated those behaviors.

## 2. Evolution includes reversals, not simply increasing strictness

### Earlier: mandatory reproducibility foundation
Archived `reproducible-project-work` could require substantial supporting infrastructure before task work.

### Later: prefer existing project facilities
Current runners emphasize native project execution and discourage compliance-only duplication.

### Earlier: notebooks only as outputs
Archived `reproducible-project-work` said notebooks should not be worked in or used as records.

### Later: notebook as operational record
Current xQTL and COSI runners explicitly use operator notebooks as the executable command record.

### Earlier: scanner/evidence ledger
Archived Route3 prescribed a scanner and evidence ledger.

### Later: avoid independent scanner/ledger/verifier systems
Current runners prefer native workflow logs, outputs, and scheduler state.

The history therefore contains real shifts in what counts as acceptable reliability behavior.

## 3. Several useful concepts predate the current runners

Canonical source authority, decisive-error diagnosis, distinctions among execution states, and caution about completion markers already appear in archived Route3 and `snakemake-lsf-triage`.

The evolution is therefore partly about **how much new machinery those principles justify**, not about discovering fidelity or evidence for the first time.

## 4. Current runners intentionally disagree

`xqtl-runner` requires an exact-graph dry-run before production and after execution-affecting changes.

`cosi-runner` explicitly forbids adding a dry-run stage while still requiring meaningful terminal products and explicit accounting for missing scientific coverage.

Therefore:

- “avoid extra verification” does not mean “accept outputs without evidence”;
- “require a dry-run” is not a universal lesson supported across all workflows;
- domain-specific history matters.

## 5. A documented corrective-action side effect

TASK-009 shows a concrete case where a correction itself required further recovery: source was reverted while active materialized commands retained old arguments.

By contrast, the idea that later blanket rules themselves caused new failures remains a hypothesis. The historical packet does not contain controlled before/after tests of current rule effectiveness.

# E. Successful-behavior patterns and counterexamples

## 1. Native workflow execution produced a documented success

TASK-011 contains both successful dry-run evidence and production logs reporting all seven steps complete for the AIDA top-loci export.

Individual products were not independently inspected during historical extraction, so this establishes native workflow completion rather than independent scientific validation.

## 2. Success complicates a simple “new rules fixed everything” narrative

The successful TASK-011 command mixed Pixi activation, conda activation, and an `xqtl-reno` Snakemake executable—a combination the current `xqtl-runner` forbids.

That does not prove the current runtime rule is wrong. It shows that the historical record does not support a claim that the forbidden combination could never succeed.

## 3. Status reporting was sometimes accurate despite poor execution

Examples include:

- TASK-004 reported failed/incomplete analysis;
- TASK-007 explicitly said no production AIDA/MESA analysis had been launched;
- TASK-009 reported the replacement controller as running rather than complete;
- TASK-013 said recovery remained unverified.

Thus, accurate status reporting and execution reliability should not be treated as the same capability.

## 4. Recovery sometimes respected the intended boundary

TASK-009 records restoration of one-fit source, recognition that live materialized execution differed, authorized termination, and non-forceful resubmission.

TASK-013 records restoration from retained configuration-generation material.

Both are useful recovery patterns, but neither establishes completed scientific recovery in the evidence packet.

# F. Open questions and competing interpretations

## Was the main cause model behavior, instruction design, or workflow immaturity?

All remain plausible contributors.

The record contains:

- actual agent-introduced changes;
- expansive archived instructions;
- changing source authority;
- continuing shared-workflow development;
- ordinary scheduler/resource failures.

It does not isolate their causal contributions.

## How representative are these incidents?

The retained record is heavily concentrated in AIDA/MESA work and several related August sessions.

There is no denominator of all successful and failed tasks, no controlled model comparison, and no comparable incident series for every workflow.

The catalogue therefore describes recurring patterns **within the selected record**, not measured failure rates.

## Which problems were ordinary workflow or scheduler failures?

TASK-003 contains a memory-limit event as well as a wrapper syntax error. TASK-012 records supervisor walltime expiry and later runtime/queue changes.

Not every failed run should be attributed to agent overengineering.

## Did current rules prevent recurrence?

Unknown.

The evidence packet explicitly does not retroactively assign current runner controls to historical tasks. A current rule that resembles a past correction demonstrates policy responsiveness, not proven effectiveness.

## Does invention imply the agent failed to understand existing code?

Not necessarily.

The record proves that new wrappers, environments, and mechanisms were created. It does not always show whether this came from misunderstanding the existing system, following older instructions, judging the existing system inadequate, or deliberately choosing a different route.

# G. Candidate insights worth investigating next

## Hypothesis 1 — Added operational components can generate a second layer of recovery work

TASK-003, TASK-007, and TASK-009 suggest that some later blockers originated in wrappers, environments, or interfaces introduced during the attempted solution.

**Potential falsifier:** complete histories show that these additions were necessary and that most subsequent failures originated independently in the underlying workflow.

## Hypothesis 2 — Operational persistence and restraint over scientific changes are separate behavioral dimensions

TASK-008 undershot the endpoint while TASK-009 overreached on method within the same broader effort.

**Prediction:** improving one of these behaviors will not necessarily improve the other.

## Hypothesis 3 — Locally plausible decisions become problematic when transferred across levels

Examples:

- per-job conservatism became workflow-wide serialization;
- runtime selection moved into scientific workflow logic;
- TWAS alignment became a second scientific fit.

The possible common failure is loss of scope during translation rather than intrinsically unreasonable local reasoning.

## Hypothesis 4 — User objections track ownership and maintenance burden, not only whether something technically works

Corrections repeatedly target alternate workflows, misplaced runtime logic, extra checks, and unwanted audits.

**Prediction:** some technically functioning solutions will still be rejected when they create an additional thing the user must understand and maintain.

## Hypothesis 5 — Expansive reproducibility instructions may encourage agents to manufacture prerequisites

Archived `reproducible-project-work` and Route3 instructions plausibly encourage additional artifacts before execution.

**Important caveat:** demonstrating this causally requires evidence that those instructions were actually active during particular incidents.

## Hypothesis 6 — Rollback difficulty may be determined more by materialized execution state than by patch size

TASK-009 shows a small source-level revert that was operationally nontrivial because thousands of materialized descendants retained old commands.

This is currently one strong case rather than a demonstrated general law.

## Hypothesis 7 — Accurate reporting is compatible with poor task completion

Several unfinished or failed efforts were honestly labeled.

**Implication for analysis:** confidence in status reporting should not be used as a proxy for confidence in execution behavior.

## Hypothesis 8 — A visible operational record may improve reconstruction and recovery without preventing mistakes

TASK-011 preserves a traceable successful execution; TASK-013 preserves both an accidental config overwrite and its restoration.

The possible benefit is recoverability and interpretability, not automatic correctness.

# Bottom-line insight

The retained history does not reduce cleanly to “agents need more rules.”

A more faithful descriptive summary is:

> The recurring failures appear when the agent changes the level at which the problem is being solved: operation becomes workflow construction, execution repair becomes scientific-method change, per-task configuration becomes workflow policy, diagnosis becomes assurance infrastructure, or a requested endpoint becomes a convenient checkpoint.

At the same time, the evidence also shows that the opposite failure exists: insufficient persistence toward the authorized endpoint.

The open question is therefore not simply how to make agents more constrained or more autonomous. It is which kinds of initiative reliably remain inside the intended operational and scientific boundary.
