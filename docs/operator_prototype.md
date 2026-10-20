# Fungen Operator vertical prototype

The prototype implements the three-action lab-tech path from structured tool arguments to
validated slots, fixed notebook cells, execution, and retained evidence. Canonical workflow
implementation remains outside the operator's write surface. Harmonization starts upstream.

First-bar status: the in-process MCP lifecycle and notebook replay passed, and the executed
example is retained. External stdio clients now pass tool discovery, calls, scientific approval,
and notebook staging in both automatic and legacy protocol modes on the host. Live HPC execution
remains untested.

## Implementation boundaries

`src/fungen_operator/actions.py` owns Pydantic input schemas, the developer-selected deployment,
parameter validation, implementation identity, and pure cell rendering. `notebook.py` owns
atomic notebook writes, recipe ordering, supersession, and exact re-render checks.
`execution.py` executes the exact saved cell through nbclient and collects native scheduler
receipts/logs. `harness.py` connects these pieces and enforces approval/readiness gates.
`server.py` exposes the action tools; the CLI uses the same harness. `fixture.py` and `demo.py`
are explicitly synthetic test infrastructure, not alternate production workflows.

There is no workflow controller or database replacing Snakemake/LSF. Notebook metadata is the
retained action record; the adjacent empty `.lock` file coordinates writers. The fixture's
`scheduler.json` simulates the external scheduler and is never used by the live backend.

## Tools and constraints

| Tool | Inputs and result |
|---|---|
| `prepare_config` | Notebook/config/work paths and a mapping of canonical parameter paths to typed values; returns materialization or a pending host command. |
| `check_readiness` | Run paths, targets, scheduler/resource slots, and `before_run` or `conclusion`; returns `ready`, `nothing_to_do`, `failed`, `unknown`, or a pending host command. |
| `initiate_run` | The same run slots; returns the retained submission receipt. The same action handles initial submission and normal resume. |
| `inspect_run` | Notebook, optional paths and `dead_child_grace_minutes` (default 10); returns history, scheduler observations, logs, and submitted/running SoS tasks whose children are terminal or missing in LSF. Read-only. |
| `control_run` | `kill`, `switch_queue`, `modify` or `sweep`; explicit job IDs or dead-wrapper / pending-queue-age / step-and-memory selector; returns membership refusals, an exact-command approval exchange, then a visible executed cell and native receipt. |

MCP arguments are nested under `request`. `python -m fungen_operator schemas` exports the input
schemas (also retained in `schemas/action_arguments.json`); MCP `tools/list` supplies the actual tool envelopes. No tool takes source code,
`extra_args`, arbitrary commands, or an approval boolean.

PATH slots must be absolute and use letters, digits, `_./:+-`. They are resolved before use;
write paths must remain within the deployment's run root, disjoint from canonical source.
This intentionally excludes paths with whitespace for the first LSF directive template.
Targets are separate rule/file strings, never option-like tokens or shell text; traversal
above the workspace is rejected. Absolute file targets must belong to the working directory.

The initial enums are queues `premium`/`express`, project `acc_LOAD`, and the deployment's
canonical runtime/profile. Bounds are controller cores 1–72, workflow cores 1–512, jobs 1–10000,
memory 32–1000 GB, latency 1–3600 seconds, and walltime 1–8640 minutes. Express is capped at
720 minutes. These are prototype admission limits, not a claim about current scheduler capacity.
Defaults follow the retained practice: premium, 40 GB, one controller core, 72 workflow cores,
2000 jobs, 60-minute readiness and 8640-minute production. Runtime is rendered as explicit HH:MM.

Optional execution settings `sos_j` and `sos_max_running_jobs` accept integers 1–10000;
`sos_queue` accepts `premium` or `express`. They travel in the literal Snakemake command and
a per-cell host YAML inside the run's log directory. The canonical workflow copies its host
configuration and applies the overrides there. Omitted settings keep existing cell text and
fingerprints unchanged. J limits each SoS engine, including pending children; it is not a
run-wide scheduler ceiling. Explicit J takes precedence over the host limit; a host-only
override leaves J unset. These settings apply to newly started engines.

`inspect_run` reads per-unit exported SoS task directories and submission headers without
executing SoS or changing task records. It joins child job files, controller submission logs,
and a batched `bjobs` query, consulting `bhist` for missing child IDs. Terminal or absent children
become dead only after the submission grace window; scheduler errors remain unknown. Reports
include task/child/wrapper IDs, rule/unit, LSF state/reason and the first decisive scheduler error.

`control_run` checks live membership against controller receipts, exact wrapper submissions and
run task directories. Selectors resolve before approval; approval shows the literal command and
frozen IDs. A mixed selection containing an outside job is refused as a whole. Membership is
rechecked after approval and at host execution. Decline, cancel and unsupported elicitation
clients keep every job unchanged. The nbclient path executes the saved `bkill` or `bswitch`
cell and retains its native receipt. `verify` re-renders control cells; replay skips them.
Resume after a kill uses `initiate_run` and its existing matching readiness gate.

