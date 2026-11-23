# Fungen Operator

Fungen Operator lets a coding agent run the [FunGen-xQTL protocol](https://github.com/StatFunGen/xqtl-protocol)
on an HPC cluster while the science stays fixed. The agent does not edit workflow code or submit jobs freely.
It works through five operator actions, exposed as MCP tools:

| Action | What it does |
|---|---|
| `prepare_config` | Prepares the canonical configuration; a scientific change requires human approval |
| `check_readiness` | Runs the canonical dry-run; records `ready`, or `nothing_to_do` once the run is complete |
| `initiate_run` | Submits or resumes the same workflow graph through a fixed scheduler cell |
| `control_run` | Kills or moves this run's jobs to another queue, after approval |
| `inspect_run` | Reads action history, scheduler states, logs and requested files |

Each action appends a fixed cell to an operator notebook. The notebook is both the recipe and the history:
`fungen-operator verify` re-renders every cell and fails if any differs. A scientific parameter changes only after
an explicit human yes. The reasoning behind this design is in [Agents Toward Determinism](MANIFESTO.md).

Schedulers: LSF, Slurm, SGE and local. Models: a local GPU model served from the container, or OpenAI.

## Evidence

| Test | Result | Record |
|---|---|---|
| Guided setup on a fresh LSF host, synthetic 500-person fixture (2026-11-06) | 7/7 steps; 24/24 planted associations recovered; 0/24 null traits called | [install guide](docs/install.md) |
| MWS-01: chr22 phenotype partition, 500 samples, 16 phenotypes (2026-09-25) | 8,000 of 8,000 phenotype values match the source | [MWS-01](https://github.com/hsun3163/fungen-operator-benchmark/blob/main/mws01/README.md) |
| Single agent vs agent swarm, with and without the operator, 5 trials per arm (2026-11-21) | Single agents passed 7/10, swarms 2/10 at 5.9× the tokens; all 31 unfinished units stopped at an approval-review step | [swarm 2×2](https://github.com/hsun3163/fungen-operator-benchmark/blob/main/swarm_2x2/README.md) |

Schedulers validated live: LSF. SGE was validated by an outside user on the previous image; Slurm has rendering tests only.

## Install

```bash
apptainer pull fungen.sif oras://ghcr.io/hsun3163/fungen-operator:latest
apptainer run fungen.sif
~/.fungen/python/bin/python3 -m fungen_operator.bootstrap setup --install "$HOME/.fungen" --image "$PWD/fungen.sif" --runtime apptainer
~/.fungen/bin/fungen serve && ~/.fungen/bin/fungen codex
```

Options and troubleshooting: [docs/install.md](docs/install.md). Releases: [CHANGELOG.md](CHANGELOG.md).

## Repository

| Path | Contents |
|---|---|
| `src/fungen_operator/` | Operator actions, MCP server, scheduler adapters, notebook executor, setup |
| `skills/fungen-operator/` | The skill that tells the agent how to use the operator |
| `container/` | Image build recipe |
| `benchmark/` | MWS-01 regression task and grader, shipped in the image |
| `docs/` | Install guide and design notes |
| `tests/` | Test suite (`pytest -q tests`) |

Agent studies: [fungen-operator-benchmark](https://github.com/hsun3163/fungen-operator-benchmark).
Earlier prototypes and working records: [fungen-operator-archive](https://github.com/hsun3163/fungen-operator-archive).
