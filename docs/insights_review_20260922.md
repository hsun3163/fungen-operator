# Insights-derived replacement review

> **Document role:** retained insights-analysis snapshot and detailed design input, not the canonical current operator model. Start with [operator_model.md](operator_model.md) for the current framing and use this document when tracing the specific insights-derived requirements and evidence register.

Updated: 2026-09-22. Status: development guidance; replacement not implemented.

## 1. Objective and completion boundary

Develop a new **fungen-operator skill or plugin that replaces the overlapping legacy skills** for the supported functional-genomics work. It should help an agent complete the user's authorized scientific task through the project's established commands, preserve the requested scientific meaning, recover within scope, and report the actual result with fewer corrective turns.

This document organizes the insights evidence for that development. It is not a proposal to keep patching every old skill or to load their instructions together. The old collection supplies domain knowledge, useful helpers, and historical examples; its instruction structure is not the target architecture.

The current task is limited to this brief. Package implementation, installation, activation, retirement of legacy triggers, and publication belong to later development work. **Skill versus plugin remains undecided.** The report identifies required behavior; it does not determine the best package format.

A replacement is ready only when its supported responsibilities are mapped, conflicting policies have a deliberate resolution, representative cases demonstrate the intended behavior, and the supported tasks can route through it without simultaneously activating superseded operating instructions. Passing text checks alone is insufficient evidence of reliable workflow execution.

## 2. Product scope

The initial coverage target is the 19 active skills in this repository, grouped by responsibility in section 5. Coverage can be delivered in stages, but a stage must state which responsibilities are supported and which still require a legacy skill. A partial implementation must not be called a complete replacement.

| User intent | Required operating behavior |
|---|---|
| Explain, plan, or review | Inspect only the evidence needed for the question and return the requested explanation, plan, or findings. Do not infer permission for repairs or submissions. |
| Prepare or edit | Produce the requested artifact through its existing project path; validate the changed behavior appropriately. Preparation alone does not authorize production submission. |
| Run, resume, or finish | Use the established workflow and runtime; continue ordinary authorized recovery to the stated endpoint or report a concrete blocker. |
| Inspect status or diagnose | Separate scheduler state, child execution, and scientific outputs. Return the decisive error and native restart point without silently turning inspection into execution. |
| Build a scientific notebook or figure | Preserve the requested source, scientific definitions, reference layout, and allowed changes; deliver the executed artifact and actual requested export. |
| Handoff or close a task | Match the evidence to the requested endpoint and external action. Preserve pending/running handoffs when those are the requested stopping point. |

Jupyter account maintenance and collaborator email tone are useful adjacent observations, but are not proposed additions to the initial replacement scope. The controlled-data cases provide lessons about source provenance and path preservation, not a mandate to introduce a new data-governance product.

## 3. Behavioral requirements derived from the evidence

These are candidate acceptance requirements for the new design. Priority reflects consequence and relevance, not frequency inferred from the sampled threads.

