# Historical Evidence Extraction

## A. Source inventory

Collection was read-only. No files were modified, workflows executed, tests run, or jobs submitted.

### Source identifiers

Paths below define the source aliases used throughout this package. Notebook cell indices are **zero-based**. Session locations are physical JSONL line numbers. Session timestamps ending in `Z` are UTC; handoff dates retain their stated timezone.

| Source | Repository/path | Material inspected |
|---|---|---|
| SRC-001 | `/hpc/users/sunh14/fungen-operator` | Git history, tracked-file inventory, commit `aaa0fbb216bcd298751aead09b7bf1018d604c86`, commit `e03239133632431898c824a2d2cd77b62139a42c`; runner-directory diff between these commits |
| SRC-002 | [fungen-operator README](/hpc/users/sunh14/fungen-operator/README.md) | Lines 1–51 |
| SRC-003 | [Source manifest](/hpc/users/sunh14/fungen-operator/docs/source-manifest.tsv) | Header and first 17 file records; source paths and retained SHA-256 values |
| SRC-004 | [Archived Route3 skill](/hpc/users/sunh14/fungen-operator/archive/xqtl-route3-analysis-20260821/SKILL.md) | Lines 1–128 |
| SRC-005 | [xqtl-snakemake-analysis](/hpc/users/sunh14/fungen-operator/skills/xqtl-snakemake-analysis/SKILL.md) | Lines 1–106 |
| SRC-006 | [Archived reproducible-project-work](/hpc/users/sunh14/fungen-operator/archive/reproducible-project-work/SKILL.md) | Selected instructions, particularly lines 28–35 and 85–89 |
| SRC-007 | [Archived human-runner text](/hpc/users/sunh14/fungen-operator/archive/human-runner/SKILL.md.orig) | Difference against current retained human-runner |
| SRC-008 | [Archived snakemake-lsf-triage](/hpc/users/sunh14/fungen-operator/archive/snakemake-lsf-triage/SKILL.md) | Lines 1–123 |
| SRC-009 | [human-runner](/hpc/users/sunh14/fungen-operator/skills/human-runner/SKILL.md) | Complete 67-line file |
| SRC-010 | [xqtl-runner](/hpc/users/sunh14/fungen-operator/skills/xqtl-runner/SKILL.md) | Complete 219-line file |
| SRC-011 | [cosi-runner](/hpc/users/sunh14/fungen-operator/skills/cosi-runner/SKILL.md) | Complete 198-line file |
| SRC-012 | `fungen-operator/archive/reproducibility-reviews/{human-runner-audit-v2.md,prompt-1-surgical-edit.md,latest-response.md}` | Opening passages and keyword-matched passages; not complete documents |
| SRC-013 | `/hpc/users/sunh14/.codex/sessions/2026/08/21/rollout-2026-08-21T22-14-55-01a0273f-ea29-7312-823c-4074f06e2c29.jsonl` | User messages, final responses, retained skill text |
| SRC-014 | `/hpc/users/sunh14/.codex/sessions/2026/08/21/rollout-2026-08-21T23-25-18-01a02780-5b2a-7bf3-93c5-0cc6ccf120b3.jsonl` | Cleanup request, user corrections, deletion-command response, subsequent plan |
| SRC-015 | `/hpc/users/sunh14/.codex/sessions/2026/08/22/rollout-2026-08-22T00-31-10-01a027bc-a92b-70f3-876e-72c725f96af2.jsonl` | Selected user messages, final responses, patch calls, submission receipt, skill-validation output |
| SRC-016 | [April Route3 handoff](/sc/arion/projects/load/users/sunh14/xqtl/handoff/2026-04-18_04-41-09_mesa_route3.md) | Lines 1–60 |
| SRC-017 | [August submission handoff](/sc/arion/projects/load/users/sunh14/xqtl/handoff/2026-08-20_20-38-22_aida_mesa_submissions.md) | Lines 1–220 |
| SRC-018 | [August status handoff](/sc/arion/projects/load/users/sunh14/xqtl/handoff/2026-08-21_22-34-55_aida_mesa_status.md) | Lines 1–112 |
| SRC-019 | [August 24 handoff](/sc/arion/projects/load/users/sunh14/xqtl/handoff/2026-08-24_20-58-27.md) | Lines 1–37 |
| SRC-020 | [AIDA operator notebook](/sc/arion/projects/load/users/sunh14/xqtl/AIDA/xqtl_protocol/AIDA_operator.ipynb) | Eight-cell inventory; full submission cells 3 and 5; retained outputs |
| SRC-021 | [MESA operator notebook](/sc/arion/projects/load/users/sunh14/xqtl/MESA/xqtl_protocol/MESA_operator.ipynb) | Forty-cell inventory; selected source excerpts and submission outputs; narrative cells 14, 38, 39 |
| SRC-022 | `AIDA/xqtl_protocol/logs/aida_finemapping_top_loci.dryrun.268320039.{out,err}` | Submission header, command, completion text, dry-run output |
| SRC-023 | `AIDA/xqtl_protocol/logs/aida_finemapping_top_loci.268320057.{out,err}` | Completion text and rule-completion lines |
| SRC-024 | `/sc/arion/projects/load/users/sunh14/xqtl/xqtl-protocol` | Latest 35 commit subjects; metadata/statistics for `38ce385d`; full Snakefile diff for `f0912cfa` |
| SRC-025 | `/hpc/users/sunh14/.codex/memories/MEMORY.md` | Retrieval pointers, especially lines 665–710 and 2778–2863; used to locate original sessions |

### Inspected Git records

| Repository | Commit | Date | Commit message |
|---|---|---|---|
| fungen-operator | `aaa0fbb216bcd298751aead09b7bf1018d604c86` | 2026-09-18 14:37:42 −04:00 | `Add human, xQTL, and COSI runner skills` |
| fungen-operator | `e03239133632431898c824a2d2cd77b62139a42c` | 2026-09-20 15:00:07 −04:00 | `Combine operator skills and preserve earlier agent-control attempts` |
| xqtl-protocol | `38ce385d1487e3b86d5877a90618fb0a1d258a9e` | 2026-09-09 01:40:01 −04:00 | `Finalize shared xQTL core execution path` |
| xqtl-protocol | `f0912cfab346694fbaf21f81c293711d3de948cc` | 2026-09-09 20:54:52 −04:00 | `Remove implicit Pixi activation from shared workflow` |

The runner-directory diff between the two inspected fungen-operator commits returned no changes.

## B. Historical task records

**Field convention:** Every task has the requested fields. Fields not populated below are explicitly `UNKNOWN`: active skill/version, original request, agent plan, complete created/modified/deleted-file lists, complete executed-command list, submitted jobs, validation commands/results, recovery actions, outputs, completion claim, user feedback, subsequent action, and associated later commit. A cited handoff or agent response establishes what that source recorded; it is not relabeled as independently verified execution.

### TASK-001 — MESA Route3 VCF-QC operation

