# Build and validate the image locally

The [repository README](../README.md) is the user guide. This directory owns the
pinned image recipe and its native Minerva build/acceptance path. Publication is
outside this round.

Prepare an allowlisted context, then build with Docker:

```bash
python container/build.py context /path/to/fungen-context
docker build --platform linux/amd64 -f /path/to/fungen-context/container/Dockerfile \
  -t fungen-operator:ollama0.40.6-codex0.155.1 /path/to/fungen-context
docker save -o fungen-operator.tar fungen-operator:ollama0.40.6-codex0.155.1
apptainer build fungen.sif container/fungen.def
```

The context contains source, skills, tests and bounded documentation. It rejects
source symlinks, excludes data, sessions, credentials, caches and binary outputs,
and replaces historical personal path prefixes in skill examples with portable
placeholders. `context --refresh DIRECTORY` updates a known context and rejects
unexpected members. Models are acquired after installation, outside the image.

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
and installs onto the host. `serve` is the GPU-only model service; Codex and the
operator execute on the host. The runtime uses an explicit `--home` bind rather
than the unsupported `--env HOME` override.

`acceptance.py` drives clean-home setup with a real PTY and records transcripts
under the stranger scratch root. `acceptance.lsf` starts the GPU-backed staged or
XS scenario. `onboarding.lsf` installs the fresh pinned mamba environment. The
full operator suite runs through the repository's Python environment or the
built image's test environment. Native logs, job IDs, exact scenario outcomes,
image hash and remaining limitations belong in [VALIDATION.md](VALIDATION.md).
