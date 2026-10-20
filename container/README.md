# Fungen Operator + Ollama

**Validation status (2026-10-20):** the image builds and all 354 operator tests
plus 12 setup tests pass. The requested Ollama 0.18.2 pin rejects the staged
Laguna S GGUF with `unknown model architecture: 'laguna'`. Completing model
setup, real interactive re-run and agent inference requires a Laguna-capable
Ollama runtime. See [the validation record](VALIDATION.md) before downloading
model weights. The supplied recipe preserves the requested 0.18.2 pin.

The Linux amd64 image combines `ollama/ollama:0.18.2` (all its CPU, CUDA,
Vulkan and MLX-CUDA backends), this checkout's installed operator, repository-owned
skills and tests, Python 3.12.13, and the benchmark-tested Codex CLI 0.155.1.
Models and user configuration live in mounted storage. No login or API key is
needed for the local agent. External workflow deployments, their domain skills,
scientific runtimes, scheduler clients and data remain deployment inputs.

## Build

From the repository root, prepare an allowlisted build context. It includes tracked
source and container files, excludes credentials/data/history and symlinks into
external projects, and replaces personal site prefixes in skill examples with
`/workspace`. Use this preparation step for every build.

```bash
python container/build.py context /tmp/fungen-context
docker build --platform linux/amd64 -f /tmp/fungen-context/container/Dockerfile \
  -t fungen-operator:ollama0.18.2-codex0.155.1 /tmp/fungen-context
docker save -o fungen-operator.tar fungen-operator:ollama0.18.2-codex0.155.1
apptainer build fungen-operator.sif container/fungen.def
```

The definition consumes `fungen-operator.tar` in the current directory. Docker's
base tag, Python download and Codex downloads are pinned; binary download hashes
are checked. Python dependencies follow `pyproject.toml` version ranges.

Minerva also supports a daemon-free build: materialize the pinned base with
`singularity build --sandbox "$FUNGEN_BUILD_DIR/fungen-rootfs" docker://ollama/ollama:0.18.2`,
prepare the context at `$FUNGEN_BUILD_DIR/fungen-context`, then submit
`bsub < container/build.lsf` from the repository root with `FUNGEN_BUILD_DIR` exported.
The job uses an isolated user-namespace chroot, the same installer, a local Docker
archive, and direct `docker-archive://` conversion. That conversion preserves the
Docker entrypoint/command/environment without requiring definition-file build
privileges on Singularity 3.11. The definition provides the equivalent conversion
on a builder that supports definition files. Run LSF clients through the approved host path.
The validation record names the successful method and retained logs.

## Laptop: Docker

```bash
docker run --platform linux/amd64 -it --name fungen -e HOME=/home/fungen \
  -v fungen-home:/home/fungen -v "$PWD:/workspace" \
  fungen-operator:ollama0.18.2-codex0.155.1
```

For NVIDIA GPUs add `--gpus all` with NVIDIA Container Toolkit installed. Without
that flag Ollama uses CPUs; Q4 needs about 96 GB disk plus runtime RAM and context
memory, so a large-memory machine is needed. Apple Silicon can emulate amd64 CPU
execution; this Linux image does not expose Apple's Metal GPU.

The default command keeps the server running after setup. Open a second terminal:

```bash
docker exec -it fungen fungen-agent --deployment /workspace/deployment.json
docker exec -it fungen fungen-operator --help
```

## First run and reuse

The prompts are:

```text
Download Laguna S? [yes/no] (default no):
Laguna S tags (approximate disk/download size):
  q4_K_M: 96 GB
  q8_0: 128 GB
  q4_K_M-256k-t2: 96 GB (256K context, 2 CPU threads; local preset)
  q8_0-256k-t2: 128 GB (256K context, 2 CPU threads; local preset)
Which tag? (default q4_K_M):
Model folder to download into or reuse (default $HOME/.fungen/models):
```

