# Fungen operator image — specification

Status: round 2 implementation contract, 2026-10-20. Local build and acceptance evidence are in `container/VALIDATION.md`. Round 1 used Ollama 0.18.2, which cannot load Laguna. Round 2 pins the latest release resolved on this date, Ollama **0.40.6**, with bundled Codex **0.155.1**, uv **0.13.4**, and standalone Python **3.12.13**. Publication in section 7 is a future phase; this round builds and tests locally and pushes nothing.

## 1. Purpose

One public Apptainer image is the installer and the model server for the fungen operator. It recreates on any machine the setup Minerva uses today: the Ollama image only serves the model (on a GPU, as a batch job on a cluster), while Codex and the operator run on the host and submit jobs through the host's own scheduler.

    apptainer pull fungen.sif library://<sylabs-user>/fungen/operator:<version>
    apptainer run fungen.sif            # setup: installs onto the host
    apptainer run --nv fungen.sif serve # model server (the only thing that runs inside the image)

## 2. Image contents

| Component | Version policy | Use |
|---|---|---|
| Ollama with CUDA 12/13, Vulkan and CPU-instruction backends | `ollama/ollama` base pinned to the current latest release (exact tag; round 1 showed 0.18.2, the current Minerva image, cannot load Laguna) | `serve`, model download |
| Codex CLI (Apache-2.0) | pinned to the version the operator is tested with | copied onto the host by setup |
| fungen-operator package, CLI and skills | this repository at the tagged commit | installed onto the host by setup |
| A standalone Python installer (e.g. `uv`) | pinned | installs the operator on the host with no system Python needed |
| `fungen` launcher (setup, check, serve, codex) | this repository | |

Not in the image: models, credentials, data, site-specific paths, anything from protected folders. Claude Code is out of scope.

## 3. Setup (`apptainer run fungen.sif`)

1. **Install folder** on the host (default `~/.fungen`; the `bin/` inside it is added to PATH through a one-line shell-profile edit the user confirms).
2. **Operator:** installs the operator CLI and its Codex skill there. Re-running upgrades it to the image's version.
3. **Codex:** uses the host's Codex if one is present and recent enough; otherwise copies the bundled Codex into the install folder.
4. **Model backend:**
   - **Local Laguna:** model and tag from the table below, model folder (cluster: scratch or project space proposed, with a home-quota warning; laptop: `~/.fungen/models`), or an existing folder that already holds the model. Downloads with `ollama pull` inside the image, resumable.
   - **OpenAI account:** Codex's own sign-in (device-code flow on machines without a browser) or `OPENAI_API_KEY`.
   Models offered, Laguna XS up to Laguna S (larger tags are left out as too large for typical cluster GPUs; MLX tags are Apple-only):

   | Choice | Download | Fits |
   |---|---:|---|
   | `laguna-xs-2.1:q4_K_M` | 20 GB | one 24–48 GB GPU |
   | `laguna-xs-2.1:q8_0` | 36 GB | one 48–80 GB GPU |
   | `laguna-s-2.1:q4_K_M` | 96 GB | one 141 GB GPU or two 80 GB GPUs |
   | `laguna-s-2.1:q8_0` | 128 GB | one 141 GB GPU (tight) or two 80 GB GPUs |

   Default: the largest choice that fits the GPU memory setup can see (it asks the scheduler or runs a short GPU probe); `laguna-xs-2.1:q4_K_M` when it cannot tell. The serve job requests a matching GPU count. An advanced option sets a longer context window (for example 256k), built locally as a Modelfile variant; it needs extra GPU memory.
5. **Server launcher (local backend):** detects the scheduler (LSF, Slurm or none) and writes `~/.fungen/serve.<scheduler>.sh`, a GPU job that runs `apptainer run --nv fungen.sif serve` and records the node and port. On a laptop it is a plain background command.
6. **Config:** `~/.config/fungen/config.toml` (backend, model, model folder, image path, port, scheduler).
7. **Check (§5)**, then prints the two commands for next time.

Setup is safe to re-run (it keeps what is valid, repairs what is not) and has a non-interactive form taking the same answers as flags or environment variables.

## 4. Daily use

- **Local Laguna S:** `fungen serve` submits or starts the server; `fungen codex` waits for it, then starts the host's Codex pointed at it (`ollama launch codex`-equivalent settings: endpoint and model). The operator skill is loaded.
- **OpenAI account:** `codex` as usual; the operator skill is loaded.
- Operator workflows run on the host and submit jobs through the host's scheduler, as on Minerva.

There is no CPU mode for the local backend; without a GPU, setup points to the OpenAI-account backend.

## 4a. First task: set up the xQTL protocol through fine-mapping

After the wizard the user runs `fungen codex` and asks to set up the xQTL protocol. The operator runs a fixed sequence of setup actions; each is a notebook cell, asks before it runs, is safe to re-run, and is checked before the next one. A failure stops at that step with the exact fix; re-running resumes there.

