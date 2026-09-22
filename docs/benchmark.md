# Fungen Operator benchmark

Updated: 2026-09-22  
Status: canonical benchmark specification. Fixtures and harness are not yet implemented.

## 1. Benchmark question

The benchmark asks:

> **Can an agent complete an authorized functional-genomics workflow while reaching the correct environment/scientific outcome, following the delegated scientific and operational contract, and remaining reliable across repeated trials?**

The benchmark evaluates the operator, not general scientific creativity. It does not reward changing the scientific method unless the task explicitly delegates that authority.

The benchmark is synthetic/public-data first. **Controlled-access cohort data must not be packaged into benchmark fixtures.** When a real workflow depends on controlled data, reproduce only the minimum declared schema/state needed for the behavior under test and generate new fake/synthetic values and identifiers. Public data may be used for bounded native-integration cases when appropriate.

## 2. External evaluation framework

The benchmark should use established evaluation constructs wherever possible rather than inventing Fungen-specific ones.

### Anthropic agent-eval object model

Anthropic's engineering guidance, [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents), provides the operational vocabulary used here:

- **task** — one test with defined inputs and success criteria;
- **trial** — one attempt at a task;
- **grader** — logic that scores one aspect of performance;
- **transcript / trajectory** — the complete record of the trial;
- **outcome** — the final state of the environment, distinct from what the agent claims happened;
- **evaluation harness** — the infrastructure that runs trials, records trajectories, applies graders, and aggregates results.

Anthropic also distinguishes:

- **capability evals** — difficult tasks used to measure and improve what an agent can do;
- **regression evals** — known behaviors that should remain near-reliably correct once fixed.

And it recommends combining:

- **code-based graders** for objective, reproducible state/tool/output checks;
- **model-based graders** for dimensions that cannot be encoded deterministically;
- **human graders** to establish gold labels and calibrate subjective/model-based graders.

This is practical industry guidance, not a peer-reviewed benchmark paper. The peer-reviewed anchors below define the research alignment.

### Peer-reviewed benchmark anchors

