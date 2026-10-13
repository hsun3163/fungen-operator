# Opportunistic librarian scribes

A **scribe** is an extra local-model worker for bounded lookups on unpublished data. Each scribe has its own
Ollama server and GPU. Scribes start only when a suitable GPU is unallocated now; they never wait for capacity. Use them to free the librarian for other work, or to compute the same small table twice
independently. They follow the same privacy and read-only source-data contract as the librarian. This is a
cooperative privacy precaution, not a security boundary; the agents have network access.

## Architecture

```text
login / Jupyter session host                         LSF GPU nodes

librarian "task" -- one session at a time -- tunnel 11435 --> flash-next :8889
  state: ~/.codex/ollama-flash-next.env                      librarian GPU
  pinned Codex 0.155.1; workspace-write sandbox

librarian --scribe "task" ---- select healthy scribe -------+
  local Codex session A, own run directory                  |
                                                           v
librarian --scribe --check "task"                     tunnel 11440+id
  parallel independent Codex sessions A and B               |
  result.tsv normalization and comparison                  v
    match -> A answer + agreement statement           Ollama :8890+id
    mismatch / no table / invalid table -> reviewer    codex-ollama-scribe-<id>
  answers/<run id>.md, latest.md (locked append)       one GPU per scribe
                                                      shared staged models
```

When no scribe is healthy, routing uses the fixed main librarian, and A/B run sequentially under its usual lock.

A and B have different processes, Codex conversations, logs, answers, scripts and working directories. With one
healthy scribe they share that scribe GPU; with two they use different endpoints. The reviewer is a third fresh
conversation on a healthy scribe, reads both answers and retained scripts, and resolves the original question.
Agreement between two workers is useful corroboration, not proof of scientific correctness.

**Where agent calls run.** Run `scribes` and librarian/scribe Codex calls from the login/session host, or inside
an LSF job placed with `-R "$(data_guard/codex_lsf_select)"`. Codex's sandbox (bwrap) needs unprivileged user namespaces. The
`ondemand` host group (`lh06c*` nodes, reachable from the premium queue) sets `/proc/sys/user/max_user_namespaces`
to 0, so bwrap fails there with `Creating new namespace failed: nesting depth or /proc/sys/user/max_*_namespaces
exceeded (ENOSPC)`, which Codex reports as "No space left on device". Host groups such as
`air_cpu` and `dwc_cpu` also contain `lh06c` hosts, so restrict by host instead: `data_guard/codex_lsf_select`
prints a select clause excluding every `ondemand` host (verified 2026-10-05: lh05g09, lh05g12, lh05g22, lh06g10,
lh06g14, lh06g18, lh06g19 have namespaces; lh06c13, lh06c17, lh06c31 do not).

## Isolation and enforcement

| Resource | Librarian (fixed) | Scribe id (1..100) |
|---|---|---|
| LSF name | `codex-ollama-flash-next` | `codex-ollama-scribe-<id>` |
| State | `~/.codex/ollama-flash-next.env` | `~/.codex/ollama-scribe-<id>.env` |
| Server port | 8889 | 8890 + id |
| Session-host tunnel | 11435 | 11440 + id |
| Default model | `qwen3.8-flash-next:125b-a6b-q4_K_M` | `qwen3.8:27b-262k` |
| Agent | pinned Codex via `CODEX_REAL_BIN` | same pinned binary and privacy instructions |

`scribes` accepts only positive numeric ids and checks the exact returned live job name before stopping a job.
It refuses `codex-ollama-flash-next`, id 0, inconsistent state identities and unexpected scheduler names. `up`
serializes lifecycle changes and skips ids with active/pending jobs. Scheduler query errors stop the operation.
`down` operates only on the verified scribe job IDs, and never cancels a librarian job or its renewals.

