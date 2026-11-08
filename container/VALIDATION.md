# Container validation

Status: **round-5 / Release 2 rebuilt-image acceptance PASS**, with **696 frozen host tests passed, 0 failed/skipped**. Source **9910940bbd0ffbcb0095bc9381a3284d7c7ed1d5**. Native XS acceptance and all requested local S/XS interactive checks passed; task services and test terminals are stopped. The GHCR package is public. Current details are in the round-5 section at the end; earlier sections are historical.

## Pinned payload and build

- Base: **ollama/ollama:0.40.6**, the latest official release resolved for this round; published 2026-10-16. [Official release](https://github.com/ollama/ollama/releases/tag/v0.40.6).
- Bundled host Codex: **0.155.1**; existing **0.162.1** is retained. A newer client was tested during tool-startup diagnosis and was not needed.
- Host Python: **3.12.13**; uv: **0.13.4**. The offline operator wheel and dependencies are installed with bundled uv.
- Scientific environment (current source, 2026-11-06): Python **3.11.13**, Snakemake **7.32.4**, R **4.5.1**, TensorQTL **1.0.10**, pecotmr **0.9.5**, pinned Miniforge **26.7.2-0**. The environment YAML pins direct packages; the bundled explicit lock records 800 package URLs and hashes.
- Upstream xQTL (current source, 2026-11-06): **e1095f6354da6a4d2c43ef812eeb099a19fe93d2**, Snakemake entrypoint `code/snakemake`.

The Minerva build reuses the allowlisted context, user-namespace `unshare`/chroot installer, local Docker archive and Singularity 3.11 `docker-archive://` conversion. No Docker daemon or registry push is involved. Runtime home isolation uses `--home`, not `--env HOME`. The context excludes models, personal data, credentials and caches; historical personal path examples are replaced with portable placeholders.

The SIF installs Python, the operator wheel, its skill and a launcher onto the host. It only runs model acquisition and the GPU model service. Codex, the MCP operator and workflow scheduler clients execute on the host. The launcher refuses image-contained Codex and workflow entrypoints. Existing Codex configuration is preserved; local settings use the install's separate Codex home. The PATH line requires an explicit yes.

Final image: [~/sunh14_project/OLLAMA/images/round2/current/fungen-operator-ollama0.40.6-codex0.155.1.sif](http://127.0.0.1:30548/lab/tree/sunh14_project/OLLAMA/images/round2/current/fungen-operator-ollama0.40.6-codex0.155.1.sif)

- Size: **3,632,717,824 bytes** (3.63 GB; 3.38 GiB).
- SHA256: `1313bdc6a2200ada57a5d12eee5d4d9a0b75baaecda3e5d0341c7ccb9b468ad7`.
- Bundled source: **9482b52**; final native build **277611569 DONE**.
- Full final in-image suite: **402 passed in 58.13 seconds**, native job **277611584 DONE**. Focused setup regressions: **47 passed**.
- Native GPFS executable-mapping regression: **277597777 PASS**; native PCA identity regression: **277596531 PASS**.

## Native model and setup evidence

The clean-home installations use real PTYs and empty working folders under the stranger scratch root. Staged models are bound read-only. Ollama 0.40.6 successfully loads both the staged Laguna S GGUF and a freshly downloaded official Laguna XS Q4 model on H100 GPUs, answers the connectivity prompt through host Codex, and reports positive GPU offload. Both local installations pass every one of the 11 `fungen check` rows.

**Staged-store provenance:** the existing alias `laguna-s-2.1:q4_K_M` reports a 117.6B **Q8_0** payload in model metadata. It is reused unchanged, not relabeled as a fresh Q4 download. Its GPU allocation uses two H100s. The freshly pulled XS is 33.4B **Q4_K_M**, with a 20,274,300,032-byte model blob, and uses one H100.

Ollama's old-manifest migration requires a writable manifest overlay. The installer copies manifests to its own runtime folder and links the original blobs, retaining the original store read-only. The advanced 262144 context option creates a Modelfile variant and passed native creation with a writable XS store. Ollama refreshes blob timestamps during creation, so a read-only base store is explicitly rejected for that advanced option. Full 256k-context inference was not tested.

The real interrupted-download test retained 22 partial files and 5,553,268,224 allocated bytes. Two empty native progress records initially caused EOF. The repair archives malformed metadata, reconstructs the exact pinned Ollama partition descriptors, preserves valid completed chunks and blob bytes, then lets native Ollama resume and verify the complete SHA256. Missing descriptor indices are also reconstructed: native cleanup requires contiguous indices. Corrected native resume job **277597701** completed successfully; the final fresh XS scenario also passed.

Both installed host launchers made a successful real MCP call and completed a native proof job: staged S test **277607743** with child **277611249**, and XS test **277611327** with child **277611411**. The host approver checked the exact returned command before execution, then checked LSF `DONE`, the proof file and notebook verification. XS initially retried the expected approval status; its successful task explicitly states that `host_approval_required` is success and must be returned without retrying. The host acceptance driver now carries that instruction and JSON event logging (commit **ba13176**). This test-driver change is outside the runtime payload built at **9482b52**.

Native Codex displayed `stream closed before response.completed` during both tool conversations. Its bounded automatic reconnects recovered, and the calls completed; this is an observed transport limitation, not an untested no-retry claim. The failed development test and successful retry transcripts are retained separately.

Binary installation is atomic. A native GPFS regression maps the old executable while replacing it, proving that a re-run preserves an already-running client's mapping. The operator connection is marked required with a 60-second startup deadline before a deployment-backed Codex task begins.

## First task: native RNA chain

The frozen fixture was generated de novo with seed **20261020**: **500 artificial participants**, four regions on two chromosomes, 512 variants, six RNA contexts, **24 planted** traits and **24 null** traits. No real individuals or legacy MWEs are used. Before fitting, the code records the criterion: every causal pair has nominal P < 5E-8 in the expected counted-G direction and its causal variant belongs to a 95% SuSiE credible set; at most one null trait crosses the threshold.

**Fresh delivered-image Mamba run: PASS.** All seven notebook cells have execution counts 1–7, and hand-off validates the deployment. Native controller **277611586** completed the first stages; ordinary resume **277612940 DONE** completed the graph and hand-off. The run includes genotype and relatedness QC, unrelated-sample QC, PCA/projection, phenotype preparation, 13 genotype covariate PCs, native hidden factors, TensorQTL cis scans, QtlDataset construction, and five-fold SuSiE/TWAS. **48 nonempty native SuSiE fit RDS files and 48 nonempty weight RDS files** exist. The grader opens native fits and reports **24/24** nominal/direction recoveries, **24/24** credible-set recoveries and **0/24** null calls. A 913-file native product metadata manifest is retained in the acceptance index.

One initial RNA6 KING task was aborted after SoS reported a missing pulse file (rule controller **277612523**, child **277612567 EXIT 137**, 29 MB peak memory). The child was confirmed terminal before the ordinary test-step resume. Completed products and the frozen inputs were retained; no force, task purge or changed recovery threshold was used. The resumed graph completed without another failure. The earlier separate scientific run **277596728** also passed; it is historical support, not the final fresh-run endpoint.

The retained upstream interface patch supplies the current QtlDataset and per-gene SoS arguments, normal SoS execution signatures, LSF integration, and PCA projection IDs derived from PLINK FAM order. It also normalizes FID=IID consistently with the upstream phenotype-ID convention. Statistical calculations remain upstream. A separate native R regression passes three FAM identity conventions and three sample-count mismatch guards (job **277596531**).

During round 2, a fresh environment exposed a missing runtime dependency constraint: the YAML-only solve selected susieR 0.14.2 although the runtime required at least 0.16.4. The round-2 environment and hash lock used **0.16.6**; the fresh-prefix import check passed in job **277611572 DONE**. The current source retains **susieR 0.16.6** for **pecotmr 0.9.5** and uses the expanded **800-package hash lock**. Its new fresh-prefix validation is recorded in the dated 2026-11-06 section below. Changing the YAML, lock or retained SoS pulse repair invalidates the software stamp.

The prepared PLINK/normalized phenotype-BED boundary needs **zero external reference download bytes**: GRCh38 coordinates and synthetic trait annotations are under 100 KB, and LD comes from the fixture genotypes. Optional raw-RNA alignment references are named separately: Ensembl 103 FASTA about 840 MB compressed and GTF about 47 MB compressed. Unused references are not downloaded.

**Pixi: FAIL, optional limitation.** Exactly one clean-home full StatFunGen pixi-setup attempt was made (job **277586939**, upstream commit **5d156cd447df1abaad97ae0d30f52c8b1c0530bc**). Upstream `safe_expose_remove` runs invalid jq `.[].exposed.[].exposed_name`; jq reports a syntax error and exits 3. The wrapper reports failure. The RNA chain was not run with Pixi. Setup, the README and the skill disclose this before the choice. Next step for Pixi is to correct that upstream jq expression and rerun its installation; it does not block Mamba acceptance.

The notebook contains seven confirmed, re-runnable steps, each with predecessor checks and a native log. Its dedicated Fungen Operator kernel uses the installed host Python; native NotebookClient execution passed. Hand-off validates an operator deployment for subsequent harmonized-user-data work, preserving source, interface patch, profile, configuration, software and acceptance provenance. User data paths and scientific choices are requested before that analysis is prepared.

## Final acceptance ledger

| Scenario | Final result | Native evidence |
|---|---|---|
| No host Codex, staged Laguna S reused read-only | **PASS** | Two H100s; Ollama 0.40.6; connectivity response; all 11 checks; installed MCP proof job 277611249 DONE. |
| Fresh Laguna XS Q4 download | **PASS** | Native resumed download and full hash verification; one H100; all 11 checks; installed MCP proof job 277611411 DONE. |
| Existing host Codex | **PASS** | 0.162.1 kept; original user config content unchanged; final edge replay 277601243 DONE. |
| OpenAI backend through sign-in | **PASS** | Real PTY device-auth flow reached; no real credentials supplied; no auth file in image or working folder. |
| No --nv / non-GPU node | **PASS** | GPU-required message supplies the exact GPU-job/--nv/OpenAI fix. |
| Port 11434 occupied | **PASS** | XS server chose and recorded 11435. |
| No network | **PASS** | Refused-proxy test reports offline acquisition/reuse guidance. |
| Completed setup re-run | **PASS** | Config bytes and modification time retained; valid host Codex kept. |
| Interrupted download | **PASS** | Partial bytes retained; native metadata repair and resumed SHA256 verification, job 277597701. |
| Slurm and no-scheduler scripts | **PASS, syntax only** | Both generated and passed bash -n; live execution is LSF only. |
| Guided Mamba first task and hand-off | **PASS, one ordinary resume** | All seven cells executed; 48 fits/48 weights; 24/24 nominal/direction, 24/24 CS, 0/24 null; 277612940 DONE. |

The final edge replay **277601243 DONE** ran from the delivered locked SIF. Earlier failures and successful retries remain together in the evidence folder. Use the consolidated final index rather than historical per-attempt scenario ledgers.

Only this session's test jobs were stopped. The XS server **277603122** was stopped after its operator proof completed. The remaining staged S server **277597292** was stopped after the final edge replay. The earlier failed XS test actor **277609167** was stopped after repeated tool calls made that attempt fail its purpose. Unrelated user jobs, staging_models and minerva_jobs were not modified.


## SGE support and backend switching — 2026-11-05

`fungen backend` (show and switch `local`/`openai`), `fungen codex --backend` and setup's retention of local model settings under `--backend openai` are a source change with unit tests, included in the pending rebuild.

SGE support is added in source: setup detection and the `sge` scheduler choice, `~/.fungen/serve.sge.sh` submitted with `qsub`, and the `profiles/sge` Snakemake profile through the operator's cluster adapter. Unit tests and `bash -n` syntax checks pass for it. Live SGE execution is the remaining validation; Minerva runs LSF, so no SGE cluster was available. The round-2 image predates this change; next step: rebuild and re-run acceptance.

## Field feedback fixes (BU SCC) — 2026-11-06

Source changes with unit tests, included in the pending rebuild:

1. **Home mount check.** Setup requires named shared-storage or verified physical host block-device identity for home/config/install destinations; memory/private/unknown sources stop before installation writes and stops before writing with `Host home/config mount identity is unknown or private. Run: <runtime> run --home $HOME:$HOME <image>` when Singularity/Apptainer runs with home mounting disabled (`--contain` or a site configuration). A chosen install folder outside home must be visible too (`--bind FOLDER:FOLDER`).
2. **Selected-model GPU offload.** The server refuses CPU-only readiness (no GPU, or selected model without positive VRAM after warm-up); partial offload may pass and exclusive GPU inference is unverified, and the serve job fails with the GPU-job/`--nv` fix. Setup on a login host reports that GPU offload remains unverified until the current launch starts and fungen check passes.
3. **`fungen check` runtime verification.** PENDING denotes incomplete verification and the overall NOT VERIFIED result exits nonzero. Run `fungen serve`, then `fungen check`. Runtime checks use the recorded launch/job, endpoint and selected-model GPU observation. Failed status/API retrieval, empty GPU observations and failed jobs remain blocking.
4. **SGE project.** With the `sge` scheduler, setup asks `SGE project (-P) []:` (also `--account`/`FUNGEN_ACCOUNT`), saves it as config `account`, and adds it as `#$ -P` to `serve.sge.sh` and as `-P` to pipeline `qsub` jobs. `fungen xqtl` inherits the launcher's account for a new xQTL root only for the same scheduler; `--account` overrides it. The account default follows the scheduler: `acc_LOAD` for LSF, empty otherwise. The scheduler default is the freshly detected scheduler; a previous answer is the default when detection finds none. `sos.yaml` (the LSF task host) is written for LSF; Slurm and SGE now generate native resource-aware SoS task hosts; local runs tasks in host rule processes. Scheduler-aware handoff/controller rendering and status are host-tested; site-native execution remains unverified for this source revision. The README adds the SGE interactive tip: add `-now no` to `qrsh` to wait for a GPU.
5. **Host suite.** Run `.venv/bin/python -m pytest -q tests` on the host with the root README test environment (htslib, SoS/sos-pbs, host Codex 0.155.1). Required grader tools fail loudly when missing; tests are excluded from the image context. Historical in-image counts above describe the older build and do not validate the current host contract.
6. **Build provenance.** `container/build.py context` refuses when any admitted file differs from HEAD (modified, staged, deleted or untracked), and records HEAD plus copied file hashes in `source.json`. The round-3 context implementation now reads one captured Git tree/blob snapshot and records source blob IDs, retaining dirty-input refusal and testing concurrent HEAD/worktree edits and index-hidden differences.
7. **Distribution.** Images move from the Sylabs Cloud Library (end of life in late October 2026) to GitHub Container Registry through ORAS: `oras://ghcr.io/hsun3163/fungen-operator`, tags `ollama0.40.6-codex0.155.1` and `latest`. The publication of a given build is recorded here.
8. **Local Codex launch.** On the local backend, interactive `fungen codex` selects the Ollama provider before onboarding: it sets `-c model_provider="ollama"` alongside `--oss`. `fungen codex -- exec` is unchanged.
9. **Laguna model catalog.** Setup requires the shipped `<install>/codex/models.json` and pinned host client 0.155.1. It includes exact Q4_K_M/Q8_0 descriptors for both families and 32768/262144 contexts. Local launch validates the current endpoint inventory/quantization/context and supplies an immutable served-ID catalog. Model-facing overrides list only verified served IDs at the session context. Full host request comparisons preserve all base/message/tool assertions and explicitly allow only the changed picker list plus validated invocation identities/timestamps. The isolated endpoint covers both families and presets; live inventory/metadata replay in round 6 verifies only `laguna-s-2.1:q8_0-256k-t2` (Q8_0, 262144), without delegated inference. Other live availability and interactive configurations remain unverified.

The audit-frozen host suite and item-level evidence are recorded in `temp_reference/codex_fix_20261106/report.md`; the round-4 section below records the post-fix suite and rebuilt-image acceptance.

Suite: **669 passed, 0 failed, 0 skipped**, frozen host suite LSF **281314035** (2026-11-07). The 238-file source snapshot remained unchanged throughout; `temp_reference/codex_fix_20261106/round7-suite.json` records exit 0. Fresh guided xQTL acceptance: driver **281314034**, controller **281314225**, **259/259 DONE**, grader **24/24** nominal/direction and **24/24** credible-set recoveries, **0** null calls. Post-fix host rerun: **670 passed, 0 failed, 0 skipped**, LSF **281317242**, 5001.43 seconds. All 240 files remained unchanged across 2,275 freeze checks. Rebuilt-image acceptance **281317523 PASS**; see round 4 below.

**Live SGE validation (previous build).** A BU SCC user ran the previous build on SGE: SGE job submission works, an L40S GPU served the model, and `fungen check` passed 11/11.

**Rebuilt-image validation:** completed in round 4 below.

## Scope and evidence

The specification was corrected to record the resolved pins, local-only acceptance, prepared-input reference boundary, frozen synthetic criterion and upstream interface patch. Section 7 publishing remains out of scope. No registry or git push occurred. The initial untracked portable MESA design document is preserved without adding it to these commits.

Evidence folder: [~/sunh14_project/fungen-operator/temp_reference/container_round2](http://127.0.0.1:30548/lab/tree/sunh14_project/fungen-operator/temp_reference/container_round2)

Final index: [~/sunh14_project/fungen-operator/temp_reference/container_round2/acceptance-final.json](http://127.0.0.1:30548/lab/tree/sunh14_project/fungen-operator/temp_reference/container_round2/acceptance-final.json)

Executed setup notebook: [~/sunh14_project/fungen-operator/temp_reference/container_round2/release/first-task/xqtl/setup.ipynb](http://127.0.0.1:30548/lab/tree/sunh14_project/fungen-operator/temp_reference/container_round2/release/first-task/xqtl/setup.ipynb)

This single validation record and the consolidated acceptance JSON index are the review entrypoints. Native transcripts, notebooks and child logs remain together beneath that evidence folder. OpenAI device-code transcripts need not be opened to verify the bounded no-credential checks.


## pecotmr 0.9.5 workflow update — 2026-11-06

The current source pins xQTL `e1095f6354da6a4d2c43ef812eeb099a19fe93d2`,
pecotmr 0.9.5 and susieR 0.16.6 with the existing 800-package explicit lock.
Historical acceptance rows above describe their dated builds. The new host-only
guided setup and final host suite are recorded in
`temp_reference/codex_workflow_20261106/report.md`.

Sample selection now reaches both analysis workers through the upstream
`susie_twas --keep-samples` interface. The construct worker receives the unfiltered
dataset inputs. The retained SoS 0.25.1 monitor patch keeps its published pulse
path present during startup; native missing-heartbeat failure detection remains
active. A deterministic regression exercises the real SoS monitor and status reader,
reproduces the original false abort and verifies the repair.

`container/onboarding.lsf` installs the explicit lock and applies the same monitor
repair as guided software setup. To regenerate the lock after a pin change, use
`python -m fungen_operator.lock` as documented in README: it overrides configured
channels with the YAML channel order and writes the lock after a successful solve.
The 800-package lock was retained for this update.


**Fresh host guided setup: PASS.** Controller **281128220 DONE** completed all
seven steps on its first attempt: a fresh pinned checkout, fresh 800-package
software prefix, reference contract, scheduler profiles, frozen fixture, native
`xqtl_core` dry-run/execution and validated handoff. The notebook records execution
counts 1–7. All 81 Snakemake steps completed, with **48 nonempty fit RDS files**
and **48 nonempty TWAS-weight RDS files**. The unchanged grader reports **24/24**
nominal/direction recoveries, **24/24** causal variants in 95% credible sets and
**0/24** null crossings. No pulse-file abort or ordinary resume occurred.
The run used `bsub -K` with in-process waiting. Native logs and job receipts are
retained beside the report through its `run/` link. This validates host workflow
execution; image rebuilding/publication remain separate from this run.


**Final host validation:** job **281141052 DONE** ran
`.venv/bin/python -m pytest -q tests`: **587 passed in 118.94 seconds**, zero
failed or skipped. The same job passed the retained PCA/FAM R regression for
three sample-ID conventions and three count-mismatch guards. Focused cause
regressions passed **31 tests** in job **281126926 DONE**. Final native job IDs,
logs, package/patch hashes and frozen grading rows are indexed in
`temp_reference/codex_workflow_20261106/report.md`.

## Round 4 release acceptance — 2026-11-07

Initial committed build `cf8088d4998a483709734c7073e60b77b86ab66b`: base job **281316840**, install/archive/convert job **281316875**, SIF SHA-256 `da128c2fb471ee9a346c5e312232d5c414fcaefd6e04accea3dc2c7b879512a1`, size **3,633,688,576 bytes**. The in-image `/opt/fungen/source.json` matches the pushed source commit.

Initial XS acceptance driver **281317062 EXIT 1** installed the host bundle, downloaded the fresh official XS Q4 model and started H100 server **281317113**. The server recorded readiness with positive GPU offload, but host Codex launch failed because `/api/show` omitted the optional `parameters` key. The launcher now handles that absence while retaining the requirement for positive loaded or configured context evidence. Regression coverage includes both absent and empty parameters, and rejects both without loaded context. Focused host catalog tests: **25 passed**; the corrected launcher also produced the exact XS entry against the live endpoint. The post-fix host suite and rebuilt-image acceptance passed as recorded below.

### Final round-4 image and acceptance

- Pushed image source: `33730da90f31edaa47a1f5c637f2b011080671c0`; rebuild/update/archive/convert job **281317244 DONE**, using the pinned base from **281316840 DONE**. `/opt/fungen/source.json` and the installed host bundle record the pushed source.
- SIF: [~/sunh14_project/OLLAMA/images/round4/fungen-operator-ollama0.40.6-codex0.155.1.sif](http://127.0.0.1:30548/lab/tree/sunh14_project/OLLAMA/images/round4/fungen-operator-ollama0.40.6-codex0.155.1.sif). Size: **3,633,692,672 bytes**. SHA-256: `2ced4e06a33fdb0d0adf9b059402f2261b7a64594213ca257196552f69b84380`.
- Required full host rerun: **281317242 DONE**, **670 passed in 5001.43 seconds**, **0 failed/skipped**. The 240-file snapshot remained unchanged throughout 2,275 monitor checks. Focused build-context tests: **11 passed**; publisher protocol/CLI checks: **5 passed**; actionlint passed; focused catalog tests: **25 passed**. Tests and Codex ran on the host.
- Clean-home production-path acceptance: driver **281317523 DONE**, GPU model service **281317582**, node **lg07c01**. The SIF installed the host bundle, host Codex returned `FUNGEN_AGENT_CONNECTED`, the selected XS Q4 model reported **20,543,805,849 GPU VRAM bytes** at **32768 tokens**, and **12/12 `fungen check` rows passed**, ending `VERIFIED`. The generated production serve script remained unchanged.
- Retained second attempt: driver **281317447 EXIT 1**, H100 service **281317459**. Host Codex and GPU offload passed, then the strict asset check correctly rejected the legacy `--h100` acceptance option's edits to generated resource/walltime directives. The final required acceptance used the ordinary generated script, preserving the integrity guard. Both failed attempts and the successful attempt remain recorded.
- All build/test/acceptance batch drivers were awaited in process with `bsub -K`. The final model service remains the verified running endpoint, with the production script's native walltime limit.

Release evidence: [~/sunh14_project/fungen-operator/temp_reference/codex_release_20261107/report.md](http://127.0.0.1:30548/lab/tree/sunh14_project/fungen-operator/temp_reference/codex_release_20261107/report.md). Later validation-only commits change this excluded record; the SIF retains the exact pushed image source commit above.

### Round-4 distribution verification

Both `oras://ghcr.io/hsun3163/fungen-operator:ollama0.40.6-codex0.155.1` and `:latest` were published through `container/publish.py`. Authenticated manifest/tag-list checks and cache-disabled native Singularity pulls passed for each tag. Both registry manifest digests are `sha256:e7ca90b67f150e388ec103021eae06a9f7bb1152c2d6b2e5375fbb678ee05747`; each pulled SIF matches SHA-256 `2ced4e06a33fdb0d0adf9b059402f2261b7a64594213ca257196552f69b84380`. The package API confirms **private** visibility after publishing.

The same SIF replaced only `cosi_drive:fungen-operator/fungen-operator-ollama0.40.6-codex0.155.1.sif`. `rclone check` found **1 matching file, 0 differences**. Remote size is **3,633,692,672 bytes**, SHA-256 matches the built image, and MD5 is `015b458d85962128b9e97f1fc70454f5`.

Owner steps: [make the package public in its settings](https://github.com/users/hsun3163/packages/container/fungen-operator/settings) when ready; optionally grant `hsun3163/fungen-operator` **Write** under **Manage Actions access** for future CI publication. Package visibility and repository settings were preserved throughout this release.


## Round 5 / Release 2 acceptance — 2026-11-07

**PASS.** Source commit **9910940bbd0ffbcb0095bc9381a3284d7c7ed1d5** was fast-forward pushed before building. The embedded and both installed host source.json records match that pushed context. Image: [~/sunh14_project/OLLAMA/images/round5/fungen-operator-ollama0.40.6-codex0.155.1.sif](http://127.0.0.1:30548/lab/tree/sunh14_project/OLLAMA/images/round5/fungen-operator-ollama0.40.6-codex0.155.1.sif)

Size **3,633,700,864 bytes**; SHA-256 **3f6ff0ee3dbd5fb8b76c25c87e5006c752c759604c5e5ade96769ddf90d4117f**. Native build jobs **281377907 DONE** (pinned base) and **281378158 DONE** (install/archive/SIF conversion), using container/build.lsf in a new round5 folder. The 63-file context was captured from the pushed commit.

| Acceptance | Native result |
| --- | --- |
| Pre-release gate | Round-2 host suite **281365521**, **696 passed, 0 failed/skipped**; 242-file before/after/current snapshot equal; zero changes in 2401 monitoring checks. Read-only 37-hunk hiding audit **APPROVE**. |
| Existing native acceptance.py XS path | Driver **281378735 DONE**, service **281380131**, node **lg05e17**. Image installer and exact XS Q4 download/reuse path; host Codex answered **FUNGEN_AGENT_CONNECTED**; **13/13** health checks PASS, positive GPU offload and 32768 context. No optional H100/busy-port script modifications. |
| Image installer and host setup | Real tmux PTY, isolated scratch HOME; installer exit 0 and every host setup prompt exercised, host setup exit 0 using the copied bundle. Installed bootstrap bytes match source. No source overlay/PYTHONPATH override. |
| Before/after serve | Fresh check exits 1 with PENDING runtime rows; after service readiness and XS warm-up, **13/13 PASS / VERIFIED**, exit 0, including the exact launch catalog validator. |
| Two-model service | **281380467**, **lg03e10**, two H100 80 GB GPUs; unmodified native script uses shared CUDA process mode and job-exclusive reservation, explicit residency=2. Exact S Q4 and XS Q4 at **32768** context, GPU VRAM **97,185,924,378** and **20,543,805,849 bytes**, respectively. S retains its true mixed Q4_K/Q8_0 payload and Q8_0 global header, accepted only through exact official identity pins. |
| Local composer and actual answer | Codex **0.155.1** local S Q4 trust/composer; no sign-in screen or metadata warning. Real shell tool wrote/read a three-line README; native assistant answered **RELEASE2_README_OK**. Independent file hash **3862e8d872d429229cfd810094f66b5742323061105a0b011a41e9e41b609050**. Ordinary client update-available notice retained. |
| Both model choices and real delegation | Parent **01a1b8e1-c456-7c22-85a1-7e927775e15d** listed both exact served IDs. Spawned XS **01a1b8e5-49b9-7133-ae69-940c5da6db91**, fork_context=false; actual child model is XS, answered **XS_CHILD_RELEASE2_OK**, parent waited and closed it. Native CUDA request/response evidence retained. |
| Backend round trip | Saved local → openai → local switches and status pass; unsigned OpenAI onboarding inspected and exited 0. Returned local composer answered **LOCAL_RETURN_RELEASE2_OK**. All saved local config values preserved; both auth.json paths absent. |
| Fake SGE guide | Fresh isolated guide detects **sge**, renders scheduler and empty project prompts; test-before-workflow and non-empty-root refusals both exit 1 with exact errors. These are fake-client prompt/guard checks. Live SGE/qrsh at BU remains unverified on Minerva. |
| Clean exits and jobs | Both local TUI exits and unsigned OpenAI exit **0**; child closed; all four tmux shell PIDs and server PID gone. Only own services **281380131** and **281380467** were bkill'ed, awaited in-process, and confirmed **EXIT 130**. All three build/acceptance CPU jobs finished DONE. No watcher armed. |

Evidence: [~/sunh14_project/fungen-operator/temp_reference/codex_release2_20261107/report.md](http://127.0.0.1:30548/lab/tree/sunh14_project/fungen-operator/temp_reference/codex_release2_20261107/report.md) . Screens: [~/sunh14_project/fungen-operator/temp_reference/codex_release2_20261107/screens/](http://127.0.0.1:30548/lab/tree/sunh14_project/fungen-operator/temp_reference/codex_release2_20261107/screens/) . Native session/tool evidence: [~/sunh14_project/fungen-operator/temp_reference/codex_release2_20261107/session-evidence.json](http://127.0.0.1:30548/lab/tree/sunh14_project/fungen-operator/temp_reference/codex_release2_20261107/session-evidence.json) . GPU native log: [~/sunh14_project/fungen-operator/temp_reference/codex_release2_20261107/interactive-server.log](http://127.0.0.1:30548/lab/tree/sunh14_project/fungen-operator/temp_reference/codex_release2_20261107/interactive-server.log) .

Retained execution diagnostics: my first installer invocation used unsupported --gpus 2 and exited at parsing before setup; ordinary native prompts then passed. The SGE observer initially expected Software manager instead of the actual Package manager label. Bounded loading/response observations expired while native work continued; later completed outputs and actual assistant response formatting were inspected. No source/test/guard was changed for these observations. The report retains exact earlier path/startup errors as well. No functional image acceptance failed, and no test was skipped or weakened.

GHCR and single-file Drive delivery verification for this exact SIF is recorded in the Release 2 report. Older validation sections describe their dated images.
