---
name: librarian
description: "Ask the local-model data librarian for scientific results in protected files instead of reading them yourself. Use when the user asks to check, inspect, list, interpret or compare scientific results (which genes/variants pass, hit counts, effect sizes, context comparisons)."
---

# Librarian

Unpublished results are read by a local Qwen model (`codex exec --oss`), not by you. You operate the project;
the librarian reads the archive and answers.

## Protected paths

`$LIBRARIAN_PROTECTED` is a colon-separated list of protected result paths. Folders have several names on
Minerva (`~/...` symlinks and `/sc/arion/...`), so compare with resolved paths (`realpath`); anything under a
protected folder is protected, including result figures.

- QC is your job: metadata, schemas, headers, identifiers, row/sample counts, missingness, joins, file sizes and
  checks that code ran correctly. Do these yourself.
- Scientific results are the librarian's job: do not print effect sizes, p/FDR values, significance calls, hit
  counts or ranked gene/variant lists from protected files into your context. Write QC so it reports pass/fail
  and structure, not those values.
- Running workflows that produce or update those files is fine.

Do not read anything under `$LIBRARIAN_HOME` (logs, answers, sessions, run directories, notebooks, `latest.md`)
unless the user explicitly tells you to.

## Calls

Before every request, follow [Query the librarian](../query/SKILL.md) to name the exact inputs, question,
operation, output audience and missing-input action. This includes follow-ups, retries and tasks sent through
LSF. The hosted agent selects and bounds the work; the librarian receives a concrete lookup to perform.

```bash
librarian "<task>"        # answer comes back to you on stdout
librarian --me "<task>"   # answer goes to the user's latest.md; you get only "Done"
```

Use `librarian "<task>"` when debugging genuinely needs result values you should not see (e.g. why a specific
result looks wrong).

Use `librarian --me "<task>"` when the user asks to check a result, inspect findings, see which genes/variants
passed, interpret the final analysis or compare scientific findings. Tell the user the answer is in `latest.md`; the
wrapper also publishes it as the README of their private answers repo.

If the librarian replies "This is a scientific-result question. Re-ask it with `librarian --me`", re-ask with
`--me`; don't rephrase to get the result yourself.

To have the librarian run code you wrote, give it the script path and say what to check:
`librarian "Run /path/check_merge.py against <protected file> and tell me what is wrong with the code."`

A call can take minutes. A failure prints one line naming what failed and the run log; report it to the user
rather than reading the log or falling back to reading the data yourself.

## Scribes and concurrency

At most **one librarian call at a time**: its GPU serves one active call. The wrapper holds a lock across
execution and resume; use that wrapper rather than starting raw Codex calls on the librarian endpoint.

Use `librarian --scribe "<bounded operational task>"` to move a small lookup to an extra local-model worker
on its own GPU. Use `librarian --scribe --me "<bounded scientific task>"` for user-facing results and
`librarian --scribe --check --me "<task defining a result table>"` for two independent parallel computations.
On mismatch, invalid tables or no defined table, a fresh reviewer reads both private answers and scripts.
Scribes follow the same named-input, read-only source-data, 1 GiB and audience rules as the librarian.
No healthy scribe is a failure; callers may set one up through `scribes up N` and test it when ready.
Scribe calls always use scribe endpoints, never the librarian endpoint.

Run librarian and scribe **agent calls** from the login/session host, or in an LSF job with
`-R "$(data_guard/codex_lsf_select)"`: the `ondemand` nodes (`lh06c*`) disable user namespaces, so Codex's sandbox fails there. See [SCRIBES.md](../../data_guard/SCRIBES.md) for setup,
lifecycle, explicit endpoint isolation, normalization, resource sizing, relaunch and debugging.

## LSF

Keep heavy jobs away from the librarian: anything expected to read more than 1 GiB or need more than 1 GiB of
memory goes through LSF from your side, and the librarian gets only the small derived output.

You own LSF submission, monitoring, reruns and workflow operation; the librarian never submits jobs. When it
returns a >1 GiB handoff, turn the requested reduction into the project's normal code or workflow target, submit
it through the standard LSF path, monitor as appropriate, then call the librarian again on the small output with
the follow-up question it gave you.

## Permissions

The librarian writes to `$LIBRARIAN_HOME`, contacts the local Qwen endpoint and runs its own Codex, so it may need
to run outside your ordinary sandbox. Request that permission in the normal way; never substitute direct
inspection of protected data.
