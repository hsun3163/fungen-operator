# Readiness reconciliation — 2026-09-24

The live smoke test reproduced the original race and now returns **ready**: job **270178190** was first observed as `RUN`, then `DONE`, with synchronous exit **0** and **21 planned jobs**. Notebook verification passed.

## Change

`src/fungen_operator/execution.py` reconciles scheduler state and log visibility after synchronous `bsub -K` returns. It retains up to four observations with 1-, 2-, and 4-second waits. Successful synchronous execution, terminal `DONE`, and canonical dry-run output are required for readiness. Explicit failure returns `failed`; incomplete evidence remains `unknown`. LSF's blank `EXIT_CODE` for `DONE` is paired with the recorded synchronous exit 0.

The four MCP actions, argument schemas, submission gate, rendered cells, and asynchronous production behavior are unchanged. The original unknown result is retained as superseded history.

## Regression validation

Command: `/tmp/fungen-operator-prototype-venv/bin/python -m pytest -q tests`

**44 passed in 15.39 seconds**, including 14 new cases covering `RUN → DONE`, explicit zero and blank LSF success exit codes, delayed logs, nothing-to-do output, nonzero exits, kernel errors, unknown or persistent active states, and absent/noncanonical output. The tests execute the real executor and notebook lifecycle with external observations simulated. Failed or incomplete readiness continues to block `initiate_run`. The full suite also exercises actual notebook kernels and MCP transports with synthetic scheduler binaries.

Source SHA256: `d3266ef14e8edc2370715679ef12ac7aa12e0fbe051b3a88aac9c031ee6521fe` (`execution.py`). Test SHA256: `cd8a3961df93950bd152946442aa41c71e146bde65aa21b52ece1cabd7090207` (`test_harness.py`). The approved host interpreter imports the executor from this checkout.

## Live evidence

The existing notebook and graph were reused under `runs/xqtl/mcp_smoke_20260923/`. These runtime artifacts are retained on the cluster and excluded from Git.

- `operator.ipynb`: original and replacement configuration/readiness cells, retained logs, source identity, scheduler observations, and results.
- `config.yaml`: the existing canonical defaults, materialized again through MCP `prepare_config`.
- `readiness_20260924.json`: exact result from the approved host execution of MCP-staged cell `7757fdb71c3641a18ac377b62db662b4`.
- `logs/7757fdb71c3641a18ac377b62db662b4.270178190.out`: successful native dry-run, total 21 jobs.
- Native resources: express, one CPU, 32 GB, ten minutes; target `all` with `--dry-run`.
- Notebook verification: `All active cells re-render identically.`

## Submission milestone

After readiness returned `ready` and notebook verification passed, MCP `initiate_run` accepted the same graph through the unchanged gate. The exact staged host command passed automatic review and submitted job **270178197**, observed natively as **PEND** in the returned receipt. The retained result is `submission_20260924.json`, from cell `7f4b4af8a8b34b119a11c88b927f989f`.

The controller uses express, one CPU, 32 GB, and a one-hour limit. The existing `jobs=1` and `workflow_cores=1` smoke-test settings are unchanged; child work uses the canonical LSF profile. Notebook verification passed again after submission. Monitoring stopped at the accepted pending state. Scientific workflow completion is unverified; the next checkpoint is native controller status and logs, followed by conclusion readiness once the controller has ended.

Final review: the requested race fix, conservative regression cases, live readiness, notebook integrity, and gated submission are verified. No action or argument surface was added. A workspace-wide `git diff --check` also reported pre-existing trailing whitespace in the untouched `docs/operator_model.md:3`; that unrelated file was preserved.
