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
| `../skills/query/` | required request guidance: exact inputs, bounded questions, outputs and missing-input actions |
| `tests/test_librarian.py` | wrapper test with a stub `codex` |

## Setup

```bash
repo=~/sunh14/fungen-operator-data-guard   # this checkout (work space)
L=${LIBRARIAN_HOME:-~/sunh14/librarian_agent}
mkdir -p "$L/codex/skills" "$L/runs"
cp "$repo/data_guard/config.toml" "$L/codex/config.toml"
ln -s "$repo/data_guard/AGENTS.md" "$L/codex/AGENTS.md"
ln -s "$repo/skills/human-runner" "$L/codex/skills/human-runner"
ln -s "$repo/data_guard/librarian" ~/.local/bin/librarian
```

Optional answers repo: clone a **private** GitHub repo to `$L/repo` (or set `LIBRARIAN_REPO`), e.g.
`git clone https://github.com/<user>/librarian.git "$L/repo"`. After every `--me` call the wrapper writes the answer
to its `README.md` (so the repo page shows the latest answer) and to `answers/<run id>.md`, commits and pushes. Git
output goes to the run log; a failed sync adds "Repo sync failed; see <log>" to the Done line and never fails the
call.

`config.toml` is copied because Codex may write to it; `AGENTS.md` and `human-runner` are links so the librarian
and the main session read the same repo versions.

Environment (e.g. in `~/.bashrc`):

| Variable | Default | Meaning |
|---|---|---|
| `LIBRARIAN_HOME` | `~/sunh14/librarian_agent` | private `codex/`, `runs/`, `latest.md` |
| `LIBRARIAN_PROTECTED` | — | colon-separated protected result paths (read by the frontier skill) |
| `OLLAMA_HOST` | unset | pin the Qwen endpoint, e.g. `http://127.0.0.1:11435` |
| `CODEX_OLLAMA_MODEL` | `qwen3.8-flash-next:125b-a6b-q4_K_M` | model name |
| `LIBRARIAN_TIMEOUT` | `1800` | seconds per Codex call |
| `LIBRARIAN_REPO` | `$LIBRARIAN_HOME/repo` | private git clone; README.md = latest answer, answers/ = all |
| `LIBRARIAN_JUPYTER_BASE_URL` | `http://127.0.0.1:$JUPYTER_PORT` | JupyterLab base URL for links (no token), as reached through the tunnel; the Minerva launcher exports `JUPYTER_PORT` |

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