Answer `yes` to pull a library quantization; the `-256k-t2` variants create a local
preset from that library base. Answer `no` and point to an existing Ollama model
store (`blobs/` and `manifests/`), including a read-only bind. Choose a tag present
there. The registry's published quantizations are documented on the
[Laguna S tags page](https://ollama.com/library/laguna-s-2.1/tags).
Download checks require write access and model size + 10% + 2 GB free space;
filesystem quota can impose an additional limit.

Setup starts `ollama serve`, waits for readiness, checks the exact model is listed,
and runs a one-line prompt. It atomically saves **one user config** at
`${XDG_CONFIG_HOME:-$HOME/.config}/fungen/config.json` after inference succeeds.
Server PID/lock/log and isolated Codex session state are adjacent runtime files.
Re-runs reuse that config and its daemon; an unrelated listener or different
model folder on the same endpoint is rejected. Use a free `--endpoint` to change
stores while another server remains running.

```bash
fungen-setup --non-interactive --download no --tag q4_K_M \
  --models-dir /models --endpoint http://127.0.0.1:11434
```

Flags also accept `FUNGEN_DOWNLOAD`, `FUNGEN_MODEL_TAG`, `FUNGEN_MODELS_DIR` and
`FUNGEN_ENDPOINT`. Downloads always require an explicit yes/no in scripted mode.
Add `--stay` to keep a container's main process alive. Next time use `fungen-serve`
to start a foreground server from saved config, then `fungen-agent` in another shell.
Raw Ollama commands need `OLLAMA_HOST` set to the saved endpoint when using a
non-default port. Setup defaults to 32K context, one parallel request, flash
attention and Q8 KV cache; the 256K presets request their declared model context.
Override Ollama tuning through environment variables at server startup.

## HPC: Apptainer / Singularity

Inside a scheduler-allocated GPU job:

```bash
apptainer run --nv --bind /persistent/model-store:/models:ro \
  fungen-operator.sif setup --non-interactive --download no \
  --tag q4_K_M --models-dir /models --stay
```

Use the same image and binds for subsequent `apptainer exec ... fungen-agent`
calls on the same allocated node, and retain the same home/config directory. Replace `apptainer` with
`singularity` where appropriate. For writable download storage omit `:ro` and
select `--download yes`. Allocate sufficient GPU memory (the retained Q4 test
requests two GPUs with at least 70 GB each); smaller GPUs can offload to CPU RAM.
The launch inherits the scheduler's GPU visibility; `--nv` supplies host drivers.
For an isolated writable home, use `--home /persistent/container-home:/home/fungen`.
Singularity does not permit overriding `HOME` through `--env HOME=...`.

`container/smoke.lsf` is the retained Minerva GPU test. Export `FUNGEN_IMAGE`,
`FUNGEN_STAGED_MODELS`, and `FUNGEN_AUDIT_DIR`, then submit it from the repository
root. It binds the staged store read-only and tests the CLI, full operator suite,
setup regressions, scripted setup, interactive no-download/re-run, and Codex.
After the suites pass on an unchanged image, `FUNGEN_SKIP_SUITE=1` reruns the
service checks. The harness script is mounted from the checkout read-only.

## Use the operator

Mount your developer-owned workflow and portable deployment JSON at `/workspace`.
Run `fungen-agent --deployment /workspace/deployment.json`. It selects the saved
model and local Ollama `/v1` endpoint, connects the operator stdio MCP server, and
loads the operator skill through its startup instructions. Codex keeps ordinary
workspace-write/on-request approvals; scientific elicitation remains human-owned.
The backend settings use the native local-provider configuration described by
[OpenAI's configuration reference](https://developers.openai.com/codex/config-reference).

The direct interface is `fungen-operator --help`. For a synthetic demonstration:
`fungen-operator demo --root /workspace/demo`. The deployment supplies canonical
workflow commands and host/scheduler integration; this image provides the operator
and agent runtime, while each workflow retains its own scientific environment.