- **Period:** On or before 2026-04-18 04:41:09; timezone UNKNOWN.
- **Repository/path:** xqtl; `MESA/work/route3_rna`; `xqtl-renovated/xqtl-protocol`.
- **Request:** Handoff objective: “Run MESA RNA route3 directly, with shared genotype built once”.
- **Agent plan/instructions:** Handoff records Snakemake submitting directly to LSF, with `sos run` no longer submitting again.
- **Files modified, source-reported:** `renovated_code/script/data_preprocessing/genotype/VCF_QC.sh`; `pipeline/VCF_QC.ipynb`; `renovated_code/snakemake/route3/notebooks/VCF_QC.ipynb`; `renovated_code/notebook/route3/VCF_QC.ipynb`.
- **Commands executed:** UNKNOWN. `bash .../MESA/commands/run_mesa_rna_route3_snake_when_ready.sh` appears as a **recommended next command**, not an execution receipt.
- **Jobs:** Failed-log references include `237610259`, `237610261`.
- **Validation/results:** Handoff records `vcf_qc -> qc_3`, exit `141`; two QC VCFs remaining; `vcf_to_plink` not reached.
- **Recovery:** Source reports removal of AI-added `pipefail`; `set -eu` and fill-tags precheck remained.
- **Completion claim:** “workflow has not reached `vcf_to_plink`.”
- **User correction:** Handoff attributes a request to remove analysis-affecting AI guardrails absent from the reference notebook.
- **Evidence:** SRC-016:2–25, 33–42.

### TASK-002 — AIDA six-context script-chain submission

- **Period:** 2026-08-20 20:38 America/New_York.
- **Repository/path:** `AIDA/downstream/`.
- **Request:** Original user wording UNKNOWN.
- **Agent plan/instructions:** Six-context cis-eQTL endpoint; fixed 10 genotype PCs and 10 expression PCs, as recorded in handoff.
- **Files created/modified:** UNKNOWN; retained controller named `AIDA/downstream/submit_once_lsf.sh`.
- **Commands executed:** Exact invocation UNKNOWN; controller path recorded.
- **Jobs submitted:** `265501338`–`265501370`, 33 jobs.
- **Validation/results:** Submission acceptance only; handoff explicitly says no subsequent scheduler/status/output polling.
- **Recovery:** Controller opt-in `XQTL_ALLOW_CONTROLLER_FROM_LSF=1` added after initial controller rejection.
- **Outputs:** `AIDA/downstream/production/SUBMISSION_MANIFEST.tsv`; scientific completion UNKNOWN.
- **Completion claim:** `submission_complete jobs=33 final_job=265501370`.
- **Later change:** TASK-006 contains a request to remove this controller bundle; completed deletion UNKNOWN.
- **Evidence:** SRC-017:16–31, 90–123, 195–203.

### TASK-003 — MESA methylation script-chain submission

- **Period:** 2026-08-20–21.
- **Repository/path:** `methylation/production/mesa_c1/`.
- **Agent plan/instructions:** Annotation, race manifests, race/visit split, eight imputation branches, fan-in verifier.
- **Files created/modified:** UNKNOWN; controller `submit_mesa_c1_lsf.sh`.
- **Jobs submitted:** `265501372`–`265501383`.
- **Parameters:** `tol_missing=0.05`, soft imputation, rank 50, lambda 30, seed `20260820`.
- **Recovery:** Annotation request increased from recorded 65,536 MB to 256 GB after `TERM_MEMLIMIT`.
- **Validation/results:** Later handoff records eight imputation retries failed; zero BEDs, TBIs, and success markers in canonical imputation directories.
- **Completion claim:** Submission handoff: “Scope ends at imputation.”
- **User response:** Later handoff says imputation was outside the requested endpoint; original user message UNKNOWN.
- **Subsequent action:** Later handoff instructs not to restart without an explicit decision.
- **Evidence:** SRC-017:125–154; SRC-018:84–95.

### TASK-004 — MESA isolated fine-mapping recovery packet

- **Period:** 2026-08-20–21.
- **Repository/path:** `methylation/production/mesa_c1/rna_finemapping_recovery/`.
- **Agent plan/instructions:** Frozen-hash guard, primary non-SSC arm, SSC sensitivity arm, exact-universe/RDS validation, publication stage.
- **Controller:** `submit_isolated_packet_resume_lsf.sh`.
- **Jobs submitted:** `265501384`–`265501388`.
- **Validation specified:** Ten source hashes; region universe; saved parameters; nonempty output pairs; RDS deserialization.
- **Validation/results:** Later handoff records both analysis arms exited `1`; validation/publication did not complete.
- **Outputs:** Submission manifest recorded; `MESA_FINEMAPPING_COMPLETE` absent according to later handoff.
- **Completion claim:** Later status: “failed/incomplete”.
- **Later change:** Cleanup request in TASK-006 names seven scripts in this directory.
- **Evidence:** SRC-017:156–176; SRC-018:75–82; SRC-014:9.

### TASK-005 — Replace Route3 skill and repository instructions

- **Period:** 2026-08-22 02:15–02:42 UTC.
- **Repository/path:** Installed `.codex/skills/`; xqtl root.
- **Active skill/version:** `xqtl-route3-analysis`, then `xqtl-snakemake-analysis`; exact Git version UNKNOWN.
- **Request:** “this should be a genrice xqtl snakemake analysis, the route3 notion should be retired.”
- **Agent plan:** Inspect skill; change source authority; replace Route3-specific skill; create dataset-application policy.
- **Files created, source-reported:** `xqtl-snakemake-analysis/SKILL.md`, agent metadata, root `AGENTS.md`, instruction archives.
- **Files modified:** Earlier Route3 `SKILL.md` and `references/workflow-contract.md`.
- **Files deleted:** UNKNOWN; old skill reported archived.
- **Validation:** Agent reports `Skill is valid!`; stale-term search reported no matches.
- **Jobs:** Agent explicitly reports no Snakemake/LSF execution.
- **Outputs:** New skill and root policy; archive `archive/agent_instructions_20260821`.
- **Completion claim:** “Created the new repository policy”.
- **User corrections:** FEEDBACK-001–005.
- **Subsequent action:** Existing AIDA/MESA custom workflows reported retained as historical artifacts.
- **Evidence:** SRC-013:9, 60, 73, 146, 158, 182, 197, 264, 273, 363, 432, 618.

### TASK-006 — Custom-code cleanup and subsequent planning

- **Period:** 2026-08-22 03:25–04:23 UTC.
- **Repository/path:** AIDA, MESA, methylation application directories.
- **Active skill/version:** UNKNOWN.
- **Request:** Supplied cleanup plan; then “actually u gave me the rm command and i will do the rm”.
- **Agent plan:** Remove named controllers/helpers while preserving outputs, logs, manifests, README files, inputs, and source checkouts.
- **Files deleted:** UNKNOWN.
- **Commands executed:** Cleanup execution UNKNOWN. An exact-path `rm -f --` command was **provided** at SRC-014:202.
- **Proposed removal objects:** AIDA `run_01`–`run_13`, `common.sh`, `stage_tools.py`, two R verifiers, dataset Snakefile/profile/controller, attestation/validation scripts; MESA recovery/provenance/imputation wrappers.
- **Validation/results:** UNKNOWN.
- **User correction:** Strict `<0.70` PC selection; bounded sensitivity must stop after comparison.
- **Subsequent action:** Proposed deterministic completion plan, source base `15962dc6`.
- **Completion claim:** Final response is labeled `<proposed_plan>`, not execution completion.
- **Evidence:** SRC-014:9, 176, 191, 202, 211, 560, 607, 663.

### TASK-007 — AIDA/MESA environment and shared-workflow implementation

