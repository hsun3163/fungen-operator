# Container validation — round 2, 2026-10-21

Status: **required local acceptance PASS**, including the fresh Mamba RNA chain. Pixi has the optional upstream installation failure documented below. This record replaces the obsolete round-1 Ollama architecture blocker. No registry publication or push is part of this round.

## Pinned payload and build

- Base: **ollama/ollama:0.40.6**, the latest official release resolved for this round; published 2026-10-16. [Official release](https://github.com/ollama/ollama/releases/tag/v0.40.6).
- Bundled host Codex: **0.155.1**; existing **0.162.1** is retained. A newer client was tested during tool-startup diagnosis and was not needed.
- Host Python: **3.12.13**; uv: **0.13.4**. The offline operator wheel and dependencies are installed with bundled uv.
- Scientific environment: Python **3.11.13**, Snakemake **7.32.4**, R **4.5.1**, TensorQTL **1.0.10**, pecotmr **0.9.3**, pinned Miniforge **26.7.2-0**. The environment YAML pins direct packages; the bundled explicit lock records 790 package URLs and hashes.
- Upstream xQTL: **f66555213b5deeb68d347690493b694de923ef4d**, Snakemake entrypoint `code/snakemake`.

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

A fresh environment exposed a missing runtime dependency constraint: the YAML-only solve selected susieR 0.14.2, while pecotmr 0.9.3 requires at least 0.16.4. The working environment and existing explicit lock use **0.16.6**. The YAML now pins it, and the installer uses the complete **790-package hash lock** for native create/install operations. Changing either specification invalidates the software stamp. A fresh prefix installed from that lock and passed every runtime import check (job **277611572 DONE**); the failed unlocked prefix remains for evidence. The subsequent delivered-image sequence uses this new prefix, source checkout and newly generated fixture.

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


## Scope and evidence

The specification was corrected to record the resolved pins, local-only acceptance, prepared-input reference boundary, frozen synthetic criterion and upstream interface patch. Section 7 publishing remains out of scope. No registry or git push occurred. The initial untracked portable MESA design document is preserved without adding it to these commits.

Evidence folder: [~/sunh14_project/fungen-operator/temp_reference/container_round2](http://127.0.0.1:30548/lab/tree/sunh14_project/fungen-operator/temp_reference/container_round2)

Final index: [~/sunh14_project/fungen-operator/temp_reference/container_round2/acceptance-final.json](http://127.0.0.1:30548/lab/tree/sunh14_project/fungen-operator/temp_reference/container_round2/acceptance-final.json)

Executed setup notebook: [~/sunh14_project/fungen-operator/temp_reference/container_round2/release/first-task/xqtl/setup.ipynb](http://127.0.0.1:30548/lab/tree/sunh14_project/fungen-operator/temp_reference/container_round2/release/first-task/xqtl/setup.ipynb)

This single validation record and the consolidated acceptance JSON index are the review entrypoints. Native transcripts, notebooks and child logs remain together beneath that evidence folder. OpenAI device-code transcripts need not be opened to verify the bounded no-credential checks.
