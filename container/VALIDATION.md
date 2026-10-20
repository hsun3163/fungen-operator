# Container validation — 2026-10-20

Status: **image built; operator and setup unit suites verified; Laguna S setup blocked by the requested Ollama version**.

## Image and source

- Image: `~/sunh14_project/OLLAMA/images/fungen-operator-ollama0.18.2-codex0.155.1.sif`
- Size: **3,434,983,424 bytes** (3.43 GB; 3.20 GiB).
- SHA256: `4024c544f3f9b93f3d8f8c48d4e63f3ff1685a6fe3336f2c4a6aa47c6d9695f4`
- Base: `ollama/ollama:0.18.2`; original CPU, CUDA 12/13, Vulkan and MLX-CUDA payload retained.
- Operator: package 0.1.0 from checkout `05c4f6b`; core source and pyproject remained unchanged during this work.
- Agent: Codex CLI **0.155.1**, matching the retained MWS-01 benchmark; native musl binary and bwrap downloads are hash-checked.
- Python: standalone CPython **3.12.13**; dependencies installed from this checkout's declared ranges, including MCP 2.3.0.
- Setup/agent program SHA256: `c1de7ec203132a4cf663f1f6590300a376ad92ba04d22a25474d8a881d46f191`, identical in the image and checkout.

The source context includes the package, tests, repository-owned skills and bounded documentation. Workflow-owned skill links into protected projects are excluded. Models, analysis products, credentials, host-home content and private Singularity sandbox metadata are excluded. Personal site prefixes in copied skill examples become portable workspace placeholders. SIF provenance records the relative source `fungen-operator.tar`.

## Working build path

The working Minerva path is:

1. Materialize the pinned Docker base as a Singularity sandbox.
2. Prepare the allowlisted context with `container/build.py context`.
3. Run `container/install.sh` in an isolated `unshare --user --map-root-user --mount` chroot through LSF.
4. Export the installed filesystem as a local Docker archive, omitting Singularity-generated metadata/action links and the builder's generated home directory. Normalize OCI ownership and make the public runtime readable to ordinary container users.
5. Convert with Singularity 3.11 using `docker-archive://fungen-operator.tar` from the archive directory.

`container/build.lsf` retains this path. Its default stage installs and builds; `FUNGEN_BUILD_STAGE=pack` re-exports an already-installed filesystem, and `convert` repeats conversion. Final build job **277510661** reached `DONE`. The installed payload was prepared through the same installer used by the Dockerfile.

The initial alternatives established concrete platform constraints: fakeroot has no subuid mapping; the remote builder token is expired; PRoot is denied by ptrace policy. A definition-file build is privilege-gated on Singularity 3.11; direct Docker archive conversion works. The Dockerfile was parsed with dockerfile-parse 2.0.1 and shell scripts passed `bash -n`. Docker daemon execution was unavailable here. The supplied definition consumes a Docker archive on a definition-capable builder.

## Tests and observed results

| Check | Result | Evidence |
|---|---|---|
| SIF default command | Pass | `singularity run IMAGE --help` displays setup/serve/agent. |
| Installed operator CLI | Pass | `fungen-operator --help` succeeds with the image's clean environment. |
| Pinned client | Pass | In-image `codex --version` reports 0.155.1. |
| Operator suite | **354 passed** | GPU job 277510265; 50.96 seconds. |
| Setup regressions | **12 passed** | Same GPU job; 0.06 seconds. |
| GPU binding | Pass | Two H100 80 GB GPUs; Ollama detects CUDA 13 and both allocated devices. |
| Existing model discovery | Pass | The exact staged Q4 preset is present in `/api/tags` and setup reaches model loading. |
| Read-only reuse / downloads | Pass | Staged store bound read-only at `/models`; download choice is explicitly `no`; no model pull is issued. |
| One-line inference | **Failed: version incompatibility** | GPU job 277514023; Ollama 0.18.2 returns HTTP 500 and logs `unknown model architecture: 'laguna'`. |
| Literal `ollama list` command | Not reached | The smoke script stops at the failed required inference check. API model discovery already succeeded. |
| Real PTY interactive setup / re-run | Blocked | Downstream of successful scripted setup; prompt and idempotency unit coverage passed. |
| Agent inference against Laguna | Blocked | Downstream of successful model setup; no successful config is committed after a failed inference. |

The first GPU attempt exposed an unwritable home: `--env HOME=...` is refused by Singularity. The retained launch now uses an explicit writable `--home` bind. The suite's 33 initial warnings were IPython's temporary-home fallback. Service retry **277514023** used the corrected home, preserved the same image, and skipped the already-passed suites. It reached the decisive model-architecture failure.

## Setup behavior

The default entrypoint asks whether to download, displays four tag choices with approximate sizes (Q4 96 GB; Q8 128 GB), asks for a tag and model folder, checks storage, and starts Ollama. The 256K/two-thread variants are local presets created from library quantizations on download, or reused unchanged from an existing store. Scripted flags and environment variables are documented in the README.

A successful one-line inference atomically commits the single Fungen user config. The current pinned runtime fails that check, so model setup remains incomplete and no successful user configuration is asserted. The image and code remain available for review and the runtime-version decision.

## Remaining decision and native state

The requested pin predates Laguna architecture support in this tested path. Upstream 0.18.2 has no Laguna implementation; the [0.34.4 source tree includes Laguna implementations](https://github.com/ollama/ollama/tree/v0.34.4/mlxrunner/model/laguna). **0.34.4 is a concrete next runtime candidate, requiring GPU verification with this GGUF**. Changing the requested runtime pin requires Hao's decision.

At the recorded checkpoint, job **277514023** remains `RUN` because its background Ollama server remains alive after the failed setup command. It has a two-hour walltime. Stopping this exact job requires permission under the supplied AGENTS.md rule for terminating commands. No job was killed.

Next step: approve a Laguna-capable runtime change and stopping job 277514023, then rebuild and complete the model, literal list, PTY re-run and agent checks.

Raw evidence is retained together in `~/sunh14_project/fungen-operator/temp_reference/container/`, including final build log `build.277510661.log`, suite log `smoke.277510265.log`, the service snapshot `smoke-live.log`, and server log under `gpu/home/.config/fungen/ollama.log`. The SIF and native build intermediates remain outside git. Final review confirmed the explicit blocked state, retained workflow boundary, exact test counts and absence of a push.