- **Period:** 2026-08-22–24.
- **Repository/path:** `xqtl-protocol`; branch reported `codex/deterministic-aida-mesa-completion`.
- **Active skill:** `xqtl-snakemake-analysis`, named in historical response; precise version UNKNOWN.
- **Request:** User supplied `/sc/arion/work/sunh14/conda/envs/xqtl-r-base-fsusie`, saying it “has fsusie and sesame”.
- **Agent plan/actions, source-reported:** New R, Snakemake, and Python environments; deterministic PC selection, routing, seeded steps, modality rules, sensitivity comparison.
- **Files created:** Extra lock/build artifacts reported; complete paths UNKNOWN.
- **Files modified:** Shared Snakefile/rules reported; complete list UNKNOWN.
- **Validation/results:** Agent reported new R/Snakemake environments verified; Python build failed on four HTTP 404 package artifacts; unit tests, fixture checks, dry-runs, and production targets “not run”.
- **Completion claim:** “Implementation is in progress; no production AIDA/MESA analysis has been launched.”
- **User correction:** Environment activation belongs in submission script.
- **Subsequent action:** Agent stated it would stop environment rebuilding and use supplied runtime.
- **Relevant later commit:** `f0912cfa` removes implicit Pixi activation. Explicit incident linkage UNKNOWN.
- **Evidence:** SRC-015:19, 1203, 1209, 1214, 1220, 1303; SRC-024.

### TASK-008 — AIDA checkpoint launch and concurrency changes

- **Period:** 2026-08-24 08:57–09:18 UTC.
- **Repository/path:** `AIDA/xqtl_protocol/submit_snakemake_lsf.sh`.
- **Active skill:** `xqtl-snakemake-analysis`; evolving unversioned text.
- **Request:** Complete AIDA using established infrastructure and dynamically selected genotype PCs; retained goal text at SRC-015:1312.
- **Agent plan:** `sample_qc_pca`, then `covariate_prep`, then association.
- **Command setting:** `--cores 1`, reported at launcher line 107.
- **Jobs:** Controller `266446197`; nested examples `266447431`, `266447538`.
- **Validation/results:** Historical agent reports effective fan-out `1`; PCA checkpoint still running.
- **Completion claim:** “Yes—operationally normal now.” Subsequently: “Effective fan-out is **1**”.
- **User corrections:** Asked why sequential, why not run to endpoint; requested mandatory concurrent independent jobs.
- **Subsequent action:** Skill patches for endpoint selection, fan-out, mandatory wording, and LSF validation.
- **Evidence:** SRC-015:3351–3782.

### TASK-009 — AIDA second-fit addition, revert, and resubmission

- **Period:** 2026-08-24 10:51 UTC–2026-08-25 00:32 UTC.
- **Repository/path:** `xqtl-protocol`; `AIDA/work/xqtl_protocol_rna_pve70`.
- **Active skill:** `xqtl-snakemake-analysis`; exact version UNKNOWN.
- **Request:** Ongoing AIDA completion; later explicit notebook revert and “stop and resubmit”.
- **Files modified:** `pipeline/mnm_regression.ipynb` / canonical `code/SoS/mnm_analysis/mnm_methods/mnm_regression.ipynb`; `code/script/pecotmr_integration/twas_weights.R`; `code/snakemake/rules/06_univariate_finemapping.smk`; two test files.
- **Change:** Added second TWAS-aligned SuSiE output and `--align-phenotype-samples`; later removed them.
- **Commands executed:** Retained patch calls; restart command:

  ```bash
  bash /sc/arion/projects/load/users/sunh14/xqtl/AIDA/xqtl_protocol/submit_snakemake_lsf.sh aida_onefit_resume xqtl_core
  ```

- **Jobs:** Historical controller `266530085`; fresh receipt `266584209`.
- **Validation:** Revert response says “No test was run”; source inspection and `git diff --check` call retained at SRC-015:10087.
- **Results:** Historical response records removed-flag errors and `0/6` final markers.
- **Recovery:** Agent reports stopping controller, six context jobs, and 2,725 remaining children; non-forceful resubmission.
- **Outputs:** Agent reports 25,007 primary SuSiE, 24,898 TWAS-aligned intermediates, 19,954 TWAS weights across 55,217 inputs.
- **Completion claim:** New controller reported `RUN`; no final endpoint completion claim.
- **User corrections:** FEEDBACK-012–014.
- **Subsequent action:** TASK-010 skill update.
- **Evidence:** SRC-015:6298, 6529, 9944–10182, 11026–11233; SRC-019:10–17.

### TASK-010 — Update xqtl skill after AIDA discussion

- **Period:** 2026-08-25 00:39–00:45 UTC.
- **Repository/path:** Installed `xqtl-snakemake-analysis`.
- **Request:** “good update the xqtl skill with these rule, if those rules are not redundent”.
- **Files modified:** `SKILL.md`; full metadata-change list UNKNOWN.
- **Change:** Scientific semantics, materialized-task handling, runtime ownership, queue defaults, non-forceful reuse, descendant termination, aggregate reporting.
- **Validation command:**

  ```bash
  /sc/arion/work/sunh14/conda/envs/xqtl-reno/bin/python \
    /sc/arion/projects/load/users/sunh14/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
    /sc/arion/projects/load/users/sunh14/.codex/skills/xqtl-snakemake-analysis
  ```

- **Jobs:** `266585893`, express, requested 32,768 MB.
- **Validation results:** Retained scheduler output: `Successfully completed.` and `Skill is valid!`.
- **Completion claim:** “Updated … with the seven non-redundant rules”.
- **Evidence:** SRC-015:11294, 11300, 11321–11396.

### TASK-011 — AIDA top-loci export

- **Period:** Dry-run submitted 2026-09-07 17:53:58, scheduler timezone unspecified.
- **Repository/path:** AIDA operator notebook; `AIDA/work/xqtl_protocol_rna_pve70`.
- **Active skill/version:** UNKNOWN.
- **Request/agent plan:** Original request UNKNOWN; notebook target `finemapping_top_loci`.
- **Files modified:** UNKNOWN.
- **Command:** SRC-020 cells 3/5 invoke shared Snakefile, generated AIDA YAML, shared LSF profile, `--cores 72 --jobs 6 finemapping_top_loci`; cell 3 adds `--dry-run`.
- **Runtime sequence:** Source `activate_local_pixi.sh`; activate `xqtl-r-base-fsusie`; invoke `xqtl-reno/bin/snakemake`.
- **Jobs:** Dry-run `268320039`; production `268320057`.
- **Validation:** Dry-run log says `Successfully completed.` and `This was a dry-run`.
- **Results:** Production stderr: `7 of 7 steps (100%) done`; stdout: `Successfully completed.`
- **Outputs:** Notebook describes `finemapping/top_loci/`; individual products not inspected.
- **Completion claim:** Native workflow completion text only; original conversational claim UNKNOWN.
- **Evidence:** SRC-020 cells 2–5; SRC-022:38,42,167; SRC-023 stderr:100–129.

### TASK-012 — MESA six-context submissions and supervisor resumes

- **Period:** Exact execution dates UNKNOWN; retained notebook inspected 2026-09-20.
- **Repository/path:** `MESA_rerun`; MESA operator notebook.
- **Active skill/version:** UNKNOWN.
- **Request:** Original message UNKNOWN; notebook specifies six 13-PC analyses through `xqtl_core`.
- **Files created/modified:** Six YAMLs reported in cell 4 output; genotype symlinks reported in cell 2.
- **Jobs:** Initial dry-runs `268710612`–`268710617`; initial production `268710618`–`268710623`; subsequent receipts listed in EVENT-025–027.
- **Validation/results:** Cell 9 prints selected rule sets from six dry-run logs.
- **Recovery:** Notebook records supervisor express walltime expiry, premium resubmission, then explicit `runtime144h` resubmission.
- **Outputs:** Current scientific products not inspected.
- **Completion claim:** UNKNOWN.
- **Evidence:** SRC-021 cells 0,2,4,8,9,11,14–19.

### TASK-013 — MESA methylation recovery and config restoration

