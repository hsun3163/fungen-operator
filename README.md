# Fungen Operator

Install a workflow operator on your host and serve Laguna from one Apptainer
image. Host Codex uses the operator's notebook actions and your scheduler. The
image contains Ollama **0.40.6**, Codex **0.155.1**, uv **0.13.4**, an offline
operator wheel bundle and its skill. Models and credentials stay on the host.
The current build targets Linux x86-64 with Apptainer/Singularity. The local
backend needs an NVIDIA GPU; the OpenAI backend runs host Codex without one.

The GitHub Container Registry package is private until the owner makes it public.
Release tags are `ollama0.40.6-codex0.155.1` and `latest`; the publication and
acceptance of each build are recorded in [container/VALIDATION.md](container/VALIDATION.md).
Authenticate with a GitHub token that has `read:packages` and package access, then pull:

```bash
gh auth token | apptainer registry login --username hsun3163 --password-stdin oras://ghcr.io
apptainer pull fungen.sif oras://ghcr.io/hsun3163/fungen-operator:ollama0.40.6-codex0.155.1
```

On Minerva, use `singularity remote login` for the login command and
`singularity pull` for the pull. Check `sha256sum fungen.sif` against the release
evidence. A registry manifest digest identifies metadata; the SIF SHA-256 identifies
the downloaded image. You can also build `fungen.sif` with the [build recipe](container/README.md).

With `fungen.sif`, the local backend quick start is two shell commands:

```bash
apptainer run fungen.sif
~/.fungen/bin/fungen serve && ~/.fungen/bin/fungen codex
```

Use `singularity` in place of `apptainer` on Minerva. The portable form of the
first command is `apptainer run --home $HOME:$HOME fungen.sif`; use it on sites
that disable home mounts (`--contain` or a site configuration). Setup checks mount identity/source for home, config and install destinations before installation writes. Unknown or private mounts stop setup with an explicit home/bind command; persistence acceptance requires a named shared filesystem source or matching physical host block-device/kernel identity. A subdirectory bind alone, tmpfs/ramfs, private images and unverified virtual block sources are refused before installation writes.
An install folder outside home is made visible the same way with `--bind FOLDER:FOLDER`.
Local builds, acceptance and the publication of a given build are recorded in
[container/VALIDATION.md](container/VALIDATION.md).

Try the distribution on Minerva with the [try-out notebook](examples/try_fungen_operator.ipynb).

Setup asks, in order:

```text
Install folder [~/.fungen]:
Scheduler (lsf/slurm/sge/local) [detected scheduler]:
Model backend (local/openai) [local]:
Models (download):
  laguna-xs-2.1:q4_K_M: 20 GB
  laguna-xs-2.1:q8_0: 36 GB
  laguna-s-2.1:q4_K_M: 96 GB
  laguna-s-2.1:q8_0: 128 GB
Model tag [largest choice fitting visible GPU memory; XS Q4 when unknown]:
Download model? (yes/no) [no]:
Model folder to download into or reuse [scratch/project on clusters; ~/.fungen/models locally]:
Context (32768; advanced 262144 needs extra GPU memory) [32768]:
Add the install bin folder to your shell PATH? (yes/no) [no]:
```

With the `sge` scheduler, setup also asks `SGE project (-P) []:` right after the
scheduler question (or takes `--account`/`FUNGEN_ACCOUNT`); an empty answer uses
the site's default project without verifying that the site permits it. Enter `-` to clear a saved project, or pass `--account ''`; sites requiring a project need `--account PROJECT`. The model questions apply to the local backend. On clusters setup warns about
home quotas. A new download requires a writable folder and model size plus 10%
plus 2 GB free space; check the site's quota too. Ollama resumes partial blobs.
If an interruption leaves an empty or truncated Ollama progress record, setup
archives that record under the model folder's `.fungen-download-recovery` and
rebuilds its native partition descriptor with zero completed bytes for that
chunk. Valid progress and partial blob bytes stay intact; Ollama resumes the
remaining chunks and verifies their hash.
A complete existing model folder may be read-only. Advanced 256k context creates
a local Modelfile variant in a writable overlay, reusing the base blobs. Ollama
refreshes blob timestamps during variant creation, so this advanced option needs
a writable base model store; use the default 32768 context for read-only reuse.