`modify` accepts optional reservation and hard-limit memory (1–1000 GB), walltime
(1–8640 minutes), cores (1–512), and queue. At least one field is required. Reservation
changes preserve the native combined resource expression and replace only its single
`rusage.mem` value. Different expressions produce separate literal commands. The expressions
are frozen for approval and checked again before execution. The `step` selector combines
an exact rule or task-kind identifier with its current reservation in GB.

`sweep` accepts typed memory remaps by step and current reservation, an optional hard limit,
queue moves with a 1–20000-job cap per pass, and an interval of 0–86400 seconds (default 300).
One approval covers the rule set, cap, interval, and literal submission cell. That cell writes
its hash-bound plan under the run logs and submits one 4 GB / one-core premium job. Interval
0 uses one synchronous pass. The worker applies `bmod` only to live pending members, writes
one JSON count line per pass, and stops when the workflow has no pending or running jobs.
Sweep receipts are run members for kill; sweep jobs do not keep upkeep alive. Scheduler
uncertainty stops mutation. Periodic passes record per-job failures and continue observing
the remaining work. Replay skips every control cell.

The worker uses the installed `jq --stream` to read receipt fields without loading notebook
outputs into Python. Its cache refreshes when the notebook changes, so later controller
receipts enter the same membership checks. The operator Python and jq paths are fixed in
the approved run-local plan and visible cell.

Configuration field types/structure come from the selected canonical default configuration.
Any represented parameter can be changed; the prototype does not freeze scientific knobs.
`parameter_defaults` registers source-exposed optional fields absent from that configuration.
Unregistered fields produce an actionable error. The developer maintains this metadata; it is
not inferred by executing or rewriting canonical code. All scientific differences require
approval. `cwd` and `resources` are operational initially; additional operational paths must be
explicitly registered. Unknown classifications default to scientific. Source/executable
selectors retain their registered canonical values. Workflow-specific scientific value ranges
and exhaustive optional-field discovery remain catalog work.

An existing configuration is adopted as the baseline, preserving its scientific values;
otherwise the initial baseline is the canonical defaults. Later changes use the last accepted
configuration. Restoring externally changed scientific values also requires approval.
Scientific approval uses the MCP SDK's elicitation resolver, with the exact proposed diff and
fingerprint. Decline/cancel/unsupported clients write neither config nor notebook. The proposal
is rechecked after approval and under the notebook lock. The client must actually present the
elicitation to a human: the server enforces the approval exchange, not the client's UI behavior.
The automated example's client response is explicitly simulated and labelled as such.

## Install and connect

Use a dedicated environment; the canonical workflow environment is not changed:

```bash
python -m venv /tmp/fungen-prototype-venv
/tmp/fungen-prototype-venv/bin/python -m pip install -e '.[test]'
/tmp/fungen-prototype-venv/bin/python -m fungen_operator schemas
```

Connect a local stdio MCP server using the environment's absolute Python path, arguments
`-m fungen_operator serve --deployment /absolute/path/deployment.json`, and this repository as
its working directory. Load `skills/fungen-operator/SKILL.md` as the operator entrypoint.

Launch the server outside Minerva's restricted command sandbox through the approved host path.
The earlier initialization timeout was reproduced with an otherwise empty MCP server:
the sandbox permits creating local socket pairs but rejects writes with `EPERM`. Python's
async runtime needs those writes to wake its event loop when stdin worker threads finish.
The identical server initialized successfully on the host. The `serve` entrypoint now checks
this capability and exits with an actionable error instead of waiting indefinitely.

The MCP client launches and manages this process; its command is:

```bash
/tmp/fungen-prototype-venv/bin/python -m fungen_operator serve --deployment /absolute/path/deployment.json
```

The SDK version range is MCP 2.2–2.x; the server uses resolver-based elicitation to support
negotiated modern and legacy clients. A client without human elicitation can still use the
operational path, but scientific changes fail closed.

`deployments/xqtl.example.json` supplies the actual xQTL/MESA runtime locations. Inspect it and
the canonical config before use: the canonical sample still contains legacy MWE input paths.
Supply the intended harmonized inputs through `prepare_config`. This file is an example
deployment, not a claim that its inputs or all optional parameter metadata are production-ready.

The live MCP backend **stages** each cell and returns an exact `host_command`. Execute that
entrypoint outside the sandbox through the platform's per-command approval mechanism:

```bash
python -m fungen_operator execute --deployment DEPLOYMENT.json --notebook RUN.ipynb --cell CELL_ID
```

The command validates the saved action again, checks current source/config/readiness and live
controller state, executes that exact cell, and captures its result in the notebook. Do not
invoke it inside the Minerva sandbox or give a persistent general interpreter/script rule.
`inspect` and `replay` also require host execution because they may invoke scheduler clients.
This explicit host step keeps execution approval in the existing platform rather than
pretending an MCP subprocess can request Codex sandbox escalation on its own.