- **Period:** On/before 2026-09-20; exact edit time UNKNOWN.
- **Repository/path:** MESA operator notebook and methylation config.
- **Active skill/version:** UNKNOWN.
- **Request:** Original recovery request UNKNOWN.
- **Files modified:** Config reported overwritten and restored; exact config pathname not extracted.
- **Jobs:** Initial dry-run/production `269821829`/`269821833`; recovery dry-run `269824453`; retry `269824457`; production `269824467`.
- **Validation/results:** Notebook narrative says first recovery dry-run failed; retry passed with 51 steps.
- **Recovery:** Re-executed retained generation cell and Black-stratum override.
- **Completion claim:** “Native extrapolate=False recovery remains unverified until real backfit completes.”
- **User response:** Notebook records 2026-09-20 decision to exclude both Black strata if current retry fails; preserve files; no further rank changes or Black retries.
- **Evidence:** SRC-021 cells 30–39.

### TASK-014 — fungen-operator history import

- **Period:** 2026-09-18 and 2026-09-20.
- **Repository/path:** fungen-operator.
- **Request/active skill/agent plan:** UNKNOWN.
- **Commits:** SRC-001.
- **Files created:** First commit adds three runner skill directories and supporting files. Second adds archived materials, additional skills, and source manifest; Git stat reports 70 changed files, 6,360 insertions, 12 deletions.
- **Files modified:** README and `.gitignore` among second-commit changes.
- **Commands executed/jobs/validation:** UNKNOWN.
- **Outputs:** Committed skill collection and archive.
- **Claim:** README: “Imported files are preserved byte-for-byte.”
- **Independent hash verification:** Not performed during this extraction.
- **Evidence:** SRC-001; SRC-002:5,31–39,49–51.

## C. Extracted behavior events

**Schema:** Each row inherits `timestamp/period`, `skill/version`, and repository from its task unless overridden. `commit/hash` is `UNKNOWN` unless stated. `validation_performed`, `user_response`, and `subsequent_action` are `UNKNOWN` unless stated in the row or its explicit linked record. “Reported” denotes a historical statement; it is not an independent confirmation.

| event_id | task_record_id | Type / actor | Action; object/path; command/change | Before → after / result | Validation; user response; subsequent action | Source and short verbatim excerpt |
|---|---|---|---|---|---|---|
| EVENT-001 | TASK-001 | Execution-interface change / agent, handoff attribution | Route3 submission moved to Snakemake-to-LSF | Handoff says SoS no longer submits again | Validation UNKNOWN | SRC-016:12: “Snakemake submits route3 jobs directly to LSF and `sos run` no longer submits again.” |
| EVENT-002 | TASK-001 | Manual removal / agent, handoff attribution | Removed `pipefail` from four VCF-QC paths | Added strictness reported → removed; later exit 141 still recorded | User objection attributed in handoff | SRC-016:17: “Removed AI-added `pipefail` behavior … after user objection” |
| EVENT-003 | TASK-002 | Script-chain submission / agent, handoff attribution | `AIDA/downstream/submit_once_lsf.sh`; 33 jobs | Accepted through final verifier `265501370`; completion UNKNOWN | Acceptance only | SRC-017:104–115: “Accepted graph: 33 jobs” |
| EVENT-004 | TASK-002 | Guard modification / agent, handoff attribution | Added `XQTL_ALLOW_CONTROLLER_FROM_LSF=1` opt-in | Controller rejected before `bsub` → rerun recorded using opt-in | Scientific execution UNKNOWN | SRC-017:197–203: “submission controller must run on the submit host, not inside an LSF worker” |
| EVENT-005 | TASK-003 | Wrapper/fan-in submission / agent, handoff attribution | Eight `bed_filter_na` branches plus imputation verifier | Jobs `265501375`–`265501383` recorded | Acceptance only | SRC-017:136–147: “imputation fan-in verifier” |
| EVENT-006 | TASK-003 | Resource retry / agent, handoff attribution | Annotation memory increased to 256 GB | Prior `TERM_MEMLIMIT`, 65,536 MB → 262,144 MB request | Scheduler values quoted in handoff | SRC-017:139–143 |
| EVENT-007 | TASK-003 | Execution error / wrapper, handoff attribution | `run_bed_filter_na_branch.sh`, line 55; job `265594207` | Nested output path reported; wrapper syntax error; eight retries failed | Canonical output counts reported zero | SRC-018:93–94: “syntax error near unexpected token 'done'” |
| EVENT-008 | TASK-004 | Guard/validation machinery / agent, handoff attribution | Frozen-hash guard, validation job, publication job | Five-job packet submitted; later arms exited 1 | Validation/publication not complete | SRC-017:164–172: “The guard checks ten frozen source hashes.” |
| EVENT-009 | TASK-005 | User scope correction / user | Requested skill contents rather than audit | Agent reports read-only inspection | Subsequent source-authority edit | SRC-013:60: “no dont audit, just tell me what was in it” |
| EVENT-010 | TASK-005 | Source-authority change / agent | Route3 skill and workflow contract | Legacy checkout authority → `./xqtl-protocol` | Agent reports `Skill is valid!` | SRC-013:73,146 |
| EVENT-011 | TASK-005 | Skill replacement / agent | Archive Route3 skill; add generic skill | Route3 scanner/ledger guidance → generic Snakemake skill | Agent reports validation; no jobs | SRC-013:264: “No broad gates, evidence ledgers, completion verifiers, or safeguard wrappers.” |
| EVENT-012 | TASK-005 | Repository-policy creation / agent | Root `AGENTS.md`; archive old policies | New shared-Snakefile policy reported | Custom workflows explicitly retained | SRC-013:618: “they were not deleted or migrated.” |
| EVENT-013 | TASK-006 | Removal command supplied / agent | Exact-path `rm -f --` list | Actual deletion UNKNOWN | User said they would execute deletion | SRC-014:191,202: “i will do the rm” |
| EVENT-014 | TASK-006 | Parameter correction / user | Genotype PC selection | User rejects prior selection; requests `<70` | Later plan adopts strict `<0.70` | SRC-014:560: “that is not what i have selected, it should use the <70” |
| EVENT-015 | TASK-006 | Scope stop / user | Single-context sensitivity | Wider rerun conditional → stop after report/comparison | Implementation at this point UNKNOWN | SRC-014:607: “dont restart the rest until i said so” |
| EVENT-016 | TASK-007 | Environment creation / agent, self-report | Repository-local environments and lock/build artifacts | Supplied runtime existed → new builds pursued | Python build reported HTTP 404; tests/dry-runs not run | SRC-015:1214: “I instead pursued unnecessary repository-local environment rebuilding.” |
| EVENT-017 | TASK-007 | Runtime placement / agent, self-report | Snakefile environment activation | Added activation/selection logic reported | User requested activation in submission script | SRC-015:1303: “I added environment selection and activation logic to the Snakefile.” |
| EVENT-018 | TASK-008 | Concurrency setting / agent, self-report | Launcher `--cores 1` | Six contexts processed sequentially | Agent reports effective fan-out 1 | SRC-015:3404: “I set `--cores 1` … by copying the conservative examples” |
| EVENT-019 | TASK-008 | Intermediate-target launch / agent, self-report | `sample_qc_pca` | Controller stops after PCA | User asks why not endpoint | SRC-015:3472: “explicitly launched with the narrow `sample_qc_pca` target” |
| EVENT-020 | TASK-009 | Model/output addition / agent patch | `mnm_regression.ipynb`, 2026-08-24 10:51:46Z | Primary fit reused → additional `twas_fine_mapping` output and second fit | Tool response `{}`; later agent confirms introduction | SRC-015:6298,6300: “a second SuSiE fit … built on that exact TWAS design” |
| EVENT-021 | TASK-009 | Sample-handling option addition / agent patch | `twas_weights.R`, 2026-08-24 10:59:55Z | Added `--align-phenotype-samples`, residual-phenotype sample handling | Validation UNKNOWN | SRC-015:6529: `parser <- add_argument(parser, "--align-phenotype-samples",` |
| EVENT-022 | TASK-009 | Scientific-source revert / agent | Notebook, rule, worker, tests | Second-fit/flag implementation → one-fit source reported | “No test was run”; source inspection and diff-check call retained | SRC-015:10171: “The source is reverted … the live runner is not.” |
| EVENT-023 | TASK-009 | Materialized-command error / historical child jobs | Removed `--align-phenotype-samples` still in submitted commands | Source reverted while old commands retained; failures reported | Representative error quoted by agent; underlying stderr not separately opened | SRC-015:11044: “Argument '--align-phenotype-samples' is not a defined optional argument or flag” |
| EVENT-024 | TASK-009 | Termination/resubmission / agent | `aida_onefit_resume xqtl_core` | Agent reports 2,725 children stopped; receipt for `266584209` | Tool result exit 0; new premium submission | SRC-015:11222: “Job <266584209> is submitted to queue <premium>.” |
| EVENT-025 | TASK-012 | Dry-run and production submissions / notebook execution | MESA cells 8/11 | Six dry-run receipts; six production receipts | Cell 9 prints selected rule sets | SRC-021 cells 8–11: “Job <268710618> is submitted to queue <premium>.” |
| EVENT-026 | TASK-012 | Supervisor queue/runtime retry / notebook execution | Cells 15/16 | Dry-runs `269240174,176,177,178,179,180`; production `269240181,183,184,185,186,187` | Notebook describes prior 12-hour express expiry | SRC-021 cell 14: “supervisor rules reached the 12-hour `express` limit” |
| EVENT-027 | TASK-012 | Explicit-runtime retry / notebook execution | Cells 18/19, names contain `runtime144h` | Dry-runs `269282289,294,303,305,313,317`; production `269285494,497,504,507,508,515` | Runtime rendering not independently extracted here | SRC-021 cells 18–19, retained receipts |
| EVENT-028 | TASK-011 | Mixed runtime command / notebook execution | Cells 3/5 | Pixi activation, conda activation, `xqtl-reno/bin/snakemake` in same cell | Native dry-run/production logs completed | SRC-020 cells 3/5: `source .../activate_local_pixi.sh` |
| EVENT-029 | TASK-011 | Workflow completion record / Snakemake and LSF logs | `finemapping_top_loci`, job `268320057` | Six exports and aggregate rule reported finished | Individual products not inspected | SRC-023 stderr:129: “7 of 7 steps (100%) done” |
| EVENT-030 | TASK-013 | Config overwrite/restoration / agent, notebook attribution | Methylation config, exact pathname UNKNOWN | Config overwritten → restored from generation cell and override | Narrative says failed dry-run then passing retry | SRC-021 cell 38: “config was accidentally overwritten during notebook editing” |
| EVENT-031 | TASK-013 | Retry scope limitation / user, notebook attribution | Both MESA Black methylation strata | Conditional exclusion if retry fails | Current outcome UNKNOWN | SRC-021 cell 39: “do not attempt further rank changes or Black retries” |
| EVENT-032 | TASK-010 | Skill validation job / agent and LSF output | `quick_validate.py`, job `266585893` | Skill patch → validation DONE | 32,768 MB request; `Skill is valid!` | SRC-015:11385,11391 |
| EVENT-033 | TASK-007 | Later workflow change / Git author attribution | Snakefile; `f0912cfa`, 2026-09-09 | Removed implicit Pixi activation block | Tests for this commit UNKNOWN; earlier-incident linkage UNKNOWN | SRC-024 diff: removed `USE_LOCAL_PIXI = bool(config.get("activate_local_pixi", True))` |
| EVENT-034 | TASK-014 | Historical-material import / Git author attribution | fungen-operator; `e032391` | Archive/support skill files added | Byte-preservation is README claim; hashes not rechecked | SRC-001 commit message: “preserve earlier agent-control attempts” |
| EVENT-035 | TASK-009 | Status inspection feedback / user | Per-gene status checking | User requests aggregate counts | Agent gives aggregate totals | SRC-015:11028: “you dont need to check for all the sinle genes” |
| EVENT-036 | TASK-009 | Redundant-check acknowledgment / agent | Pending scientific-setting response | Agent says it was waiting on redundant check | Later AGENTS edits reported | SRC-015:10814: “Nothing necessary—I was waiting on a redundant check.” |

