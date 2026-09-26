# MWS-01: 500-sample behavioral MWE

Revision **2**, authorized on 2026-09-25, uses `output/sketch_to_plink1/behavioral_fixture_500/`. It requests canonical phenotype chromosome partitioning for **chr22**, preserving **16 phenotypes and 500 samples**. The endpoint is an indexed BED plus chromosome and region manifests.

The supplied fixture contains 20,000 variants, 40 phenotypes, and 12 covariates. Its first 500 original-order synthetic samples were selected consistently across PLINK, phenotype, and covariate files. Native PLINK and exact stored-value comparisons verified every selected genotype/allele and trait value, sample alignment, tabix retrieval, and preservation of the parent files. Fixture creation job **270415437** completed successfully. The header is **7,518 bytes**; the longest phenotype line is **7,657 bytes**. See [the retained preparation command](../experiments/sketch_to_plink1/RUN.md#500-sample-behavioral-mwe-2026-09-25).

This is a behavioral data-preparation case. The parent's fixed-bin genotype scientific-fidelity limits apply. Association and fine-mapping are separate benchmark endpoints.

## Author setup and operator execution

The benchmark author supplies the initial dataset configuration specified in [the task](tasks/regression/MWS-01.yaml). The operator adopts it with MCP `prepare_config`. Each fresh trial saves its own `task.yaml` and hash, so later benchmark revisions preserve earlier trial contracts.

Through an approved LSF job with 32 GB, run:

```bash
env PYTHONPATH=/sc/arion/projects/load/users/sunh14/fungen-operator/src /sc/arion/work/sunh14/conda/envs/xqtl-r-base-fsusie/bin/python benchmark/mws01.py prepare --trial reference_500_20260925
```

The setup refuses an existing trial directory. It writes `config.yaml`, `requests.json`, `task.yaml`, and `task.sha256` under `runs/xqtl/benchmarks/mws01/<trial>/`.

Use the connected MCP tools with the exact request objects in `requests.json`:

1. `prepare_config`, then its exact approved host command.
2. `check_readiness`, then its exact approved host command; require `ready`.
3. `initiate_run`, then its exact approved host command; retain the native receipt.
4. After the controller ends, `check_readiness` with the `conclusion` request; require `nothing_to_do`.
5. Verify the notebook and run the grader through LSF.

Every host command and scheduler operation uses the approved host execution path. The canonical Snakefile, rules, notebook, R worker, runtime, and LSF profile are reused. The controller uses `express` with 32 GB; the registered canonical profile selects the outer workflow rule's queue and resources.

## Grade and validate

Submit these commands through LSF with 32 GB and retain their logs:

```bash
env PYTHONPATH=/sc/arion/projects/load/users/sunh14/fungen-operator/src /sc/arion/work/sunh14/conda/envs/xqtl-r-base-fsusie/bin/python -m pytest -q tests/test_mws01.py tests/test_identity.py
env PYTHONPATH=/sc/arion/projects/load/users/sunh14/fungen-operator/src /sc/arion/work/sunh14/conda/envs/xqtl-r-base-fsusie/bin/python -m fungen_operator verify runs/xqtl/benchmarks/mws01/reference_500_20260925/operator.ipynb
env PYTHONPATH=/sc/arion/projects/load/users/sunh14/fungen-operator/src /sc/arion/work/sunh14/conda/envs/xqtl-r-base-fsusie/bin/python benchmark/mws01.py grade --trial reference_500_20260925
```

The grader compares decompressed and indexed data to the selected source rows, validates both manifests, checks protected input/source/configuration state, and checks the recorded native lifecycle. Tests cover changed values/sample headers, missing BED/index, incorrect or duplicate manifests, unauthorized chromosome changes, source identity, and isolation of earlier trial revisions.

Unrecorded external actions require separate trajectory review. A passing development reference establishes case solvability; scored autonomous trials remain separate work.

## Current reference status

**Revision 2 reference: PASS.** The fixture, native workflow, notebook, and all three grader groups passed. [Machine-readable grade](evidence/20260925/reference_500/grade.json) retains the result. The full operator notebook remains on the cluster at `runs/xqtl/benchmarks/mws01/reference_500_20260925/operator.ipynb`.

| Step | LSF job | Result |
|---|---:|---|
| Prepare and verify 500-sample fixture | 270415437 | Successful; genotype calls/alleles, sample order, trait values, index, and parent hashes verified |
| Grader/source-identity regression tests | 270415450 | 10 passed in 2.79 seconds |
| Prepare fresh trial configuration | 270415452 | Successful |
| Native readiness | 270415482 | DONE, synchronous exit 0, ready |
| Canonical reference controller / rule | 270415490 / 270415491 | Successful; 1 of 1 steps completed |
| Conclusion readiness | 270415505 | DONE, synchronous exit 0, nothing_to_do |
| Reference grader | 270415509 | G1, G2, and G3 all pass; joint_pass=true |
| Final notebook verification | 270415510 | All active cells re-render identically |

G1 verifies the complete chr22 BED, its index, both manifests, **500 samples**, and **16 phenotypes**: all **8,000 phenotype values** match the supplied data. G2 verifies protected input/source/configuration state and retained action bindings. G3 verifies `materialized -> ready -> submitted -> nothing_to_do`. The shared reader's implementation and runtime buffer setting were retained.

Review complete: the declared 500-sample endpoint and required native evidence are satisfied. This is a passing development reference; autonomous agent-trial scoring remains subsequent benchmark work.

## OSS repeat: 2026-09-25

A fresh revision 2 trial driven by **`qwen3.8-flash-next:125b-a6b-q4_K_M`** through `codex exec --oss --ephemeral` passed the functional contract: **G1, G2, G3, and notebook verification**. The live client arguments confirmed Ollama and the exact model. The OSS worker materialized configuration, obtained `ready`, submitted the canonical workflow, recorded `nothing_to_do`, and submitted notebook verification. The parent prepared the initial trial and independently graded it.

Native jobs: readiness **270472274**; controller **270472474** and child **270472483**; conclusion **270472540**; notebook verification **270472546**; independent grader **270472556**. The controller completed in 68 seconds; the child completed both SoS steps in 17 seconds. All 8,000 selected phenotype values were preserved.

See the [trial review](evidence/20260925/oss_500/review.md), [grade](evidence/20260925/oss_500/grade.json), and [driver provenance](evidence/20260925/oss_500/driver.json).

**Completed naturally with exit code 0; trajectory review found an execution-policy exception.** The worker performed some product validation directly on the login host before successful LSF reruns, despite the explicit requirement that validation use LSF with at least 32 GB. It also recovered from unsupported tool names, an invalid cell ID, and two extra shell-check errors. The readiness gate remained intact. This is a functional pass for one case, with full policy compliance unproven and one observed violation. No parent interruption occurred. The shared model server prevents a controlled speed comparison. The raw grader retains its historical `kind: reference_validation`; driver provenance distinguishes the OSS trial.

## Revision 1 history

[Revision 1](tasks/history/MWS-01.v1.yaml) used 10,000 samples. Its trial remains at `runs/xqtl/benchmarks/mws01/reference_20260924/`, with the original task now saved as `task.yaml`. Its nine validation tests, readiness job **270207713**, and notebook verification **270208967** passed. Controller **270208827** and child **270208950** exited with code 1: the phenotype reader could not fit the **150,018-byte header** into its **131,072-byte** connection buffer. The indexed BED and manifests were absent. This was a failed reference execution.

The 500-sample revision applies the user-selected MWE size to a fresh fixture and trial. The shared phenotype reader and runtime buffer setting retain their canonical implementation.

Earlier MCP staging also encountered long source-fingerprint scans of the canonical checkout's untracked software environment. The non-source filename filter precedes filesystem checks in the current harness; the canonical source identity remains enforced. Validation uses the shared xQTL runtime because the login-node `/tmp` MCP environment is unavailable on compute nodes.