Setup installs under the chosen folder and retains host Codex 0.155.1 or newer for OpenAI. Local sessions use the bundled host Codex 0.155.1, matching the catalog version. It installs the Codex skill without
replacing the user's Codex configuration. Backend settings live in
`~/.config/fungen/config.toml`; local Codex sessions use the install folder's
separate Codex home. Setup installs the required Laguna descriptor catalog at
`<install>/codex/models.json` (frozen Codex CLI 0.155.1 instructions, Apache-2.0;
provenance is recorded in the file). It contains exact Q4_K_M/Q8_0 identifiers
for both Laguna families at 32768 and 262144 tokens. At local launch, the host
queries Ollama's inventory, quantization and effective/configured context, then
passes an immutable catalog under `<install>/codex/served/` to `model_catalog_json`.
Only exact served IDs matching the session context become model-facing
`spawn_agent` override choices. The selected model must have matching metadata;
unavailable or invalid evidence blocks launch with the serve/check instruction.
Downloaded templates alone do not establish that an endpoint serves a choice.
Host Codex 0.155.1 request captures verify both Laguna families, Q4/Q8 and both
contexts against an isolated endpoint. They compare the complete request and
every tool definition: the intentional behavior change is the local picker list;
validated fresh request identities/timestamps also differ. Base instructions,
AGENTS/skill/operator guidance, tool schemas and remaining fields match.
The live service inventory checked in round 6 contains only
`laguna-s-2.1:q8_0-256k-t2` (Q8_0, 262144 tokens); replaying that metadata through
the pinned host client lists exactly that alias. Other live model availability,
interactive configurations and actual delegated inference remain unverified.
The launcher requires the shipped catalog and pinned client, with rerun-setup
instructions for missing or invalid assets. Setup upgrades to the image's operator bundle on re-run.
Unchanged files are kept, and changed binaries are replaced atomically so a
running host client retains its existing executable mapping.
The PATH line is appended only after an explicit `yes`.

