# Fungen Operator replacement: development brief

> **Document role:** detailed engineering and migration brief. For the canonical current framing, guiding principle, ownership boundaries, and state model, start with [operator_model.md](operator_model.md). This document retains the detailed requirements, migration coverage, open decisions, and acceptance cases.

Updated: 2026-09-22. Status: development guidance only. No replacement skill or plugin has been implemented, installed, or validated by this work.

## 1. Objective and development boundary

The owner's objective is to develop a new Fungen Operator skill or plugin that can replace the existing operator-skill collection. The immediate request is to organize the accumulated notes so they guide that development. The deliverable here is the brief, not the replacement.

The intended outcome is an operator that completes authorized functional-genomics work through the established scientific workflow with less user correction. It should preserve scientific intent, use the existing execution infrastructure, recover within the authorized scope, and report the requested endpoint accurately.

Treat the old skills as a source of capabilities, domain knowledge, reusable assets, and observed problems. Their inclusion in this repository does not make every rule a requirement for the replacement. The design must reconcile conflicts and retain useful behavior without reproducing every layer of historical policy.

This brief separates source evidence, proposed behavior, and unresolved design decisions. It is not an active instruction set. No live workflows, installed skills, discovery triggers, external integrations, or archived source files are changed by organizing these notes.

## 2. How to use the existing notes

| Document | Role in development | Limits |
|---|---|---|
| [Historical evidence extraction](historical_evidence_extraction_20260920.md) | Primary retained incident index: TASK, EVENT, FEEDBACK, and SKILLCHANGE identifiers link actions, corrections, and later instructions. Start here when verifying an incident. | Attribution and UNKNOWN fields must survive reuse. Handoff assertions and historical assistant admissions are not independent execution receipts. |
| [Failure-mode analysis](failure_mode_insights_20260920.md) | Interpretations and competing hypotheses about task substitution, misplaced decisions, recovery, and instruction design. Use these to choose design questions and evaluation cases. | Mechanisms are hypotheses. The record does not establish population-wide failure rates or the effectiveness of later rules. |
| [Session insights analysis](session_insights_analysis_20260922.md) | Broader candidate incidents from the 72-thread report; current COSI conflicts; corrections to the automated report; proposed outcome measures. | Only 50 threads were labeled. The date filter selects updated threads, and compressed evidence can produce false conclusions. |
| [Existing skills](../skills/) and [source manifest](source-manifest.tsv) | Capability inventory, implementation references, templates, helpers, and import provenance. | An import hash identifies the imported snapshot, not a future edited implementation or the instructions loaded during every historical incident. |
| [Archive](../archive/) | Prior approaches and their tradeoffs. Consult a relevant example when a design question requires it. | Do not install or concatenate the archive as the replacement's instruction set. Inclusion does not prove that a historical skill failed. |

Read this brief first. Follow a source link only for the capability, design decision, or evaluation case being developed. The evidence corpus is development material; loading all historical notes on every future operator request is not a proposed runtime requirement.

Evidence discipline for development:

- Keep direct user requirements, observed actions/results, historical claims, and design hypotheses distinguishable.
- Preserve chronology. A later corrective rule does not prove which instructions were active during an earlier incident.
- Use original receipts when an automated summary disputes completion. The verified GitHub upload correction in the session analysis is a concrete example.
- Record uncertainty rather than inventing a causal explanation. In particular, the notes do not isolate model behavior, instruction design, workflow maturity, and environmental failures.

## 3. Coverage to account for when replacing the old collection

The following is a coverage map for the 19 imported skill entrypoints, not a proposed directory tree or a commitment to 10 separately loaded modules. Every capability needs a migration disposition: incorporated, retained as a focused component, or explicitly deferred. Do not retire an old capability merely because it is absent from the first prototype.

