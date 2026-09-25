---
name: librarian
description: "Ask the local-model data librarian about protected result files instead of reading them yourself. Use whenever a task needs the contents of files under $LIBRARIAN_PROTECTED (schemas, rows, values, QC counts, debugging a script against real results) or when the user asks to check, inspect, list, interpret or compare scientific results (which genes/variants pass, hit counts, effect sizes, context comparisons)."
---

# Librarian

Unpublished results are read by a local Qwen model (`codex exec --oss`), not by you. You operate the project;
the librarian reads the archive and answers.

## Protected paths

`$LIBRARIAN_PROTECTED` is a colon-separated list of protected result paths.

- Metadata is fine: names, directory structure, sizes, timestamps (`ls -l`, `du`, `stat`, `find -name`).
- Contents are the librarian's job. Do not read protected files into your context, and do not run shell, Python
  or R that prints their contents (`cat`, `head`, `zcat`, `grep`, `pandas.read_*`, `awk`, ...).
- Running workflows that produce or update those files is fine.

Do not read anything under `$LIBRARIAN_HOME` (logs, answers, sessions, run directories, notebooks, `latest.md`)
unless the user explicitly tells you to.

## Calls

```bash
librarian "<task>"        # answer comes back to you on stdout
librarian --me "<task>"   # answer goes to the user's latest.md; you get only "Done"
```

Use `librarian "<task>"` for your own coding, QC, schema inspection, debugging and diagnosis.

Use `librarian --me "<task>"` when the user asks to check a result, inspect findings, see which genes/variants
passed, interpret the final analysis or compare scientific findings. Tell the user the answer is in `latest.md`.

If the librarian replies "This is a scientific-result question. Re-ask it with `librarian --me`", re-ask with
`--me`; don't rephrase to get the result yourself.

To have the librarian run code you wrote, give it the script path and say what to check:
`librarian "Run /path/check_merge.py against <protected file> and tell me what is wrong with the code."`

A call can take minutes. A failure prints one line naming what failed and the run log; report it to the user
rather than reading the log or falling back to reading the data yourself.

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
