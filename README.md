# fungen-operator

**Fungen Operator is an experimental reliability layer for coding agents operating established functional-genomics workflows.**

It is not a new workflow engine and not an autonomous scientist. The project already has scientific mini-protocol infrastructure in maintained Snakemake `.smk` files. The operator's job is to select and compose those existing mini-protocols into the requested analysis, run them through the native execution path, recover from operational failures, and reach the authorized endpoint without silently changing the science or building a parallel orchestration layer.

> **Maximum initiative inside the delegated scientific and operational contract; minimum invention outside it.**

That is the guiding principle for the replacement.

## Current status

As of 2026-09-25, this repository includes a **thin executable lab-tech prototype** alongside its development evidence.

**2026-09-23 MWE update:** the fixed-bin PLINK1 genotype fixture, 12 covariates and 40 phenotypes are generated and verified. See the [progress report](docs/mwe_progress_20260923.md) for results, source, reproducibility commands and the closed reconstruction pilot.

The [prototype](docs/operator_prototype.md) exposes configuration, readiness, and submission through typed MCP tools and fixed notebook cells. It includes scientific approval, retained superseded history, replay, and a synthetic lifecycle. [Live LSF readiness and gated submission](docs/readiness_reconciliation_20260924.md) are verified. The [500-sample MWS-01 reference and OSS repeat](benchmark/README.md) passed the phenotype-partitioning endpoint and independent grader. The OSS trajectory review records a login-host validation exception; broader scientific endpoints and the full action catalog remain separate work. The repository also contains:

- 19 imported skill entrypoints with domain procedures, helpers, templates, and site/runtime knowledge;
- historical attempts and retired approaches under `archive/`;
- an attributed incident/evidence packet;
- multiple analyses of recurring agent failures and user corrections;
- a detailed replacement-development brief;
- the new canonical operating model and research/evaluation basis.

The current skill collection contains overlapping and sometimes conflicting procedures. Do not interpret the whole `skills/` directory as one combined instruction set.

## Start here

For the executable harness, start with the [prototype architecture and setup](docs/operator_prototype.md),
the [operator skill](skills/fungen-operator/SKILL.md), and the [executed synthetic notebook](examples/operator_lifecycle.ipynb).
The [action-surface design](docs/operator_action_surface_20260923.md) supplies the fixed-cell model;
the prototype implements its configuration/readiness/submission subset, with harmonization upstream.

1. **[Operating model](docs/operator_model.md)** — the canonical current conceptual model: what the operator is, its positive action contract, ownership boundaries, state model, and parsimony principle.
2. **[Operator action surface](docs/operator_action_surface_20260923.md)** — the concrete proposal that all state-changing behavior occurs through fixed operator-notebook cell templates with bounded slots.
3. **[Benchmark](docs/benchmark.md)** — the canonical evaluation contract, explicitly aligned to Anthropic's task/trial/grader/outcome framework and peer-reviewed agent benchmarks (τ-bench, ToolSandbox, WorkArena++, AgentBoard, MAST, ScienceAgentBench).
4. **[Skill baseline and migration map](skills/README.md)** — what capabilities exist in the current collection and how they should be treated during consolidation.
5. **[Development brief](docs/fungen_operator_development_brief.md)** — detailed requirements, migration questions, case derivation, and implementation sequence.
6. **[Research basis](docs/research_basis.md)** — how the project's observed problems map to published work on compositional workflows, stateful tool use, rule-constrained agents, trajectory evaluation, scientific agents, and agent complexity.

Only then descend into the evidence corpus when a design decision needs traceability.

The workflow contract for the current implementation is the local `../xqtl/xqtl-protocol` checkout; see the [source boundary](docs/operator_model.md#authoritative-workflow-source). Existing individual-derived MWEs under `../xqtl/` are excluded from the new benchmark; see the [fixture boundary](docs/benchmark.md#legacy-mwe-exclusion).

The active [MWS-01 development reference](benchmark/README.md) uses a verified **500-sample synthetic MWE**, with matched genotype, phenotype, and covariate inputs.

## Operating model in one page

The operator has six legitimate moves:

```text
select -> compose -> execute -> recover -> verify -> report/stop
```

The scientific task and established project own the method and workflow semantics. The operator owns the reasoning needed to carry out that authorized operation.

The canonical implementation is immutable to the operator. The operator may instantiate it through already-exposed interfaces and parameters. Read-only observation may remain flexible, but every state-changing action must be materialized as a retained notebook cell selected from a fixed template catalog; the agent fills bounded slots rather than authoring a free-form execution path.

The model is **composition, not reconstruction**. Maintained Snakemake `.smk` files are the existing mini-protocol interface; notebooks and R/Python scripts remain implementation details invoked by those mini-protocols rather than pieces for the operator to rewire. The operator uses the existing composition mechanisms. A missing capability or canonical defect is handed to the developer role rather than bridged by an operator-created wrapper, controller, validator, environment, helper, or alternate execution path.

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
  operator_action_surface_20260923.md
                                 fixed notebook action-surface design
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
- a finite catalog of fixed state-changing notebook-cell templates derived first from successful MESA/CARDIA operation;
- direct use of the existing `.smk` mini-protocol infrastructure for both fixed and composed analyses;
- composition by selecting and connecting maintained mini-protocols through their existing inputs/outputs and configuration conventions, not by building a new composition framework;
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