Before *every* scribe launcher call the code sets `MINERVA_OLLAMA_STATE_FILE`, `MINERVA_OLLAMA_JOB_NAME`,
`MINERVA_OLLAMA_REMOTE_PORT`, `MINERVA_OLLAMA_LOCAL_PORT` and `MINERVA_OLLAMA_DEFAULT_MODEL` explicitly. It also
pins `OLLAMA_HOST`, `CODEX_OSS_BASE_URL` and `CODEX_OLLAMA_MODEL` to the selected healthy scribe, discarding
inherited librarian endpoint overrides. State is parsed and validated before the existing launcher sources it.
Only when no scribe is healthy, routing explicitly restores the main librarian identity, reports the fallback
on stderr, and uses the ordinary serialized wrapper. Healthy scribe calls retain all endpoint isolation.

The shared model store is read by servers; no lifecycle or routing command pulls, creates or deletes models.
Staging is a separate operator step. Scribes share the librarian's Codex configuration and `AGENTS.md` privacy
instructions, with source data outside each run directory read-only under `workspace-write`. Explicit `--add-dir` arguments are forwarded unchanged to each child session when the caller authorizes
a bounded manuscript operation; ordinary lookup sessions receive no additional writable roots.

The server publishes state only after `/api/tags`, model warmup, `/api/ps` and full-context checks succeed.
State is replaced atomically. On exit it removes only its own state (verified by LSF job ID) and stops only its
own child server. If LSF kills a job without delivering a trappable signal, stale state may remain; health checks
reject it. A later `up` replaces it after a healthy startup.

The librarian wrapper holds `librarian.lock` across its full call and any resume: **at most one librarian call
at a time**. Scribes use their own endpoints and do not take this lock. All callers must use this wrapper;
bypassing it with raw Codex calls also bypasses serialization. `answers.lock` serializes publication.

## One-time setup from a fresh account

Requirements: Minerva LSF client commands, Bash, Python 3.10+, `curl`, `ssh`, `ss`, `flock`, passwordless SSH
from the session host to your GPU nodes, shared home/work directories, and access to the LOAD GPU allocation.
Adjust `#BSUB -P acc_LOAD` in the retained server script for your allocation. Run scheduler operations outside
the coding agent's sandbox through the normal execution approval mechanism.

```bash
repo=~/sunh14/fungen-operator-data-guard
L=${LIBRARIAN_HOME:-~/sunh14/librarian_agent}
mkdir -p "$L/codex/skills" "$L/runs" "$L/answers" "$L/scribes" ~/.local/bin ~/.codex
cp "$repo/data_guard/config.toml" "$L/codex/config.toml"
ln -s "$repo/data_guard/AGENTS.md" "$L/codex/AGENTS.md"
ln -s "$repo/skills/human-runner" "$L/codex/skills/human-runner"
ln -s "$repo/data_guard/librarian" ~/.local/bin/librarian
ln -s "$repo/data_guard/scribes" ~/.local/bin/scribes
export PATH="$HOME/local/bin:$HOME/.local/bin:$PATH"
export LIBRARIAN_HOME="$L"
export LIBRARIAN_PROTECTED=/your/exact/protected/path
```

For an existing account, preserve its config and links; setup is a one-time recipe, not a reset command.
The repository includes the Minerva launcher (`data_guard/codex-oss`) and common tunnel helper
(`data_guard/minerva_ollama_common.sh`), plus the required compact model catalogue (`data_guard/ollama-models.json`), copied from the existing working session-host installation. On a fresh
account, install them once:

```bash
mkdir -p ~/local/bin ~/local/scripts
install -m 755 "$repo/data_guard/codex-oss" ~/local/bin/codex-oss
install -m 644 "$repo/data_guard/minerva_ollama_common.sh" ~/local/scripts/minerva_ollama_common.sh
install -m 644 "$repo/data_guard/ollama-models.json" ~/.codex/ollama-models.json
```

Preserve an existing working account installation during ordinary scribe operation. The `codex` found in `PATH`
must be the Minerva wrapper, **not** an unwrapped global Codex binary. Verify `command -v codex`.

Install the pinned standalone Codex package in a private version directory:

```bash
mkdir -p ~/sunh14/codex-0155
npm install --prefix ~/sunh14/codex-0155 @openai/codex@0.155.1
mkdir -p ~/sunh14/codex-0155/bin
ln -s ../node_modules/.bin/codex ~/sunh14/codex-0155/bin/codex
~/sunh14/codex-0155/bin/codex --version  # codex-cli 0.155.1
```