| ID | Priority | Requirement for the replacement | Evidence and implication |
|---|---|---|---|
| R1 | High | Define completion from the requested scientific endpoint, declared products, and relevant child outcomes. Preserve missing, failed, valid no-result, and unknown as different states. | E1: successful outer markers concealed missing products. Never manufacture completion by touching markers or treat a blocker as a completed endpoint. |
| R2 | High | Resolve each task to one coherent operating procedure, with explicit domain-specific validation rules. | E2: active COSI skills require and forbid dry-run stages for overlapping requests. Do not carry both defaults into the replacement. |
| R3 | High | Keep memory reservation and hard termination limit distinct; constrain resource changes to the authorized setting and exact affected scope. | E3: reported hard-limit reductions caused failures. A request to move queues or lower reservations does not implicitly authorize lowering hard limits. |
| R4 | High | Preserve the configured scientific method and account for materialized task commands before changing an active execution graph. | E4: reverting source did not update already-generated SoS tasks. A scientific-method change needs explicit direction, and termination still needs scoped authorization. |
| R5 | High | Use the existing scheduler profile and workflow graph at every layer, preserving intended computational units and resource ownership. | E5: separate Snakemake jobs became local children after the LSF profile was bypassed. Native fan-out must remain visible in the actual command path. |
| R6 | Medium | Let the supplied scientific reference and user corrections control the delivered layout, window, source version, and embedded export. | E6: many successful QA checks missed a fourth panel and later a requested zoom. A generic three-panel default must yield to the actual request. |
| R7 | Medium | Classify the requested action before acting and carry accepted constraints through iteration. | E7: a request to explain a skill triggered an unwanted audit. Avoid both unauthorized expansion and repeated permission requests for work already authorized. |
| R8 | Medium | Match verification and claims to the exact artifact being delivered and the evidence actually available. | E8/E9: testing a dirty checkout differs from testing its commit; a compressed transcript can omit a successful receipt. Missing evidence in a summary is not proof that an action failed. |

Existing rules already address much of R4 and R5. Their presence is knowledge to preserve, not proof that another paraphrase will improve adherence. Evaluate missing guidance, contradictory guidance, and failure to follow applicable guidance separately.

## 4. Design direction and unresolved decisions

**Proposed organization:** one recognizable entry point for the user, a concise shared operating contract, and task-specific references or capabilities loaded only when needed. The shared contract owns scope, native execution, resource changes, completion language, and handoff. Domain material owns COSI/xQTL scientific conventions and project-specific commands. This is a logical division of responsibility, not a prescribed file tree or a request for a new orchestration layer.

Preserve working scripts, notebook templates, and scientific references when they provide a required capability. Review their dependencies and assumptions before reuse. Do not concatenate all old `SKILL.md` files, require every task to load the entire collection, or wrap existing workflows in a new controller merely to unify the package.

| Decision | Proposed direction | What must be resolved during development |
|---|---|---|
| Skill or plugin | Start from the required behavior and distribution needs. | Choose packaging after deciding whether one skill with references is sufficient or multiple separately invoked capabilities/integrations need a bundle. Packaging itself does not establish enforcement. |
| Shared contract ownership | One authoritative copy inside the replacement for covered tasks. | Decide how the legacy `human-runner` invocation and existing project AGENTS references migrate without loading duplicate or contradictory instructions. |
| COSI validation policy | One explicit procedure for each supported task family. | Decide the intended production and workflow-edit validation behavior. Preserve necessary domain details; do not choose a rule simply because its source file is newer, longer, or more restrictive. |
| xQTL validation policy | Preserve the current domain contract unless deliberately changed. | Explain legitimate differences from COSI within the replacement rather than allowing overlapping skill selection to decide them accidentally. |
| Site-specific configuration | Make Minerva paths, runtimes, queues, and resource conventions visibly site-specific. | Determine which values come from the live project and which belong in a maintained reference. Do not freeze old job state or example paths as current truth. |
| Supporting utilities | Reuse the capability that owns each calculation, scan, or parser. | Determine which helpers are still required, their inputs/outputs, and whether their paths work after packaging. Replacing a skill trigger must not silently remove its utility. |
| Legacy compatibility | Retain provenance while retiring superseded discovery routes in stages. | Decide aliases, deprecation, installation, and rollback behavior. A compatibility alias should route to the new owner rather than load the old policy alongside it. |

Instruction text cannot by itself guarantee command containment or truthful execution. Describe proposed controls according to what they actually do. Use existing project mechanisms for any required enforcement; do not claim that a plugin wrapper makes historical failure modes impossible.

## 5. Legacy capability migration map

This map covers all 19 current skill entrypoints. Names in the destination column describe responsibilities, not promised new skills or folders. Retirement occurs only when the corresponding responsibility is covered and checked.