The librarian estimates how much a request would actually read and how much memory it needs. Up to 1 GiB of each it runs locally (indexed or subset
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
`--me` answers show every path as `~/...` (the wrapper rewrites absolute paths through the most specific
symlink in `$HOME`, because JupyterLab opens only paths under its root) and turns each one outside code blocks into a
link, `<base_url>/lab/tree/<path>`, with the base URL `http://127.0.0.1:$JUPYTER_PORT` (the tunnelled address `jinfo` shows) so it
follows the server to new jobs. Tokens are never included.

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

## Placeholder manuscripts

`librarian mask` is the single deterministic implementation for manuscript exchange. The user edits the human
Markdown file or Google Doc; hosted agents edit its masked Markdown export and read its slot-status file.
`FRONTIER.md` contains their short instructions. The local model only retrieves or computes pending values.
The existing `librarian --slots` request path carries descriptions and sentence contexts over stdin and returns
JSON privately to the calling script. It does not publish these responses to the answers repository.
Each request includes the document key and masked manuscript path so the librarian can follow its source
references and active-run provenance. A failed request or malformed JSON response leaves pending slots and
outputs unchanged; an explicit unresolved answer marks that slot `needs-human`.

The implementation consists of plain functions in `masking.py` and the `google_docs.py` adapter. The existing
shell launcher dispatches `librarian mask` directly to Python, outside the model's read-only run. There is no
background process. Every successful export/import/retrieval updates just the private dictionary, the masked
file, and its slot-status file (plus the human source for import/retrieval).

### Setup

Install the optional Python dependencies in the environment used by `python3`:

```bash
python3 -m pip install 'markdown-it-py==3.0.0' 'zstandard>=0.22,<1'
```

Add the `[masking]` section from `data_guard/config.toml` to the existing librarian config, preserving its other
settings. The launcher already sets its separate home to `$LIBRARIAN_HOME/codex`, with
`LIBRARIAN_HOME` defaulting to `~/sunh14/librarian_agent`. No production configuration was edited during development.

```toml
[masking]
dictionary = "../dict.json.zst"
rclone_remote = "cosi_drive"
dictionary_doc = "YOUR_PRIVATE_DICTIONARY_GOOGLE_DOC_ID"
```

`dictionary` resolves relative to the config file. It must resolve to `dict.json.zst` beside this separate
CODEX_HOME, never inside CODEX_HOME or a Git repository. With the current launcher layout the location is
`~/sunh14/librarian_agent/dict.json.zst`. The command refuses the shared default `~/.codex`. The dictionary is
zstd-compressed JSON, atomically replaced with mode 0600; its containing directory is locked for each command.
Keep the dictionary private and back it up yourself. A saved dictionary plus the repository's code and masked
files preserves the assigned IDs and allows the human text to be reconstructed. Tests require no tracking.

The current librarian code/config has no knowledge-map ID allocator or type assignments. Resolved numbers get
VALUE, other new values get TEXT. Pending descriptions are TEXT unless already supplied with a type by a caller;
a pending slot retains that type and ID when it binds. IDs use four random uppercase base32 characters and are
unique across the dictionary. Existing entries and their types are reused according to the rules below.

For Google Docs, reuse the existing rclone account and enable the Google Docs API in its Google Cloud project.
The adapter lets rclone refresh its own token, then uses that token in memory for direct Docs API requests.
Credentials and HTTP bodies are never printed. The dictionary destination should be a dedicated, private,
single-tab Google Doc. Its ID is configuration, not a second dictionary store.

### Commands the user or local librarian runs

For the first upload, create a native Google Doc and initialize its masked export in one command:

```bash
librarian mask upload --document results \
  --markdown ~/Myloid-paper/3_Production/COSI_paper/text/results_draft.md \
  --masked ~/Myloid-paper/3_Production/COSI_paper/text/results_draft.md \
  --folder COSI-paper/manuscript --title Results
```

This one-time operation permits the initial source and masked output to be the same Markdown path: it uploads
and verifies the human Doc before replacing that local file with placeholders. Existing `{{NUM:name}}` and
`{{INFO:name}}` requests become pending slots; the script uses their names as descriptions without inventing
values. Other body bold spans follow the ordinary protection rules. Repeating a completed upload returns its
recorded links and does not overwrite human edits. An interrupted upload reuses only an app-tagged Doc with the
same source hash and refuses different content. Sources with unsupported markup stop before creating a Doc.

The upload prints only the folder and document URLs. It uses the existing rclone OAuth account through the
direct [Drive files API](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/create)
and Docs API; it does not change sharing permissions. Native Docs API errors report only a status and a safe
reason such as `SERVICE_DISABLED`.

When explicitly delegating manuscript setup to the local librarian, prepend repeated `--add-dir DIR` options
to the usual `librarian "task"` command for just the manuscript output directory, separate librarian home,
and rclone configuration directory. These are ordinary Codex writable-directory arguments. Normal retrieval
calls retain their existing read-only project boundary; the local model still makes no masking decisions.

Export an existing human Markdown source. These are examples with explicit paths; substitute your own files.
The masked file's parent directory must already exist.

```bash
librarian mask export --document results \
  --markdown ~/private-paper/results.md \
  --masked ~/Myloid-paper/3_Production/COSI_paper/text/results_draft.md
```

For a Google Doc, export the selected tab instead:

```bash
librarian mask export --document results \
  --google-doc YOUR_MANUSCRIPT_GOOGLE_DOC_ID --tab YOUR_TAB_ID \
  --masked ~/Myloid-paper/3_Production/COSI_paper/text/results_draft.md
```

`--tab` can be omitted only for a single-tab Doc. The source, revision/hash, and output paths are stored under
`results` in the private dictionary. Use a different `--document` key for each manuscript section. `--slots`
overrides the default status filename, which is the masked filename with `.slots.tsv` in place of `.md`.

After hosted edits to the masked file:

```bash
librarian mask import --document results
librarian mask retrieve --document results
librarian mask sync-dictionary
```

Import registers new requests, renders their descriptions in bold in the human source, and rewrites them as IDs
in the masked file. Retrieval sends pending requests through the existing local librarian, binds answers once,
updates the human source, and refreshes the masked file and statuses. Unresolved slots become `needs-human`.
Retrieval requires new bold requests to have been imported first. The final command publishes a readable
one-way dictionary view; it is an explicit operator step after dictionary updates.

When the local librarian already retrieved answers, have it save the same ID-keyed response JSON in its
private run directory and apply it directly:

```bash
librarian mask retrieve --document results --reply-file /private/run/slot-replies.json
```

This starts no second model. Each file can contain one small group of pending slots; only those IDs are
bound or marked `needs-human`, and other pending slots remain pending. The script still checks the live
revision, validates document membership, preserves immutable bindings, and masks before publishing. An
empty, malformed, unknown-ID, or already-bound-ID response fails without changing outputs. Keep reply files
outside repositories and hosted-agent access. A local librarian operating the manuscript should use this
form instead of nesting another timed librarian inside its own run; the default retrieval command remains
the direct request path for a human operator.

After editing the human source, run its original export command again before further imports. A changed human
revision/hash blocks import and retrieval, including changes made while retrieval was running. Preserve and
merge any pending masked edits yourself before re-exporting. Errors contain fixed codes, IDs and positions;
source text, contexts, API response bodies and values are excluded.

### Deterministic rules

- Every bold body span is protected. Adjacent/overlapping bold runs merge; surrounding whitespace is trimmed;
  partial tokens expand. Letters/digits form tokens; `.` and `-` belong to a token only between letters/digits.
  Bold in real Markdown/Google headings is structural. The known-value scan still covers headings.
- Comparisons normalize Unicode minus/dash variants, non-breaking/thin spaces, and `×`/`x`. A pending description
  in this document matches its existing slot first. One equal resolved value reuses its ID. Multiple equal IDs
  use one document-specific generic entry, created once and reused. Otherwise a new entry is created. If repeated
  pending descriptions exist, dictionary insertion order selects the first; there is no semantic disambiguation.
- Whole bold spans are masked first. Known values from this document are then matched longest first, with token
  boundaries and no overlaps. A known substring never splits a larger bold span. A value that remains in a link
  target or unsupported structural syntax causes a closed failure rather than an incomplete masked export.
- Each entry has `id`, `value`, original formatting `runs`, `type`, `context`, and `documents`. Unbound slots also
  have `description` and `status`. Binding removes those two pending-only fields. Bound values/runs/types are
  immutable; human value changes get new IDs. Exported status lines contain only ID and `resolved`, `pending`,
  or `needs-human`.
- Import rejects unknown, foreign-document, malformed and escaped placeholders. Bold around exactly one
  placeholder has no separate meaning. Other bold body spans create pending requests, with their sentence as
  context. Values are restored in bold, retaining italic/superscript/subscript runs. New unbolded quantities and
  reworded quantities receive no semantic classification; published values are not automatically declassified.
- Dictionary persistence precedes masked output. A save failure leaves the prior masked file intact and releases
  no new masked file. An interrupted human-source update can be recovered by exporting the current human source;
  stored values and IDs remain available in the dictionary.

Markdown parses with CommonMark and supports `<sup>`/`<sub>` for run formatting. Untouched Markdown paragraphs
retain their original bytes. Google Docs edits use `SUGGESTIONS_INLINE`, UTF-16 indexes, and
`requiredRevisionId`; only changed paragraphs are patched. Unchanged paragraphs containing comments,
suggestions, and citation fields receive no write requests. Editing a paragraph containing a suggestion or
non-text field stops for a human edit. Tables and other unsupported Google structures stop export, preserving
those structures in the original Doc. The adapter edits only the chosen tab's body.

Dictionary Doc sync reads revision and body-length metadata only, then replaces that dedicated Doc's body with
the local dictionary's readable rendering. It never reads document text or imports dictionary entries from it.

API contracts: [document structures and UTF-16 indexes](https://developers.google.com/workspace/docs/api/reference/rest/v1/documents),
[revision-controlled batch updates](https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/batchUpdate),
[tab targeting](https://developers.google.com/workspace/docs/api/how-tos/tabs), and
[suggestion-safe indexes](https://developers.google.com/workspace/docs/api/how-tos/suggestions).

### Synthetic verification

```bash
python3 -m pytest data_guard/tests
```

Tests use invented genes/numbers, temporary dictionaries and manuscripts, a stub local librarian, and recorded
synthetic Google API responses in `tests/fixtures/google_docs.json`. Network and credential operations are mocked
for adapter tests. No production dictionary, manuscript, private session log, dictionary Google Doc, or credential
was opened during development. Live Google authorization and live document edits are operator-run checks.