`data_guard/librarian` exports `CODEX_REAL_BIN` using `LIBRARIAN_CODEX_BIN` or, by default,
`~/sunh14/codex-0155/bin/codex`. This keeps both librarian and scribe agent calls independent of global upgrades.
For a new account install Ollama 0.34.4's Linux binary in `~/sunh14_project/conda/ollama-v0.34.4/bin/ollama`, or
set `SCRIBE_OLLAMA_BIN` to your installed binary. The lifecycle command sends this environment to the GPU job.
The existing Minerva helper also accepts `MINERVA_OLLAMA_REAL_BIN` for its CLI path.

**Stage models before starting scribes.** The default store is
`~/sunh14_project/OLLAMA/minerva_jobs/ollama_jobs/models`; `SCRIBE_MODELS_DIR` selects another staged store.
On this account the model `qwen3.8:27b-262k` already exists. A fresh installation may copy a complete staged
Ollama store from an authorized source, preserving both `manifests/` and `blobs/`. To build the alias yourself,
use a separate temporary staging store/server, with a port other than every librarian/scribe port:

```bash
# Operator staging only; this is not a scribe job or the shared production store.
mkdir -p ~/sunh14/ollama-staging/models
export OLLAMA_MODELS=$HOME/sunh14/ollama-staging/models
export OLLAMA_HOST=127.0.0.1:11999
~/sunh14_project/conda/ollama-v0.34.4/bin/ollama serve
# In a second session with the same OLLAMA_HOST and OLLAMA_MODELS:
~/sunh14_project/conda/ollama-v0.34.4/bin/ollama pull qwen3.8:27b
printf 'FROM qwen3.8:27b\nPARAMETER num_ctx 262144\n' > ~/sunh14/ollama-staging/Modelfile
~/sunh14_project/conda/ollama-v0.34.4/bin/ollama create qwen3.8:27b-262k \
  -f ~/sunh14/ollama-staging/Modelfile
# Stop this staging server in its terminal after staging; copy the complete
# manifests/ and blobs/ into the shared store during a separate authorized staging step.
```

Never issue a pull against the librarian or scribe endpoint. Staging does not require a loaded GPU model;
production warmup does. Model licenses/download access and binary installation remain operator prerequisites.

## Daily commands

From the session host:

```bash
scribes up 1             # start id 1 only if a suitable GPU is free now
scribes up 2             # ensure up to ids 1 and 2, capped by currently free GPUs
scribes status           # job/state/node, ports, model, VRAM, health, pending age in seconds
scribes test 1           # create scribes/synthetic.tsv; agent computes/verifies result.tsv
scribes down 2           # stop only verified scribe id 2
scribes down             # stop all verified scribe jobs
librarian --scribe "Bounded operational lookup with exact input files and completion criteria."
librarian --scribe --me "Bounded scientific lookup with exact input files, filters and rounding."
librarian --scribe --check --me "Compute the defined result table from these exact files."
```

Options `--scribe`, `--check`, `--me` and `--receipt` may be combined before the task. `--check` requires
`--scribe`. `LIBRARIAN_SCRIBE_ID=1` pins a particular healthy scribe for troubleshooting; otherwise routing
selects healthy staged scribes by state file. No healthy scribe falls back to the main librarian, with one
operational line on stderr; `--check` runs independent A and B sequentially there. Routing never launches a GPU job.

`--check` asks each session to write `result.tsv` with a header and to retain its computing script in its run
directory. A/B do not see each other's work. Comparison sorts column names and complete rows (retaining duplicate
rows), strips cell whitespace, treats empty/NA/NaN/null/None/N/A as missing, and rounds finite numeric cells to
**seven significant digits, half-even**. Text comparison is case-sensitive. Significant-digit rounding preserves the scale of small values such as P values. Use explicit meaningful
precision in the task and inspect the tables when scientific accuracy needs tighter tolerances. Nonfinite numbers, ragged rows or duplicate headers trigger review.
No result table, invalid tables or a mismatch invokes the third reviewer.

