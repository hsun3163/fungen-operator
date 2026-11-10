# Build and validate the image locally

The [repository README](../README.md) is the user guide. This directory owns the
pinned image recipe and its native Minerva build/acceptance path. Validated builds
are published to GitHub Container Registry through ORAS (below); the publication of
a given build is recorded in [VALIDATION.md](VALIDATION.md).

Prepare an allowlisted context, then build with Docker:

```bash
python container/build.py context /path/to/fungen-context
docker build --platform linux/amd64 -f /path/to/fungen-context/container/Dockerfile \
  -t fungen-operator:ollama0.40.6-codex0.155.1 /path/to/fungen-context
docker save -o fungen-operator.tar fungen-operator:ollama0.40.6-codex0.155.1
apptainer build fungen.sif container/fungen.def
```

The context contains source, skills and bounded documentation. Host tests and container test hooks are excluded in both the generated context and the Docker allowlist. It rejects
source symlinks, excludes data, sessions, credentials, caches and binary outputs,
and replaces historical personal path prefixes in skill examples with portable
placeholders. `context --refresh DIRECTORY` updates a known context and rejects
unexpected members. `context` builds only from a commit: it refuses when any
admitted file differs from HEAD (modified, staged, deleted or untracked), so
`context` captures one commit, reads its tree and blobs, and then applies the declared portable-path transformation. `source.json` records that captured commit, source blob IDs and transformed file hashes. Concurrent worktree/HEAD edits cannot change the copied snapshot; differing index-hidden admitted worktree files are refused too. Models are
acquired after installation, outside the image.

On Minerva use `container/build.lsf`: set `FUNGEN_BUILD_DIR` under the image folder,
submit with `FUNGEN_BUILD_STAGE=base` to acquire the exact pinned base, prepare
`$FUNGEN_BUILD_DIR/fungen-context`, then submit again with the default `install`
stage. Every scheduler and network command uses the host approval path. The
installer runs inside an isolated user-namespace chroot. The installed rootfs is
exported to a Docker archive, then converted through `docker-archive://` with
Singularity 3.11. `pack` and `convert` repeat those respective stages. No Docker
daemon, subordinate UID mapping or remote builder is required.

`install.sh` pins Python 3.12.13, Codex 0.155.1 and uv 0.13.4 and checks download
hashes. It builds the operator wheel and downloads its dependency wheels for
offline host installation with uv. The image's default command copies this bundle
and prints the command that completes setup on the host, where scheduler clients are visible. `serve` is the model service with a positive selected-model GPU-offload readiness gate; Codex and the
operator execute on the host. The runtime uses an explicit `--home` bind rather
than the unsupported `--env HOME` override. Setup inside the image checks that the
host storage has positive shared-filesystem or physical block-device/kernel evidence and stops before installation writes with the exact
`<runtime> run --home $HOME:$HOME <image>` fix when home mounting is disabled
(`--contain` or a site configuration); an install folder outside home needs
`--bind FOLDER:FOLDER`. `serve` refuses CPU-only inference: with no GPU, or a
model loaded without VRAM, the serve job fails with the GPU-job/`--nv` fix.

`acceptance.py` drives clean-home setup with a real PTY and records transcripts
under the stranger scratch root. `acceptance.lsf` starts the GPU-backed staged or
XS scenario. `onboarding.lsf` installs the fresh pinned mamba environment. The
full operator suite runs on the host through `.venv/bin/python -m pytest -q tests`, with htslib (`bgzip`, `tabix`), SoS/sos-pbs and bundled host Codex 0.155.1. See the root README's host test environment. Missing required tools fail loudly. Tests are excluded from the image context; image validation covers installer copying and model serving/downloads. Native logs,
job IDs, exact scenario outcomes, image hash and remaining limitations belong in [VALIDATION.md](VALIDATION.md).

## Publish and pull through GHCR

GHCR replaces the retired Sylabs Cloud Library distribution path. Models and
runtime state stay outside the image. The released package is public and supports anonymous pulls. Authentication is
needed only when publishing or accessing a private package.

For an accepted Minerva-built SIF from reviewed, committed source, run the
publisher on Minerva outside the sandbox. Provide `GHCR_TOKEN` with `write:packages`
and `read:packages`, or use a `gh` login with those scopes:

```bash
python3 container/publish.py "$SIF_PATH" ollama0.40.6-codex0.155.1 latest \
  --output "$EVIDENCE_DIR/publish.json"
```

The publisher checks authenticated manifests and tag listings, then pulls each tag
with caching disabled and requires its SIF SHA-256 to match the built image.
The evidence records the SIF hash and registry manifest digests.

Releases are built on Minerva, accepted with GPU and interactive checks, and
published from Minerva using the accepted SIF bytes. No GitHub Actions workflow
publishes images. Moving aliases are updated only to an accepted release.

Private pulls require `read:packages` and package access:

```bash
gh auth token | apptainer registry login --username hsun3163 --password-stdin oras://ghcr.io
apptainer pull fungen.sif oras://ghcr.io/hsun3163/fungen-operator:ollama0.40.6-codex0.155.1
# Minerva Singularity 3.11:
gh auth token | singularity remote login --username hsun3163 --password-stdin oras://ghcr.io
singularity pull fungen.sif oras://ghcr.io/hsun3163/fungen-operator:ollama0.40.6-codex0.155.1
```

Check `sha256sum fungen.sif` against the publication evidence. Record functional
image acceptance separately in [VALIDATION.md](VALIDATION.md).

## Operator release tags

Operator semantic versions are independent of the Ollama/Codex component pins.
Annotated Git tags `v1.0.0`, `v1.1.0`, and `v1.2.0` identify release commits;
GitHub releases contain the corresponding [CHANGELOG](../CHANGELOG.md) entry.
The immutable GHCR tags for this release are `1.2.0` and
`1.2.0-ollama0.40.6-codex0.155.1`. The component-only
`ollama0.40.6-codex0.155.1` and `latest` tags move to the accepted release.
Existing version tags must never be repointed to different bytes. Historical
`1.0.0` and `1.1.0` tags refer to their original registry manifests; if an original
manifest is unavailable, the changelog records that fact without a rebuilt substitute.

The package version is defined in `src/fungen_operator/__init__.py`; setuptools
reads it through `tool.setuptools.dynamic.version`. `fungen --version` reports
that value and the build context records the value from the captured source blob
in `source.json` beside the image source commit. The changelog and validation
record distinguish image source commits from later release documentation commits.

For release 1.2.0, publish all four tags through the native publisher:

```bash
python3 container/publish.py "$SIF_PATH" 1.2.0 \
  1.2.0-ollama0.40.6-codex0.155.1 ollama0.40.6-codex0.155.1 latest \
  --output "$EVIDENCE_DIR/publish.json"
singularity pull fungen.sif oras://ghcr.io/hsun3163/fungen-operator:1.2.0
```

Keep package visibility and repository settings unchanged.
