---
name: query
description: Compose specific, bounded requests to the existing local data librarian. Use before every librarian request, follow-up, retry, or librarian task submitted through LSF, including scientific lookups, manuscript slots, and private operational diagnostics.
---

# Query the librarian

The hosted agent owns the question and input selection. Give the librarian enough detail to perform the
lookup directly. Apply `human-runner` first and follow the [librarian privacy and execution rules](../librarian/SKILL.md).
Use the existing `librarian` command; put this contract in its ordinary task text.

## Prepare a bounded question

- Obtain exact input paths from the user's request, a named configuration entry, a source manifest, or source
  references in the masked manuscript. Do allowed metadata/schema checks yourself. Prefer existing small
  exports over raw analysis outputs. Identify the intended run/release and any explicitly permitted substitute.
- Ask one question or a small group answered from the same named inputs. Specify the quantities, row filters,
  columns when known, unit of counting, denominator, thresholds and rounding needed for that question. State
  unknown schema details explicitly; the librarian may inspect the headers of the named files.
- Separate unrelated work such as result retrieval, artifact discovery and Drive upload into distinct requests.
  Each follow-up names the remaining IDs/questions, exact inputs and any relevant prior private artifact path;
  do not send an open-ended "continue", "find everything" or "fill all results" request.
- Estimate the read volume and memory from file metadata and the proposed operation. Respect the librarian's
  1 GiB boundary; the hosted agent prepares any larger reduction through the existing LSF workflow.

If an input location is unknown, resolve that before sending a scientific lookup. A pointer lookup must name
the exact config/manifest and key or section to inspect. Ask for the referenced path and its metadata only.
Do not ask the librarian to list directories, search filename patterns, scan trees or build filesystem
inventories, even with a depth or result limit. For `knowledge_map`, supply its configured location or a named
pointer file. If neither is known, the caller must obtain that input before dispatch; do not delegate a search.
When the librarian asks for clarification, the frontier model obtains the exact missing details from permitted
metadata, configuration or the user when necessary, then sends a revised, self-contained request. Do not send
the vague task back or tell the librarian to explore until it finds an answer.

## Include these details in the request

Use concise prose or this template, with concrete values for every applicable field:

```text
Question / slot IDs: the exact facts to retrieve or compute.
Inputs: exact files, intended run/release, and allowed lookup scope.
Operation: filters, columns, counting unit, denominator, and output precision.
Output / audience: answer fields and destination; what the hosted caller may receive.
Limits: expected read size, named-file access scope, and allowed writes.
If underspecified or blocked: ask the frontier caller for the exact missing path,
           column or question detail; pause that item and continue independent,
           specified items without widening the search.
Completion: the concrete output or verification that establishes success.
```

Keep source paths, hashes and reproducible calculations in the librarian's private evidence. Ask it to distinguish
an unavailable input from a computed empty result. Reading the named input tables is expected; searching for
additional analyses or choosing a different release requires a new, explicitly scoped request.

## Dispatch and follow up

- Scientific answers for the user go through `librarian --me`. Operational requests return only permitted
  metadata, stage/error codes and artifact links to the hosted agent. Private logs, dictionaries and real
  manuscript values stay with the librarian. Do not inspect them yourself to make a request more specific.
- For manuscript slots, name the document, slot IDs, source tables and requested facts. Have the local librarian
  retrieve the values itself, save a private ID-keyed reply JSON and run
  `librarian mask retrieve --document DOCUMENT --reply-file PRIVATE_JSON`. Only the requested group is committed.
  The deterministic script owns masking, IDs, binding and revision checks. Never ask a librarian model to invoke
  an unqualified `mask retrieve` or another librarian model inside its own run.
- Keep one active librarian inference task on the shared endpoint. For longer work, use the existing LSF path
  with an explicit time allowance; LSF does not make an open-ended request precise. Split work by input and
  deliverable so a finished group is saved before the next starts.
- Check the declared output, not just launch acceptance. A timeout or missing response means the request is
  incomplete. Retry only after identifying the failed stage and changing the scope or execution condition that
  caused it. A retry carries the outstanding items and their inputs, rather than repeating the entire task.

## Synthetic example

For an invented support table whose path and schema are already known, a sufficient request is:

> Using only `~/synthetic-fixtures/invented_support.tsv` from release `synthetic-v1`, select `keep == true`.
> Return the number of distinct `gene_id` values and the number of distinct `(gene_id, dataset_id)` pairs.
> Use integers; drop rows with missing keys and report that exclusion in the private evidence. The file is
> below 1 MiB. Send the scientific answer to the user through `--me`, with its source hash. If the file or a
> named column is missing, report that exact missing input and stop this lookup; do not search elsewhere.

Replace the fixture reference with the actual exact path before dispatch. For a masked manuscript, replace the
answer destination with the specified pending slot IDs and private reply file; return only slot status to the host.
