# Skill baseline and migration map

This directory preserves the current imported skill collection. It is **not** the target architecture of Fungen Operator and should not be loaded wholesale.

Use [docs/operator_model.md](../docs/operator_model.md) for the canonical conceptual model and [docs/fungen_operator_development_brief.md](../docs/fungen_operator_development_brief.md) for detailed migration decisions.

## How to read this directory

The skills serve three purposes:

1. **capability source** — domain procedures, helpers, templates, and site/runtime knowledge worth retaining;
2. **behavioral evidence** — examples of how operating policy evolved in response to incidents;
3. **migration input** — responsibilities that the replacement must deliberately incorporate, retain separately, or defer.

Overlapping instructions are historical design material, not an instruction to combine them.

## Shared operating baseline

| Skill | Role in migration |
|---|---|
| [human-runner](human-runner/SKILL.md) | Main source for shared native-execution, scope, recovery, evidence, and handoff behavior. |

## Domain runners and workflow ownership

| Skill | Role in migration |
|---|---|
| [xqtl-runner](xqtl-runner/SKILL.md) | Primary current xQTL runner reference: shared DAG, runtime ownership, scientific semantics, materialized-task recovery. |
| [xqtl-snakemake-analysis](xqtl-snakemake-analysis/SKILL.md) | Additional xQTL operating/editing knowledge to reconcile with the replacement. |
| [cosi-runner](cosi-runner/SKILL.md) | Current minimal/native COSI runner reference. |
| [cosi-run](cosi-run/SKILL.md) | Richer COSI run-packet and validation procedure; overlaps with and sometimes conflicts with `cosi-runner`. Preserve unique domain knowledge while resolving policy conflicts. |
| [cosi-workflow-edit](cosi-workflow-edit/SKILL.md) | COSI workflow-edit behavior and validation obligations. |

The replacement should expose one coherent operating procedure for each supported intent. The existence of two historical procedures is not itself a desired routing mechanism.

## Diagnosis and execution-state utilities

| Skill | Role in migration |
|---|---|
| [debug-pipeline](debug-pipeline/SKILL.md) | Decisive-error tracing and recovery ideas; review manual-marker/completion shortcuts before reuse. |
| [snakemake-sos-parser](snakemake-sos-parser/SKILL.md) | Parse Snakemake/SoS structure and execution evidence. |
| [sos-status-sampler](sos-status-sampler/SKILL.md) | Focused SoS task-state sampling. |
| [lsf-queue-move](lsf-queue-move/SKILL.md) | Scoped scheduler queue intervention. |

These capabilities should support the native workflow rather than become a second completion or orchestration system.

## Scientific and data utilities

| Skill | Role in migration |
|---|---|
| [sumstat-munger](sumstat-munger/SKILL.md) | Summary-statistic preparation through the maintained conversion path. |
| [cosi-sketch-ld](cosi-sketch-ld/SKILL.md) | Regional LD generation and provenance. |
| [cosi-weight-scan](cosi-weight-scan/SKILL.md) | Targeted weight/result scanning. |
| [intact-gene-query](intact-gene-query/SKILL.md) | Freshness-aware INTACT result queries. |

These are examples of the mini-protocol/capability model: retain their scientific contracts and implementation where useful rather than re-expressing them as generic prose.

## Scientific notebooks and figures

| Skill | Role in migration |
|---|---|
| [cosi-notebook](cosi-notebook/SKILL.md) | Executable scientific notebook conventions. |
| [cosi-locus-zoom](cosi-locus-zoom/SKILL.md) | Locus zoom construction and requested-window fidelity. |
| [cosi-locus-case-study](cosi-locus-case-study/SKILL.md) | Multi-track locus interpretation, allele/CS/LD provenance, and figure contract. |

## Handoff and external coordination

| Skill | Role in migration |
|---|---|
| [record-handoff](record-handoff/SKILL.md) | Durable continuation state when a handoff is requested. |
| [todoist-task-completion](todoist-task-completion/SKILL.md) | Evidence-backed completion of an external task; integration-specific rather than core scientific execution. |

## Migration rule

Do not retire a skill merely because its policy text is undesirable. First identify whether it contains a unique capability, helper, scientific convention, or site/runtime fact that still needs an owner.

Conversely, do not preserve an entire skill merely because one useful rule or script lives inside it.

The target is **capability preservation with policy consolidation**.
