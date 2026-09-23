# Operator action surface: fixed notebook moves

Updated: 2026-09-23  
Status: design note; candidate implementation contract beneath the canonical operating model.

## Purpose

This note turns the positive operator contract from prose into a concrete action surface.

The operator is not treated as an adversarial process trying to escape containment. It is treated as a capable user-facing agent that may wander, overgeneralize, or solve the wrong problem when given unnecessary degrees of freedom. The design goal is therefore to make the intended moves easy and explicit, while keeping state-changing behavior inside a small repertoire of known forms.

## Core boundary

The operator is a **consumer of the canonical workflow, not its developer**.

The canonical workflow implementation is immutable to the operator. This includes canonical:

- Snakemake `.smk` files and Snakefiles;
- analysis notebooks;
- R and Python implementation scripts;
- shared workflow libraries and helpers.

The operator may instantiate the workflow through interfaces and parameters that the workflow already exposes. Examples include configuration fields, declared targets, supported profiles, documented runtime choices, dataset paths, and scheduler/resource parameters.

If the requested behavior cannot be expressed through an already-exposed interface, the operator should diagnose the missing capability and hand it to the developer role. Creating or editing canonical implementation to make the run work is not an operator move.

This separates two roles:

```text
developer -> defines and maintains the repertoire of possible workflow moves
operator  -> selects, parameterizes, composes, executes, observes, and resumes those moves for the user
```

## Notebook as the state-changing boundary

Read-only observation may remain relatively flexible.

Every action that changes execution state must be represented by filling and executing a retained operator-notebook cell.

```text
read-only observation
        |
        v
reason about current state
        |
        v
choose an allowed notebook-cell type
        |
        v
fill its bounded slots
        |
        v
execute the cell
        |
        v
retain the instantiated cell and its result
```

The notebook is therefore both:

1. the interface through which the operator changes state; and
2. the materialized record of the operations actually requested.

The notebook is not intended to expose arbitrary free-form shell or arbitrary Python as the state-changing interface.

## Fixed cell templates

A state-changing cell has:

```text
cell type
fixed command skeleton
bounded editable slots
slot constraints
execution result / evidence
```

The operator selects a template and fills its slots. It does not redesign the command skeleton.

The first template catalog should be derived from successful MESA and CARDIA operator notebooks rather than invented abstractly.

### Candidate initial cell types

#### PREPARE_CONFIG

Create or modify a run-specific configuration using fields already exposed by the canonical workflow.

The operator may choose values for exposed fields. The template owns how those values are materialized. This action does not authorize editing canonical notebooks, Snakefiles, scripts, or workflow libraries.

#### HARMONIZE_INPUT

Transform user/run inputs into an input form expected by a canonical mini-protocol.

This is likely the least uniform initial action family. It should be represented by a small collection of explicit harmonization templates discovered from successful workflow use rather than by generic Python or shell access.

#### CHECK_READINESS

Run the workflow-native readiness operation when the workflow requires one, such as the canonical Snakemake dry-run.

The template fixes the command form while exposing only the values needed to instantiate the run.

#### INITIATE_RUN

Submit a canonical workflow target through the maintained runtime and scheduler path.

A representative successful shape is:

```bash
%%bash
mkdir -p {{LOG_DIR}}
bsub <<'LSF'
#BSUB -J {{JOB_NAME}}
#BSUB -P {{PROJECT}}
#BSUB -q {{QUEUE}}
#BSUB -W {{WALLTIME}}
#BSUB -n {{CORES}}
#BSUB -R "span[hosts=1] rusage[mem={{MEMORY}}]"
#BSUB -oo {{LOG_DIR}}/%J.out
#BSUB -eo {{LOG_DIR}}/%J.err

source {{CONDA_SH}}
conda activate {{CONDA_ENV}}
export PATH="{{CONDA_ENV}}/bin:$PATH"
hash -r
set -eo pipefail
cd {{WORKDIR}}

python -m snakemake \
  --snakefile {{SNAKEFILE}} \
  --configfile {{CONFIGFILE}} \
  --profile {{PROFILE}} \
  --jobs {{JOBS}} \
  --latency-wait {{LATENCY_WAIT}} \
  --printshellcmds \
  {{TARGETS}}
LSF
```

The literal template may vary by maintained workflow/runtime. The important property is that the skeleton is fixed and the operator fills bounded slots such as target, config, resource values, paths, and supported runtime/profile choices.

#### CANCEL_RUN

Cancel an identified run or scheduler job using the maintained scheduler operation. The cell exposes the run/job identifier; it does not expose arbitrary shell mutation.

#### RESUME_RUN

Resume the same canonical workflow after interruption or repair of user-owned execution state. Where Snakemake reuse semantics are sufficient, this may use the same fixed submission template as `INITIATE_RUN`, instantiated against the existing run workspace without force.

## Conceptual verbs versus executable moves

The broader operator vocabulary remains useful for reasoning:

```text
Understand
Select
Bind
Compose
Check readiness
Execute
Observe
Diagnose
Repair user-owned execution state
Resume
Conclude
```

These verbs are not themselves the enforcement mechanism.

The executable layer is:

```text
verb / reasoning stage
        |
        v
allowed notebook-cell type
        |
        v
bounded editable slots
        |
        v
fixed command skeleton
        |
        v
state transition
```

For example:

```text
Execute
  -> INITIATE_RUN
      -> choose declared target/config/resources/profile
          -> render retained LSF + Snakemake cell
              -> submit run
```

## What the operator may repair

Recovery is limited to user-owned execution state and already-exposed workflow controls, for example:

- run-specific configuration;
- input and output paths;
- exposed workflow parameters;
- scheduler resources and concurrency;
- supported runtime/profile selection;
- stale or invalid submitted jobs;
- generated/materialized execution state that belongs to the run;
- resubmission or resumption through the canonical workflow path.

A defect in canonical implementation is a developer issue. The operator may collect minimal evidence sufficient to identify it, but implementation repair is outside the operator action surface.

## Empirical source for the first catalog

The first concrete templates should be extracted from operator notebooks that already produced useful MESA and CARDIA runs.

In particular:

- the retained CARDIA structural template at `skills/xqtl-runner/templates/operator_notebook.ipynb`;
- the MESA operator notebook referenced by the historical evidence at `/sc/arion/projects/load/users/sunh14/xqtl/MESA/xqtl_protocol/MESA_operator.ipynb`.

For every state-changing cell in those notebooks, extract:

```text
cell class
fixed skeleton
fields that varied across runs
fields that remained invariant
result/evidence produced
```

Recurring successful shapes should become the first fixed templates. Historical failure cases should then be used to tighten specific slots or ownership boundaries, not to invent a large preventive policy layer.

## Near-term implementation question

The next design task is not to add more prose rules. It is to enumerate the successful state-changing cells from MESA and CARDIA and reduce them to the smallest useful template catalog.

The target product is a finite menu of notebook moves with bounded arguments, not an unrestricted shell with instructions telling the model how to behave.
