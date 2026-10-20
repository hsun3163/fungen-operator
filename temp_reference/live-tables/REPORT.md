# Live COSI librarian installation

Status: verified. Operator policy: ~/sunh14/librarian_agent/operator/broker-policy.json.
Policy SHA256: 8743fe0215f2b923f23c9356152958c30a338363d942fcaae3a46b52bf6afcfa.
Inputs: 593. Distinct source headers: 2044. Unclassified columns: 0.
Structure probes: 593 passed; 0 failed, through installed librarian --broker.
Full catalog is installation-owned; the wrapper selects only named candidates into a
private request policy and policy_file validates it. The core 64 KiB policy-artifact
limit remains unchanged. Installed probes return headers and logical row counts,
with no cell examples, value typing, model calls or Google result publication.

## Supervised request

Run: run-8ba3fc1b70a4450aaa286c28d6b4ca5a.
The returned text has 18 eQTL rows with integer row and distinct-gene counts. The
representative keys are TEXT placeholders and all fractional summaries are VALUE
placeholders. Each fraction has a bin and whole-number percentile. Gene and decimal
cell values were verified solely through the masked return, rather than human.tsv.
The existing Google adapter returned sent for [Librarian results](https://docs.google.com/document/d/1ssEEQMHv6VwHC7uGYzIPe4fwviof3LuywABEmxCd-iE/edit).
The representative key and count fraction are masking controls alongside the requested counts.
The first count-only run was run-1ea7f0befd3c4fe382767cadd3c7af71; it had no masked fields.

## Validation and retained files

headers-live.tsv: filenames, resolved paths, sizes and headers only.
probes.tsv / probes.log: input-specific pass/fail, headers and counts only.
count_by_eqtl.py / count-request.json / count.reply / count.status: rerunnable supervised request and permitted return.
cleanup.json: owned backend-4 tunnel closed successfully under the endpoint lock.
The main librarian job/state and all scribe server launch settings were unchanged.

Tests: 45 wrapper/inventory/network passed; 98 broker passed, 17 native sandbox
integrations skipped on this login host; 13 scorer/transport passed, 1 native transport
integration skipped. Native installed probe and real analysis paths were exercised.
Two real-local-fix-002 push-backs were rescored as handed back, kind size; no human.tsv
was required. Hand-back kinds size, attempts and tries differ have synthetic regression coverage.

## Core observations kept separate from this change

broker.py's generic policy loader admits at most 64 KiB. The installed wrapper's
request-scoped catalog addresses that limit without changing broker.py.
The original model-mediated main-table probe run-6e5497ef8a024475a9333bd1db164259
ended with TimeoutError. Fixed structure-only probing now succeeds for every catalog input.
No change was made to broker.py, masking.py, standins.py or their tests by this task.
The two-tries agreement and temperature 0.2 / seeds 11 and 23 remain being measured
in runs/temp-bench-* by the other session.

## Benchmark changes in the librarian commit

The canonical scorer, round reports, regression tests and RELIABILITY_DESIGN.md were
updated in ~/Myloid-paper/3_Production/scribe_benchmark. data_guard/live_benchmark.patch
retains those exact code/document edits in the librarian repository's single commit;
apply it from the benchmark directory with git apply when reproducing elsewhere.