Outputs use the existing `$LIBRARIAN_HOME/runs/<id>/` trail. A scribe run has `A/` (and `B/`, `reviewer/` when
needed), each containing `task`, full `log`, `answer.md`, computing scripts and `result.tsv` when defined.
The outer run has `answer.md`, `log` and, for checks, `comparison.json` (status and evidence paths only).
Individual session answers are archived and appended to private `latest.md` under a lock (A/B entries are preliminary, the outer entry is the released answer). They are stored under `$LIBRARIAN_HOME/answers/<run id>-A.md`, `-B.md`, `-reviewer.md`;
the released answer has `$LIBRARIAN_HOME/answers/<run id>.md`. Scribe answers append to private `latest.md`
under a lock. `--me` prints only completion and publishes the final answer to the user's optional private repo;
scientific results remain out of the hosted caller's stdout. Ordinary librarian `--me` keeps its existing
latest-answer replacement behavior. Receipt/slot modes retain their filtered/private delivery behavior.

Each agent must execute a startup command. After every Codex run, the wrapper checks the JSON event log for a
successful command, and for bwrap/sandbox/unified-exec failures even when Codex returns zero and writes an
answer. A failure prints `Librarian failed: <reason>. Log: <path>` and exits nonzero instead of printing `Done`.
Logs and answers are private; inspect only your synthetic probe logs when debugging with a hosted agent.

## Free-GPU admission and minimum resources

Hao's decision, **2026-10-05**, revised **2026-10-13**: `scribes up N` starts the missing ids on GPUs that are free now. When no GPU is free now, the server job is submitted to the `gpu` queue and waits there like any other job (Hao, 2026-10-13); `scribes up` never cancels a job it submitted.

| Resource | Default minimum |
|---|---|
| GPU | One unallocated GPU with at least 32 GB total memory, any model |
| Examples | A100 40/80 GB, L40S, H100 PCIe/HBM3, B200 |
| CPU | 2 host cores / scheduler slots |
| Host RAM | 32 GB |
| Parallel sessions | `SCRIBE_PARALLEL=1` |
| Walltime | `SCRIBE_WALLTIME=04:00` (4 hours) |
| Pending limit | `SCRIBE_MAX_PENDING=10080` (minutes; accepts `[hour:]minute`) |
| Context / cache | 262,144 tokens, flash attention, q8_0 KV, model kept loaded |

The measured reason for this minimum is about **27 GB GPU memory for one full 262k session** with
`qwen3.8:27b-262k`. The earlier draft measurement (job 273377057 on lg02e13) reported 29.3/80 GB total GPU
memory used, including server overhead. `/api/ps size_vram` reports model residency rather than the full KV
allocation; status labels it VRAM_GB. Raising parallel sessions needs a separately sized GPU allocation.

Admission uses native LSF queries, outside the agent sandbox:

1. `bqueues -l gpu gpuexpress` supplies open/active queues and their `HOSTS`; `bmgroup -w -r` expands host groups.
2. `bhosts -gpu <queue hosts>` supplies per-GPU `NJOBS`, `RUN`, `SUSP`, `RSV`. All four must be zero. These
   fields track scheduler allocation/reservation, unlike memory use or utilization.
3. `lsload -gpuload -w <queue hosts>` supplies `gpu_mtotal` and `gpu_status`; capacity must be >=32 GB and status ok.
4. `bhosts -w <queue hosts>` supplies host status and slots. Status must be ok; `MAX - NJOBS` must leave at least
   two slots per new scribe. NJOBS already includes reservations. Candidate count is capped by both GPUs and cores.

Each submission targets one eligible host with `-m`, requests an exclusive GPU with `gmem=32G`, and prefers
`gpuexpress` when its walltime limit permits, otherwise `gpu`. `SCRIBE_GPU_MODEL` optionally narrows by exact
native model name; there is no H100/A100-80 allowlist. Query/schema errors fail closed before submission.

A snapshot cannot guarantee immediate dispatch: other jobs may win the GPU, and GPU hosts enforce exclusive
GPU allocation plus CPU/GPU core affinity. This explains why throwaway jobs can pend even when GPU memory
looks unused or the host has spare aggregate cores. LSF remains responsible for affinity placement.

Every submission includes `bsub -ptl 10080` (one week) by default, so a scribe job stays queued until a GPU is free. `scribes up` reports each submitted job as running or waiting and leaves a waiting job in the queue; `scribes down [id]` is the way to remove one.

