# Data librarian

Hosted coding agents (Codex, Claude Code) write code, operate workflows, run QC and debug. A separate Codex
instance running a **local Qwen model** on a Minerva GPU node, the librarian, reads unpublished results. Final
scientific results go from the librarian to the user, not to the hosted agent.

This is a practical precaution, not a security boundary.

## Mental model

```text
hosted frontier agent
        |
        | coding / QC / debug question        librarian "<task>"
        v
local-model librarian  (codex exec --oss, local Qwen)
        |
        | reads protected data locally
        v
final message -> frontier stdout
```

Scientific-result questions:

```text
hosted frontier
        |
        | librarian --me "<task>"
        v
local librarian
        |
        v
$LIBRARIAN_HOME/latest.md / review notebook  -> user
(frontier receives only "Done")
```

The frontier only ever receives the librarian's final message. The Codex transcript, commands and their output
go to the run log.

| Boundary | Rule |
|---|---|
| scientific results | final findings -> user (`--me`) |
| operations | code / QC / debugging facts -> frontier |
| computation | <= 1 GiB interactive read -> librarian; > 1 GiB -> frontier writes it, submits via LSF |
| mutation | protected data read-only; librarian writes only its run directory (and `/tmp`) |

## Files

| File | Role |
|---|---|
| `librarian` | the wrapper (`librarian [--me] "<task>"`) |
| `AGENTS.md` | librarian instructions; linked into the librarian's `CODEX_HOME` |
| `config.toml` | librarian Codex config template |
| `../skills/librarian/` | frontier skill: how hosted agents use the librarian |
| `tests/test_librarian.py` | wrapper test with a stub `codex` |

## Setup

```bash
repo=~/sunh14_project/fungen-operator            # this checkout
L=${LIBRARIAN_HOME:-~/sunh14_project/librarian_agent}
mkdir -p "$L/codex/skills" "$L/runs"
cp "$repo/data_guard/config.toml" "$L/codex/config.toml"
ln -s "$repo/data_guard/AGENTS.md" "$L/codex/AGENTS.md"
ln -s "$repo/skills/human-runner" "$L/codex/skills/human-runner"
ln -s "$repo/data_guard/librarian" ~/.local/bin/librarian
```

`config.toml` is copied because Codex may write to it; `AGENTS.md` and `human-runner` are links so the librarian
and the main session read the same repo versions.

Environment (e.g. in `~/.bashrc`):

| Variable | Default | Meaning |
|---|---|---|
| `LIBRARIAN_HOME` | `~/sunh14_project/librarian_agent` | private `codex/`, `runs/`, `latest.md` |
| `LIBRARIAN_PROTECTED` | — | colon-separated protected result paths (read by the frontier skill) |
| `OLLAMA_HOST` | unset | pin the Qwen endpoint, e.g. `http://127.0.0.1:11435` |
| `CODEX_OLLAMA_MODEL` | `qwen3.8-flash-next:125b-a6b-q4_K_M` | model name |
| `LIBRARIAN_TIMEOUT` | `1800` | seconds per Codex call |
| `LIBRARIAN_JUPYTER_BASE_URL` | unset | JupyterLab base URL for notebook links, without token |
| `LIBRARIAN_JUPYTER_ROOT` | `$HOME` | Jupyter server root the links are relative to |

**Endpoint.** `librarian` calls `codex exec --oss` through the existing Minerva launcher (`~/local/bin/codex`,
`~/local/scripts/minerva_ollama_common.sh`). With `OLLAMA_HOST` unset, the launcher finds the running
`codex-ollama-flash-next` LSF job and tunnels `127.0.0.1:11435` to it, so a new GPU node needs no change. Set
`OLLAMA_HOST` to pin a specific endpoint. There is no hosted-model fallback: if Qwen is unreachable the call fails.

**Reasoning.** The librarian works at `model_reasoning_effort = "xhigh"`. After a tool call, Ollama sometimes
returns Qwen's reply as reasoning, so Codex records no final message; the wrapper then resumes the same session
with reasoning off only to write the final message.