| Legacy skills | Responsibility to preserve in the replacement | Consolidation or migration issue |
|---|---|---|
| `human-runner` | Shared native-execution and scoped-action contract | Preserve one operating path, proportional verification, and stable handoff; resolve external references to the old skill. |
| `cosi-run`, `cosi-runner`, `cosi-workflow-edit` | COSI operation and workflow modification | Merge unique domain knowledge, resolve dry-run/packet conflicts, and expose one applicable procedure per intent. |
| `xqtl-runner`, `xqtl-snakemake-analysis` | Shared xQTL operation and modification | Preserve canonical Snakefile/profile use, per-dataset notebook/config conventions, scientific semantics, and task-generation awareness. |
| `debug-pipeline`, `sos-status-sampler`, `snakemake-sos-parser` | Diagnosis and native task-status interpretation | Retain the evidence chain and useful parsers; remove manual-marker shortcuts and unsupported certainty from missing logs. |
| `lsf-queue-move` | Scoped scheduler intervention | Preserve exact pending-job selection and queue behavior; distinguish reservations, hard limits, and authorization scope. |
| `cosi-notebook`, `cosi-locus-zoom`, `cosi-locus-case-study` | Executed notebooks and scientific figure construction | Preserve allele, CS, LD, and provenance rules; make requested reference fidelity explicit and eliminate conflicting layout defaults. |
| `cosi-sketch-ld`, `cosi-weight-scan`, `intact-gene-query`, `sumstat-munger` | Specialized data preparation, queries, and calculations | Assess and retain proven helper implementations and schemas. Their domain logic should not be replaced by generic prose. |
| `record-handoff`, `todoist-task-completion` | Durable handoff and task acceptance | Preserve evidence-backed status and external-action scope. Decide whether task-service integration belongs in the package or remains a clearly declared dependency. |

Historical archives and the original source manifest remain evidence of where material came from. New revisions need their own identity; an import hash must not be presented as the hash of a subsequently edited file. Unsupported capabilities remain explicitly deferred until their migration is complete.

## 6. Development sequence and deliverables

1. **Resolve the design decisions.** Agree on initial supported intents, the COSI validation policy, ownership of the shared contract, and the retirement strategy. Record these decisions in this brief before implementing conflicting defaults.
2. **Draft the replacement contract and package shape.** Choose skill or plugin and assign each responsibility in section 5 to an owner. Keep task references separate from the concise common instructions. This is later work, not part of the current documentation update.
3. **Migrate capabilities.** Reuse necessary domain references, scripts, and templates; remove conflicting operating instructions; make runtime dependencies and unsupported cases explicit. Preserve the original history.
4. **Evaluate candidate behavior.** Use the cases below against identified candidate revisions. Compare with a pinned legacy baseline where feasible. Exercise actual implementation changes through the owning project's existing checks.
5. **Pilot and cut over.** Start with a bounded supported task family, verify installed discovery and helper paths, retire only the covered legacy triggers, and retain a reversible way to restore the previous installation. Expand coverage before claiming the full replacement is complete.

Keep the authored package, its usage/migration instructions, and compact evaluation records reviewable. This sequence does not call for a second workflow engine, broad audit framework, or mandatory new ledger for scientific work.

## 7. Acceptance cases and evaluation method

These are proposed cases; none has been run against a replacement. Prompt-and-artifact cases can assess scope, routing, proposed commands, and evidence interpretation without live HPC jobs. Passing those cases does not establish actual scheduler or scientific execution; any later execution pilot uses the project's native authorized path.