```bash
SCRIBE_MAX_PENDING=2 scribes up 1
SCRIBE_GPU_MODEL=NVIDIAA100_PCIE_40GB scribes up 1
# Optional SCRIBE_MODEL, SCRIBE_MODELS_DIR, SCRIBE_OLLAMA_BIN refer to staged inputs.
```

At walltime the server exits and clears its owned state. There is **no automatic renewal** for scribes.
Run `scribes up N` again when capacity is free, then `scribes status` and `scribes test <id>` when ready.
Existing running jobs retain their original settings; change them with an intentional `down <id>` then `up N`.
Failed/expired jobs are not counted as active. With no healthy scribe, lookups continue on the main librarian.

## Debugging checklist

| Symptom | Check and fix |
|---|---|
| Global Codex upgrade breaks sandbox | Verify `CODEX_REAL_BIN` in wrapper and pinned `--version`; use 0.155.1 via `LIBRARIAN_CODEX_BIN`, preserve the backend. |
| LSF-node bwrap namespace/no-space error (ENOSPC) | The job landed on an `ondemand` node (`lh06c*`). Check `cat /proc/sys/user/max_user_namespaces` in the job (0 = disabled). Resubmit with `-R "$(data_guard/codex_lsf_select)"`, or run the agent call from the session host. |
| Wrapper formerly said Done with failed commands | New log check fails closed; read the named synthetic log and successful `command_execution` events. |
| Scribe local port busy | Inspect `ss -ltnp` for 11440+id on this session host. Check the common helper's tunnel diagnostics. Use a free scribe id; leave 11435 untouched. |
| Remote port busy | Inspect the scribe job log and 8890+id listener on its node; server refuses to adopt an existing process. Use a distinct id or intentionally stop that scribe. |
| Model missing | `/api/tags` or warmup fails; stage the exact model/alias separately. Never pull through a running production endpoint. |
| GPU job PEND | New `up` submissions are cancelled immediately if dispatch loses the race. Status includes pending age for older jobs. Retry `up N` when capacity is free; lookups use the main librarian meanwhile. |
| State exists but no health | Job may have expired or been killed; inspect that exact scribe's LSF log, `up N`, then test when ready. |
| A/B mismatch or no table | Read `comparison.json`, both private scripts/answers, and reviewer log. Ensure task defines exact inputs/columns/precision; unresolved review is reported explicitly. |
| No successful command / empty answer | Open named log; check pinned binary, sandbox, timeout and endpoint. The wrapper resumes a successful command session with reasoning off only to obtain its final answer. |
| Scheduler authentication/approval fails | Use the approved host execution path; do not retry LSF inside the sandbox or diagnose a sandbox network error as a scheduler outage. |

## Verify the librarian remains unchanged

Before scribe work, save the checksum **value** and the model names (never source/edit the state):

```bash
sha256sum ~/.codex/ollama-flash-next.env
curl -sf --noproxy '*' http://127.0.0.1:11435/api/ps
librarian "Operational probe: run ls -1 | wc -l in your own run directory. This explicit probe permits listing that directory only; no protected inputs. Report command success."
```

Afterward repeat these three checks. The checksum must match, `/api/ps` must still list
`qwen3.8-flash-next:125b-a6b-q4_K_M`, and the operational probe's JSON log must include a completed
`command_execution` with `exit_code: 0`, with no sandbox error. Run only one librarian call at a time.
Do not restart, stop or reconfigure `codex-ollama-flash-next`, its automatic renewals, port 8889/11435, model
or state to diagnose scribes.

## Synthetic regression tests

```bash
python3 -m pytest data_guard/tests
```

`test_scribes.py` checks identity/state isolation, exact-name refusal, idempotent submission parameters,
normalization, successful command evidence, failed execution despite a plausible answer, recorded native free-GPU parsing, submission caps, minimum resources, pending limits/age, immediate cancellation,
independent A/B routing, serialized fallback and third-reviewer dispatch. All scheduler/model endpoints in these unit tests are stubs and all
values invented. `scribes test 1` is the separate live, synthetic, login-host end-to-end check.