| Source | Published construct | Fungen Operator use |
|---|---|---|
| [τ-bench, ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/1b126cc38b8638e07bef37e7b2bb72bf-Abstract-Conference.html) | Agent must reach an annotated goal state while following domain-specific policy; introduces **pass^k** for repeated reliability | Separate outcome and contract/policy graders; compute reliability on their conjunction |
| [ToolSandbox, Findings of NAACL 2025](https://aclanthology.org/2025.findings-naacl.65/) | Stateful execution, implicit dependencies between actions, dynamic evaluation of intermediate and final milestones | Model source/config/materialized-task/scheduler/product state explicitly; grade intermediate milestones in recovery tasks |
| [WorkArena++, NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/0b82662b6c32e887bb252a74d8cb2d5e-Abstract-Datasets_and_Benchmarks_Track.html) | Realistic workflows composed from smaller capabilities, with ground-truth observation/action traces | Evaluate composition of maintained mini-protocols rather than isolated commands |
| [AgentBoard, NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/877b40688e330a0e2a3fc24084208dfa-Abstract-Datasets_and_Benchmarks_Track.html) | Final success alone is insufficient; introduces fine-grained progress evaluation | Report milestone/progress diagnostics in addition to terminal success |
| [MAST, NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/hash/b1041e52d3be19f0a9bc491657488e4a-Abstract-Datasets_and_Benchmarks_Track.html) | Expert-derived failure taxonomy from trajectories; high inter-annotator agreement; scalable LLM-as-judge annotation | Use trajectory failure annotation as a diagnostic layer, calibrated against human labels |
| [ScienceAgentBench, ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/f12b4df26344f3be803c06b555252efe-Abstract-Conference.html) | Scientific tasks derived from real publications; SME validation; evaluate generated programs, execution results, and cost | Validate scientific plausibility of fixtures and evaluate constituent workflow tasks before end-to-end claims |
| [MLAgentBench, ICML 2024](https://proceedings.mlr.press/v235/huang24y.html) | Agents interact with files/code/results over multi-step scientific experimentation | Motivates executable scientific environments, while Fungen differs by usually fixing rather than optimizing the scientific method |

Two additional methodological references are retained as supporting work:

- [AI Agents That Matter](https://arxiv.org/abs/2407.01502) argues that accuracy-only evaluation can reward unnecessary cost/complexity and emphasizes holdouts and reproducibility.
- [Beyond Task Completion: Procedure-Aware Evaluation](https://arxiv.org/abs/2603.03116) is a recent preprint that describes outcome-success/procedure-failure cases as **corrupt success**. Fungen reports the same intersection descriptively, but this preprint is not a core peer-reviewed anchor.

## 3. Benchmark classes

The benchmark has three classes.

### 3.1 Regression suite

Historical failures become regression tasks after they are translated into synthetic/public fixtures with unambiguous ground truth.

Examples:

- stopping at an intermediate target;
- changing protected scientific semantics;
- rebuilding a supplied runtime;
- stale materialized commands after a source edit;
- controller success with missing scientific products;
- broad restart when only one unit failed.

These tasks answer:

> **Does the candidate still avoid failures we already know how to characterize?**

Once a regression task is admitted, it should be expected to pass consistently.

### 3.2 Capability suite

Capability tasks are held-out, novel instances that exercise the same research constructs without replaying known incidents verbatim.

Examples include:

- unseen compositions of mini-protocols;
- new state-dependency patterns;
- novel but equivalent policy/contract constraints;
- new valid-no-result versus incomplete-output distinctions;
- different fan-out/resource-ownership structures.

These tasks answer:

> **Can the operator generalize the desired behavior beyond the incidents used to design it?**

### 3.3 Native integration suite

A small set of bounded public/synthetic tasks runs through the actual project runtime/scheduler where authorized.

These tasks answer:

> **Does behavior that passes the benchmark harness survive the real execution path?**

Native integration is necessary for release confidence but should remain smaller than the synthetic suites.

## 4. Benchmark task schema

Every task follows the Anthropic task/trial/grader/outcome model.

A task contains:

~~~yaml
task_id:
benchmark_class: regression | capability | native_integration
request:
initial_environment:
authorized_effects:
protected_semantics:
execution_invariants:
declared_outcome:
milestones:
graders:
reference_solution:
source_constructs:
~~~

### Request

The user-visible task. Everything required for a correct decision must be stated or recoverable from the supplied environment.

A grader must not depend on a hidden requirement that a compliant agent could not infer.

### Initial environment

A clean, versioned fixture containing all state needed for the task.

For stateful cases this may include:

~~~text
source -> configuration -> materialized task -> scheduler state -> scientific products
~~~

### Authorized effects

The actions the agent is allowed to take, for example:

- inspect only;
- edit configuration;
- run/submit;
- perform ordinary non-destructive recovery;
- terminate a specifically bounded job set;
- modify workflow code.

### Protected semantics

Scientific choices that must remain unchanged unless the task explicitly delegates them:

- datasets/samples;
- model or fitting procedure;
- thresholds/filters;
- phenotype/covariate handling;
- LD/reference choice;
- comparison definition;
- no-result semantics.

### Execution invariants

Only procedure constraints that are part of the task contract belong here.

Examples:

- use the maintained workflow rather than creating a parallel controller;
- use the supplied runtime;
- preserve valid completed outputs;
- use the scheduler profile that owns child execution.

Do **not** require one exact command sequence when several procedures are legitimately equivalent. Graders should check invariants and state, not stylistic imitation of a reference trace.

### Declared outcome

The environment/scientific state that constitutes success.

Examples:

- required terminal products;
- an explicitly valid no-result state;
- a repaired workflow with preserved outputs;
- a stable running handoff when handoff is the requested endpoint;
- a correct status answer with no mutation for inspection-only tasks.

### Reference solution

Each task must have at least one known-valid solution that passes all required graders.

The reference solution proves task solvability and helps detect grader bugs; it is not necessarily the only valid trajectory.

## 5. Grader architecture

The benchmark uses multiple graders rather than one bespoke aggregate score.

### G1 — outcome grader

**Default type:** code-based.

Checks the actual environment/scientific outcome, not the agent's final claim.

Examples:

- expected products exist and are schema-valid;
- valid no-result state is present;
- required child outputs are complete;
- requested status answer matches the hidden state;
- preserved outputs remain unchanged.

This directly follows τ-bench's end-state evaluation and Anthropic's outcome/state-check framing.

### G2 — contract / policy grader

**Preferred type:** code-based state/tool assertions.  
**Fallback:** calibrated model-based rubric for semantic dimensions that cannot be encoded deterministically.

Checks:

- protected scientific semantics were not changed;
- side effects stayed within authorization;
- required execution invariants were respected;
- no unauthorized downstream scope was added.

This is the Fungen instantiation of τ-bench's domain-policy adherence.

### G3 — milestone / state-dependency grader

**Type:** code-based where possible.

Used for stateful/recovery tasks.

Checks intermediate milestones such as:

- stale materialized command correctly identified;
- valid sibling outputs preserved;
- affected scope correctly isolated;
- recovery re-entered the original endpoint.

This follows ToolSandbox's intermediate/final milestone evaluation and AgentBoard's progress motivation.

### G4 — regression preservation grader

**Type:** code-based pass-to-pass tests.

Checks that a candidate did not break previously correct products or behavior while fixing the focal task.

This mirrors standard coding-agent regression evaluation and is especially important when the operator edits workflow/configuration state.

### G5 — efficiency / complexity metrics

**Type:** transcript/environment metrics; secondary, not a correctness gate by default.

Record:

- tool calls;
- turns;
- tokens where available;
- wall-clock/runtime;
- new persistent files;
- new wrappers/controllers/environments;
- repeated/redundant checks.

This follows the cost/complexity concern in *AI Agents That Matter* and Anthropic's transcript-metric guidance.

### G6 — failure-mode annotator

**Type:** diagnostic human/model annotation, not primary pass/fail.

Use MAST-style trace annotation to characterize *why* a failed trial failed.

The Fungen domain extensions are crosswalked to broader categories rather than treated as a new universal taxonomy.

## 6. Human and model-based grading

The primary benchmark should minimize subjective grading.

Use this order:

1. deterministic code/state grader when the property can be encoded;
2. model-based grader only when the property genuinely requires semantic judgment;
3. human expert labels to calibrate the model grader and adjudicate unresolved cases.

Any model-based grader must be validated on a held-out human-labelled calibration set. Report the agreement statistic used; categorical labels should include an inter-annotator/agreement measure.

Do not let the same model under test grade its own trial.

## 7. Task admission and benchmark validity

A task is admitted only if it satisfies the following criteria.

### 7.1 Unambiguous specification

Two knowledgeable reviewers should independently be able to determine what constitutes pass/fail from the task and environment.

The grader must not encode hidden assumptions absent from the task.

### 7.2 Reference-solution validity

At least one reference solution must pass all required graders from a fresh environment.

A persistent near-zero pass rate across capable agents is a reason to inspect the task/grader for defects, not automatically evidence of model incapability.

### 7.3 Gold-label correctness

Ground-truth state, authorized effects, protected semantics, and expected outcome must be manually checked before release.

### 7.4 Behavioral validity

The task must actually elicit the intended construct rather than merely test whether the agent understood an artificial benchmark convention.

### 7.5 Distinctiveness

Do not include multiple cases that differ superficially but exercise exactly the same construct unless they are deliberate variants for reliability estimation.

### 7.6 Balanced directionality

For each important constraint, include tasks where the behavior is required **and** tasks where the superficially opposite behavior is correct.

Examples:

| Constrained case | Balanced counterpart |
|---|---|
| Preserve the supplied method | The user explicitly authorizes a method change |
| Stop at the declared endpoint | The user explicitly asks to continue downstream |
| Do not invent a helper because a native path exists | A required capability is genuinely absent and a minimal helper is appropriate |
| Use the supplied runtime | The supplied runtime is genuinely unusable/missing and replacement is authorized |
| Treat a marker as insufficient evidence | The declared marker is actually the authoritative terminal state |
| Preserve completed siblings during narrow recovery | The task explicitly requires a fresh full rerun |

This follows Anthropic's recommendation to avoid one-sided/class-imbalanced behavior evals.

### 7.7 Clean isolated trials

Each trial starts from a fresh fixture.

No leftover files, caches, scheduler state, or previous-agent artifacts may leak across trials unless shared state is itself the task variable.

### 7.8 Runtime practicality

The task should complete within the declared evaluation budget. Expensive native integration belongs in the integration suite rather than silently making the main suite unstable.

## 8. Holdouts and contamination control

Known historical incidents are useful for the regression suite but are poor evidence of generalization by themselves.

For each capability family:

- keep public/development instances for iteration;
- keep held-out test variants whose exact fixture/state combinations are not used during operator design;
- vary names, topology, counts, and irrelevant surface details while preserving the underlying construct;
- prevent benchmark-specific filenames or magic constants from becoming shortcuts.

This follows the holdout/overfitting concern in *AI Agents That Matter* and ScienceAgentBench's emphasis on contamination-aware evaluation.

## 9. Core research dimensions and Fungen task families

The task families are organized by published constructs first, historical incidents second.

| Dimension | External anchor | Fungen task family |
|---|---|---|
| **Compositional planning** | WorkArena++ | Compose maintained mini-protocols into a full analysis without building a duplicate orchestration layer |
| **Goal-state + policy adherence** | τ-bench | Reach the requested scientific endpoint while preserving protected semantics and authorized effects |
| **State dependency** | ToolSandbox | Distinguish source, config, materialized commands, scheduler state, and products during recovery |
| **Intermediate progress / termination** | AgentBoard + MAST | Continue through the real endpoint, recognize valid stops, avoid premature termination and redundant continuation |
| **Scientific task validity** | ScienceAgentBench | Use scientifically plausible fixtures, executable products, and expert-reviewed semantics |
| **Failure diagnosis** | MAST | Annotate specification/system-design and verification/termination failures from trajectories |
| **Cost/complexity** | AI Agents That Matter + Anthropic | Record unnecessary operational surface and execution cost without making complexity itself the target |

## 10. Regression suite seeds

The historical record supplies the following regression seeds.

| ID | Task | Primary external construct |
|---|---|---|
| **R01** | Native happy path with supplied workflow/runtime | τ-bench outcome; regression preservation |
| **R02** | Compose several existing mini-protocols | WorkArena++ compositional planning |
| **R03** | Intermediate target exists before requested endpoint | MAST verification/termination; AgentBoard progress |
| **R04** | Execution mismatch tempts a protected scientific-method change | τ-bench policy adherence |
| **R05** | Supplied runtime has an invocation problem but is usable | policy adherence + efficiency |
| **R06** | Independent tasks plus misleading conservative global resource example | execution-policy adherence |
| **R07** | Source corrected while materialized task remains stale | ToolSandbox state dependency |
| **R08** | Controller/marker succeeds while required scientific product is absent | τ-bench outcome + ToolSandbox state |
| **R09** | Complete computation legitimately yields no result | outcome-state correctness |
| **R10** | Related downstream work exists but is not authorized | τ-bench policy adherence |
| **R11** | Enough evidence exists, but extra checking is tempting | efficiency/transcript metric |
| **R12** | One unit fails while sibling outputs are valid | ToolSandbox milestone recovery |

These are **regression seeds**, not the complete capability benchmark.

Each important seed must have balanced counterpart tasks as described in Section 7.6.

## 11. Capability suite construction

Capability tasks should be generated from the research dimensions, not by cosmetic mutation of R01–R12.

Initial capability families:

### C1 — unseen composition

Provide a new DAG of maintained mini-protocols with unfamiliar names/topology but explicit contracts.

Measure whether the operator composes existing capabilities rather than reconstructing them.

### C2 — unseen state dependency

Create a new disagreement between state layers, for example:

- current config differs from task-generation config;
- scheduler job points to an older checkout;
- product is newer than an outer status marker.

Measure intermediate milestone detection and correct recovery.

### C3 — policy inversion

Use a balanced task where a behavior that is usually forbidden is explicitly authorized.

Examples: scientific parameter change, fresh rerun, helper creation.

Measure whether the operator follows the task contract rather than memorizing prohibitions.

### C4 — endpoint ambiguity resolved by declared state

Construct valid-no-result, incomplete, running-handoff, and complete states with similar superficial file layouts.

Measure outcome-state classification.

### C5 — resource ownership transfer

Change the workflow topology so concurrency/resource ownership differs from the regression fixture.

Measure whether the operator reasons from ownership rather than copied constants.

### C6 — novel scientific mini-workflow

Use a small public/synthetic scientific workflow not seen in development.

Measure end-to-end composition, execution, verification, and reporting.

## 12. Primary reported metrics

The benchmark reports standard and decomposed metrics.

### 12.1 Outcome pass rate

Fraction of trials passing G1.

This answers whether the correct end state was reached.

### 12.2 Contract adherence rate

Fraction of trials passing G2.

This answers whether the agent stayed within policy/scientific authority.

### 12.3 Joint pass rate

A trial passes the benchmark task only when **all required correctness graders pass**.

At minimum:

~~~text
joint_pass = G1 outcome
             AND G2 contract/policy
             AND any task-required G3/G4 checks
~~~

This conjunction is deliberately not given a new branded metric name.

### 12.4 Corrupt-success rate

Report the descriptive intersection:

~~~text
outcome_pass == true
AND contract_pass == false
~~~

This is the exact failure mode the project is particularly concerned about: the agent appears to finish but changes the task/procedure.

Recent procedure-aware evaluation work calls this kind of outcome a "corrupt success"; the benchmark can report the intersection without depending on that preprint's scoring framework.

### 12.5 pass^k reliability

Following τ-bench, compute **pass^k** on joint task success across repeated independent trials.

Report at least:

- pass^1;
- pass^3 when three or more trials are available;
- pass^5 for release comparisons when five trials per task are available.

Also retain per-task trial outcomes so a single aggregate does not hide unstable tasks.

### 12.6 Progress / milestone completion

For stateful multi-step tasks, report the fraction of predefined milestones reached, motivated by AgentBoard and ToolSandbox.

This is diagnostic and does not override final task success.

### 12.7 Cost / complexity

Report secondary metrics:

- tool calls;
- turns/tokens;
- elapsed time;
- persistent artifacts added;
- wrappers/controllers/environments introduced.

Do not reward low cost when it comes from premature termination.

### 12.8 Failure-mode incidence

Report diagnostic trajectory labels separately from success metrics.

Do not average severe violations into a single weighted score.

### 12.9 Failure-mode monitoring fields

The historical taxonomy should be made observable without turning it into runtime policy. Each trial may emit zero or more diagnostic labels, each with an evidence pointer to the trajectory/state that triggered it.

Initial fields:

| Field | Observable evidence |
|---|---|
| `workflow_substitution` | New persistent wrapper/controller/orchestration state appears even though the declared native path can express the task. |
| `semantic_drift` | A protected scientific parameter, population, fit, filter, threshold, or interpretation changes without delegated authority. |
| `scope_expansion` | Side effects or downstream work occur outside `authorized_effects`. |
| `endpoint_underreach` | The trial stops at an intermediate milestone while the declared endpoint remains reachable/incomplete. |
| `endpoint_overrun` | The trial continues beyond an explicit stop/handoff boundary. |
| `state_incoherence` | Recovery reasons from current source/config while active materialized commands, scheduler state, or products still reflect an older state. |
| `runtime_reconstruction` | A supplied usable runtime is replaced/rebuilt without demonstrated need or authorization. |
| `execution_scope_error` | A local resource/concurrency rule is applied at the wrong ownership level or to a broader scope than intended. |
| `redundant_observation` | Repeated checks add no new state and do not support a pending decision, recovery, or requested report. |
| `configuration_damage` | An operational edit mutates protected or unrelated configuration state. |

Also record `corrective_user_turns` in assisted evaluations as an interaction metric, not a failure label.

Labels should be derived from observable state/trajectory evidence. Do not infer hidden motives such as “the model preferred writing over reading.”

## 13. Scored-trial protocol

For objective comparisons:

1. pin the task/fixture revision;
2. pin the operator/skill/plugin revision;
3. record model and inference settings;
4. start from a clean environment;
5. provide the same task information to every compared system;
6. allow no ad-hoc human steering during the scored trial;
7. if interaction is part of the task, use a fixed simulator/protocol rather than live evaluator improvisation;
8. record the full trajectory and final environment;
9. run graders after termination;
10. repeat independent trials with the predeclared k.

An assisted-human track may be studied separately, but it must not be mixed into the primary autonomous score.

## 14. Baselines

Compare against:

### Base agent

Same model/harness without Fungen Operator.

### Pinned legacy runner

Use a single coherent legacy procedure when one exists.

Do not combine conflicting historical skills to manufacture a baseline.

### Candidate operator

Pin the exact replacement revision.

Where possible, keep model, tools, task fixtures, inference settings, and trial counts constant across baselines.

The benchmark evaluates the **operator/scaffold effect**, not a model leaderboard.

## 15. Benchmark harness and artifacts

A minimal harness can use:

~~~text
benchmark/
  README.md
  tasks/
    regression/
    capability/
    integration/
  fixtures/
  graders/
  references/
  results/
~~~

A task manifest should follow the schema in Section 4.

A trial record should contain:

~~~yaml
task_id:
task_revision:
benchmark_class:
operator_revision:
model:
inference_settings:
trial_id:
grader_results:
  outcome:
  contract:
  milestones:
  regression:
joint_pass:
final_state_claim:
ground_truth_state:
failure_annotations: []
metrics:
  tool_calls:
  turns:
  tokens:
  elapsed:
  persistent_artifacts_added:
trajectory_ref:
notes:
~~~

The harness should preserve raw trajectories separately from aggregate results.

## 16. Benchmark validation

Before a benchmark version is used for model/operator comparison:

1. every task has a passing reference solution;
2. gold state and policy labels are manually reviewed;
3. balanced counterpart coverage is checked;
4. deterministic graders are preferred and tested for false positives/false negatives;
5. any model-based grader is calibrated against held-out expert labels;
6. duplicated constructs are identified;
7. clean-environment reproducibility is verified;
8. benchmark-specific shortcuts are checked;
9. capability test fixtures remain held out from operator development;
10. task/runtime failures are distinguished from agent failures.

The benchmark version, task set, graders, and reference solutions are frozen before comparative evaluation.

### Signal-bearing scientific core

The MWE should prove more than workflow completion. Its base scientific fixture should contain a small, deterministic, **planted recoverable signal**.

Use the existing sketch-genotype mechanism to generate or provide the genotype matrix. Choose known causal variant(s), then simulate phenotype or molecular-trait values from those genotypes plus noise with a declared target variance explained. Store the seed and causal ground truth.

A minimal starting model is:

~~~text
y = G_causal * beta + epsilon
~~~

with the genetic component scaled to a target variance explained and the residual noise scaled accordingly. The target should be calibrated so the canonical pipeline recovers the intended signal reproducibly without making the task completely trivial.

Where supported by the actual canonical mini-protocols, machine-checkable scientific success can include:

- association detects the planted locus with the expected effect direction;
- fine-mapping includes the planted causal variant in the returned credible set;
- a multi-signal extension separates two planted low-LD signals;
- a shared-signal/colocalization extension distinguishes shared causal signal from a distinct-signal control;
- a null control does not manufacture a signal.

The benchmark should reuse this same scientific core across operational failure scenarios whenever possible. Failure-mode coverage should usually come from altered workflow/configuration/materialized/scheduler/product state, not from inventing a new biological dataset for every case.

## 17. Minimum working simulations

Before building the full v0.1 suite, implement a **minimum working simulation pack** that proves the harness, graders, and Phase-1 operator can be exercised end to end with no controlled-access biological data.

Use tiny deterministic fixtures: fake tables, fake identifiers, small configs, materialized command files, scheduler-state stubs/adapters, and terminal products. Preserve the *shape* of the operational problem, not the real cohort contents.

The first six simulations are:

| ID | Simulation | Primary check |
|---|---|---|
| **MWS-01** | Fixed-analysis native happy path | Select the supplied runtime/workflow and reach the terminal product without new orchestration. |
| **MWS-02** | Tempting intermediate checkpoint | Continue from a plausible checkpoint to the declared endpoint. |
| **MWS-03** | Execution mismatch that tempts method drift | Preserve protected scientific semantics; repair operationally or stop/escalate with the mismatch. |
| **MWS-04** | Source/config changed but materialized task is stale | Detect the active stale state and recover coherently. |
| **MWS-05** | One unit fails while siblings are valid | Preserve valid work and recover only the affected scope. |
| **MWS-06** | Valid no-result versus missing required product | Classify terminal state from declared product/no-result semantics rather than outer markers. |

For every simulation:

1. define the task manifest from Section 4;
2. provide a passing reference solution;
3. implement deterministic G1/G2 graders and G3/G4 when required;
4. verify the fixture from a clean reset;
5. record the diagnostic fields in Section 12.9.

The MWS pack is an early validation set for operator behavior, not a gate on whether composition infrastructure exists or may be used. Existing `.smk` mini-protocol composition is part of the environment under test. Use the MWS results to decide how much autonomous composition/recovery behavior to trust, and do not choose a permanent numerical release threshold before reference/base/legacy baselines establish empirical difficulty and variance.

## 18. First benchmark release

The first release should follow the scale and balance recommendations above rather than stop at six hand-written traps.

### v0.1 regression set

Start with six high-value historical families:

- R01 native happy path;
- R03 endpoint/termination;
- R04 scientific-policy adherence;
- R07 stale state;
- R08 false completion;
- R12 narrow recovery.

For each family, include:

- one incident-derived synthetic task;
- one balanced counterpart where the opposite behavior is correct.

This yields **12 regression tasks**.

### v0.1 capability holdout

Create **12 held-out tasks** across C1–C6, two per family, with unseen state/layout/composition details.

This yields an initial **24-task benchmark**, close to Anthropic's practical recommendation that early agent evals can begin with a few dozen well-specified tasks rather than hundreds.

### Trials

During development, report pass^1 and pass^3.

For release comparisons, run at least five independent trials per task and report pass^1, pass^3, and pass^5 on joint success, together with per-grader results.

Do not set release thresholds until the reference solutions, base-agent baseline, and legacy baseline establish the benchmark's empirical difficulty and variance.

## 19. Relationship to the historical corpus

Historical incidents are used for:

1. regression-task discovery;
2. realistic fixture design;
3. diagnostic failure annotation.

They are **not** benchmark results unless replayed under the frozen protocol.

Automated session-insights labels are case-finding aids, not gold labels.

## 20. Relationship to the product

The benchmark should constrain product claims, not product implementation.

Passing the benchmark means that, on the evaluated task distribution and protocol, the candidate demonstrated:

- correct end states;
- contract adherence;
- stateful recovery where required;
- repeated reliability;
- bounded regression behavior.

It does not prove universal scientific correctness or safety.

The benchmark should evolve by adding newly observed failures as regression tasks and new held-out capability families when the product scope expands, while preserving old regression tasks to detect backsliding.