## Recipe, history, and completion

The active order is configuration → readiness → submission → conclusion readiness. A replacement
keeps old code, outputs, timestamps and receipts under `superseded`; configuration replacement
also supersedes dependent actions. Each new attempt gets unique log paths. Config writes are
atomic and leave identical content untouched, preserving modification times and native reuse.

```bash
python -m fungen_operator verify RUN.ipynb
python -m fungen_operator replay --deployment DEPLOYMENT.json --notebook RUN.ipynb
```

Replay re-enters the same gates, preserves previous executions, skips superseded cells, and
stops when an asynchronous controller still needs observation, retaining the unexecuted suffix
as active cells. Calling replay again after termination continues that suffix. It never blindly executes every
code cell as Jupyter Run All would. Inspect the pending controller and continue with the next
action or resume replay after it terminates. Concurrent or unknown controller state blocks execution.

Each action records its template/version, slots, source identity, full config content where
applicable, configuration fingerprint, targets, runtime/profile, outputs, and receipt. Identity
includes Git SHA, dirty status, source hashes, activation-script hash, and relevant textual Git
diffs. Dirty notebooks/untracked source are fingerprinted, not completely archived; this identifies
the implementation but is not a complete dirty-checkout backup or an environment lockfile.

Readiness uses the retained synchronous `bsub -K` form. The harness reads its actual scheduler
logs and requires successful execution plus canonical dry-run text. A successful
`Nothing to be done` message records `nothing_to_do` for the current graph. Unknown/missing
logs, unknown scheduler state, submission receipts, and ordinary production stdout cannot
create that completion fact. This is canonical workflow completion evidence; scientific
interpretation and the accuracy of the canonical workflow's own output contract remain external.

## Executed example and validation

```bash
python -m fungen_operator demo --root /tmp/fungen-new-example
python -m pytest -q tests
```

The example is generated through an in-process MCP client, real validation/rendering/notebook
code, and real nbclient execution. Only the external scheduler and workflow are simulated.
It prepares defaults, approves a simulated scientific change, dry-runs, submits a deliberately
interrupted run, resumes with the same action, and records final nothing-to-do readiness.
`examples/operator_lifecycle.ipynb` retains the executed demonstration; its paths refer to the
fixture used during generation. Regenerate to obtain local runnable prerequisite paths.

Tests cover all ten requested behaviors, plus denied/stale approval, path and shell injection,
source/config drift, readiness gating, host-execution deferral, and preservation of receipts and
output modification times through replay. Live LSF execution and the connected client's human
approval UI are not established by the synthetic run.

Recorded validation for this first pass: the full initial 25-case suite passed, including actual
notebook execution and replay against fixture commands. After adding existing-config adoption
and external scientific-drift protection, all 26 lightweight cases passed; the previously
passing integration case was not repeated. The retained notebook has four active cells and six
superseded attempts, all executed, with final `nothing_to_do` evidence and the interrupted
submission's receipt preserved. Its active cells also passed the CLI re-render verification.

The subsequent MCP connection fix passed three focused checks (`pytest -q tests/test_harness.py
-k stdio`) on the host: clear rejection of blocked local sockets and real subprocess clients
in both protocol modes. The clients discover all four tools, reject an injected target flag,
decline then accept a simulated scientific approval, stage a notebook cell, and inspect it.
The tests use the live backend's staging path with synthetic files; they submit no jobs.
The actual restricted `serve` invocation also returned the expected startup diagnostic.
An external client using `deployments/xqtl.example.json` also discovered all four tools and
successfully called `inspect_run` without creating a notebook or submitting work.

Mechanically enforced inside the harness: known actions, typed/validated slots, scientific
approval exchange, fixed rendering, write-path boundaries, source/config identity checks,
readiness before submission, supersession, and replay integrity. Advisory outside the harness:
the broader agent's tool discipline, true human handling by the MCP client, harmonization,
scientific interpretation, and other processes with access to these files. This is not an
adversarial containment system.

## Next evidence to extract

Cell indices below are zero-based, matching the source notebook arrays inspected for this work.

- MESA cells 30–31 and imported CARDIA template cells 6–8 supplied the initial skeleton.
- MESA cells 15–19 capture controller/runtime corrections; cell 38 records accidental config
  overwrite/restoration and motivates replayable full config cells.
- CARDIA cells 20–24 capture target-scoped resumption and scheduler dependencies.
- MESA cells 47–50 and CARDIA cells 72–74 capture user-approved one-PC/no-TWAS changes.
- MESA cells 54–55 and CARDIA cells 78–79 contain forced reruns; retain them as distinct future
  catalog candidates rather than adding arbitrary flags to normal submission.

Native unlock has historical recovery evidence, but the three-action lifecycle does not need
it. Unlock, dependency slots, per-rule command-line resource overrides, and a
complete parameter catalog remain explicit later additions.
