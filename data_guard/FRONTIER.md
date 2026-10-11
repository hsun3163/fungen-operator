# Working with live result tables

Use the installed [librarian skill](../skills/librarian/SKILL.md) for the short worked
request-file example. Start with `librarian --broker probe.json`:
`{"action":"probe","inputs":{"table":"LIVE_INPUT_ID"}}` returns structure and counts.
Write a plain Python or configured R script from those headings, pin its hash in
`request.json`, and hand it to `librarian --broker request.json`.

Counts, whole numbers and categories arrive in clear. Genes and fractional decimals
arrive as placeholders, with bins, percentiles and directions. Preserve placeholders
exactly in code, tables and prose; treat them as stable opaque labels. Keep the full
masked table. The generated rephrase sentence names the available stand-ins: use
attached facts or submit `action: rephrase` with the original run ID, your question
using placeholders and the requested count, rank, group, match, compare, direction,
percentile, absolute_percentile or bin operation.

A short `action: question` request supports simple lookups on one named policy input: one table, under about 100 words, answerable by a short pandas chain. Requests naming several tables, or needing loops, branches or several sections, are handed back.
The push-back sentence ends “Send it as a script, or ask one part at a time.” Follow
it by supplying a script or a smaller question. Hao's own open questions continue
through `librarian --me "<question>"` with full user delivery. Protected source values,
figures, human manuscripts and dictionaries stay with the librarian.

# Working on masked manuscripts

- Read and edit only the masked manuscript and its slot-status file.
- Preserve placeholders exactly, for example `{{VALUE-ABCD}}`.
- Request a new private value by writing a **bold description of the value needed** in its sentence. The next operator import assigns its slot ID.
- Never reuse an ID for a different quantity. Request a new slot instead.
- If a read is denied, request a slot instead of retrying another way.
- Use real Markdown headings (`#`, `##`, etc.) for structural bold. Every bold span in body text requests protection, including a standalone bold paragraph.
- The user or local librarian runs export, import, retrieval and dictionary publication. Hosted agents never run those commands on real data, inspect the dictionary, or open the human manuscript or librarian logs.