## D. User corrections and feedback

Quotes preserve original spelling. Handoff-attributed statements are identified separately from direct user messages.

| feedback_id | Task/event | Date/time | Verbatim evidence | Source |
|---|---|---|---|---|
| FEEDBACK-001 | TASK-005 / EVENT-009 | 2026-08-22 02:16:49Z | “no dont audit, just tell me what was in it” | SRC-013:60 |
| FEEDBACK-002 | TASK-005 / EVENT-010 | 2026-08-22 02:17:45Z | “now the source of truth is ./xqtl-protocol” | SRC-013:73 |
| FEEDBACK-003 | TASK-005 / EVENT-011 | 2026-08-22 02:22:22Z | “the route3 notion should be retired.” | SRC-013:158 |
| FEEDBACK-004 | TASK-005 / EVENT-011 | 2026-08-22 02:23:15Z | “there should not be any over engineered gate, verifier, safeguard and such” | SRC-013:182 |
| FEEDBACK-005 | TASK-005 / EVENT-012 | 2026-08-22 02:31:53Z | “the thing i hate the most is that it keep overengineered, and then deviate from the xqtl-protocol snakemake framework.” | SRC-013:363 |
| FEEDBACK-006 | TASK-005 / EVENT-012 | 2026-08-22 02:34:17Z | “each should not have their own project specific snakefile” | SRC-013:432 |
| FEEDBACK-007 | TASK-006 / EVENT-013 | 2026-08-22 03:34:23Z | “actually u gave me the rm command and i will do the rm” | SRC-014:191 |
| FEEDBACK-008 | TASK-006 | 2026-08-22 03:39:02Z | “with all these trash gone, plan again” | SRC-014:211; deletion verification UNKNOWN |
| FEEDBACK-009 | TASK-006 / EVENT-014 | 2026-08-22 04:13:54Z | “that is not what i have selected, it should use the <70” | SRC-014:560 |
| FEEDBACK-010 | TASK-007 / EVENT-017 | 2026-08-24 00:45:10Z | “the invokayion of the env should be part of the suvmission script, not the snakefile” | SRC-015:1220 |
| FEEDBACK-011 | TASK-008 / EVENT-018 | 2026-08-24 09:00:20Z | “why did u run them sequentially, isnt it my instruction that things should be faned out?” | SRC-015:3389 |
| FEEDBACK-012 | TASK-009 / EVENT-022 | 2026-08-24 22:09:11Z | “i want the notebook revert to the faithful state” | SRC-015:9944 |
| FEEDBACK-013 | TASK-009 / EVENT-020 | 2026-08-24 22:41:13Z | “so just to be clear, YOU introduce the problemetic 2 step process” | SRC-015:10177 |
| FEEDBACK-014 | TASK-009 / EVENT-023 | 2026-08-25 00:24:28Z | “so this probem is due to u messing with the notebook” | SRC-015:11050 |
| FEEDBACK-015 | TASK-009 / EVENT-024 | 2026-08-25 00:25:27Z | “stop and resubmit” | SRC-015:11073 |
| FEEDBACK-016 | TASK-009 / EVENT-036 | 2026-08-24 23:42:21Z | “dont keep polling for agent activity, adn dont initial redundant check, those burn token without any good reason” | SRC-015:10820 |
| FEEDBACK-017 | TASK-009 / EVENT-035 | 2026-08-25 00:23:09Z | “just tell me howmany are done how many fails” | SRC-015:11028 |
| FEEDBACK-018 | TASK-008 | 2026-08-24 09:07:53Z | “alwayse aimed at the real endpoint unless explocitu instruct” | SRC-015:3499 |
| FEEDBACK-019 | TASK-008 | 2026-08-24 09:11:05Z | “Single-threaded deterministic jobs may run concurrently, not may, must” | SRC-015:3581 |
| FEEDBACK-020 | TASK-008 | 2026-08-24 09:16:56Z | “anytesting should be done through an lsf jobd, not locally” | SRC-015:3735 |
| FEEDBACK-021 | TASK-009 | 2026-08-24 16:21:14Z | “lets still use -1 the one that are faitful.” | SRC-015:7416; original introduction of 5,000 cap UNKNOWN |
| FEEDBACK-022 | TASK-009 | 2026-08-24 18:44:38Z | “change the config such that all future substask request 12hr and aimed for the express queue” | SRC-015:8837 |
| FEEDBACK-023 | TASK-001 | By 2026-04-18 | Handoff attribution: “if an analysis-affecting guardrail was introduced by AI and is not in the truth notebook, remove it.” | SRC-016:40; original user message UNKNOWN |