For the OpenAI backend, use `fungen codex` after sign-in; skip `fungen serve`.
Setup prints `codex login --device-auth` for headless
sign-in. You may instead set `OPENAI_API_KEY` in your shell. The launcher passes
the key through the environment; it never writes it to a configuration, image
or working folder. Ordinary host `codex` also sees the installed skill.
See [Codex authentication](https://developers.openai.com/codex/auth/) and
[configuration](https://developers.openai.com/codex/config-reference/).

Switch backends with `fungen backend`. With no argument it prints the active
backend and local asset configuration (complete model, matching serve script, catalog and pinned client). Runtime health and OpenAI authentication remain separate checks: run `fungen check`. `fungen backend local` or `fungen backend openai` saves the choice in
`~/.config/fungen/config.toml`. Switching to `local` uses a completed local setup
(model and serve script); when one is missing, it prints the exact fix
`<runtime> run <image> setup --backend local`. After switching to `local`, run
`fungen serve`, then `fungen codex`; after switching to `openai`, run
`fungen codex` directly. `fungen codex --backend local|openai` selects a backend
for one session and keeps the saved setting. Re-running setup with
`--backend openai` keeps the configured local model settings, so
`fungen backend local` validates those assets before switching back. Changing install or scheduler can require local setup again to regenerate a matching serve script. On the OpenAI backend, `fungen serve`
prints the switch hint `fungen backend local`.

Daily commands:

```bash
fungen serve                  # submit/start the GPU model server
fungen codex                  # wait for the recorded endpoint; start host Codex
fungen check                  # checks and exact fixes
fungen backend                # active backend and configuration; health via check
fungen backend openai         # save the OpenAI backend (no server)
fungen backend local          # save the local backend; then fungen serve
fungen codex --backend openai # this session only; saved backend unchanged
fungen codex --deployment deployment.json
fungen codex -- exec --skip-git-repo-check 'Your task'
```

The local launcher selects the Ollama provider before interactive onboarding by passing `-c model_provider="ollama"` together with `--oss`. Argument and catalog loading tests pass on the host; the complete interactive trust/composer path for this source revision remains unverified.

With `--deployment`, the operator connection must be ready before Codex begins
the task. A connection startup failure stops the session with its error.

The server script is `~/.fungen/serve.lsf.sh`, `serve.slurm.sh`, `serve.sge.sh` or `serve.local.sh`.
It requests the tag's GPU count, uses `apptainer run --nv IMAGE serve`, selects a
free port, tests inference, and records the node and port. Server readiness requires selected-model GPU offload: a visible GPU and positive selected-model VRAM are required after the warm-up generation. CPU-only readiness is refused; partial offload can pass. This does not establish exclusive GPU inference or prevent an initial CPU warm-up. The fix is a GPU job with `--nv`; `fungen serve` provides both. On a login host without a GPU, setup reports that
GPU offload remains unverified until the current launch starts on a GPU and `fungen check` passes. Choose OpenAI on a
machine without a GPU. Workflows and their scheduler clients run on the host.

Setup detects the scheduler in this order: LSF (`bsub` or `LSF_BINDIR`), Slurm
(`sbatch`), SGE (`qsub` plus `SGE_ROOT` or `qconf`), then local. `--scheduler`
accepts `lsf`, `slurm`, `sge` or `local` for `setup` and for `fungen xqtl`.
The scheduler default is the freshly detected scheduler; a previous answer is the
default when detection finds none, with a visible explanation. Explicit `--scheduler local` selects local even when a saved cluster scheduler exists.

SGE: `fungen serve` submits `~/.fungen/serve.sge.sh` with `qsub`. The script
requests `-N fungen-serve`, `-S /bin/bash`, `-P <project>` when a project is
set, `-pe smp 4`, `-l h_rt=12:00:00,h_vmem=16G,gpu=<GPU count>` and `-j y`, and logs to
`serve.$JOB_ID.log` in the install folder. `smp` and `gpu` are common SGE
defaults; adjust the parallel environment and GPU resource names to the site's.
Setup rewrites the script when its rendered content changes, so site-specific changes must be reflected in the serve renderer/configuration before local setup; `fungen check` rejects a script that differs from its configuration. xQTL rule jobs use `profiles/sge` through the
operator's cluster adapter: `qsub -terse -S /bin/bash -N <rule>`, `-P <project>`
when a project is set, `-pe smp <threads>` when threads exceed 1, and
`-l h_vmem=<memory per slot>M,h_rt=<runtime>`, with logs `$JOB_ID.out` and `$JOB_ID.err` and status from `qstat -j`, then
`qacct -j`. Accounting must identify every complete job record and report success throughout; arrays are unsupported. SGE jobs use the site queue unless `--queue` selects one.
The SGE project is saved as `account` in `~/.config/fungen/config.toml`;
`fungen xqtl` inherits the launcher's account for a new xQTL root only when the scheduler matches; `--account` overrides it. Existing scheduler/account/queue/software settings require a new root when changed. The account default follows the scheduler: `acc_LOAD`
for LSF, empty otherwise. `sos.yaml` (the LSF task host) is written for LSF; on
Slurm and SGE, SoS tasks use generated native task hosts with their declared cores, memory and walltime. Local tasks run in host rule processes.
For an interactive GPU session, add `-now no` to `qrsh` to wait for a GPU; on
sites such as BU SCC, `qrsh` otherwise returns at once when no GPU is free.
A BU SCC user validated SGE live with the previous build: SGE job submission
works, an L40S GPU served the model, and `fungen check` passed 11/11.
Acceptance on the rebuilt image is the next validation step.

A scripted setup accepts the same answers as flags or `FUNGEN_*` variables:

```bash
apptainer run fungen.sif setup --non-interactive --backend local --scheduler lsf \
  --model laguna-xs-2.1:q4_K_M --models-dir /scratch/user/models --download yes \
  --install "$HOME/.fungen" --add-path no
```

Ask Codex to “set up the xQTL protocol through fine-mapping”, or run:

```bash
fungen xqtl --root /scratch/user/xqtl-setup
```

It writes `setup.ipynb` with one confirmed cell per step: pinned upstream workflow,
software, references, scheduler profile, a new synthetic fixture, the native test
chain, and hand-off. Each step checks its predecessors and retains a native log.
The guide keeps its cloned source in `workflow/` and its registered runtime in
`user-runs/guided-test/`. The test step uses the standard deployment-owned action
and notebook executor: its actual commands, scheduler receipt and completion are
retained in `user-runs/guided-test/operator.ipynb`. On cluster schedulers it
requires the exact graph dry-run, then waits for the tracked controller with
`bsub -K`, `qsub -sync y`, or `sbatch --wait` before grading. Work, native logs and
the isolated SoS home stay inside that runtime boundary. Controller streams are
`user-runs/guided-test/work/logs/<cell-id>.<job-id>.out` and `.err`; the submission
journal is in that log directory's `rules/` subdirectory. The frozen grade is
`user-runs/guided-test/acceptance.json`.

Inspect the actual emitted deployment and executed receipt through the public path:

```bash
fungen-operator inspect --deployment ~/xqtl-setup/deployment.json \
  --notebook ~/xqtl-setup/user-runs/guided-test/operator.ipynb
```

Both the runtime/source disjointness and evidence-inside-runtime guards apply.
Older setup roots retain their historical layout; use a fresh setup root for this
runtime contract.
Setup registers the **Fungen Operator** Jupyter kernel using the installed host
Python, so these cells import the operator even when Jupyter itself uses another environment.
Resume with `--step workflow|software|reference|scheduler|fixture|test|handoff`.
Mamba is the required route, using hash-pinned Miniforge 26.7.2-0 and the bundled version-pinned environment with its 800-package hash lock.
The runtime dependency susieR is pinned to 0.16.6 for pecotmr 0.9.5.
The existing LSF software installer consumes that explicit lock. Regenerate it only
when package pins change, using the YAML's channels in their declared order even
when site/user condarc files configure strict channel priority:

```bash
.venv/bin/python -m fungen_operator.lock --mamba /path/to/mamba \
  --prefix /scratch/user/xqtl-lock-solve \
  --output src/fungen_operator/resources/xqtl-linux-64.lock
```

Run the command in a host scheduler allocation on HPC. It uses `mamba create
--override-channels -c dnachun -c conda-forge -c bioconda` with the YAML package
specifications, then exports URLs and MD5 hashes. A failed solve leaves the
reviewed lock intact.

Software has a 35 GB budget and a user-selected folder. Pixi is offered through
StatFunGen pixi-setup. On Minerva its full setup fails in `safe_expose_remove`
because the upstream jq expression `.[].exposed.[].exposed_name` is invalid. The
exact native failure is retained in the validation record. It does not silently fall back to another package manager.

The workflow pin is `e1095f6354da6a4d2c43ef812eeb099a19fe93d2`. A retained interface
patch connects its current QtlDataset workers and per-gene SoS interface to its
Snakemake fine-mapping rule, uses normal SoS signatures, and maps PCA sample IDs
from the PLINK FAM order. The manifest sample list reaches both fine-mapping and
TWAS workers through the analysis-time `--keep-samples` argument. Software setup
also applies the retained `sos-pulse.patch` to SoS 0.25.1: monitor startup keeps the
already published pulse path present while native abort detection stays active.
Statistical calculations remain upstream. Cluster profiles
use 2000 jobs. The prepared-input RNA chain needs no genome, dbSNP or external LD
download; the notebook names the optional Ensembl 103 FASTA (about 840 MB) and GTF
(about 47 MB). This test generates fresh PLINK and normalized phenotype inputs.

The frozen seed is 20261020: 500 artificial participants, four regions on two
chromosomes, 512 variants and six contexts with four planted and four null traits
each. Genotype QC, native PCA, phenotype/covariate preparation, hidden factors,
TensorQTL and five-fold SuSiE/TWAS run through the upstream DAG. Every planted
causal pair must have nominal P < 5E-8 with its expected counted-allele direction
and causal membership in a 95% SuSiE credible set; at most one null trait may cross
that threshold. Acceptance checks native products and the generated truth.
The final deployment starts the user's own harmonized-data analysis after their
input paths and scientific choices are reviewed.
The 2026-11-06 fresh host LSF run at the new pin passed all seven guided steps
on its first attempt: 24/24 planted nominal/direction recoveries, 24/24 credible-set
recoveries and 0/24 null calls. Controller job: **281128220 DONE**. Native evidence
and host-suite results are in `temp_reference/codex_workflow_20261106/report.md`.

Troubleshooting mirrors `fungen check`, which reports PASS, FAIL or PENDING.
A fresh installation has PENDING runtime rows and an overall **NOT VERIFIED**
result with a nonzero exit status. Run `fungen serve`, then `fungen check`.
Recorded scheduler failures, unreachable endpoints and failed API observations
are failures. Empty or wrong-model GPU observations also block readiness.
Old log text is diagnostic context; readiness follows the current launch receipt,
endpoint and selected-model GPU observation.

| Check | Exact action |
|---|---|
| Install writable | Rerun setup with `--install WRITABLE_FOLDER`. |
| Install on PATH | Add `export PATH="$HOME/.fungen/bin:$PATH"` or confirm the setup PATH prompt. |
| Operator importable / skill visible | Rerun `apptainer run fungen.sif`. |
| Codex recent enough | Rerun setup to install the bundled client. |
| Internet reachable | Download on a login node or another machine; rerun with `--download no --models-dir FOLDER`. |
| Local backend assets | Rerun local setup to restore the pinned host client, shipped catalog, complete model and matching serve script. |
| Model present | Rerun with `--download yes` to resume. |
| Model folder writable | Select a writable download folder, or reuse a complete read-only store. |
| Model space and quota | Free storage, check your site quota, or choose scratch/project storage. |
| Server reachable / port | Run `fungen serve`, then `fungen check`. Inspect the recorded launch/job and its log on failure; unavailable scheduler status blocks another submission. |
| GPU visible / driver | Selected-model positive VRAM must be observed through `/api/ps`. Empty lists, API failures and CPU-only loads block readiness. Use a GPU queue and `--nv`; inspect driver errors in the recorded job log. |
| OpenAI signed in | Run `codex login --device-auth` or export `OPENAI_API_KEY` in the shell. |

Developer material: [build recipe](container/README.md), [image specification](docs/operator_container_spec.md),
[operator architecture](docs/operator_prototype.md), [operating model](docs/operator_model.md),
[benchmark](benchmark/README.md), [manifesto](MANIFESTO.md).


## Host test environment

Codex, the operator, tests and workflows execute on the host. The image runs
`serve` and `download`; its default entrypoint copies/installs the host bundle.
The image build context excludes `tests/`.

Activate a host environment providing **htslib** (`bgzip` and `tabix`), **SoS**
and **sos-pbs** on PATH. For example, install these tools with
`conda install -c conda-forge -c bioconda htslib sos sos-pbs`.
Install the Python test dependencies with `.venv/bin/python -m pip install -e '.[test]'`.
Set `FUNGEN_TEST_CODEX` to the bundled **host** Codex 0.155.1 binary, for example
`export FUNGEN_TEST_CODEX="$HOME/.fungen/bin/codex"`. Set `FUNGEN_TEST_SOS_PYTHON`
to the Python in that SoS environment when it differs from `python` on PATH.
The guided SGE/Slurm integration cases also require the locked xQTL tools and
pinned, patched upstream checkout. Run the guided setup through `fixture`, then
set `FUNGEN_TEST_XQTL_ROOT` to that setup root. These cases reuse its installed host
tools, clone the pinned workflow under each temporary setup root, generate fresh
500-person inputs, and run the actual guided test and frozen grader using synthetic
scheduler executables on PATH. Public inspection consumes the unmodified emitted
deployment and executed receipt notebook; the test creates neither receipt nor
replacement deployment.
They execute the scientific workflow on the host and need batch-sized CPU/memory
resources; native site acceptance remains separate. Then run on the host:

```bash
.venv/bin/python -m pytest -q tests
```

Missing htslib tools fail the required MWS-01 grader cases with the installation
command. Pinned-client tests load and round-trip the shipped catalog through `codex debug models` and compare actual local-provider Requests at an isolated loopback endpoint. No model inference is run.
SGE/Slurm controller and task-host unit/host tests establish rendering, receipts,
accounting and resource interpolation. Live site resource directives and a rebuilt
image still require site acceptance. Controller submission/readiness and retained controller/rule/SoS-child inspection use the configured scheduler. Inspection follows exact external-job receipts and task records; missing streams, missing task provenance, unknown native status and unavailable accounting raise an error; job-control/sweep actions remain LSF-only and report
that boundary before rendering a command. SGE success dependencies are unsupported
because `hold_jid` does not establish predecessor success.


Legacy server receipts containing only `job_id` are validated as LSF receipts:
configuration must select LSF and native `bjobs`/`bacct` evidence must identify
that job. A pending/running legacy launch is reused; a verified terminal launch
can be restarted once. Unknown status or a different configured scheduler blocks
resubmission with the native inspection/recovery instruction. Receipt validation
preserves the original file timestamp and server-state freshness checks.

Local operator actions complete synchronously on the host; replay continues after
completed actions without a scheduler job lookup. Local inspection marks external
scheduler health and dead-child counts as not applicable. Legacy `codex` client
keys remain readable, with the exact local client-version check enforced.
Deployment-registered scheduler account/queue bindings take precedence over
per-action defaults; unextended legacy LSF bindings retain their rendered bytes.


Public native inspection uses the same `submissions.jsonl` journal verifier for
LSF, SGE and Slurm. A durable intent/receipt pair identifies each rule/task
submission, controller/wrapper boundaries establish completion, exact output
streams must agree with the set, and the journal must remain stable. Zero jobs
or a successful scheduler query alone cannot verify discovery. Missing or
incomplete evidence returns `inspection_status: not_verified`,
`discovery_coverage.verified: false`, `scheduler_ok: false` and
`dead_child_count: null`; the CLI exits nonzero and retains observed job states.
Unknown scheduler status/accounting is an error.

Fresh LSF, SGE and Slurm setups use the same tracked rule/task adapter and
journal protocol. Native command rendering differs by scheduler; discovery proof
does not. Historical LSF setups generated before round 7 used direct task bsub
and omitted rule/task journal records. Those old launches remain unverified;
missing historical records cannot be reconstructed from observed output alone.
Generate a fresh setup to obtain complete tracking. LSF job-control membership
snapshots remain observations of identified jobs, not a completeness certificate.

A local receipt now records PID, kernel process-start ticks and boot identity.
A live recorded launch whose current endpoint fails remains a failure to inspect,
with its receipt preserved. A positively vanished or replaced process permits one
fresh launch. Permission/identity inspection errors block restart.