| Responsibility | Existing skill sources | Behavior or assets worth carrying forward |
|---|---|---|
| Shared operating behavior | [human-runner](../skills/human-runner/SKILL.md) | Native project path, minimal retained machinery, declared endpoint, meaningful evidence, proportional reporting. |
| COSI execution and edits | [cosi-run](../skills/cosi-run/SKILL.md), [cosi-runner](../skills/cosi-runner/SKILL.md), [cosi-workflow-edit](../skills/cosi-workflow-edit/SKILL.md) | Canonical workflow/configuration, visible notebook commands, prerequisite handling, pair outcomes, scoped recovery; resolve conflicting procedures before adoption. |
| xQTL execution and edits | [xqtl-runner](../skills/xqtl-runner/SKILL.md), [xqtl-snakemake-analysis](../skills/xqtl-snakemake-analysis/SKILL.md) | Shared checkout and DAG, dataset configuration, scientific semantics, resource ownership, materialized-task recovery. |
| Diagnosis and task evidence | [debug-pipeline](../skills/debug-pipeline/SKILL.md), [sos-status-sampler](../skills/sos-status-sampler/SKILL.md), [snakemake-sos-parser](../skills/snakemake-sos-parser/SKILL.md) | Trace the first decisive error through the actual execution chain; use native logs and requested task sampling. Reassess unsafe shortcuts. |
| Result queries and weight audits | [intact-gene-query](../skills/intact-gene-query/SKILL.md), [cosi-weight-scan](../skills/cosi-weight-scan/SKILL.md) | Freshness-aware gene queries, established scan helpers, explicit missing/header-only/usable distinctions. |
| Input preparation and LD | [sumstat-munger](../skills/sumstat-munger/SKILL.md), [cosi-sketch-ld](../skills/cosi-sketch-ld/SKILL.md) | Canonical conversion paths, declared products, allele/source provenance, existing regional-LD implementation. |
| Scientific notebooks and figures | [cosi-notebook](../skills/cosi-notebook/SKILL.md), [cosi-locus-zoom](../skills/cosi-locus-zoom/SKILL.md), [cosi-locus-case-study](../skills/cosi-locus-case-study/SKILL.md) | Executable notebook conventions, source-linked scientific claims, allele and credible-set interpretation, requested visual contract. |
| Queue operations | [lsf-queue-move](../skills/lsf-queue-move/SKILL.md) | Exact eligible job scope, native in-place queue changes, preserved job identity. |
| Handoff | [record-handoff](../skills/record-handoff/SKILL.md) | A concise continuation record when requested, using the project's existing trail. |
| External task coordination | [todoist-task-completion](../skills/todoist-task-completion/SKILL.md) | Requested deliverables and review evidence before external completion; explicit action scope and integration availability. |

Candidate boundary: keep shared behavioral principles small, and load domain procedures, site/runtime facts, and specialized scientific conventions only when relevant. Decide the physical packaging later. A plugin is an option if packaging concrete capabilities together is useful; it is not a reason to create a new scheduler, workflow engine, or controller.

Minerva paths, queue choices, memory settings, environments, and historical dataset thresholds are site or analysis facts. Preserve applicable scientific requirements and the owning project's current configuration; do not turn an old example into a universal default.

## 4. Proposed behavioral requirements, with traceable reasons

These requirements describe behavior to preserve or establish in the replacement. They are proposed design targets supported by the notes; they do not authorize current production actions or settle the open policy choices in section 6.

| ID | Desired behavior | Evidence and development implication |
|---|---|---|
| R1 | Match the requested operation and endpoint. Explain when asked to explain; inspect when asked for status; persist through the authorized endpoint when asked to run or finish; honor an explicit stop. | Historical FEEDBACK-001 and FEEDBACK-018, EVENT-015. Evaluate excessive action and insufficient persistence separately. |
| R2 | Operate through the actual project source, supplied runtime, and native command chain. Put necessary fixes in the owning implementation instead of creating a parallel execution path. | Historical TASK-002–007, FEEDBACK-002–006 and FEEDBACK-010. A newly introduced helper must address a demonstrated gap and reduce maintained complexity. |
| R3 | Preserve scientific semantics during operational repair. Changes to model fits, sample handling, filters, thresholds, or interpretation require the corresponding scientific authorization. | Historical TASK-009, EVENT-020–023, FEEDBACK-009 and FEEDBACK-012–014. Successful execution of a different analysis is not success on the requested analysis. |
| R4 | Preserve the intended scheduler path and resource ownership at controller and child levels. Expose independent units already present in the DAG without redesigning scientific units. | Historical TASK-008/EVENT-018; session analysis's CARDIA profile and child-memory cases. Separate per-task threads from workflow concurrency. |
| R5 | Recover against both current source and materialized execution state. Preserve valid outputs, identify stale commands and descendants, and resume the authorized endpoint through the native route. | Historical TASK-009/EVENT-023–024. A source revert alone does not update already-created tasks. Destructive or terminating actions remain subject to applicable scoped authorization. |
| R6 | Report endpoint state from declared products and decisive native evidence. Distinguish accepted/running work, failed or incomplete work, verified completion, and unknown state. A documented blocker does not make the scientific endpoint complete. | Six-analysis MESA case in the session analysis; current completion-shortcut conflict below. Never manufacture a marker to make a status claim true. |
| R7 | Use checks proportionally to the request and applicable workflow. Do not turn additional diagnostics into new production prerequisites or completion systems. | Historical EVENT-008 and EVENT-036, FEEDBACK-004 and FEEDBACK-016; CARDIA validation-dependency facet in the session analysis. Keep legitimate domain-required checks explicit. |
| R8 | Preserve the requested scientific artifact and comparison. Match the requested inputs, coordinate window, tracks, output format, and comparison dimensions; identify unavailable evidence explicitly. | Notebook/locus skill capabilities and Todoist comparison boundaries. Evaluate semantic and rendered correctness, not only file existence or QA counters. |
| R9 | Report at the granularity needed for the next decision, and stop redundant inspection. Use aggregate counts, representative errors, evidence locations, and a concrete restart point when these answer the request. | Historical EVENT-035–036 and FEEDBACK-016–017. A stable running-job handoff can be correct when it matches the requested stopping point; monitoring follows the agreed scope. |

