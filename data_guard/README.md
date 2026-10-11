# Data librarian

## Live table contract — 11 October 2026

Start with a structure probe, then hand a plain Python or configured R script to
`librarian --broker`. Counts and all whole numbers are always released; categories
are shown, while gene identifiers and fractional decimals use stable placeholders.
Code and the staff identifier check protect against accidental leakage. An operator
heading whitelist keeps schema names readable; gene/protected column headings are
also shown. Source cell values retain their own masking decisions.

One generated sentence template explains each masked item and its available
stand-ins. Probability columns get policy bins and percentiles; other decimals get
direction, percentile and absolute-value percentile. Percentiles use an inclusive
empirical CDF rounded to whole percentiles, referenced to the named returned or
selected source column. Linked rephrase requests keep the original table and audit.
The main librarian is the review backend under its existing shared lock and resident
model check. Routine staff use backend 4; transports close after each request.

Simple no-script questions use the local agent. Requests exceeding 180 words or
40 clause marks are handed back before inference; two failed computed attempts
also trigger “Send it as a script, or ask one part at a time.” Two independent tries
must agree on the table (row order normalized, duplicate rows retained); differing
tries get the same advice. **Being measured:** two-tries agreement and temperature
0.2 with fixed seeds 11 and 23, in `runs/temp-bench-*`. Those settings are current
code decisions under measurement, rather than established reliability claims.

The archive qualification report separates completion, correctness and usefulness;
`real-final-002` recorded zero disclosures and did not pass all targets. Live table
installation and the supervised request have their own metadata-only report in
`temp_reference/live-tables/REPORT.md`. The results document for Hao is titled
**Librarian results**, in the existing **Librarian/results** Drive folder.

### Installed live policy and structure path

The installed wrapper defaults to `~/sunh14/librarian_agent/operator/broker-policy.json`.
That operator-owned file contains the complete catalog and release settings, outside
frontier-writable workspaces. `live_inventory.py` selects the named candidate IDs
into the private wrapper run, preserving every release setting; `policy_file` checks
that request-scoped policy. This supports a catalog larger than the unchanged core
loader's 64 KiB artifact limit. Linked requests reuse their original admitted IDs.

Installed `action: probe` is a fixed code calculation of headings and logical row
counts. It releases no sample cells, infers no scalar values, makes no model calls
and records a private audit. Analysis/rephrase/review keep the core broker path.
Structure metadata stays in the native reply rather than filling Hao's results Doc.

Rebuild and validate headers:
```bash
python3 data_guard/live_inventory.py --output temp_reference/live-tables/headers-live.tsv \
  --policy ~/sunh14/librarian_agent/operator/broker-policy.json
python3 data_guard/live_inventory.py --validate-probes --output temp_reference/live-tables \
  --policy ~/sunh14/librarian_agent/operator/broker-policy.json
```
The inventory covers exported paper data, nested analysis results, figure source data,
and the handoff's gene/locus, judge, role-atlas, interactome and sensor/machinery layers.
Raw workflow data, downloaded references and staged annotation work remain outside
this live export catalog. Every listed column has one explicit gene/protected/shown
classification; a new input or header causes the inventory check to fail.

## Who does what

You hand your code to the librarian, and the librarian runs it. The frontier writes the script and works with placeholders. Two Laguna XS scribe conversations on backend 4 choose bindings; one issues the run and checks text for missed identifiers. Code owns sandbox execution, masking, whole-number release, bins, percentiles, directions, positive rephrase replies, unmasked table restoration, operator-selected Google delivery and the audit. Laguna S on Hao's main librarian resolves eligible text reviews and bounded escalation under Hao's existing lock; it leaves gene and decimal release decisions to code. Hao owns the policy and receives unmasked broker tables through `--me` and Google. Open `--me` investigations remain model-written. Escalation may resolve a binding after the scribe agreement budget expires.

