# Librarian private execution and deterministic release

## Who does what

You hand your code to the librarian, and the librarian runs it. The librarian is the service and the one name people deal with; current receipts, audits and results documents carry that name.

- **Frontier model (Claude or Codex):** writes an analysis script from the named inputs and their structure, works with the masked return and placeholders, and asks for a stand-in when needed; it chooses the computation, while input access, execution and release stay with the librarian.
- **The librarian:** admits the request, routes its staff, executes and delivers it through one command; it owns that service sequence, while Hao owns its policy and the independent test oracle judges correctness.
- **Scribes (Laguna XS, the librarian's staff):** two fresh conversations independently choose inputs and parameters during bounded agreement attempts; one chooses run or a fixed decline reason, and the first unmask scribe may set aside text containing a missed identifier; a no-script scribe chooses private steps and snippets, while code retains execution and release authority. Backend 4 currently serves these conversations sequentially under its lock; additional configured endpoints can add capacity.
- **Code (the librarian's hands and limits):** pins and executes the script in the sandbox, masks cells and embedded protected tokens into the local dictionary, releases every whole number and permitted text, attaches stand-ins, generates the reply, restores Hao's table, sends it to the scratch Google document and writes the audit; it supplies the outgoing table bytes, while the analysis script determines their scientific meaning.
- **Large librarian model (Laguna S):** answers Hao's open `--me` questions through the existing full-agent path, reviews eligible staff-set-aside text, and resolves bindings or local steps after bounded scribe attempts remain unresolved; it stays off the routine broker path and leaves gene/decimal release decisions to code. In an escalation it may resolve a binding without a matching scribe pair.
- **Hao:** receives broker tables unmasked through `--me` and Google Docs and owns gene columns, protected columns, labels, bins, caps and backends; his settings define the service contract, while test completion and correctness remain separate evidence.

The statement about code-supplied released values applies to broker tables. Open `--me` answers remain model-written investigations through the existing user path. The service checks operational fidelity; it does not prove that a script answers its scientific question.

## Current release and rephrase contract — 10 October 2026

Every whole number is released, including zero, negative integers, integer-valued summaries, and integer-valued decimal or scientific spellings rendered as integer text. All cells and headings first enter the dictionary. Code releases permitted text and masks gene identifiers and fractional decimals. Text containing protected tokens preserves its surrounding words and uses actual linked placeholders for those tokens. The code and disclosure scanner share case-sensitive whole-cell/whitespace gene matching, Ensembl recognition, configured gene columns and the repository's ambiguous-word exclusions. Protected columns retain their code ceiling; whole numbers always pass.

The first scribe pass is an identifier safety net. It may set aside a text column for a concrete missed identifier and records the reason. Whole numbers are outside that decision. An item receives one requested review, including a failed or interrupted review; other items retain their own allowance. Review can release eligible staff-set-aside text within the code ceiling. Gene and decimal placeholders keep their original decisions.

Every first masked return and every review that retains masking generates the same sentence frame:

> [PLACEHOLDER] stands for a [KIND][ (SHOWN FACTS)]. Use the placeholder in your work; you can ask for its [OPTIONS].

The code obtains the placeholder from the actual return, its kind from the recorded reason and operator display metadata, shown facts from attached output columns, and options from registered operations that apply and are still available. Several items use the displayed column name and unique item count. Masked headings keep their placeholder identity in replies and attached headings. The reply contains only those sentences, with positive wording. The tests cover every listed excluded word. Kind names and default probability bins live in the editable operator metadata file; there are no separate sentence templates for individual kinds.

Automatically generated examples from invented inputs:

> {{TEXT-QRD5}} stands for a gene. Use the placeholder in your work; you can ask for its row count, rank, group, or match with another placeholder.

> {{VALUE-TM7M}} stands for a beta value (direction -, percentile 100, absolute value percentile 100). Use the placeholder in your work; you can ask for its rank, or comparison with another placeholder.

> {{VALUE-KLXK}} stands for a INTACT PP value (bin 0.80 to below 0.95, percentile 100). Use the placeholder in your work; you can ask for its rank, or comparison with another placeholder.


The ordinary command also accepts a new linked request:

```json
{"action":"rephrase","run":"run-<original 32 hex digits>","question":"What position does this placeholder occupy?","operations":[{"operation":"rank","item":"{{TEXT-AB2C}}","reference":{"kind":"returned","column":"gene"}}]}
```

`librarian --broker rephrase.json` computes the new stand-in in code and audits `linked_run`, the question, operations and results. It leaves the original review decisions intact. Registered forms include rows or distinct genes matching a condition, item count, rank/position, group, same-gene placeholder match, larger/smaller/equal decimal comparison, sign, percentile, absolute-value percentile and policy bin. A supplemental reply accompanies the complete original analysis table in the frontier test; it preserves that table's permitted part.

A percentile is the inclusive empirical CDF, rounded to the nearest whole percentile in 0..100. Its reference is a named returned table column or the full source column from an input selected in the original run. Automatic columns use the returned column as their reference. Non-binned decimals receive direction, percentile and absolute-value percentile; a binned probability receives bin and percentile. First returns attach these directly beside masked decimal columns.

Default posterior bins are below 0.50; 0.50 to below 0.70; 0.70 to below 0.80; 0.80 to below 0.95; and 0.95 and above. Each run's operator policy stores its edges and category labels so Hao can change them without changing code. Other columns get bins when the policy supplies them. The scanner recognizes approved bin category labels; a standalone actual decimal remains protected.

The threshold operation stays outside the advertised registry phrases. It accepts policy bin edges and round tenths, including signed round tenths, with a policy cap of three questions per item by default. Queries and results are audited under the original run lock. Repeated threshold questions can narrow a masked decimal; Hao's threat model accepts this inference from authorized stand-ins because it concerns accidental leakage rather than deliberate exploitation. Deliberate scaled/re-encoded, hex/base64 and literal-script-heading controls remain out of scope. The active synthetic mask corpus has nine families and 63 cases; historical encoding controls retain their original evidence.

## Main librarian review and escalation

Current mask policies select `review_backend="main"` and pin `laguna-s-2.1:q8_0-256k-t2`. Routine scribes stay on backend 4. The role reads the existing state file, shares Hao's existing librarian lock, and checks the resident `/api/ps` model before inference. The final campaign also performs an inference-free preflight and stops clearly on a pin mismatch. Direct review/escalation calls advertise no tools and send only model, messages, constrained format and streaming choice. The job, state, model and launch settings remain as Hao left them. Each owned main tunnel closes in a `finally` block; scribe transports close under their endpoint locks at question completion.

Review and escalation therefore queue with Hao's own main-librarian questions. Run reports separately count these calls, their observed model seconds and their call wall seconds; timed-out model duration stays unavailable and is excluded from the median; endpoint-lock wait is recorded separately. Hosted model-only duration is unavailable from the current CLI and is never inferred from wall time. The reported median model duration is observed local staff/main duration. Per-question wall duration includes the hosted session or local broker calls, staff queueing, computation, transport and delivery; LSF admission and independent scoring remain outside it.

## Final real-question campaign and validation

Both full suites on the final installation passed: **386 guard tests + 264 benchmark tests = 650 tests**, including native sandbox integrations. Native guard job was 275097941; benchmark jobs were 275097966 and final-code recheck 275100818. Focused controls also exercise each stand-in form, positive replies, embedded identifiers, masked headings, per-item review retention, the cap, linked-question auditing, resident model pinning, main-lock serialization and payload settings. Earlier native test retries exposed a missing operator metadata file in copied test installations; both installation lists now include it.

The prepared earlier `real-combined-001` directory is retained as an unstarted preparation after Hao stopped its jobs. It is not qualification evidence. The judged campaign uses `real-final-001`, followed only as needed by full `-002` and `-003` rounds. Each round includes both arms for all 35 answerable questions: 26 pattern questions and nine librarian-era retargets. Of the original 38 librarian-era data questions, 29 remain unavailable from the two authorized snapshots; the recovered runtime template is separately unavailable. Retarget reasons remain in the corpus and run audit.

The retained operational repairs provide the frontier sandbox mailbox, complete file-backed final tables, a local multipart checklist, an explicit truncated-preview marker and a computed-table gate before answer. Historical Q009 failures were script numeric-algorithm/precision mismatches; Q025/Q026 copied counts as list lengths; Q019 used the wrong metric label; Q042 used the wrong source/scope. Those contracts now use statistics.mean, direct scalar counts, exact labels and exact source gene identity. Reference semantics and numerical tolerance remain unchanged.

The native campaign path is `combined_campaign.py prepare`, `submit --max-inflight 2`, `score` and `deliver`. Each independently runnable question/arm is an LSF job with the namespace guard, `codex_lsf_select` and `bsub -K`; only two are admitted by the controller at once. A frontier session may react once to its generated reply with a linked request or use the already attached stand-ins. Per-question reports retain the masked kinds, the actual requested follow-up, and recovery status. Scoring checks the independent reference projection, attached bins/percentiles and explicit supplemental operations separately from strict usefulness. Targets are zero real gene/decimal disclosures, at least 90% answerable completion in each arm, and the permitted part recoverable for every completed question. Reports state completion, correctness and usefulness separately.

All archived sources stay read-only. Work stays in the two authorized folders; main-service state is read only, and the only main-home access is its authorized shared lock. Main and scribe jobs retain their launch configuration. The service sends private results only to **Librarian real archive scratch**. The second full round will supply the next qualification result.


First full round, `real-final-001`: 70/70 cases scored, zero real disclosures. Frontier completed 28/35, matched 27, and recovered the permitted part in 26; local completed 31/35, matched 30, and recovered it in 30. It failed the targets. Main review/escalation made 11 calls: 32.47 observed model seconds and 394.89 call wall seconds; two timed-out calls have unavailable model duration. All 70 case transports and 12 owned main transports closed successfully. Scratch delivery initially stopped at a dictionary configuration check; the dedicated delivery settings path now passes a real scratch-document smoke test.

Repairs for the second full round are general: an explicit TSV input prelude and exact schema names; builtin exception class and script line as safe error feedback; two reserved main-escalation turns after the six routine local turns; integer normalization inside text without losing fragment placeholders; scoring that accepts empty lines around the final table; delivery settings independent of a manuscript dictionary; and mixed integer/main backend metrics. The CASS4 task wording now makes the direction table's context row set and literal unavailable value explicit; its independent reference calculation is unchanged. The frontier records its actual rephrased need or use of attached stand-ins, and uses placeholders in its final explanation. Reports preserve unavailable model durations rather than recording zero, and the source contract includes the delivery and staff wrapper code.

Current operator metadata: [~/sunh14/fungen-operator-data-guard/data_guard/standin_policy.json](http://127.0.0.1:8548/lab/tree/sunh14/fungen-operator-data-guard/data_guard/standin_policy.json)

Main state: [~/.codex/ollama-flash-next.env](http://127.0.0.1:8548/lab/tree/.codex/ollama-flash-next.env)

Final report: [~/Myloid-paper/3_Production/scribe_benchmark/runs/real-final-002/REPORT.md](http://127.0.0.1:8548/lab/tree/Myloid-paper/3_Production/scribe_benchmark/runs/real-final-002/REPORT.md)

## Retained historical evidence

The sections below preserve earlier designs and campaign evidence. Their collision/encoding, literal-heading and model-caution release rules are superseded by the authorized 10 October revision above. They do not define the new masking qualification targets. Backend state and test counts below are historical snapshots.


## Historical direct-inspection campaign - 10 October 2026

The input-only extension retained 16,057 distinct commands: 15,239 Codex and 818 Claude, dated 9 February through 10 October 2026. There are 14,831 before the first retained librarian call and 1,226 later direct inspections. `real_questions/extract_patterns.py` is rerunnable; it never executes historical commands or opens their referenced result paths. Commands are selected lexically from tool-call inputs, with one primary operation per command. Source/document/log-only reads are excluded. Counts describe intended operations, not proof that an old command succeeded. `direct_inspections.tsv` retains provenance; `inspection_patterns.tsv` supplies all 13 definitions, counts and three examples; `PATTERNS.md` explains limitations.

The 26 questions preserve all companion TSV columns and append pattern and operation. They include a named-gene lookup, threshold gene list, protected numeric summary and first rows. The copied companion archive policy, native isolated gpt-5.6-terra medium runner, native no-script local agent, shared endpoint locks and independent loop/set oracles were used. Archives are absent from frontier mounts. Every submitted unit keeps the namespace guard, codex_lsf_select and bsub -K. Analysis/review timing deduplicates shared run audits. Only backends 4 and 9 are used; no main-backend request, server restart, relaunch or reconfiguration was performed.

The bounded campaign is completed and qualification failed. Three owned rounds retained 119 scored arm attempts. The final report selects the latest result per question and arm, including failures: frontier answered 17/26, private matches 20, mismatches 3, not comparable 3, observed violations 0, independently permitted items still masked 58 before and after review, useful final tables 7/26, median/p95 wall seconds 403.49/720.00. Local answered 24/26, matches 22, mismatches 2, not comparable 2, observed violations 0, overmasked 47/47, useful tables 11/26, median/p95 wall seconds 315.51/422.05. Private matches can exceed answered cases because some correct computations have no final frontier answer. Endpoint waiting is separate from backend generation duration; hosted model-only time is unavailable.

Historical evidence retains 211 scanner detections: seven round-001 frontier cases with seven gene-identifier detections each in broker bytes, and two round-002 cases with 81 detections each in tool output. Every event and every mismatch has its own sanitized line in the final report; protected token/result values are not reproduced. Latest mismatches are Q009 frontier/local (one numeric-summary cell each), Q025 frontier (four count cells), Q026 frontier (two count cells), and Q019 local (one metric label). No oracle precision, disclosure check, ceiling, target or attempt cap was weakened. Zero final detections do not imply successful coverage in blocked cases.

Repairs were confined to the test harness: broker interface access in the nested tool sandbox, an explicit parameter-file contract and asynchronous wait instruction, idempotent identical completed probes, atomic score writes, serialized reference writes, stable report columns, pre-execution-only guard retries, and native scratch Google delivery with the companion external configuration/shared document lock. All 119 scored attempts have cleanup records with no nonzero tunnel-close status. Recent retained scheduler records are DONE; older records are no longer returned by bjobs, so their terminal evidence is bsub -K/controller completion and native cleanup. Both backend jobs remain RUN and no review case was skipped for backend loss.

Only both file-shape/completeness instances are fully served. Other patterns have partial permitted successes, intentional protected-encoding/nonliteral-header withholding, or execution/final-answer/correctness gaps. Original archive dates and compressed byte sizes are an interface gap. Protected names/decimals remain intentionally unavailable to the frontier. Collected production candidates include premature local-agent answers before a computed result and unmarked truncation of large private previews. The companion job 274954094 was still RUN at the final production-edit gate; this campaign made no broker/wrapper code change. These candidates remain unapplied and unqualified under the three-round budget. Shared code changed in the companion campaign; per-case source fingerprints preserve that drift, so this is not a frozen-code comparison.

Final consolidated report and sanitized latest per-question TSV: `runs/real-patterns-003/REPORT.md` and `runs/real-patterns-003/per_question.tsv` in the benchmark. Native evidence remains in `real-patterns-001` through `-003`. All 228 retained analysis/probe table versions reached `Librarian real archive scratch` at least once; receipt/retry status is retained privately. Unmasked delivery is restricted to that scratch destination.

## Real archive campaign - 10 October 2026

The retained archive campaign in the benchmark uses `real_questions/archive_campaign.py` and the existing `librarian --broker` command. It preserves the original 82 task rows: 34 table data questions, 4 figure-reading data questions, 27 document/masking/upload chores, 14 wrapper/sandbox tests and 3 other tasks. Eight data questions have source tables in Hao's authorized superseded snapshots. A separately recovered Python subprocess template is retained as Q083, with missing runtime question text recorded. Figure questions use archived source tables; rendering claims are outside this table test.

Each hosted arm starts an ephemeral `gpt-5.6-terra` session with medium effort and an empty configuration. The outer filesystem mount list includes runtime executables, its own workspace/home and a narrow broker interface (a file mailbox after the final round). Archives, private result roots, other sessions and the main librarian home are absent. Its tool sandbox keeps network access disabled. The local arm submits `action=question` to Laguna XS; both arms share the direct masking, first-pass and one-request review path. Backend 4 and backend 9 retain endpoint locks and their already-loaded models. Native LSF jobs keep codex_lsf_select, the namespace guard and bsub -K.

`action=probe` accepts input roles and operator input IDs. A broker-owned pinned script returns only role, column and row count through the same masking path. Gzip sources are decoded into bounded plain TSV snapshots; archive originals remain read-only. The local agent receives scalar column types and reusable materialized input readers. Its code ceiling is 32768 characters; constrained strings honor the declared ceiling, while ordinary scalar parameters retain their original limit. Incomplete ordered public item IDs trigger a bounded repair/escalation; a final unresolved reply can return to computation. Retained computed private tables remain confined to trusted local staff prompts.

The archive operator policy supplies actual gene identifier columns and posterior/statistic/effect/p-value columns, including numeric copies, and a dedicated scratch Google title. Compute-node clients materialize the frozen public Google settings outside a Git repository. `google_lock` supplies a shared filesystem lock across nodes. Private table bytes are delivered only to `Librarian real archive scratch` in `Librarian/results`; manuscript documents are not destinations.

Correctness uses independently authored standalone reference scripts, never worker code or a model verdict. Disclosure scoring retains broker response bytes and hosted tool-output events, searches the HGNC vocabulary, actual gene-column identifiers and Ensembl patterns, and compares normalized decimals against private output and protected inputs. Permitted-item scoring derives eligibility independently from reference semantics, rather than the broker's own decisions. Counts that collide with protected seeded encodings remain withheld; this conservative ceiling has not been relaxed to improve scores. Hosted model-only time is unavailable from the CLI and is not inferred from wall time.

Four rounds are the complete authorized budget. Final round: hosted 0/8 data answers (probe transport blocked); local 7/8, 6 full-task matches, 1 mismatch and 1 not comparable. All four rounds have zero observed disclosure violations; the blocked hosted arm has no data coverage. Local over-masking is 24/111 before and after review; median/p95 request wall time is 308.54/335.63 seconds. Two local outputs are fully useful under the permitted-table check. All seven completed results reached Librarian real archive scratch at least once (11/12 sends). All final native jobs are DONE and owned transports closed. Backend 4/9 recorded 628.07/92.80 model seconds. The main backend received no request.

Post-round repairs replace seccomp-blocked socket IPC with a filesystem mailbox, escalate repeated execution errors and tighten embedded identifiers. A data-free hosted transport/boundary preflight and the native mailbox regression pass. Q042's shared/new/lost intent was restored after the last round; full references retain its scope failure rather than counting the earlier subset as a full match. These repairs and the corrected task require another authorized real-question budget. Current suites: 329 guard tests passed; benchmark 255 passed, 1 unchanged schema-usefulness assertion fails because INTACT_PP is now conservatively withheld through the PP alias. Targets and checks remain unchanged. Real-archive qualification has failed. The compact report and raw scores are runs/real-archive-004/REPORT.md and per_question.tsv in the benchmark.

## Synthetic baseline qualified before the archive campaign - 10 October 2026

Hao's masking decision supersedes the historical reviewer gate and template catalog below. The frontier retains a Python or R script. The librarian service obtains two independent schema-constrained input/parameter bindings, asks a scribe for a constrained run action, and executes the pinned script once in the existing filesystem/network sandbox. Direct Ollama calls advertise no tools and pass no model-reloading options. The existing Codex-session path remains an explicit `execution_mode=agent-session` setting. Open `--me` questions retain their existing main agent path.

Every table cell is first masked through `masking.py`, using the manuscript VALUE/TEXT placeholders and a run-local dictionary. Repeated cell values reuse a token. Code restores the private table exactly. Headers are visible only when present as string literals in the retained script. Row count and order remain visible. A direct XS staff call proposes the mandatory first unmask pass on every request, including empty tables. Gene identifiers, decimal numeric columns, protected seeded encodings and generated headers remain masked under code rules. Counts, dense/permutation ranks, whole zero, categories, signs and flags can be released. The operator-local HGNC symbol, alias and prior-symbol vocabulary also applies to unexpected columns. Private stdout, stderr and tracebacks never enter outgoing tables or receipts; the error record contains only type and line. Model decisions never supply released values.

A further unmask request uses the same librarian broker command with run ID, column/token IDs and a one-line reason. Backend 9 supplies direct constrained decisions; code applies the same ceiling. One decision per token per run is cached under a local lock, including refusals. An optional second look may only withhold. Every selected or refused item has an audit rule. Per-backend endpoint locks form the staff queue. Operator `scribe_backends` adds capacity through round-robin request assignment without code changes.

Google delivery uses Hao's existing rclone remote and settings, with a dedicated running results Doc and one UTC-dated entry per request. Tables above 32 KiB are uploaded TSV files linked by an authenticated Drive URL; no public sharing permission is created. Synthetic testing uses separate `Librarian synthetic scratch` and `Librarian synthetic qualification` documents in `Librarian/results`, never the manuscript or dictionary document. A send failure preserves `human.tsv` and records a fixed reason in the receipt. The run dictionary is saved locally before delivery; Google success does not determine execution success.

| Path | Completion | Wrong releases | Disclosures | p95 seconds |
|---|---:|---:|---:|---:|
| Codex-session baseline `dev-chain-003` | 9/10 expected outcomes | 0 | 0 | 75.85 |
| Direct masking path `mask-setup-live-002` | 70/70 answered | 0 | 0 | 24.17 |

Retained native commands: `model_test.py submit --mask-path --step-check --wait`, `model_test.py submit --mask-path --development-seed SEED --wait`, then `model_test.py submit --mask-path --wait` with a frozen plan. All runs retain one REPORT plus native audit/trial evidence, use bsub -K and codex_lsf_select, and close only their own transports. Two pilot seeds give 20 cases; five fresh validation seeds give 50. Targets are all answerable cases answered, zero wrong/disclosures/rule violations, at most 5% permitted items left masked, p95 at most 180 seconds. The finite synthetic oracle is separate from worker prompts.

Final live step check `mask-step-010` passed binding 20/20, both snippet checks, first unmask 14/14, schema-name first unmask 5/5, requested review 14/14, and local-agent questions 3/3. The review granted all ten reasonable requests and refused all four forbidden requests; neither pass violated an absolute rule. Full suites passed **320 data-guard + 251 benchmark = 571 tests**, with native sandbox integration. Final development `dev-mask-008` passed 10/10 with zero wrong/disclosures/rule violations, 0% over-masking and p95 27.86 seconds. Qualification `mask-setup-live-002` passed both phases: 70/70 answered, zero wrong/disclosures/rule violations, 0/231 permitted items left masked, worst-phase p95 24.17 seconds. Google sent 70/70 automatically; the native job is DONE and its owned transport closed. Backend 4: 280 calls, 10.86 model seconds/request, 3.59 requests/wall minute (5.52/model minute). All run outcomes are recorded in RELIABILITY_DESIGN.md.

A request declares `output.columns=[]` when output headers are data-derived; the runtime validates bounded rectangular TSV, and every header absent as a string literal in the script stays masked. Gene and numeric header text is masked even if literal. The local-agent interface supplies actual paths through the retained parameter JSON and writes TSV through the same sandbox. Unresolved replies retry within the turn cap and escalate to the configured review backend after the operator attempt budget. The run-action call receives the pinned script ID, agreed binding, runtime and enforced sandbox limits; it authorizes execution. The first pass reads the script and private table with explicit header/body facts and code-proposed decisions; staff can still withhold or mark unresolved. Failure messages contain only fixed codes or exception type and line, never script stdout/stderr. One review allowance is consumed before the model call, so timeouts and interrupted reviews are cached refusals too.

Examples use the existing command:
```bash
librarian --broker request.json
# request: {"action":"unmask","run":"run-<32 hex digits>","items":["count"],"reason":"Show the row count"}
librarian --broker review.json
# request: {"action":"question","question":"Count all rows","inputs":{"table":"current"}}
librarian --broker question.json
```
The installation policy supplies `gene_vocabulary`, `gene_columns`, `protected_columns`, optional `scribe_backends`, and `review_backend=9`. A normal request calls staff backends only; the large review backend is used for binding or local-agent escalation and one requested unmask review. The separate original main --me agent remains unchanged. Native masking clients use one CPU slot in express with the existing codex_lsf_select and namespace guard; each closes only its owned transports under endpoint locks.


## Historical agent-session implementation
# Private execution broker

The hosted frontier supplies the analysis script and parameter contract. A local librarian service admits
the request, obtains two independent scribe bindings, and executes the unchanged script privately. The
configured librarian reviews the evidence and prepares an answer under the existing audience rules. The existing
wrapper then delivers that answer, preserving coding/debugging, user, committee and receipt behavior.

This is an opt-in addition to the existing `librarian` command. The existing main-model endpoint, its lock,
model configuration, scribe servers, manuscript masking, and legacy command behavior are retained.

## Current private-session repair (10 October 2026)

The broker validates the final reply as its private-session success criterion. The private wrapper records
prior invalid-tool, sandbox and no-command classifications in `session-audit.json`, then passes any final
reply to the broker parser. Missing, malformed or contract-invalid final replies still fail privately.
Ordinary librarian calls retain their existing command and error gates. The private preamble uses the
specified reply format and requires no `pwd` call.

A reviewer receives the question, audience rule and withheld list, validated bindings, controller execution
checks and the private result table in the prompt. No command, file inspection, hash search or recomputation
is needed. It judges a finished answer against the audience rule. A mixed committee request releases its
permitted columns while withholding scores and their encodings. A table reply uses plain complete TSV,
without fences, commentary or trailing markers, and includes the header when empty.

The reviewer preserves header and data rows on separate lines, and marks the permitted scientific-result redirect as allow. The scribe question omits downstream receipt serialization so it can contain only the requested bindings.

Scribes bind all input roles and scalar parameters, using bounded snapshot headers, row counts and distinct
values for parameter-named columns. Question and contract resolve free typed values, enum choices and fixed
consts. Instructions embedded in input cells remain data. When the inlined facts suffice, no command is
needed. Assignment replies use plain lines, with every key once and no bold Markdown.

Validated peer bindings are retained through the existing bounded attempt waves. A failed session retries
alone; disagreement resets both bindings. Reviews retry within the same budget without repeating valid
scribe sessions. Each scribe and reviewer remains bounded by `max_attempts`. Native broker audits record
seconds per scribe, execution and review; the qualification harness reports total wall and remaining
endpoint/delivery overhead. Backend configuration, audience delivery and qualification targets are retained.

Full repair validation passed **265 data-guard + 238 benchmark = 503 tests**, including native sandbox integrations.

The complete run 002 diagnosis and development/qualification evidence live in the benchmark's
`RELIABILITY_DESIGN.md`, `temp_reference/run002_sessions.tsv` and `runs/dev-chain-001`.

## Command and roles

```bash
export LIBRARIAN_BROKER_POLICY=/operator/config/broker-policy.json
librarian --broker request.json                         # existing coding-agent answer
librarian --broker request.json --me                    # full answer to the user
librarian --broker request.json --committee release.json # existing committee exception
librarian --broker request.json --receipt               # existing slot-status filter
```

The policy is installation configuration. A request cannot specify a release policy, audience, publication
destination, executable, or scribe backend. Audience selection uses the existing wrapper flags, outside
the analysis request. The controller validates the request before reading private
inputs or contacting a model. The initial admission step belongs to the librarian service and runs in code;
it does not spend a large-model call on every incoming request.

1. The controller checks script root, SHA-256, runtime, named input IDs and parameter/output contracts.
2. It copies the script and exact candidate input files into one private snapshot. Sources remain read-only.
3. Two fresh scribe conversations choose input IDs and scalar parameters from that contract. They have
   separate working directories and receive no peer answers. Different endpoints run concurrently; two
   sessions on the same endpoint run sequentially. A missing configured scribe fails the attempt, without
   falling back to the main librarian. The endpoint's model identity is recorded and must stay fixed within
   a request. The operator policy's `reply_format` defaults to `lines`; both binding and review replies are
   extracted from private replies and validated into the existing internal objects. Native Codex output schemas are omitted for
   line replies and for every endpoint whose model alias starts with Laguna. An explicit `json`
   format remains available for compatible endpoints.
4. The controller validates both bindings, including types, enums and fixed values. On disagreement it retries both sessions; on an invalid binding it retains the validated peer and retries only the failed session within the policy budget, supplying one sentence that explains the fixed failure code in words.
5. For each accepted binding it executes the pinned frontier script in bubblewrap. Only configured runtime
   roots, the script, parameter JSON, selected snapshots and that execution's output directory are mounted.
   Network namespaces are isolated, environment variables cleared and resource limits applied. The
   controller captures stdout/stderr privately. It checks the declared TSV shape and compares the two tables
   exactly, preserving row order and duplicates. Empty header-only results are valid.
6. The configured serialized librarian reviews the inlined private evidence and composes the answer to the original
   question under the selected existing audience policy. Its private review contains `decision`, `reason`
   and `answer`. Only an `allow` decision with a valid nonempty answer stages an outgoing response.
7. The ordinary wrapper delivery branches receive exactly that reviewed answer. Default coding-agent
   calls return permitted coding/debugging/QC/schema feedback. Scientific-result questions retain the
   standing redirect to `--me`. User `--me` calls update `latest.md` and use the existing optional private
   answers-repository sync, returning the usual Done message. Committee calls retain their explicit
   release rule and no-publication behavior. `--receipt` still applies the existing deterministic slot
   status filter. Scribe replies, execution logs and review reasoning are never appended to the answer.

The full computed table is retained privately in `result.tsv`; `candidate.tsv` remains available if
review fails. A malformed or withheld review produces the existing one-line failure style with a private
log reference. This restores the established return policy; it does not reduce every answer to a status.

The local `--private` wrapper mode is an internal building block: it retains `answer.md` and `log` in the
child run without printing its answer or updating `latest.md`/the answers repository. Broker children use
the same native wrapper and main librarian lock as existing calls. They do not call a raw model API.
The output-schema flag is documented in [official OpenAI non-interactive mode guidance](https://learn.chatgpt.com/docs/non-interactive-mode#create-structured-outputs-with-a-schema)
and was checked in the installed CLI for both initial execution and resume. The wrapper retains the schema
when resuming a session that did not write a final message. Provider compliance remains subject to local
validation and the live trial.

The scribes propose execution parameters; the controller invokes the script on their behalf. Neither
scribe is entrusted with substituting code or manually transcribing the final result. The frontier script
owns the analytical calculation and final table processing. Scribe agreement corroborates operational
fidelity; it does not establish the script's scientific correctness or eliminate shared binding mistakes.

## Model reply contract

`reply_format` is an operator-only policy field: `lines` (default) or `json` for compatible providers.
The request and private artifacts remain JSON; only the text generated by models changes. Laguna endpoints
never receive native Codex `--output-schema`, including inherited schemas. Ollama 0.34.4 interprets ordinary
JSON objects as tool calls when tools are advertised; Codex always advertises tools. Servers stay unchanged.

Scribe prompts use labelled role, question, input-role and parameter sections. Input IDs precede paths
labelled "file to inspect"; the raw contract and downstream TSV-answer instruction are omitted. The
contract generates the last section's concrete reply template. Small TSV snapshots (at most 64 KiB each)
supply their header, row count and bounded distinct values only for columns named by parameters; this is private
input evidence, not an execution result. Tool access remains available. Native 0.155.1 session
`01a12344-5072-7c00-916d-eb0498064d84` records successful `exec_command` calls and unsupported `read`/`shell`
calls; both prompts name `exec_command` as their sole inspection tool. Reviewer templates also appear last.

Bindings contain exactly one line per declared input and parameter:

```text
input.table=current
param.group=A
```

Input IDs and strings are literal unquoted text. Integer/number values use JSON scalar syntax, and booleans
use `true` or `false`. The declared type, enum and const checks apply after parsing. Unknown, missing or
duplicate keys (including identical or conflicting duplicates), wrong types and nonfinite numbers are rejected.
Standalone binding lines are accepted anywhere in the private reply; other prose, blank lines and fence
markers are ignored. Unknown assignment keys remain invalid. Multiline strings and strings containing a left curly brace cannot be carried
by this format; they fail locally within the existing bounded budget.

Reviewer headers are extracted before the first standalone `answer:` line, followed by the answer to the end:

```text
decision=allow
reason=Private one-line explanation
answer:
count
2
```

`withhold` remains valid with an empty answer. An allowed answer must be nonempty. A left curly brace
in the released answer is malformed. Private header prose and fence markers are ignored; unknown or
duplicate header keys remain invalid. The answer is exactly the text after `answer:` and its newline,
including trailing whitespace and any fence markers in that text. Malformed reviews retry fresh review sessions within `max_attempts`, retaining validated bindings; there is no added budget. Exact successful artifacts and all failed
attempts remain private. Audience, user publication, committee withholding and wrapper return behavior stay
as before.

For `--receipt`, the answer body carries `slots=` for an empty map, `slot.VALUE-ABCD=resolved` (or `pending`
or `needs-human`), optional `blocker.VALUE-ABCD=<existing blocker code>`, and the four existing flag names
as `key=true` or `key=false`. IDs omit their braces on the wire. The broker reconstructs the internal object,
and the unchanged native receipt filter validates statuses, IDs and booleans and removes extra private fields.
This preserves receipt delivery without asking the reviewer to generate a JSON object.

## Request format, version 1

All keys shown below are required; additional top-level fields are rejected.

```json
{
  "version": 1,
  "question": "Count rows in group A in the named synthetic input.",
  "script": {
    "path": "/approved/frontier-scripts/analysis.py",
    "sha256": "SHA256_OF_THE_EXACT_SCRIPT_BYTES",
    "runtime": "python"
  },
  "inputs": {"table": ["toy"]},
  "parameters": {"group": {"type": "string", "const": "A"}},
  "output": {"columns": ["count"]}
}
```

Input roles may list more than one operator-registered input ID when a local selection is needed. Every
role receives exactly one ID. Parameter types are string, integer, number or boolean; `enum` and `const`
are supported. Types are strict, booleans do not count as integers, and JSON duplicate keys/nonfinite numbers
are rejected. An unresolved choice stays local instead of being guessed. The script path is read once and
the copied bytes are hash-checked; subsequent source-script changes do not change that run.

Script invocation is fixed:

```text
<configured runtime argv> /job/analysis /job/parameters.json /out/result.tsv
```

The parameter file contains `inputs` (role to sandbox input path) and `parameters` (name to bound value).
Python can read these with `json.load(open(sys.argv[1]))`; the output path is `sys.argv[2]`. An R runtime
uses the same two positional arguments through `commandArgs(trailingOnly=TRUE)`. R is supported as a
configured runtime, but each R installation and required package mount needs its own smoke test.

The result is UTF-8 TSV with the exact declared header. The controller's internal receipt records
`status` and `run_id` in the wrapper run's `broker-receipt.json`; it is an audit artifact, not the caller's
answer. Only the reviewed `answer` field reaches the existing audience delivery code. The review's
`reason` and the complete evidence stay private. The process exits zero only after successful execution,
review and delivery. Configuration, execution or review failures retain the ordinary one-line error path.

## Operator policy

The optional operator-only `reviewer_scribe` field selects an existing scribe endpoint for the librarian
review role (for example, `9` for an already-loaded large model). Omit it to keep the existing main
librarian and its native lock. The review prompt and audience delivery use the selected reply contract.
A selected endpoint uses the ordinary private wrapper and endpoint identity checks; failure stays local.
It neither reconfigures the standing main service nor falls back to that service. The operator must
serialize clients of the selected endpoint; the reliability harness locks all its configured backends.
The analysis request cannot choose its reviewer.

```json
{
  "version": 1,
  "reply_format": "lines",
  "private_root": "/local-private/broker",
  "script_roots": ["/approved/frontier-scripts"],
  "inputs": {"toy": "/local-private/inputs/toy.tsv"},
  "runtimes": {
    "python": {
      "argv": ["/usr/bin/python3", "-I"],
      "read_only_roots": ["/usr", "/lib", "/lib64", "/bin"]
    }
  },
  "scribes": [4, 7],
  "max_attempts": 2,
  "agent_timeout_seconds": 180,
  "execution_timeout_seconds": 30,
  "max_input_bytes": 1048576,
  "max_output_bytes": 1048576
}
```

Configuration paths are absolute; generate them with `Path(...).expanduser().resolve()` when starting from
home-relative paths. Runtime roots must exist and must not expose the input catalog or private run tree.
Only the operator configures them; include the minimum runtime/package roots required. Avoid directories
containing credentials. The root uses mode 0700 and must not be group/world accessible. Runs and artifacts
are private, uniquely named and retained without overwriting an earlier attempt. The CLI uses umask 077.

Version 1 supports file inputs with a total snapshot size at most 1 GiB, 1 GiB execution memory and bounded
runtime/output. Larger work continues through the project's ordinary LSF reduction workflow, followed by
a broker request on the small derived files. The broker does not submit or manage jobs.

## What remains beyond the current FunGen setup

The existing setup explicitly describes its model sandbox as a cooperative precaution. This new mode
validates the review envelope and sandboxes the submitted analysis, but does not turn the entire account
into an enforced privacy boundary:

- The hosted agent must lose read access to private data, runs, logs, model histories and outputs. Mode
  0700 does not distinguish processes running as the same Unix user. Use a separate service identity or
  an equivalently enforced filesystem boundary with a narrow request interface.
- The broker's policy and implementation must be outside hosted-agent and worker write access.
- Local agent tools must be confined to their named input snapshot and own work area, without sibling
  transcripts, hosted API credentials, remote publication tools or arbitrary network connections. The
  existing Codex `network_access=false` setting alone is not verified evidence of that isolation here.
- Hosted routes must apply the existing audience rules consistently. Direct worker access must not
  bypass librarian review; existing audience modes remain intentional interfaces rather than being
  replaced by status-only replies.
- The user's viewer must be local and separate from hosted-model context. Opening an answer through a
  hosted agent's read tool would disclose it regardless of the selected return audience.

The existing policy permits model-written coding and debugging answers, and explicitly authorized
committee findings. The envelope validator enforces routing and review structure; it does not prove that
the answer text obeys the scientific-disclosure policy. That semantic judgment remains with the local
librarian, as before, and needs adversarial and held-out reliability testing. A fixed status-only return
is not the requested contract.

## Validation

Run focused tests from this checkout:

```bash
python -m pytest -q data_guard/tests/test_broker.py
BROKER_TEST_SANDBOX=1 python -m pytest -q data_guard/tests/test_broker.py
```

The latter requires host user namespaces. It executes only invented data, testing actual network and
filesystem isolation, private stdout, exceptions, symlink outputs and valid empty results. Ordinary tests
cover admission, snapshots, fixed parameter enforcement, two-worker disagreement/retry, withheld/malformed
reviews, strict JSON and private native-wrapper publication. Integration coverage checks that default
answers, `--me`, committee rules and the existing `--receipt` filter retain their return behavior. Production validation additionally
requires the permission changes above, live local-model trials and a held-out workload that measures
faithful completion, leaks, unnecessary failures, retries and end-to-end latency separately.

Current line-contract validation (9 October 2026): the complete data-guard suite passed **252 tests** with
broker sandbox integrations enabled; the complete benchmark suite passed **237 tests** with reliability
sandbox integrations enabled. Backends 4 and 9 each passed all four line binding/review protocol controls
at reasoning none and medium, with tools advertised, exact text, HTTP 200 and a completed event. Their
JSON-object failures remain reproducible on the unchanged Ollama 0.34.4 servers. The native trial is
recorded in the benchmark's `runs/native-binding-review-002` packet.

That native trial ended blocked: first-scribe prose failed the strict line keys; the bounded retry made
unsupported `read` and `shell` tool calls and also returned prose/fences/an input path. The first session
completed seven commands without bwrap or stream errors. Execution and review were not reached, so the
fixed qualification plan was not resubmitted. The live native format/tool-adherence gate remains open.

Development evidence lives in the benchmark runs. Round 001 passed 7/10 expected outcomes; round 002 retained five correct cases before a scheduled fresh-run collision. Final round 003 uses seed 61003 and native bsub -K job 274897942. The fixed setup, audience rules, attempt budget and 180-second targets remain unchanged; qualification waits for every defined development outcome.



Final development stopping point: 9/10 expected outcomes, one encoded-refusal parser failure, zero wrong releases/disclosures. Both reviewer files end at `answer:` without a newline; the current `^answer:\n` parser rejects that otherwise correct empty refusal twice. The three permitted rounds are exhausted and qualification was not submitted. The next repair is to admit the terminal empty-answer delimiter under the existing strict validation, followed by a newly authorized native development check. Stage timing and the concrete reply are recorded in the benchmark design and round-003 report.
