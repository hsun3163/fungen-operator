# Fungen Operator: operating model

Updated: 2026-09-22  
Status: canonical conceptual model for the replacement; implementation is not yet complete.

## 1. What Fungen Operator is

Fungen Operator is a reliability layer for coding agents that operate **existing functional-genomics workflows**.

It is not a new workflow engine, a new scheduler, or an autonomous scientist. Its job is to let an agent compose and run the scientific building blocks that already exist, recover from operational failures, and reach the user's authorized endpoint **without silently changing the science or manufacturing a parallel way to run it**.

The concise design principle is:

> **Maximum initiative inside the delegated scientific and operational contract; minimum invention outside it.**

That principle resolves the tension visible throughout the repository history: the operator should be persistent about finishing authorized work, but conservative about redefining the method, workflow, runtime ownership, or scope.

## 2. The positive operator contract

The operator has six legitimate moves.

1. **Select** — identify the applicable project, checkout, runtime, task family, scientific scope, and requested endpoint.
2. **Compose** — connect existing mini-protocols through their declared inputs and outputs. Snakemake/SoS rules, notebooks, scripts, and maintained project helpers are building blocks, not invitations to create a second orchestration layer.
3. **Execute** — use the project's native command path, scheduler profile, and runtime ownership.
4. **Recover** — identify the smallest confirmed operational defect, preserve valid work, repair within scope, and resume the original endpoint.
5. **Verify** — inspect the actual execution state and declared scientific products, not only outer markers, submission receipts, or plausible-looking logs.
6. **Report and stop** — distinguish running, failed, incomplete, valid no-result, and verified completion; stop at the authorized endpoint.

Everything else must be justified as part of one of these moves. This is intentionally a **positive contract**: it defines the operator's action space rather than trying to enumerate every possible bad behavior.

## 3. Ownership boundaries

Reliability depends on keeping decisions at the level where they belong.

| Layer | Owns |
|---|---|
| User / scientific task | Scientific question, datasets, method, thresholds, comparison, authorized endpoint, explicit stop conditions |
| Project workflow | DAG, declared inputs/outputs, rule boundaries, maintained helpers, scientific artifact contracts |
| Operator | Selection, composition, execution, diagnosis, scoped recovery, evidence-based status reporting |
| Runtime / scheduler | Environment activation, queues, resource admission, job/task state |
| Produced artifacts | Evidence of what actually ran and what scientific products exist |

The operator may reason freely about **how to complete the authorized operation**. It does not gain authority to change the scientific operation merely because another method is easier to execute.

This boundary is the common thread behind the historical incidents involving new controllers, scientific-method changes, runtime logic placed in workflow code, scope expansion, and intermediate endpoints.

## 4. Composition, not reconstruction

The intended product model is a library of small, maintained scientific procedures that can be composed into a full analysis.

A mini-protocol can be a Snakemake rule family, SoS workflow, notebook, script, or maintained project capability. The operator should use the smallest existing building blocks that express the requested analysis.

A new wrapper, controller, validator, environment, or helper is justified only when all of the following are true:

- the requested composition cannot be expressed through an existing maintained path;
- the missing capability is demonstrated rather than assumed;
- the new artifact has a clear owner and does not duplicate workflow state or recovery logic;
- it does not redefine scientific semantics;
- it reduces, rather than increases, the total operational surface that must be understood and maintained.

This is the repository's practical interpretation of parsimony.

## 5. State is layered and material

A scientific run is not represented by one mutable code checkout. At minimum, distinguish:

```text
source -> configuration -> materialized task/command -> scheduler state -> scientific product
```

Changes at one layer do not automatically update later layers.

This matters especially during recovery. A reverted source file can coexist with already-materialized commands containing the old option. A completed controller can coexist with missing scientific products. A scheduler job can be running the wrong execution path even though the current Snakefile looks correct.

The operator therefore reasons from the **state that actually governs the active work**, not merely the newest editable file.

## 6. Completion is a scientific state

Submission, a green controller, a marker file, or an empty queue is not by itself scientific completion.

For each supported task family, completion should be defined from:

- the declared endpoint;
- the required terminal scientific products or explicitly valid no-result states;
- relevant child-task outcomes;
- unresolved missing/failed coverage;
- the exact source/configuration/task generation that produced those products.

The same principle applies to handoff. A stable running job can be a correct endpoint when the user asked for a handoff; it is not the same state as verified scientific completion.

## 7. Parsimony is a product property

Parsimony does **not** mean "fewest lines of instruction." It means minimizing unnecessary operational state while retaining the information needed to act correctly and recover.

The replacement should therefore have:

- one recognizable operator entry point;
- one small shared operating contract;
- task/domain references loaded only when relevant;
- native project evidence rather than duplicated ledgers;
- retained historical evidence outside the runtime instruction path.

Long historical analyses can remain in this repository without becoming prompts that every run must load.

## 8. How failures are interpreted

The repository evidence is best understood as failures of constrained operation, not simply coding mistakes.

The recurring families are:

- **selection/routing failure** — wrong skill, directory, runtime, checkout, target, or endpoint;
- **workflow substitution** — replacing operation of the established workflow with locally invented infrastructure;
- **semantic or scope drift** — changing scientific choices or expanding the task to resolve an operational problem;
- **execution-layer failure** — correct-looking settings applied at the wrong level, including scheduler and concurrency mistakes;
- **state incoherence** — editable source and already-materialized execution state diverge;
- **endpoint/evidence failure** — stopping early, overchecking irrelevant details, or claiming completion without the declared scientific products.

These categories are diagnostic. They should not be turned into another large runtime policy layer.

## 9. Evaluation model

Evaluation should test both outcome and behavior.

The minimum questions are:

1. Did the operator reach the declared endpoint or a valid requested handoff?
2. Did it preserve the scientific and operational contract?
3. Did it remain coherent with materialized execution state during recovery?
4. Did it report completion from real scientific evidence?
5. How many corrective user interventions were required?
6. How much additional operational machinery did it create?
7. Does the same behavior remain reliable across repeated attempts?

A dangerous contract violation should remain visible rather than being averaged away inside a single composite score.

See [benchmark.md](benchmark.md) for the canonical benchmark specification, [research_basis.md](research_basis.md) for the published work that motivates the evaluation vocabulary, and [fungen_operator_development_brief.md](fungen_operator_development_brief.md) for the detailed migration and case derivation.

## 10. Current implementation status

As of 2026-09-22:

- the historical evidence and failure analyses are retained;
- 19 imported skill entrypoints remain available as capability and design sources;
- overlapping operating procedures still exist in the legacy collection;
- a replacement operator has **not** yet been implemented or validated;
- the next implementation target is a single recognizable operator entry point with a concise shared contract plus task-specific references/capabilities;
- legacy procedures should be retired only after their capabilities have a deliberate migration disposition and representative acceptance cases pass.

The repository should therefore be read in this order:

1. this operating model;
2. [benchmark.md](benchmark.md) for how reliability is evaluated;
3. [skills/README.md](../skills/README.md) for the capability map;
4. [fungen_operator_development_brief.md](fungen_operator_development_brief.md) for detailed engineering decisions;
5. historical evidence only when a design choice needs to be traced back to an incident.
