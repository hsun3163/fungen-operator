# Fungen Operator

Install a workflow operator on your host and serve Laguna from one Apptainer
image. Host Codex uses the operator's notebook actions and your scheduler. The
image contains Ollama **0.40.6**, Codex **0.155.1**, uv **0.13.4**, an offline
operator wheel bundle and its skill. Models and credentials stay on the host.
The current build targets Linux x86-64 with Apptainer/Singularity. The local
backend needs an NVIDIA GPU; the OpenAI backend runs host Codex without one.

With a locally built `fungen.sif`, the quick start is two shell commands:

```bash
apptainer run fungen.sif
~/.fungen/bin/fungen serve && ~/.fungen/bin/fungen codex
```

Use `singularity` in place of `apptainer` on Minerva. Local builds and acceptance
are recorded in [container/VALIDATION.md](container/VALIDATION.md). Registry
publication is a separate step.

Setup asks, in order:

```text
Install folder [~/.fungen]:
Scheduler (lsf/slurm/local) [detected scheduler]:
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

The model questions apply to the local backend. On clusters setup warns about
home quotas. A new download requires a writable folder and model size plus 10%
plus 2 GB free space; check the site's quota too. Ollama resumes partial blobs.
If an interruption leaves an empty or truncated Ollama progress record, setup
archives that record under the model folder's `.fungen-download-recovery` and
retains the partial blob. Ollama resumes the remaining chunks and verifies their hash.
A complete existing model folder may be read-only. Advanced 256k context creates
a local Modelfile variant in a writable overlay, reusing the base blobs. Ollama
refreshes blob timestamps during variant creation, so this advanced option needs
a writable base model store; use the default 32768 context for read-only reuse.

Setup installs under the chosen folder, keeps host Codex 0.155.1 or newer, and
copies the bundled client when needed. It installs the Codex skill without
replacing the user's Codex configuration. Backend settings live in
`~/.config/fungen/config.toml`; local Codex sessions use the install folder's
separate Codex home. Setup upgrades to the image's operator bundle on re-run.
The PATH line is appended only after an explicit `yes`.

For the OpenAI backend, setup prints `codex login --device-auth` for headless
sign-in. You may instead set `OPENAI_API_KEY` in your shell. The launcher passes
the key through the environment; it never writes it to a configuration, image
or working folder. Ordinary host `codex` also sees the installed skill.
See [Codex authentication](https://developers.openai.com/codex/auth/) and
[configuration](https://developers.openai.com/codex/config-reference/).

Daily commands:

```bash
fungen serve                  # submit/start the GPU model server
fungen codex                  # wait for the recorded endpoint; start host Codex
fungen check                  # checks and exact fixes
fungen codex --deployment deployment.json
fungen codex -- exec --skip-git-repo-check 'Your task'
```

The server script is `~/.fungen/serve.lsf.sh`, `serve.slurm.sh` or `serve.local.sh`.
It requests the tag's GPU count, uses `apptainer run --nv IMAGE serve`, selects a
free port, tests inference, and records the node and port. Without a GPU the local
server stops with the exact `--nv`/GPU-job fix. Choose OpenAI on a machine without
a GPU. Workflows and their scheduler clients run on the host.

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
Setup registers the **Fungen Operator** Jupyter kernel using the installed host
Python, so these cells import the operator even when Jupyter itself uses another environment.
Resume with `--step workflow|software|reference|scheduler|fixture|test|handoff`.
Mamba is the required route, using hash-pinned Miniforge 26.7.2-0 and the bundled version-pinned environment;
software has a 35 GB budget and a user-selected folder. Pixi is offered through
StatFunGen pixi-setup. On Minerva its full setup fails in `safe_expose_remove`
because the upstream jq expression `.[].exposed.[].exposed_name` is invalid. The
exact native failure is retained in the validation record. It does not silently fall back to another package manager.

The workflow pin is `f66555213b5deeb68d347690493b694de923ef4d`. A retained interface
patch connects its current QtlDataset workers and per-gene SoS interface to its
Snakemake fine-mapping rule, uses normal SoS signatures, and maps PCA sample IDs
from the PLINK FAM order. Statistical calculations remain upstream. Cluster profiles
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

Troubleshooting mirrors `fungen check`:

| Failed check | Exact action |
|---|---|
| Install writable | Rerun setup with `--install WRITABLE_FOLDER`. |
| Install on PATH | Add `export PATH="$HOME/.fungen/bin:$PATH"` or confirm the setup PATH prompt. |
| Operator importable / skill visible | Rerun `apptainer run fungen.sif`. |
| Codex recent enough | Rerun setup to install the bundled client. |
| Internet reachable | Download on a login node or another machine; rerun with `--download no --models-dir FOLDER`. |
| Model present | Rerun with `--download yes` to resume. |
| Model folder writable | Select a writable download folder, or reuse a complete read-only store. |
| Model space and quota | Free storage, check your site quota, or choose scratch/project storage. |
| Server reachable / port | Run `fungen serve`; inspect its native job log. The server records the selected free port. |
| GPU / driver | Use a GPU queue and `--nv`; update the host driver if the log reports CUDA incompatibility. |
| OpenAI signed in | Run `codex login --device-auth` or export `OPENAI_API_KEY` in the shell. |

Developer material: [build recipe](container/README.md), [image specification](docs/operator_container_spec.md),
[operator architecture](docs/operator_prototype.md), [operating model](docs/operator_model.md),
[benchmark](benchmark/README.md), [manifesto](MANIFESTO.md).