The literal term `slop` returned no matches in the inspected handoff directory and three archived review documents. Direct user descriptions recovered here include “overengineered,” “ad hoc script,” and “trash.” These are retained as source wording, without assigning those descriptions to other artifacts.

## E. Skill-version changes

### Chronological changes with session evidence

`commit/hash = UNKNOWN` for installed-skill edits unless stated. A later import commit does not establish the original edit date.

| skillchange_id | Skill/version and date | Added / removed / modified instruction | Relevant diff or exact excerpt | Explicit associated request | Evidence |
|---|---|---|---|---|---|
| SKILLCHANGE-001 | `xqtl-route3-analysis`; 2026-08-22 02:17–02:20Z | Modified source authority | Legacy checkout → “`./xqtl-protocol/` is the scientific semantic source of truth.” | User source-authority correction | SRC-013:73,146 |
| SKILLCHANGE-002 | Route3 → `xqtl-snakemake-analysis`; 2026-08-22 02:22–02:26Z | Generic skill introduced; old skill archived | Agent reports “No Route3/MESA terminology or specialized auditor.” | FEEDBACK-003/004 | SRC-013:158,182,264 |
| SKILLCHANGE-003 | `xqtl-snakemake-analysis`; same period | Added memory instruction | “strictly more than 30 GB”; then reported minimum 31 GB for integer settings | User: “every submitted task should be larger than 30G” | SRC-013:197,264 |
| SKILLCHANGE-004 | `xqtl-snakemake-analysis`; 2026-08-24 09:08:38Z | Added endpoint section; modified run/resume text | `+ ... targeting the real scientific endpoint by default.` | FEEDBACK-018 | SRC-015:3521 |
| SKILLCHANGE-005 | Skill agent metadata; 2026-08-24 09:08:48Z | Modified default prompt | Added “launching the furthest authorized scientific endpoint by default.” | Same endpoint request | SRC-015:3527 |
| SKILLCHANGE-006 | `xqtl-snakemake-analysis`; 2026-08-24 09:10:00Z | Added fan-out section | `+ Do not set the controller to --cores 1 merely because individual numerical jobs use one thread.` | User fan-out request | SRC-015:3562 |
| SKILLCHANGE-007 | Same; 2026-08-24 09:11:18Z | Modified permissive concurrency wording | `- ... allowing many independent one-thread jobs ...` / `+ Independent one-thread jobs must run concurrently whenever the DAG permits.` | FEEDBACK-019 | SRC-015:3593 |
| SKILLCHANGE-008 | Same; 2026-08-24 09:17:49Z | Added validation section | `+ Run every test and validation command through an LSF job, never in the local or foreground session.` | FEEDBACK-020 | SRC-015:3782 |
| SKILLCHANGE-009 | Same; 2026-08-25 00:43:39Z | Added scientific-semantics section | “Do not silently change the number of model fits, filtering population, variant filters, residualization or scaling…” | User accepted proposed seven-rule update | SRC-015:11300,11321; SRC-005:37–42 |
| SKILLCHANGE-010 | Same; same patch | Added production-contract section | “Treat generated SoS task commands as snapshots…” | Same explicit update request | SRC-015:11321; SRC-005:44–48 |
| SKILLCHANGE-011 | Same; same update | Added runtime and queue instructions | Runtime in thin launcher/nested template; eligible nested work express/12h | Same explicit update request | SRC-015:11396; SRC-005:66–68 |
| SKILLCHANGE-012 | Same; same update | Added reuse/termination instructions | “default nested execution to non-forceful reuse”; exact descendants; no broad name kill | Same explicit update request | SRC-015:11396; SRC-005:94–96 |
| SKILLCHANGE-013 | Same; same update | Added aggregate-reporting instruction | “Inspect one representative decisive stderr for each distinct failure signature rather than every feature.” | Same explicit update request | SRC-015:11396; SRC-005:106 |

### Retained snapshots and imports

| skillchange_id | Skill/version | Date / commit | Instruction or change observed | Earlier version / removal / incident |
|---|---|---|---|---|
| SKILLCHANGE-014 | Archived `reproducible-project-work` | Import 2026-09-20, `e032391`; original date UNKNOWN | R04 requires adding environment spec, canonical program, smoke config, commands, submission file, runbook, decision log, handoff, remote history protection when absent | Prior version and associated incident UNKNOWN. SRC-006:33 |
| SKILLCHANGE-015 | Same | Same | R06: “Do not validate a dirty working tree.” | Prior version and incident UNKNOWN. SRC-006:35 |
| SKILLCHANGE-016 | Archived Route3 skill | Import `e032391`; retirement directory dated 20260821 | “run the bundled read-only scanner first when a Route3 work root exists”; includes evidence-ledger section | A prescribed rule, not proof it was executed. SRC-004:41–61 |
| SKILLCHANGE-017 | Archived `snakemake-lsf-triage` | Import `e032391`; original edit dates UNKNOWN | Explicit runtime example `runtime=144h`, required render `runtime=8640` | Associated original edit/session UNKNOWN. SRC-008:61,103–105 |
| SKILLCHANGE-018 | Archived/current `human-runner` snapshot comparison | Change date UNKNOWN | Seven-line LSF fan-out paragraph replaced with four-line paragraph beginning “Use the project's existing LSF infrastructure…” | Direct file diff observed; deployment chronology and incident UNKNOWN. SRC-007 versus SRC-009:35–38 |
| SKILLCHANGE-019 | `human-runner`, `xqtl-runner`, `cosi-runner` | 2026-09-18, `aaa0fbb` | Three skill directories added to Git | Original installed histories UNKNOWN. Commit message: `Add human, xQTL, and COSI runner skills` |
| SKILLCHANGE-020 | Same three runners | 2026-09-20, `e032391` | No changes returned by directory diff against `aaa0fbb` | No rule-change event inferred |
| SKILLCHANGE-021 | Additional support/domain skills | 2026-09-20, `e032391` | Git adds the 16 skill directories listed below | Original authorship dates, earlier versions, and associated incidents UNKNOWN |

The 16 imported skill names for SKILLCHANGE-021 are:

`cosi-locus-case-study`, `cosi-locus-zoom`, `cosi-notebook`, `cosi-run`, `cosi-sketch-ld`, `cosi-weight-scan`, `cosi-workflow-edit`, `debug-pipeline`, `intact-gene-query`, `lsf-queue-move`, `record-handoff`, `snakemake-sos-parser`, `sos-status-sampler`, `sumstat-munger`, `todoist-task-completion`, `xqtl-snakemake-analysis`.

Their addition is established by Git inventory. Their complete original instruction histories were not recovered.

### Archived review records

These are retained review text, not execution incidents:

| Record | Source wording | Provenance |
|---|---|---|
| REVIEW-001 | “Audit date: 2026-08-26”; “This audit does not propose a replacement skill.” | SRC-012, `human-runner-audit-v2.md`:1–11 |
| REVIEW-002 | “Apply only the replacements below to Prompt 1. Leave all omitted text unchanged.” | SRC-012, `prompt-1-surgical-edit.md`:1–5 |
| REVIEW-003 | “I did not overwrite the directory: it is not under version control…” | SRC-012, `latest-response.md`:5 |
| REVIEW-004 | “Verdict: fail.” | SRC-012, `latest-response.md`:1; historical reviewer judgment, not this extraction’s judgment |

For these records, original task/session, reviewer identity, actual application of proposed text, and incident linkage are `UNKNOWN`.

## F. Current runner controls

Snapshot: fungen-operator `e032391`; runner text unchanged from `aaa0fbb`.

**Mechanical field convention:** `UNKNOWN` means the cited passage does not state a separate requirement. “Permission” and “user clarification” are not inferred from prohibitions. Each row supplies trigger, allowed action, forbidden action, validation, stop condition, clarification, and evidence through the columns below.

### human-runner

| control_id | Exact/near-exact instruction | Trigger; allowed action | Forbidden action | Required validation | Stop / clarification | Evidence |
|---|---|---|---|---|---|---|
| CONTROL-001 | “Keep one operating path.” | Adding mechanism: add only when existing path lacks behavior and addition removes more complexity than it creates | Addition failing that condition | UNKNOWN | Stop UNKNOWN; clarification UNKNOWN | SRC-009:21–23 |
| CONTROL-002 | Read commands, configuration, workflows, history before creating a new pattern | New pattern; use ordinary tool/language convention when no precedent | UNKNOWN | Read existing project material | UNKNOWN / UNKNOWN | SRC-009:28–30 |
| CONTROL-003 | A result built on becomes kept work; redo through project path | Exploration adopted into kept work | UNKNOWN | Kept work meets Trail | UNKNOWN / UNKNOWN | SRC-009:31–34 |
| CONTROL-004 | Submit every runnable independent unit as a separate LSF job | Existing LSF infrastructure; expose available parallelism | UNKNOWN | UNKNOWN | DAG/scheduler admission controls; clarification UNKNOWN | SRC-009:35–38 |
| CONTROL-005 | “Completion and result are separate facts” | Finished job; inspect output | UNKNOWN | Check output | UNKNOWN / UNKNOWN | SRC-009:39–40 |
| CONTROL-006 | Declared inputs/outputs, exit status, user criteria form pass/fail contract | Additional checks allowed as native-log diagnostics | Additional checks controlling status/control flow | Declared contract | UNKNOWN / UNKNOWN | SRC-009:41–43 |
| CONTROL-007 | Use a live native query for current status | Status report | UNKNOWN | Native status query | Give restart point if work remains | SRC-009:44–45 |
| CONTROL-008 | Stop polling after stable accepted job/agent state | Normally PEND/RUN; check again at requested checkpoint/new evidence | Repeated status calls merely observing no change | Native stable-state observation | Stop polling; monitoring may be user-requested | SRC-009:46–51 |
| CONTROL-009 | Submission scripts contain directives, environment, native invocation/arguments | Submission script | UNKNOWN | UNKNOWN | UNKNOWN / UNKNOWN | SRC-009:60–62 |

### xqtl-runner

| control_id | Exact/near-exact instruction | Trigger; allowed action | Forbidden action | Required validation | Stop / clarification | Evidence |
|---|---|---|---|---|---|---|
| CONTROL-010 | Use repository-local canonical workflow; dataset choices in YAML | Dataset operation; shared-code edit when decisive evidence shows defect | Dataset Snakefiles, copied rules, custom controllers, stage chains | Read AGENTS and canonical sources | UNKNOWN / UNKNOWN | SRC-010:18–26 |
| CONTROL-011 | Copy template once; reuse same operator notebook | Dataset lifecycle | Separate phase/retry notebooks; direct production from template | Replace every dataset-specific template value before execution | Before replacement, no execution; clarification UNKNOWN | SRC-010:35–41 |
| CONTROL-012 | Execute every dry-run/production submission from visible notebook cell | Kept submission | External-shell retained submission | Save acknowledgment and job ID in executed notebook | UNKNOWN / UNKNOWN | SRC-010:47–61 |
| CONTROL-013 | Complete command in production cell | Production | `bsub <wrapper-script>` replacing command | Command visible | UNKNOWN / UNKNOWN | SRC-010:73–96 |
| CONTROL-014 | Activate `xqtl-r-base-fsusie` directly | Retained Minerva submission | Pixi activation/PATH, relocated Pixi `sos_bin`, mixed fallback runtime | Verified shared contract required for explicit executable overrides | UNKNOWN / UNKNOWN | SRC-010:67–71 |
| CONTROL-015 | One canonical-style YAML per output graph | Distinct modality/consent graph | Parallel config format | Preserve canonical keys/types/defaults; YAML inspectable in notebook | UNKNOWN / UNKNOWN | SRC-010:100–108 |
| CONTROL-016 | Neutral genotype location per dataset/consent group | Cohort genotype preparation | Copy/recompute cohort outputs; modality ownership | Record symlink commands before dry-run | Finish genotype writer before another production writer | SRC-010:112–123 |
| CONTROL-017 | “Do not submit production after a failed dry-run.” | Production and execution-affecting changes | Production before successful exact-graph dry-run | Same YAML, Snakefile, directory, target, profile, environment/options; repeat after listed changes | Production blocked until success | SRC-010:137–143 |
| CONTROL-018 | Run to furthest authorized endpoint | Run/resume/finish request | Method change, other graph/dataset, destructive cleanup, approval bypass | Dry-run after repair | Explicit user stop defines endpoint | SRC-010:147–155 |
| CONTROL-019 | Preserve scientific semantics | Workflow operation | Improvised replacement analysis or unrequested changes to listed scientific settings | Canonical sources authoritative | User must explicitly change scientific request | SRC-010:159–163 |
| CONTROL-020 | Finalize contract before fan-out | Materialized SoS tasks invalidated by authorized change | Mixed task generations | UNKNOWN | Stop affected graph and resubmit | SRC-010:165–167 |
| CONTROL-021 | Host execution; at least 32 GB outer and child requests | Every submission | Foreground memory-heavy work | Set both outer/nested memory | UNKNOWN / UNKNOWN | SRC-010:171–173,179 |
| CONTROL-022 | Premium controller/rules; express SoS tasks | Queue routing | Rule-local `bsub`, per-rule queue override, queue/runtime `--set-resources` routing | Shared profile/host settings | UNKNOWN / UNKNOWN | SRC-010:174–178 |
| CONTROL-023 | One controller per graph; expose independent DAG branches | Fan-out | Extra controllers, copied rules, manual partition, DAG redesign for concurrency | Preserve rule threads/resources | UNKNOWN / UNKNOWN | SRC-010:180–187 |
| CONTROL-024 | Capture exact invocation/config/target/rule/first error | Failure | Dataset-specific alternative route | Inspect child layer only if rule launches it | Resume authorized endpoint after narrow repair | SRC-010:191–196 |
| CONTROL-025 | Preserve valid outputs; native non-forceful reuse | Restart | Deleting outputs to restart; competing controllers | Force only confirmed-invalidated outputs | UNKNOWN / UNKNOWN | SRC-010:198–200 |
| CONTROL-026 | Stop exact controller and descendants | User-authorized termination | Broad job-name kill | Confirm clearance once | Termination authorization required | SRC-010:202–203 |
| CONTROL-027 | Completion requires successful Snakemake, outputs, children | Completion claim | New verifier requirements/markers/control flow from extra checks | Declared outputs and successful child completion | UNKNOWN / UNKNOWN | SRC-010:207–210 |
| CONTROL-028 | Distinguish execution states; one status snapshot | Status | Independent scanner/ledger/verifier; unrequested polling | Representative errors and requested outputs | Stop polling at stable PEND/RUN unless requested/new evidence | SRC-010:212–219 |