Current role limits and the operator policy are documented in [~/sunh14/fungen-operator-data-guard/data_guard/BROKER.md](http://127.0.0.1:8548/lab/tree/sunh14/fungen-operator-data-guard/data_guard/BROKER.md). The main job and resident model keep their existing launch settings. The broker targets accidental leakage; deliberate encoded leakage is outside Hao's current threat model.

## Private execution broker

`librarian --broker request.json` adds the frontier-script workflow: two private scribe parameter bindings,
controller execution of the pinned script, and local librarian review. It preserves the existing return
logic: coding/debugging answers to the caller, `--me` delivery to the user, explicit committee rules, and
the `--receipt` filter. It uses the operator's `LIBRARIAN_BROKER_POLICY` configuration. See [BROKER.md](BROKER.md) for the request/policy formats,
tests, and the additional runtime permissions required for an enforced backend-privacy boundary.

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

For manuscript slot operations, use `librarian --receipt "<specific task>"` after any `--add-dir` options.
This mode filters the final answer locally before releasing it. Only `VALUE`/`TEXT` placeholder IDs with
`resolved`, `pending`, or `needs-human` statuses, four Boolean verification fields (`doc_verified`,
`mask_verified`, `dictionary_synced`, `preserved`), and fixed blocker codes can pass. Extra fields are dropped;
malformed allowed fields fail closed with a fixed message. The complete answer stays in the private run.
Default free-text operational replies are not a reliable boundary for numeric QC values.

| Boundary | Rule |
|---|---|
| scientific results | final findings -> user (`--me`) |
| operations | code / QC / debugging facts -> frontier |
| computation | <= 1 GiB interactive read -> librarian; > 1 GiB -> frontier writes it, submits via LSF |
| mutation | protected data read-only; librarian writes only its run directory (and `/tmp`) |

## Scribes

For opportunistic local-model workers on currently free GPUs, see [SCRIBES.md](SCRIBES.md): setup from scratch,
`scribes up/status/test/down`, isolated routing with `librarian --scribe`, independent A/B verification with
`--scribe --check`, free-GPU admission, 2 cores/32 GB RAM/one >=32 GB GPU, relaunch and debugging.
No healthy scribe falls back to the serialized main librarian; A/B run sequentially there. The librarian backend stays fixed. Agent sessions run on
the login/session host or in LSF jobs placed with `-R "$(data_guard/codex_lsf_select)"` (see SCRIBES.md, debugging). The wrapper serializes librarian calls.

## Files

| File | Role |
|---|---|
| `librarian` | wrapper (`librarian [--scribe [--check]] [--me] "<task>"`) |
| `scribes`, `scribe_server.lsf`, `scribe_support.py` | scribe lifecycle, GPU server and local checks/routing |
| `minerva_codex`, `minerva_ollama_common.sh`, `ollama-models.json` | existing Minerva launcher/helper, retained for fresh setup |
| `SCRIBES.md` | complete setup, isolation, use and debugging guide |
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
4. A run with no successful command or any bwrap/sandbox execution error now fails even if Codex wrote an answer.
5. Check `$LIBRARIAN_HOME/codex/config.toml` (`codex exec --oss --strict-config ...` validates it).
6. Check timeout (`LIBRARIAN_TIMEOUT`) and sandbox errors in the log.

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

This starts no second model. Each file can contain one small group of unbound slots, including an explicit
retry of `needs-human` slots when answers become available; only those IDs are bound or marked `needs-human`.
Unrelated slots keep their status. Ordinary retrieval requests only pending slots. The script still checks the live
revision, validates document membership, preserves immutable bindings, and masks before publishing. An
empty, malformed, unknown-ID, or already-bound-ID response fails without changing outputs. Keep reply files
outside repositories and hosted-agent access. A local librarian operating the manuscript should use this
form instead of nesting another timed librarian inside its own run; the default retrieval command remains
the direct request path for a human operator.

Equal values are valid. When a later export finds several IDs holding the same value, it uses the documented
generic entry for their occurrences. The original IDs keep their immutable values in the dictionary; using
the generic placeholder does not rebind them. Verify value equivalence rather than requiring identical
placeholder labels across that export. An equal value alone is not a reason to mark a slot `needs-human`.

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
