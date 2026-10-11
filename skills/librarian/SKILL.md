---
name: librarian
description: "Use the local librarian to execute scripts on protected results and return masked tables, or deliver Hao's open scientific questions with --me."
---

# Librarian

Apply human-runner, then [query](../query/SKILL.md): name exact inputs, operation,
counting unit, audience, limits and completion. Compare resolved paths against the
colon-separated `$LIBRARIAN_PROTECTED`; result figures are protected too. Inspect
filenames, sizes, schemas, headers, counts and QC pass/fail directly. Keep source
cell values, effect sizes, P/FDR, gene lists and result figures with the librarian.
Keep private dictionaries, human manuscripts, logs, answers and sessions under
`$LIBRARIAN_HOME` private unless Hao explicitly authorizes inspection.

Read input IDs and headers from `~/sunh14/fungen-operator-data-guard/temp_reference/live-tables/headers-live.tsv`.
Start with structure. Use an installed policy input ID in `probe.json`:
```json
{"action":"probe","inputs":{"table":"LIVE_INPUT_ID"}}
```
Run `librarian --broker probe.json`; read its headings and counts.
Then write ordinary Python or R using that schema. The script reads the parameter
JSON at its first argument (`inputs` maps roles to sandbox paths) and writes UTF-8
TSV at its second argument. Choose an installed runtime. For example, Python:
```python
import csv, json, sys
p = json.load(open(sys.argv[1]))
rows = list(csv.DictReader(open(p['inputs']['table']), delimiter='	'))
with open(sys.argv[2], 'w') as f:
    f.write('row_count\n' + str(len(rows)) + '\n')
```
Hand it to the librarian with this short `request.json` (substitute the absolute
script path, its `sha256sum` hash and the input ID):
```json
{"version":1,"question":"Count all rows; return row_count.","script":{"path":"/approved/count.py","sha256":"EXACT_SHA256","runtime":"python"},"inputs":{"table":["LIVE_INPUT_ID"]},"parameters":{},"output":{"columns":["row_count"]}}
```
Run `librarian --broker request.json` for the coding-agent audience. Counts,
whole numbers and categories return in clear. Gene identifiers and fractional
decimals return as stable placeholders, with probability bins, whole-number
percentiles and directions. Preserve placeholders exactly in code, tables and
text; use them as opaque labels or join keys. Use attached categories and ranks
for comparisons and keep the complete returned table.

A generated sentence explains each placeholder and available stand-ins. Rephrase
what you need using that placeholder, then submit a linked request, for example:
```json
{"action":"rephrase","run":"ORIGINAL_RUN_ID","question":"Where does {{TEXT-ABCD}} rank?","operations":[{"operation":"rank","item":"{{TEXT-ABCD}}","reference":{"kind":"returned","column":"gene"}}]}
```
Use `librarian --broker rephrase.json`. Available operations include counts,
rank, group, same-gene match, decimal comparison, direction, percentile,
absolute_percentile and bin. Keep supplemental replies beside the original table.

For a simple lookup, use `{"action":"question","question":"Count all rows; return columns row_count.","inputs":{"table":"LIVE_INPUT_ID"}}`.
Larger or unsuccessful questions return a sentence ending **“Send it as a script,
or ask one part at a time.”** Follow that instruction with the named inputs.

`librarian --me "<Hao's exact open scientific question>"` keeps its existing
full-answer path and user delivery. Use the existing wrapper and shared locks;
a call may wait for minutes. Run calls outside the sandbox when needed. The
coding agent owns LSF and project workflows; reductions reading or using more
than 1 GiB go through the project's normal LSF path, followed by a bounded request
on the small output. Retain `codex_lsf_select` for agent jobs and the namespace guard.