### cosi-runner

| control_id | Exact/near-exact instruction | Trigger; allowed action | Forbidden action | Required validation | Stop / clarification | Evidence |
|---|---|---|---|---|---|---|
| CONTROL-029 | Every kept submission from complete visible `bsub <<'LSF'` cell | Kept COSI submission | Dry-run stage, out-of-band audit, wrapper/controller/alternative path | Complete notebook command | UNKNOWN / UNKNOWN | SRC-011:12 |
| CONTROL-030 | Identify exact scientific/run contract | Start run | Old-checkout executables/symlinks to avoid required local implementation | Read AGENTS/YAML/Snakefile/profile/SoS | Shared defect change needs user authorization | SRC-011:32–41 |
| CONTROL-031 | Reuse one copied operator notebook | Run lifecycle | Separate phase/retry notebooks; executing template directly | Replace all template specifics; save job receipts | No execution before adaptation | SRC-011:45–62 |
| CONTROL-032 | Commands literal/minimal; activate correct runtime | Submission | Hidden command generators/wrappers; unsupported duplicate driver aliases | Inspect workflow if driver-scoped aliases required | UNKNOWN / UNKNOWN | SRC-011:66–78 |
| CONTROL-033 | One YAML per output graph | Configuration | Pair slots, YAML J overrides, force options, extra controllers/parallel format | Preserve keys/types/semantics and specified retained settings | User changes scientific contract explicitly | SRC-011:82–103 |
| CONTROL-034 | Show exact contract before first submission when not explicit | First submission | Production outside authorized graph/endpoint | Run root, notebook, YAML, prerequisites, counts, target, environment, queue, edits shown | Prepare-only request stops before `bsub`; missing contract details shown to user | SRC-011:107–116 |
| CONTROL-035 | Native dependency for running prerequisite munger | Missing/in-flight prerequisite | Dry-run controller or separate review stage | Retain munger job ID | COSI dependency `done(MUNGER_JOB_ID)` | SRC-011:120–131 |
| CONTROL-036 | Same production cell, without force | Resume | Deleting/overwriting scientific outputs to manufacture clean run | Follow receipt → accounting/log → rule → task → output | Resume original endpoint after smallest confirmed repair | SRC-011:135–145 |
| CONTROL-037 | Use declared isolation and coloc-derived weight union | Retained rerun | Parallel failure ledger | Native `failed_genes.tsv` when workflow requires | UNKNOWN / UNKNOWN | SRC-011:147–152 |
| CONTROL-038 | One live snapshot, native logs, declared outputs | Completion/status | Extra auditor/scanner/ledger/verifier/controller unless requested | Native evidence | Stop polling at stable pending/running unless monitoring requested | SRC-011:156–158 |
| CONTROL-039 | Exactly one declared endpoint per configured pair | Pair-completion graph | Calling recorded weight failures complete | Schema-valid nonempty INTACT or legitimate `.no_coloc_hits`; all units/products resolved | Incomplete coverage must be reported | SRC-011:160–167 |
| CONTROL-040 | Only requested aggregation from canonical results | Aggregation | Unrelated audit suite | Stated thresholds/legacy comparison | UNKNOWN / UNKNOWN | SRC-011:169–175 |
| CONTROL-041 | Do not paste shell submission into notebook afterward | Kept submission | Out-of-band submission; copied rules; unauthorized force/termination/deletion; silent scientific changes | UNKNOWN | Explicit authorization for listed destructive/force actions | SRC-011:179–186 |
| CONTROL-042 | Notebook valid nbformat; every bash cell passes syntax check | Pre-delivery | UNKNOWN | `bash -n` after removing magic line; valid notebook JSON | UNKNOWN / UNKNOWN | SRC-011:190–198 |

## G. Evidence gaps

1. **Top-level workspace Git history:** The visible xqtl `.git` directory was not accepted as a Git repository. Both ordinary Git discovery and explicit `--git-dir` inspection failed. Its commit history was not recovered. Nested `xqtl-protocol` history was accessible.

2. **Coverage:** This package covers the inspected sources and session windows above. It is not a complete enumeration of every historical session or task in the workspace.

3. **Installed-skill chronology:** fungen-operator contains two inspected commits. Imported archived files do not, by themselves, establish their original creation dates, deployment dates, or which task loaded them.

4. **Original skill versions:** Exact active skill hashes remain UNKNOWN for most workflow tasks. Session references to a skill name do not establish the full loaded instruction text.

5. **Bulk scientific data:** Not scanned. No participant-level data were extracted.

6. **Handoff assertions:** Job states, artifact counts, edits, and user requirements appearing only in handoffs remain attributed to those handoffs.

7. **Session completeness:** Selected messages and tool calls were extracted. Complete mutation/submission/validation command lists were not reconstructed for the long August execution session.

8. **Two-fit execution details:** The addition patch, later acknowledgment, revert references, removed-flag error report, and new submission receipt were recovered. All original second-fit submission receipts and individual child stderr files were not separately recovered.

9. **Cleanup:** The exact removal command was supplied historically; user execution and the complete resulting deletion set remain UNKNOWN. “with all these trash gone” is preserved as a user statement, not filesystem verification.

10. **Validation versus receipt:** Notebook submission receipts establish acceptance. A `<<Job is finished>>` notebook message alone was not converted into a successful dry-run result.

11. **Current notebook chronology:** Notebook cell order was not used to infer historical execution order. MESA recovery cells and their narrative contain different job IDs; exact execution times were not reconstructed.

12. **Current runner application:** The runner controls are extracted as current reference text. They were not assigned retroactively to earlier tasks or evaluated against them.

13. **Other imported skills:** Git establishes addition of the additional 16 skill directories. Complete instruction-level histories and associated tasks for all of them were not recovered.

14. **Archived reviews:** Critiques and proposed changes were not converted into historical execution events. Their original sessions and proof of application remain UNKNOWN.

15. **Negative search boundary:** The absence of literal `slop` applies only to the searched handoffs and archived review documents, not all workspace history.

16. **Memory provenance:** Memory was used to find original sessions. Historical records above cite inspected source evidence; memory-only interpretations were not adopted as findings.

<oai-mem-citation>
<citation_entries>
MEMORY.md:2806-2841|note=[located original shared workflow and cleanup sessions]
MEMORY.md:2778-2782|note=[located AIDA execution and skill update session]
MEMORY.md:670-688|note=[located cleanup and PC selection planning session]
</citation_entries>
<rollout_ids>
01a0273f-ea29-7312-823c-4074f06e2c29
01a02780-5b2a-7bf3-93c5-0cc6ccf120b3
01a027bc-a92b-70f3-876e-72c725f96af2
</rollout_ids>
</oai-mem-citation>