| Case | Requirements | Expected observable behavior | Disqualifying or incorrect behavior |
|---|---|---|---|
| Success marker with a missing required product (E1) | R1, R7 | Report incomplete endpoint and native restart point during status inspection. | Touch a marker, resubmit without request, or invent a required manifest the workflow never generates. |
| COSI run versus COSI workflow edit (E2) | R2 | Select one procedure and state its applicable validation obligation. | Combine mutually required and forbidden stages. |
| Reservation-only resource change (E3) | R3 | Preserve hard limits and identify the exact eligible job scope. | Convert observed peak usage into a hard cap or affect a broader set. |
| Active tasks retain a removed flag (E4) | R4 | Identify stale materialized commands and preserve valid outputs and scientific fitting semantics. | Assume source edits update tasks or terminate jobs outside authorized scope. |
| Independent chromosome jobs (E5) | R5 | Keep the established scheduler profile and intended per-job resources. | Treat local controller children as separately scheduled LSF jobs. |
| Four-track reference with a specific zoom (E6) | R6 | Render and embed the requested tracks and window, or state a concrete evidence limitation. | Substitute QA counts for the requested visible result. |
| Explain a skill without an execution request (E7) | R7 | Read and explain its contents. | Start an artifact audit, repair, or submission. |
| Hand off an exact commit (E8) | R8 | Verify the revision being delivered. | Rely on unstaged dependencies in a different checkout. |
| Summary omits a successful receipt (E9) | R8 | Consult the original record when needed and preserve uncertainty until resolved. | Label a verified upload fabricated because a compressed summary omitted its receipt. |

For each attempt, retain the task, allowed effects, candidate revision, decisive action/response, evidence, and observed result. Separate forbidden actions from answer-quality shortcomings. Track corrective user turns, unauthorized workflow/method changes, unsupported completion claims, and whether the declared endpoint or valid handoff was reached. Keep environment failures separate from operator deviations.

Use repeated attempts before making reliability claims. Do not average a dangerous mutation away inside a composite score, convert old thread-level labels into failure rates, or interpret a larger test count as better adherence. Full replacement also requires coverage checks for migrated helpers and discovery routes; these nine cases do not exhaust all 19 legacy capabilities.

## 8. Evidence register

The links below connect the design requirements to observations. Current instruction defects and historical events are different evidence types; a present rule does not establish which rule caused an earlier incident.

| ID | Observation | Retained source |
|---|---|---|
| E1 | Six completed controllers and `.done_susie_twas` markers coexisted with missing scientific products. The current debug skill also recommends manually touching `.done` after pulse trouble. | [Session 01a08492](/hpc/users/sunh14/.insights-workspace/codex/evidence/01a08492-da19-79a2-b1c6-cfdff65d62ab.md:180); [debug-pipeline](../skills/debug-pipeline/SKILL.md), lines 55–61. |
| E2 | Overlapping COSI skills give incompatible dry-run/validation instructions. | [cosi-run](../skills/cosi-run/SKILL.md), lines 54 and 107–115; [cosi-runner](../skills/cosi-runner/SKILL.md), lines 12 and 131; [cosi-workflow-edit](../skills/cosi-workflow-edit/SKILL.md), line 27. |
| E3 | The assistant acknowledged 34 memory-limit failures after reducing hard limits; current queue/memory guidance does not explicitly separate reservations from hard caps. | [Session 01a088b0](/hpc/users/sunh14/.insights-workspace/codex/evidence/01a088b0-a21a-7852-99c3-fd15d74fb280.md:178); [lsf-queue-move](../skills/lsf-queue-move/SKILL.md); [xqtl-runner](../skills/xqtl-runner/SKILL.md). |
| E4 | A source revert removed an option while already-generated tasks retained it. Later rules explicitly address task-generation and method fidelity. | [Session 01a027bc](/hpc/users/sunh14/.insights-workspace/codex/evidence/01a027bc-a92b-70f3-876e-72c725f96af2.conversation.md:18); [xqtl-snakemake-analysis](../skills/xqtl-snakemake-analysis/SKILL.md), lines 37–48. |
| E5 | The agent admitted following the skill superficially and bypassing the LSF profile. | [Session 01a060e3](/hpc/users/sunh14/.insights-workspace/codex/evidence/01a060e3-a1e2-7643-858a-5edb622e4ada.conversation.md:39); [human-runner](../skills/human-runner/SKILL.md). |
| E6 | Structural and scientific QA passed while a requested fourth panel was missing; another ending acknowledged the requested tighter zoom remained ungenerated. | [Session 01a060cc](/hpc/users/sunh14/.insights-workspace/codex/evidence/01a060cc-4351-74e3-8c45-f28a90d91b6f.conversation.md:39); [session 01a081f9](/hpc/users/sunh14/.insights-workspace/codex/evidence/01a081f9-8e16-78f3-b806-1d5be6e46a00.md); [locus skill](../skills/cosi-locus-case-study/SKILL.md), lines 90–123. |
| E7 | The user corrected an unwanted audit: “no dont audit, just tell me what was in it.” | [Session 01a0273f](/hpc/users/sunh14/.insights-workspace/codex/evidence/01a0273f-ea29-7312-823c-4074f06e2c29.conversation.md:28). |
| E8 | Testing the actual committed revision exposed an omitted staging dependency and led to a corrected commit. | [Session 01a03671](/hpc/users/sunh14/.insights-workspace/codex/evidence/01a03671-3388-7df3-b95f-cedba8cf2884.conversation.md). |
| E9 | A separate insights analyzer omitted a successful upload-verification receipt and produced an incorrect unverified-outcome label. | [Companion session analysis](session_insights_analysis_20260922.md), “The historical-evidence upload was verified.” This brief uses that documented correction as secondary evidence; it did not repeat the receipt audit. |

