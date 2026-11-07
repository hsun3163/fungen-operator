---
name: fungen-operator
description: Operate one existing canonical xQTL workflow through the Fungen MCP harness, retaining configuration, readiness, submission, and completion in an operator notebook. Use for lab-tech operation when the Fungen tools are connected.
---

# Fungen Operator prototype

Use the connected `prepare_config`, `check_readiness`, `initiate_run`, and `inspect_run` tools.
Read source, configuration, notebook history, logs, and output paths to select the next action.
The developer owns workflow implementation. Harmonized input paths are the starting boundary.

Start the stdio server through the approved host path outside Minerva's command sandbox.
Its async transport requires local socket writes; restricted startup reports this explicitly.

1. Bind one notebook, configuration, and working directory to the requested output graph.
   Inspect the deployment's canonical defaults; supply exposed parameters as typed values.
2. Call `prepare_config`. Defaults are recommended. Scientific differences go to the human
   through MCP elicitation before the harness writes a cell or config. The connected client
   must present that elicitation to a person; never answer it with model-generated consent.
3. Call `check_readiness` for the intended targets. Use its successful recorded result to
   authorize `initiate_run` with matching arguments when work remains. A `nothing_to_do`
   result already supplies canonical completion evidence. Controller walltime may differ.
4. Call `initiate_run`; inspect its receipt and native state. A receipt means submitted.
   After interruption, call the same action for the same workspace. Snakemake reuses valid work.
5. When the controller has ended, call `check_readiness` with `phase="conclusion"`.
   A successful `nothing_to_do` result records canonical workflow completion for those targets.
   Report scientific interpretation separately when the user requests it.

For an `lsf` deployment, an action returns `host_approval_required` and an exact `host_command`.
Run that command through `exec_command` with `sandbox_permissions="require_escalated"` on its
first attempt. This requirement also covers the CLI `inspect` and `replay` commands, which can
invoke scheduler clients. Never add a persistent interpreter/script rule. If review rejects
the command or escalation is unavailable, report an approval-path failure and stop that action.
The host entrypoint validates the saved cell and current state again before executing it.

Inspect operational failures and change only exposed configuration/resources through these
tools. A source defect or an unsupported recovery operation is a developer handoff. The current
catalog contains no source-edit, harmonization, unlock, cancellation, force, or composition tool.

Use `fungen-operator verify NOTEBOOK` at conclusion. Use the harness `replay` command to run
active cells in order; superseded code remains visible as history and is excluded by replay.
Ordinary Jupyter Run All executes historical cells too and is not the supported replay path.

Setup, exact constraints, examples, and limitations: [prototype architecture](../../docs/operator_prototype.md).

## First task: guided xQTL setup through fine-mapping

Codex and this operator run on the host. The SIF installs the tools and serves
Laguna on a GPU. Use `fungen serve`, `fungen codex`, `fungen check`, and
`fungen backend` (show or switch `local`/`openai`) on the host. `fungen check`
rows are PASS, FAIL or PENDING; the server and GPU rows stay PENDING until
`fungen serve` starts the GPU job and `fungen check` verifies the current endpoint and selected-model offload. PENDING produces NOT VERIFIED and a nonzero exit; run `fungen serve`, then `fungen check`. Failed scheduler/API retrieval is a failure.
Local `fungen codex` uses the Ollama provider and the required shipped Laguna
catalog. It validates exact IDs, quantization and context against the endpoint;
`spawn_agent` lists only served Laguna choices matching the session context.
Pinned 0.155.1 host captures verify both families/Q4/Q8/context presets against a
model-free endpoint. The live round-6 inventory and metadata replay verify only
`laguna-s-2.1:q8_0-256k-t2` at Q8_0/262144; other live choices and delegated
inference remain unverified. A missing selected model or metadata is an error.
Public native inspection requires the same journal proof on LSF, SGE and Slurm.
Incomplete coverage is `not_verified` with `scheduler_ok: false`, an unknown
dead-child count and a nonzero CLI exit. Fresh LSF, SGE and Slurm setups use the same tracked native rule/task adapter.
Historical launches without intent/receipt records remain unverified; generate a
fresh setup for the complete protocol.

When asked to set up the xQTL protocol, use `fungen xqtl --root FOLDER`.
It writes `setup.ipynb` before executing anything. Each fixed step asks the user
before running, checks its prerequisites, records a native log and stops at the
first failure. Never answer these prompts on the user's behalf. The user may run
the notebook cells individually or resume with `--step STEP`.

1. `workflow`: upstream StatFunGen/xqtl-protocol at
   `f66555213b5deeb68d347690493b694de923ef4d`, using `code/snakemake`.
   The distributed interface patch connects its current QtlDataset workers to
   Snakemake; its content and provenance are retained with the installation.
2. `software`: ask for mamba or StatFunGen pixi-setup and a software folder; show
   the 35 GB budget first. Mamba uses the bundled pinned environment file. Pixi
   fails on Minerva in upstream `safe_expose_remove` with invalid jq expression
   `.[].exposed.[].exposed_name`; state this before the choice and retain
   its native failure. Never silently switch the user's package manager.
3. `reference`: explain and record the prepared PLINK/normalized-BED boundary:
   GRCh38 coordinates, a tiny synthetic trait annotation, fixture-derived LD.
   Full genome FASTA, dbSNP and RNA alignment indexes are upstream of this chain.
   Name and size optional Ensembl 103 references before any requested acquisition.
4. `scheduler`: generate the detected LSF, Slurm, SGE or local profile. Cluster
   job caps are 2000. Submit the controller on the host approval path outside the
   sandbox. Each native Snakemake rule uses the same scheduler profile. On SGE the
   saved project (`account`) becomes `qsub -P`; Slurm and SGE use native resource-aware SoS task hosts. Local runs tasks in host rule processes.
5. `fixture`: generate 500 samples de novo with seed 20261020, four regions,
   512 variants and six artificial RNA contexts. Preserve 13 genotype covariate
   PCs, native hidden factors, TensorQTL and five-fold SuSiE/TWAS CV. Freeze the
   truth and acceptance criterion before fitting; use no legacy MWE or real data.
6. `test`: genotype QC, phenotype preparation, sample matching, native PCA and
   hidden factors, TensorQTL cis scans, QtlDataset construction and SuSiE/TWAS.
   All 24 planted causal pairs must have nominal P < 5E-8, the counted-G direction,
   and membership of the causal variant in a 95% SuSiE credible set. At most one
   of 24 null traits may cross that threshold. Grade native products and truth;
   markers and controller completion alone do not establish recovery.
7. `handoff`: retain the deployment for the user's own harmonized data, the
   installation notebook, source pin and patch, configuration and acceptance.
   Ask for the user's input paths and scientific choices before preparing their
   own analysis. The synthetic acceptance is an installation test.

All commands that contact the network or an HPC scheduler, including this guided
sequence and generated controller scripts, require the host approval path on
Minerva. A step is finished only after its declared output checks pass.
