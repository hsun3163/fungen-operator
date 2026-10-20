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

## Workflow ownership

Workflow-specific skills live with their deployment providers in the owning workflow repository. COSI owns its run, edit, data and locus procedures; xQTL owns its runner and Snakemake procedures. Load the workflow's deployment by path to select its operator capabilities. Existing local transition links preserve the paths held by running processes.

## Diagnosis and execution-state utilities

| Skill | Role in migration |
|---|---|
| [snakemake-sos-parser](snakemake-sos-parser/SKILL.md) | Parse Snakemake/SoS structure and execution evidence. |
| [sos-status-sampler](sos-status-sampler/SKILL.md) | Focused SoS task-state sampling. |
| [lsf-queue-move](lsf-queue-move/SKILL.md) | Scoped scheduler queue intervention. |

These capabilities should support the native workflow rather than become a second completion or orchestration system.

## Protected data

| Skill | Role in migration |
|---|---|
| [librarian](librarian/SKILL.md) | Route protected-result questions to the local-model data librarian (`data_guard/`). |
| [query](query/SKILL.md) | Compose bounded requests to that librarian. |

Scientific data preparation, result queries and locus notebooks remain owned by their workflows.

## Handoff and external coordination

| Skill | Role in migration |
|---|---|
| [record-handoff](record-handoff/SKILL.md) | Durable continuation state when a handoff is requested. |
| [todoist-task-completion](todoist-task-completion/SKILL.md) | Evidence-backed completion of an external task; integration-specific rather than core scientific execution. |

## Migration rule

Do not retire a skill merely because its policy text is undesirable. First identify whether it contains a unique capability, helper, scientific convention, or site/runtime fact that still needs an owner.

Conversely, do not preserve an entire skill merely because one useful rule or script lives inside it.

The target is **capability preservation with policy consolidation**.