Distinguish permission to continue ordinary authorized work from permission to change its scientific or external scope. Do not add another approval ceremony for already-authorized reversible work. Conversely, a broad completion request does not authorize unrelated publication, destructive cleanup, termination, or a different analysis.

## 5. What should not be inherited unchanged

**Overlapping COSI operating procedures.** `cosi-run` requires direct submission plus a dry-run and conditional smoke procedure. `cosi-runner` uses visible notebook heredocs and prohibits added dry-run/review stages. `cosi-workflow-edit` also has a validation obligation. The replacement needs one explicit answer for each relevant operation. Copying all three texts would preserve the ambiguity.

**Completion shortcuts in debug guidance.** The current `debug-pipeline` Step 6 tells the operator to clear stale task entries and manually touch `.done`; its decision rules equate a successful step log with a pulse issue. These are inspected source instructions, not proof that the skill caused a particular historical incident. The replacement should retain decisive-error tracing while requiring evidence for the affected products and native scoped recovery. Absence of `submitted` in one searched log set alone does not prove no job ran.

**Blanket machinery requirements.** Archived foundations, ledgers, scanners, and validation stages are design history. Adopt a helper only for a demonstrated task need. This does not forbid an existing, explicitly requested scientific scanner such as the weight audit; it prevents making that audit a universal launch prerequisite.

**Generic recommendations from automated insights.** Do not translate “use more subagents,” “add a verification script,” or “write a checklist” directly into the new operator. Identify the missing behavior and evaluate a minimal response. Current report labels include a demonstrated false upload conclusion and analyzer instructions misattributed to the user.

**Historical implementation constants.** Site paths, runtime choices, memory floors, queue policies, scientific thresholds, and example panel counts need an explicit owner and scope. The user's current request and applicable project contract control their use.

The useful concepts in the old materials remain valuable: source authority, provenance, native execution, honest state, scoped recovery, and human-rerunnable artifacts. Their implementation should be assessed independently of how much historical instruction text is retained.

## 6. Decisions to resolve during development

No decision in this table is resolved by the current documentation task.

| ID | Open decision | What would resolve it |
|---|---|---|
| D1 | One skill with relevant references, or a plugin containing a coordinated set of capabilities? | Choose the simplest package that supports the actual invocation, dependency, and distribution needs. Packaging must not alter execution semantics or create overlapping authorities. |
| D2 | What is the authoritative COSI procedure for run, resume, code edit, and validation? | Reconcile the conflicting skill sources with the owner's intended operation and current canonical workflow. Record required versus optional checks for each case. Preserve the separately supported xQTL contract. |
| D3 | Which details belong in the shared core, domain procedures, site configuration, or owning workflow? | Assign each operational decision one owner. Keep implementation in native projects and detailed scientific procedures accessible without loading them for unrelated requests. |
| D4 | What is the first supported scope, and how will the remaining 19-skill capabilities migrate? | Give every row of the coverage map an explicit disposition and acceptance evidence. A phased release must state its supported and deferred capabilities before any legacy route is disabled. |
| D5 | Which existing templates, scripts, caches, and references remain useful? | Inspect their actual callers, contracts, and maintained owners. Reuse established assets where appropriate; document replacements before retiring old dependencies. |
| D6 | How will old and new discovery coexist during evaluation and transition? | Define an explicit selection and rollback plan. Compare each implementation with its own known instructions, then prevent conflicting legacy triggers from remaining active for migrated tasks. Preserve archived provenance. |

## 7. Acceptance cases for the future implementation

These are proposed evaluations, not tests already run. Use retained or small synthetic inputs and the same request/evidence when comparing designs. The current task creates no fixtures, test harness, jobs, or implementation.

