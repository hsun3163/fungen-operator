# fungen-operator

**Fungen Operator is an experimental reliability layer for coding agents operating established functional-genomics workflows.**

It is not a new workflow engine and not an autonomous scientist. The first product stage operates fixed analyses through the project's existing runner/workflow paths, recovers from operational failures, and reaches the authorized endpoint without silently changing the scientific analysis. Composition is a second-stage capability: after the fixed-operation trust gate, the operator may assemble maintained `.smk` mini-protocols into a full analysis with the scientist approving the composition before execution.

> **Maximum initiative inside the delegated scientific and operational contract; minimum invention outside it.**

That is the guiding principle for the replacement.

## Current status

As of 2026-09-22, this repository is a **development and evidence repository**.

The accumulated material is substantial, but the replacement operator has not yet been implemented or validated. The repository currently contains:

- 19 imported skill entrypoints with domain procedures, helpers, templates, and site/runtime knowledge;
- historical attempts and retired approaches under `archive/`;
- an attributed incident/evidence packet;
- multiple analyses of recurring agent failures and user corrections;
- a detailed replacement-development brief;
- the new canonical operating model and research/evaluation basis.

The current skill collection contains overlapping and sometimes conflicting procedures. Do not interpret the whole `skills/` directory as one combined instruction set.

## Start here

1. **[Operating model](docs/operator_model.md)** — the canonical current conceptual model: what the operator is, its positive action contract, ownership boundaries, state model, and parsimony principle.
2. **[Benchmark](docs/benchmark.md)** — the canonical evaluation contract, explicitly aligned to Anthropic's task/trial/grader/outcome framework and peer-reviewed agent benchmarks (τ-bench, ToolSandbox, WorkArena++, AgentBoard, MAST, ScienceAgentBench).
3. **[Skill baseline and migration map](skills/README.md)** — what capabilities exist in the current collection and how they should be treated during consolidation.
4. **[Development brief](docs/fungen_operator_development_brief.md)** — detailed requirements, migration questions, case derivation, and implementation sequence.
5. **[Research basis](docs/research_basis.md)** — how the project's observed problems map to published work on compositional workflows, stateful tool use, rule-constrained agents, trajectory evaluation, scientific agents, and agent complexity.

Only then descend into the evidence corpus when a design decision needs traceability.

## Operating model in one page

The operator has six legitimate moves:

```text
select -> compose -> execute -> recover -> verify -> report/stop
```

The scientific task and established project own the method and workflow semantics. The operator owns the reasoning needed to carry out that authorized operation.

The long-term model is **composition, not reconstruction**, but composition is not the first milestone. Phase 1 proves reliable operation of fixed analyses through the existing runner paths. In Phase 2, maintained Snakemake `.smk` files are the primary compositional interface; notebooks and R/Python scripts remain implementation details invoked by those mini-protocols rather than a new graph for the operator to invent. New wrappers, controllers, validators, environments, or execution paths must demonstrate that they fill a real gap and reduce net operational complexity.

Execution state is layered:

```text
source -> configuration -> materialized task/command -> scheduler state -> scientific product
```

A change to one layer does not automatically change later layers. This is central to recovery.

Completion is defined by the requested scientific endpoint and actual terminal products or explicitly valid no-result states—not merely by submission, a controller exit, a marker file, or an empty queue.

## Why this exists

The historical record repeatedly shows a characteristic failure pattern: an agent asked to operate an existing workflow starts solving a different problem.

Examples include:

- building alternative wrappers/controllers instead of using the shared workflow;
- adding assurance machinery that becomes another operational dependency;
- rebuilding a supplied runtime;
- changing scientific semantics to resolve an execution mismatch;
- stopping at an intermediate checkpoint instead of the requested endpoint;
- expanding the scope of the task;
- fixing source while leaving already-materialized execution state stale;
- applying a sensible resource convention at the wrong level;
- spending attention on redundant inspection rather than the requested decision;
- damaging consequential configuration while editing the operational record.

The repository's design question is therefore not simply how to make an agent "more autonomous" or "more constrained." The target is **persistence within delegated authority**.

## Repository map

```text
README.md                         this entry point
docs/
  operator_model.md              canonical conceptual model
  benchmark.md                   canonical benchmark specification
  research_basis.md              external research/evaluation grounding
  fungen_operator_development_brief.md
                                 detailed replacement engineering brief
  historical_evidence_extraction_20260920.md
                                 primary retained TASK/EVENT/FEEDBACK evidence
  failure_mode_insights_20260920.md
                                 interpretation of historical failure patterns
  session_insights_analysis_20260922.md
                                 separate session-insights run and corrections
  insights_review_20260922.md     additional insights-derived development review
  source-manifest.tsv             provenance for imported files
skills/
  README.md                       capability and migration map
  */SKILL.md                      imported operating/domain skill baseline
archive/                          prior approaches, reviews, and retired policy
```

Nothing in the renovation requires deleting the historical material. The goal is to keep evidence rich while making the runtime/product concept small.

## Evidence discipline

The documents play different roles:

- **historical evidence** records attributed incidents and uncertainty;
- **failure analyses** infer recurring patterns and competing mechanisms;
- **development documents** convert those observations into candidate requirements;
- **current skills** are capability/policy sources, not proof that their rules were active during historical incidents;
- **published research** supplies vocabulary and evaluation precedent, not product requirements by itself.

A later rule does not prove what caused an earlier incident. Automated session labels are useful for finding cases, not for estimating failure rates without checking the underlying evidence.

## Development direction

The replacement should converge toward:

- one recognizable, skill-first Fungen Operator entry point;
- one concise shared operating contract;
- **Phase 1:** reliable operation of fixed analyses through existing runner/workflow paths;
- a benchmark trust gate before composition is enabled;
- **Phase 2:** composition of existing `.smk` mini-protocols through declared inputs/outputs, initially with scientist approval of the composed graph;
- task/domain references or capabilities loaded only when relevant;
- preservation of useful scientific helpers and conventions;
- explicit ownership of runtime and scheduler facts;
- controlled-data-safe synthetic acceptance cases plus bounded native integration tests;
- repeated evaluation of endpoint completion **and** contract adherence;
- staged retirement of overlapping legacy discovery routes only after capability coverage is accounted for.

Start skill-first. Add a plugin, custom agent, or heavier harness only if a concrete capability gap demonstrates that the skill layer is insufficient.

## Provenance

This repository incorporates the original `hsun3163/runner-skills` history and a refreshed local skill snapshot. The [source manifest](docs/source-manifest.tsv) records imported source locations and hashes. Imported snapshots are historical provenance; subsequent edited files require their own revision identity.

Analysis datasets and the external workflow implementations themselves are not bundled here.
