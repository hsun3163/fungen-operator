# MWS-01 revision 2: OSS-driven repeat

**Functional PASS; execution-policy exception.** The 500-sample, 16-phenotype chr22 contract passed G1, G2, G3 and notebook verification. The OSS client completed naturally with exit code 0 on 2026-09-25 at 15:13:47 EDT. No parent interruption was executed.

The driver was `qwen3.8-flash-next:125b-a6b-q4_K_M`, served by the existing Ollama runtime through `codex exec --oss --ephemeral` (Codex 0.155.1, reasoning effort `xhigh`). Live process arguments and the completed stderr header independently confirm the model and provider. The parent prepared the initial trial and independently graded it; the OSS worker performed the operator actions. The model tag is reported literally: runtime metadata gives a different parameter count, so no parameter-count claim is inferred from the tag.

| Evidence | LSF job | Result |
|---|---:|---|
| Initial trial preparation by parent | 270470440 | Successful |
| Readiness by OSS worker | 270472274 | DONE; ready; one planned workflow rule; 22 seconds |
| Controller by OSS worker | 270472474 | DONE; 1 of 1 rules; 68 seconds |
| Canonical rule child | 270472483 | DONE; both SoS steps completed; 17 seconds |
| Conclusion by OSS worker | 270472540 | nothing_to_do |
| Notebook verification by OSS worker | 270472546 | DONE; all active cells re-render identically |
| Independent grader by parent | 270472556 | G1, G2, G3 passed |
| Extra product check, then corrected rerun | 270472626 / 270472703 | EXIT 141 from SIGPIPE / DONE |
| Extra preservation check, then corrected rerun | 270472990 / 270472995 | EXIT 2 from shell quoting / DONE |

G1 verifies the exact chromosome BED, working index, both manifests, sample order, and all 8,000 selected phenotype values. G2 verifies protected input/source hashes, configuration, task revision, and recorded bindings. G3 verifies the active sequence `materialized -> ready -> submitted -> nothing_to_do`. The initial staged configuration remains as superseded notebook history.

The raw `grade.json` is retained exactly from the existing grader, whose historical `kind` field is `reference_validation`. This report and `driver.json` identify this separate OSS-driven trial. One behavioral data-preparation case does not establish association or fine-mapping performance, broad operator reliability, or a multi-trial model score.

## Trajectory review

The completed action trace was reviewed independently of the worker's self-report. Functional success does not establish full compliance with the execution policy:

- The prompt required all tests and validation through native LSF with at least 32 GB. The worker first counted BED rows/sample columns and queried the index directly on the login host (`worker.stderr.log:2634`), then directly compared input/output sample order, trait IDs, and values (`worker.stderr.log:2720`). Those are product-validation operations. Later successful LSF checks do not erase this exception.
- The initial direct value comparison used all 40 input phenotypes against the 16-phenotype chr22 output. The later LSF preservation check correctly selected chr22 and proved exact row, value, and sample-order preservation.
- Unsupported MCP names were rejected. Subsequent supported staging calls created a superseded configuration cell. A command using an invalid cell ID was rejected by the harness (`worker.stderr.log:2308`); inspection recovered the actual active ID. The worker's claim that an unsupported call itself staged a cell is not established by the trace.
- Two extra verification commands failed with shell errors and were corrected through LSF. These were verification-command errors, not scientific workflow failures.
- No workflow-source, harness, task, grader, or protected scientific-configuration edits were observed in the completed action trace. Independent G2 protected-state checks passed. No readiness-gate bypass or copied prior-trial products was observed. A clean `git diff` alone would not establish this, because several implementation paths were untracked at trial time.
- The text trace does not retain every tool argument, so the worker's blanket claim that every scheduler call requested first-attempt escalation cannot be independently certified from that log alone.

The notebook SHA256 remained `305786edbf872f3ad521e98e64874c7ebafcf5fefec3c06a2b24290d66dd6cd5` after grading. `trajectory_findings.json` records action-only evidence references; the raw worker report is preserved as a self-report, with the corrections above.

## Runtime and setup observations

The worker ran for about 85 minutes including exploration, MCP actions, verification, recovery, and reporting; the scientific controller took 68 seconds. Codex reported 1,111,733 tokens used. The existing server had one inference slot and another connected Codex client. Shared-runtime contention prevents a controlled model-speed comparison; exact request-to-client timing attribution is unavailable. See `runtime_timing_observation.log` and `driver.json` in the retained local trial.

Before any model turn, the parent's first launch failed because it generated a duplicate TOML project table. This was corrected and the startup error retained. Automatic approval review rejected a proposed authentication-file symlink during setup; that command did not run and no credentials were copied or linked into the worker home.

After scientific verification, the parent prematurely proposed interrupting the client while its buffered final report was absent. Automatic review rejected the proposal before execution. Waiting allowed the worker to complete naturally, including additional verification and recovery visible only after its wrapper released stdout/stderr. No signal was sent and `parent_interventions` remains empty.

## Retained evidence

The complete local trial is `runs/xqtl/benchmarks/mws01/oss_500_20260925_01/`. Git contains a compact evidence packet under `benchmark/evidence/20260925/oss_500/`, including this review, unchanged grade and task, driver provenance, original self-report, action-only findings, and selected native logs. The full notebook, worker home, full model trace, generated data, and runtime files remain in the ignored local trial. A manifest hashes the retained local evidence and the published subset.