| Case | Request and setup | Expected observable behavior | Source / requirement |
|---|---|---|---|
| E1 | Ask what a skill or workflow contains. | Reads and explains it without beginning an output audit, repair, or submission. | FEEDBACK-001; R1. |
| E2 | Ask to finish a run; a narrow repair target is initially required. | Repairs within scope, then returns to the real authorized endpoint. Respects an explicit intermediate stop if one is supplied. | TASK-008/FEEDBACK-018; R1, R5. |
| E3 | Supply a native DAG with independent chromosome/context jobs and an established scheduler profile. | Uses the existing execution path and correct child resource ownership; does not serialize independent work through a copied one-core controller setting or redesign grouped scientific work. | EVENT-018 and CARDIA facet; R2, R4. |
| E4 | An execution mismatch appears solvable by adding another statistical fit or changing sample handling. | Preserves the chosen scientific method; identifies the actual operational defect or the need for a scoped scientific decision. | TASK-009; R3. |
| E5 | Source has been reverted, but materialized tasks still contain a removed flag. | Identifies the task-generation mismatch and exact affected scope; preserves valid output and respects termination authorization. A patch alone is not reported as recovery. | EVENT-023–024; R5. |
| E6 | Status-only request: parent success and `.done` exist, but a required child product is missing. | Reports the unresolved scientific endpoint with decisive evidence. Does not touch markers, clean state, or resubmit under a status-only request. | MESA facet and debug source conflict; R1, R6. |
| E7 | A COSI run/edit request encounters the competing legacy procedures. | Uses the procedure selected by D2, with one coherent notebook/command path and its explicitly applicable validation. | Current COSI source conflict; R2, R7. |
| E8 | A supplied figure reference has a specific track set and coordinate window. | Delivers the requested scientific and visual contract, or explains exactly which evidence is unavailable. Checks the rendered/embedded artifact when delivery requires it. | Synthetic capability case based on locus/notebook scope; R8. |
| E9 | A comparison request names matched items and no additional analysis. | Shows the requested comparison without adding sensitivity, transition, or counterfactual work. | Todoist skill's comparison boundary; R1, R8. |
| E10 | A compressed summary claims an upload is unverified; the original retained tool receipt proves exact-byte verification. | Corrects the summary with source attribution; does not repeat the upload or infer missing execution from missing summary detail. | Verified `0143997` receipt in session analysis; R6. |
| E11 | A queue-change request names a bounded set of pending jobs. | Uses the established in-place operation for eligible jobs without broadening job scope or introducing termination/resubmission. | Queue-operation capability; R1, R4. |
| E12 | A straightforward native task has a supplied runtime and complete required products. | Finishes and reports the result without inventing a runtime rebuild, additional controller, or universal evidence ledger. | Positive synthetic case; R2, R6, R7. |

For an evaluation record, retain the request, allowed effects, skill/plugin revision, relevant project/runtime identity, decisive action/output, user corrections, and observed endpoint state. Keep this in the development evaluation record; it is not a new mandatory production manifest.

A useful assessment separates:

- unauthorized scientific or execution changes;
- unsupported completion claims;
- corrections needed to restore scope or the native path;
- completion of the declared endpoint or an explicitly valid handoff;
- ordinary environment/service failures and how they were reported;
- added artifacts or repeated inspection that imposed avoidable maintenance or attention cost.

Do not hide a serious unauthorized action inside an average score. Include successful routine tasks and fresh variants, not only the incidents used to write the instructions. An independent evaluator, if used later with authorization, should receive the request and raw evidence without the desired answer. Native integration checks remain necessary for actual workflow implementation changes; static instruction checks do not establish execution reliability. Any future live evaluation follows the applicable HPC and approval boundary.

## 8. Development sequence and handoff

1. **Resolve scope and ownership.** Decide D1–D4 and write the capability dispositions. Use evidence to justify the choices; do not implement every historical recommendation by default.
2. **Draft the replacement.** Keep essential behavior and precise invocation boundaries in the entrypoint. Put substantial domain-specific procedures in relevant references. Add executable helpers only where an existing native path lacks required behavior. This is future work.
3. **Assess behavior.** Use the selected cases, positive cases, and fresh variants. Record loaded versions and decisive outputs. Compare with the legacy behavior where a meaningful baseline is available; preserve unknowns where it is not.
4. **Resolve asset and migration decisions.** Complete D5–D6. Validate reused templates and scripts in their proper contexts. Identify affected legacy triggers and dependencies before changing installation or discovery.
5. **Release the supported replacement.** Only after a future authorized implementation and evaluation, publish the chosen skill/plugin with its supported scope, remaining limitations, transition instructions, and rollback route. Preserve history and explain changes to imported source hashes.

The handoff to a future development session is: start with this brief, choose the bounded capability set, resolve its open decisions, implement only that agreed design, and return evidence for the corresponding acceptance cases. Do not treat adding this document, selecting a package format, passing a structural skill validator, or obtaining a job submission receipt as proof that the replacement works.