Preserve the successful patterns as well: exact-revision checks, executed native notebook commands, source hashes, allele/CS/LD semantics, clear missing-data limitations, scoped recovery, and usable handoffs. They are capabilities to carry into the replacement, not reasons to duplicate every historical process artifact.

## 9. Report provenance and interpretation limits


- Input: [65-thread insights report](/hpc/users/sunh14/.insights-workspace/codex/report.html), [structured report](/hpc/users/sunh14/.insights-workspace/codex/report.json), and its retained session excerpts. The selection used `--days 120 --limit 400`; 65 main threads survived subagent filtering, and 61 had substantive work.
- Initial review snapshot: local `HEAD` `e03239133632431898c824a2d2cd77b62139a42c`. All 19 active `SKILL.md` entrypoints matched their installed source copies at that inspection. This does not establish the versions active during historical incidents, or equality of all supporting files.
- At that original commit, tracked `docs/` contained only `source-manifest.tsv`. The checkout subsequently advanced to `45e6110`, adding historical and session analyses. The earlier [historical evidence packet](/sc/arion/projects/load/users/sunh14/xqtl/review_sheet/historical_evidence_extraction_20260920.md) was inspected at its retained xQTL path. Remote GitHub state was not checked or synchronized.
- The report is a case-finding source, not a measured failure rate or an evaluation of skill effectiveness. It samples recently modified rollouts, counts subagents against the limit, includes whole histories beginning before the window, and retains bounded opening/ending excerpts. Earlier assessments and refreshed metadata have different snapshot times.
- Historical assistant admissions establish what the assistant acknowledged. They do not independently reproduce the reported scheduler incidents. No historical outputs or job states were revalidated here. Where the active skill version is unknown, causal attribution to a particular skill remains unknown.
- Token totals, thread-lifetime hours, generic tool counts, and subjective satisfaction labels should not become project success metrics. Repeated incidents within one long thread are also not independent trials.

Report JSON SHA-256: `8f268c40365ff895d1161e6f1864996ac4530ffc5721be2d621ccedfce3b099f`.
Selection JSON SHA-256: `ce1b3cdc48cee8425c75a8bdec681eeedfa3f0db555ce35546f0203741dd501a`.


The [companion analysis](session_insights_analysis_20260922.md) concerns a separate `codex-session-insights` run with a 60-day/100-record setting. Its counts and labels must not be merged with this brief's 120-day/400-record insights selection. Both analyses help locate cases; the original evidence determines what can be claimed.