**Old shield.** If the previous `sanitize-layer` PreToolUse hook is still registered in `~/.claude/settings.json`
or `~/.codex/hooks.json`, remove it from your own terminal. While it is active, agent shell commands run with
protected paths masked, which also hides them from a librarian launched by that agent.

## Usage

```bash
librarian "Inspect the schema of X and tell me why analysis.py fails."
librarian --me "Which genes pass the final INTACT threshold?"
librarian "Run /path/to/check_merge.py against the protected result and tell me what is wrong with the code."
```

## Large analyses

The librarian estimates how much a request would actually read. Up to 1 GiB it runs locally (indexed or subset
reads into larger files count by what they read). Beyond that it returns a handoff: the files and read volume,
exactly what to compute, the existing workflow target or a spec for the reduction code, the small output it needs,
and the follow-up question. The frontier writes or reuses the target, submits it through LSF, monitors it and
calls the librarian again on the small output. The librarian never submits or polls LSF jobs. For `--me` calls
the handoff goes to `latest.md`.

## History

Each call creates `$LIBRARIAN_HOME/runs/<YYYYmmdd-HHMMSS>-{agent,me}-<pid>/` with `task`, `log` (the full local
Codex output), `answer.md` and, when written, `analysis.ipynb`. `latest.md` is replaced atomically by each `--me`
call. There is no other audit system.

## When a call fails

1. Read the one-line error (timeout, `codex exec` exit code, or no answer).
2. Open the run log it names.
3. Check the Qwen node: `bjobs -J codex-ollama-flash-next`, `curl -s --noproxy '*' http://127.0.0.1:11435/api/tags`.
4. Check `$LIBRARIAN_HOME/codex/config.toml` (`codex exec --oss --strict-config ...` validates it).
5. Check timeout (`LIBRARIAN_TIMEOUT`) and sandbox errors in the log.

## Review notebooks

For substantive analyses the librarian writes `runs/<id>/analysis.ipynb` (from a Jupytext or `nbformat` source),
executes it with `jupyter nbconvert --execute --allow-errors --inplace`, and keeps the outputs. The wrapper points
Jupyter's config, runtime and IPython dirs into the run directory because the sandbox makes `~/.jupyter` read-only.
`--me` answers include the notebook path and, when `LIBRARIAN_JUPYTER_BASE_URL` is set,
`<base_url>/lab/tree/<path relative to LIBRARIAN_JUPYTER_ROOT>`. Tokens are never included.

## Tests

```bash
python3 -m pytest data_guard/tests
```

A stub `codex` checks that default mode prints only the answer, `--me` replaces `latest.md` and prints only
`Done`, failures print one line with the log path, and run directories are tagged `-agent-`/`-me-`.

## Verified behaviour (Minerva, Codex 0.155.1, 2026-09-25)

- Codex's own `workspace-write` sandbox works on the Minerva kernel: the librarian read a file outside its run
  directory, and overwrite, delete, rename, chmod and create all failed with `Read-only file system`; run-directory
  writes succeeded. `/tmp` is also writable.
- Network is on inside the sandbox: librarian commands reached the Qwen endpoint and the public internet.
- A Jupyter kernel executed a librarian-built notebook over ordinary localhost TCP.
- The librarian lists the linked `human-runner` skill and, per `AGENTS.md`, runs small multi-unit work locally
  without submitting LSF jobs. It also sees personal skills in `~/.agents/skills`.

## Short explanation for other people

I use hosted coding agents for code, workflow operation and debugging, but I keep unpublished result files out of
their normal context. When an agent needs to inspect those results, it delegates the question to a separate Codex
instance running a local Qwen model on our compute environment. That local librarian can read the results and run
analyses but cannot modify the protected source data. Scientific-result questions are answered directly to me
through a local file or review notebook; hosted agents receive only the coding and QC information they need. This
is a practical precaution rather than a formal security boundary.

Limits:

- Hosted agents still see project code, filenames and structural metadata.
- They may receive QC and debugging facts needed to do their job, and anything I choose to share.
- The librarian has network access.
- Nothing here resists a malicious agent or user; it relies on cooperative agents following the skill.
