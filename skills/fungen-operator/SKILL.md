---
name: fungen-operator
description: Operate one existing canonical xQTL workflow through the Fungen MCP harness, retaining configuration, readiness, submission, and completion in an operator notebook. Use for lab-tech operation when the Fungen tools are connected.
---

# Fungen Operator prototype

Use the connected `prepare_config`, `check_readiness`, `initiate_run`, and `inspect_run` tools.
Read source, configuration, notebook history, logs, and output paths to select the next action.
The developer owns workflow implementation. Harmonized input paths are the starting boundary.

1. Bind one notebook, configuration, and working directory to the requested output graph.
   Inspect the deployment's canonical defaults; supply exposed parameters as typed values.
2. Call `prepare_config`. Defaults are recommended. Scientific differences go to the human
   through MCP elicitation before the harness writes a cell or config. The connected client
   must present that elicitation to a person; never answer it with model-generated consent.
3. Call `check_readiness` for the intended targets. Use its successful recorded result to
   authorize `initiate_run` with matching arguments when work remains. A `nothing_to_do`
   result already supplies canonical completion evidence. Controller walltime may differ.
4. Call `initiate_run`; inspect its receipt and native state. A receipt means submitted.
   After interruption, call the same action for the same workspace. Snakemake reuses valid work.
5. When the controller has ended, call `check_readiness` with `phase="conclusion"`.
   A successful `nothing_to_do` result records canonical workflow completion for those targets.
   Report scientific interpretation separately when the user requests it.

For an `lsf` deployment, an action returns `host_approval_required` and an exact `host_command`.
Run that command through `exec_command` with `sandbox_permissions="require_escalated"` on its
first attempt. This requirement also covers the CLI `inspect` and `replay` commands, which can
invoke scheduler clients. Never add a persistent interpreter/script rule. If review rejects
the command or escalation is unavailable, report an approval-path failure and stop that action.
The host entrypoint validates the saved cell and current state again before executing it.

Inspect operational failures and change only exposed configuration/resources through these
tools. A source defect or an unsupported recovery operation is a developer handoff. The current
catalog contains no source-edit, harmonization, unlock, cancellation, force, or composition tool.

Use `fungen-operator verify NOTEBOOK` at conclusion. Use the harness `replay` command to run
active cells in order; superseded code remains visible as history and is excluded by replay.
Ordinary Jupyter Run All executes historical cells too and is not the supported replay path.

Setup, exact constraints, examples, and limitations: [prototype architecture](../../docs/operator_prototype.md).