1. **Workflow:** upstream StatFunGen/xqtl-protocol at a pinned commit, using its Snakemake path (`code/snakemake`: Snakefile, config.yaml, rules, tests).
2. **Software:** the protocol's tools (PLINK, bcftools, TensorQTL, the R fine-mapping packages, …) into a folder the user picks, with the size shown first. The operator asks which package manager the user prefers:
   - **mamba**, from conda environment files carrying pinned versions (the route that must pass);
   - **pixi**, through StatFunGen's pixi-setup (upstream's documented route), offered with any limitation found on test sites stated.
3. **Reference data:** name and size the references required by the selected starting boundary. The prepared PLINK/normalized phenotype-BED chain uses GRCh38 coordinates and fixture-derived trait annotation (under 100 KB); its LD comes from the synthetic genotypes, so it requires zero external reference bytes. Raw RNA alignment would additionally need the protocol's Ensembl 103 FASTA (about 840 MB) and GTF (about 47 MB); record these as optional, rather than downloading unused references.
4. **Scheduler:** detects LSF, Slurm or none and writes the Snakemake profile with resource defaults.
5. **Test run up to fine-mapping** on synthetic data with planted eQTLs: genotype QC → phenotype preparation → covariates (PCA, hidden factors) → cis-eQTL scan (TensorQTL) → SuSiE fine-mapping on a few regions. Passes when every step finishes on the user's scheduler and the planted eQTLs are recovered.
6. **Hand-off:** an operator deployment for the user's own data and the notebook recording what was installed and tested.

The selected test is a de novo seeded fixture, never a legacy MWE or real individual: 500 participants, four regions, 512 variants, six RNA contexts, 24 planted traits and 24 null traits. Freeze the recovery criterion before fitting: every planted causal pair has nominal P < 5E-8 in its expected counted-allele direction and belongs to a 95% SuSiE credible set; at most one null trait crosses that threshold. The seed is 20261020. The upstream workflow pin is `f66555213b5deeb68d347690493b694de923ef4d`; retain and record its interface patch for current QtlDataset/SoS workers, scheduler integration, normal SoS signatures and PCA/FAM sample identity. Statistical calculations remain upstream. Mamba uses pinned Miniforge 26.7.2-0 and the versioned environment file plus its explicit 790-package hash lock, including susieR 0.16.6 required by pecotmr 0.9.3. Pixi remains offered with the tested Minerva limitation stated explicitly.

## 5. Checks (`fungen check`)

Each item reports pass or fail with the exact fix.

| Check | Applies to |
|---|---|
| Install folder writable and on PATH; operator importable; skill visible to Codex | all |
| Codex present and recent enough | all |
| Internet reachable (model registry or OpenAI API) | all |
| Model folder writable; free space and quota enough for the tag; model present | local |
| GPU visible inside the image with `--nv`; driver new enough for the bundled CUDA (run on a GPU node) | local |
| Server reachable at the recorded node and port; port free when starting | local |
| Codex signed in or API key present | OpenAI account |

## 6. Acceptance test

On Minerva, as a stranger would: a fresh shell, a clean home-like directory and an empty working folder, using the locally built SIF. Do not publish or pull a newly published operator image in this round. Exercise prompts through a real PTY and verify the model on H100 GPUs.

| Scenario | Expected |
|---|---|
| Setup with no Codex on PATH, local backend, staged Laguna S folder (read-only); and a fresh `laguna-xs-2.1:q4_K_M` download into an empty scratch folder | operator and Codex installed on the host; the LSF serve script runs on a GPU node; `fungen codex` answers a test prompt and makes one operator call that submits and completes a small LSF job |
| Setup with an existing Codex on PATH | host Codex kept |
| OpenAI-account backend | setup reaches the sign-in step; no credential file in the image or working folder |
| Server started without `--nv` / on a non-GPU node | GPU message with the exact fix |
| Port 11434 busy | another port chosen and recorded |
| No network | offline guidance (download on a login node or another machine, then point at the folder) |
| Re-run after a completed setup; after an interrupted download | no changes; download resumes |
| Slurm and no-scheduler serve scripts | generated and syntax-checked (live run on LSF only) |

## 7. Distribution

| Item | Value |
|---|---|
| Registry | Sylabs library, public: `library://<sylabs-user>/fungen/operator` |
| Tags | `<operator version>` and `latest` |
| Build | Sylabs remote builder from `container/fungen.def`; also buildable from `container/Dockerfile` |
| Signing | Signed with Hao's Sylabs key when available |
| Source | `container/` in the fungen-operator repository |

## 8. Out of scope

Claude Code; Ollama Cloud; models other than Laguna XS and S; the scientific workflow containers and data (the portable MESA reproduction is designed separately in `portable_mesa_reproduction.md`).

## 9. Decisions for Hao

| Decision | Proposed default |
|---|---|
| Sylabs account and collection name | `<sylabs-user>/fungen/operator` |
| Install folder and PATH edit | `~/.fungen`, PATH edit after confirmation |
| Operator version in the first public tag | the current main commit once its push is done |
