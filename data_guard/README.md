# data_guard

A hook-based layer that keeps protected result data out of coding-agent context for **Claude Code** and **Codex**.
Agents can still run the workflow and read code, configuration and published inputs. Protected tables are reachable
only through a broker whose output passes a deterministic egress filter, or through a local (Ollama) model.

## How it works

```text
agent tool call ──► PreToolUse hook (guard.py)
                      ├─ shell command ─► rewritten to `sbx -c '<cmd>'` (bubblewrap, protected paths mounted empty)
                      ├─ Read/Edit/Write/Grep/other tools on protected paths ─► denied, pointed to sanitize-query
                      ├─ `sanitize-query …` (standalone) ─► allowed unwrapped
                      └─ guard error ─► denied (fail closed)

sanitize-query run <script|cmd>   exact computation: read-only filesystem, no network, private work dir
sanitize-query ask "<q>" <files>  local Ollama model answers from whole-file summaries + sample rows
                     └─► egress filter ─► agent        (every release appended to ~/.sanitize-layer/audit.jsonl)
```

Both agents use the same `guard.py`; it recognises Claude Code (`Bash`, `Monitor`, file tools) and Codex
(`exec_command`, `shell` argv forms, `apply_patch`) payloads. The rewrite does not grant permission, so each
agent's normal approval / auto-mode checks still apply.

### Egress filter

| Released | Redacted to `<R>` |
|---|---|
| gene IDs and symbols, variant IDs, alleles, positions | decimals and integers < 1000 on any line naming a gene/variant (`ENSG…`, `rs…`, `chrN:pos`, symbols from `symbol_files`) |
| counts, aggregate statistics, hashes, file listings | decimals beyond `max_anonymous_numeric_lines` entity-free lines |
| | output beyond `max_lines` / `max_chars` is truncated |

Published inputs (e.g. summary-statistic VCFs) are not protected and can be read directly; values from them are
redacted only when routed through `sanitize-query` next to an identifier.

## Install

```bash
python3 data_guard/install.py --dry-run   # show changes
python3 data_guard/install.py             # policy scaffold, ~/.local/bin/sanitize-query, hooks for both agents
```

Then edit `~/.config/sanitize-layer/policy.json`:

- `protected`: directories whose contents agents must not read directly (derived results, the broker state dir).
- `self_paths`: the policy directory and this checkout, so agents cannot modify the guard.
- `egress`: limits and `symbol_files` (TSV with a `gene_name` column) for symbol detection.
- `ollama`: URL and model for `ask` mode.

Codex runs a new hook only after you approve it; start Codex once and approve the PreToolUse hook.
Check it from inside each agent: `ls <protected dir> | wc -l` should print `0`.

Disable temporarily with `touch ~/.config/sanitize-layer/DISABLED` (from your own terminal); remove the file to
re-enable. `install.py --remove` unregisters the hook. Config files are backed up before every change.

## Use (from an agent)

```bash
sanitize-query run check.R                       # R/Python/shell script or a command string
sanitize-query ask "how many distinct genes pass intact_pp >= 0.95?" results/table.tsv.gz
```

Scripts may write only to `$SANITIZE_WORK` (inside the protected state dir). Use `run` for exact audits; `ask`
sees summaries and a sample, not every row.

## Tests

```bash
python3 -m pytest data_guard/tests
```

Covers hook decisions for both agents' payload shapes, self-protection, kill switch, fail-closed behaviour,
egress rules, sandbox masking, and `run` isolation (sandbox tests skip when bubblewrap is unavailable).

## Scope and limits

- Threat model: accidental disclosure by a cooperative agent. A deliberately adversarial agent could encode values
  to evade the filter.
- Hooks cover agent tool calls only. Commands you run with `!`, and text you paste, reach the model unfiltered.
- Requires Linux with unprivileged bubblewrap (`bwrap`). Nested use inside Codex's own sandbox is supported.
- Shell state changes inside a rewritten command (e.g. `cd`) happen inside the sandbox.
